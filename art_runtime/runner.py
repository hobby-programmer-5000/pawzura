"""Optional trusted image worker. JSON stdin/stdout; never executes generated data."""
import argparse
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import time

os.environ.update(HF_HUB_DISABLE_TELEMETRY="1", HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
                  DO_NOT_TRACK="1", TOKENIZERS_PARALLELISM="false",
                  HF_HUB_DOWNLOAD_TIMEOUT="120", HF_HUB_DISABLE_SYMLINKS_WARNING="1")
CATALOG = json.loads(Path(__file__).with_name("catalog.json").read_text(encoding="utf-8"))
PRESETS = {2: ("sd15", 384, True), 4: ("sd15", 512, False),
           6: ("sdxl", 768, True), 8: ("sdxl", 1024, False)}


class WorkerError(Exception):
    pass


def report(stage, completed=None, total=None, **extra):
    event = {"stage": stage}
    if completed is not None:
        event.update(completed=completed, total=total)
    if extra:
        for k, v in extra.items():
            if isinstance(v, (str, int)) and (not isinstance(v, str) or len(v) <= 128):
                event[k] = v
    print("PAWZURA_PROGRESS " + json.dumps(event), file=sys.__stderr__, flush=True)


def sampling_progress(pipeline, step, timestep, callback_kwargs):
    report("art_sampling", step + 1, len(pipeline.scheduler.timesteps))
    if step + 1 == len(pipeline.scheduler.timesteps):
        report("art_decoding")
    return callback_kwargs


def snapshot(name, cache, download=False):
    from huggingface_hub import snapshot_download
    model = CATALOG[name]
    patterns = (["*.json", "*.txt", "*.fp16.safetensors"] if name in ("sd15", "sdxl")
                else ["config.json", "preprocessor_config.json", "model.safetensors"] if (name == "safety" or name.startswith("pose"))
                else ["u2netp.onnx"])
    for attempt in range(2 if download else 1):
        try:
            return snapshot_download(model["repo"], revision=model["revision"], cache_dir=str(cache),
                                     allow_patterns=patterns, local_files_only=not download, token=False)
        except OSError as error:
            status = getattr(getattr(error, "response", None), "status_code", None)
            if not download or attempt or status in (400, 401, 403, 404):
                if download:
                    raise WorkerError("art_download_failed") from None
                raise
            # One bounded retry resumes a partial network download, not generation.
            time.sleep(2)


def detected_vram_gb():
    """Return installed CUDA device total VRAM in GiB, or 0.0 when CPU-only."""
    try:
        import torch
        if torch.cuda.is_available():
            return float(torch.cuda.get_device_properties(0).total_memory) / (1024 ** 3)
    except Exception:
        pass
    return 0.0


def pose_candidates(vram_gb=None, tier=None):
    """Return ordered pose model catalog keys matched to GPU VRAM and chosen tier."""
    if tier is not None and tier < 8:
        return ("pose",)
    vram = detected_vram_gb() if vram_gb is None else float(vram_gb)
    if vram >= 11.5:
        return ("pose_huge", "pose_large", "pose")
    if vram >= 7.0:
        return ("pose_large", "pose")
    return ("pose",)


def pose_key_for_vram(vram_gb=None, tier=None):
    """Return primary pinned pose model catalog key for the active VRAM tier."""
    return pose_candidates(vram_gb=vram_gb, tier=tier)[0]


def resolve_pose_snapshot(cache, tier=None):
    """Return (snapshot_path, catalog_key) for the best locally cached pose model."""
    last_error = None
    for key in pose_candidates(tier=tier):
        if key not in CATALOG:
            continue
        try:
            return snapshot(key, cache, download=False), key
        except OSError as error:
            last_error = error
    if last_error is not None:
        raise last_error
    return snapshot("pose", cache, download=False), "pose"


def scan(image, cache):
    """Additional CPU classifier; unavailable or ambiguous means rejection."""
    import torch
    from transformers import ViTForImageClassification, ViTImageProcessor
    path = snapshot("safety", cache)
    processor = ViTImageProcessor.from_pretrained(path, local_files_only=True)
    model = ViTForImageClassification.from_pretrained(path, local_files_only=True, use_safetensors=True)
    with torch.inference_mode():
        probabilities = model(**processor(images=image.convert("RGB"), return_tensors="pt")).logits.softmax(-1)[0]
    scores = {str(model.config.id2label[i]).lower(): float(value) for i, value in enumerate(probabilities)}
    if scores.get("normal", 0) < .95 or scores.get("nsfw", 1) > .05:
        raise WorkerError("art_output_blocked")


def strip_exterior_floor_shadow(rgb_arr, alpha, bg_rgb=None, extra_neutral_luma=0.78, extra_max_alpha=0.38):
    """Flood-fill from the image border to drop exterior paper mist and neutral bottom cast shadows."""
    import numpy as np
    from scipy.ndimage import label

    out = alpha.astype(np.float32, copy=True)
    rgb = rgb_arr.astype(np.float32)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    luma = rgb.mean(axis=2)

    fg_y, _ = np.where(out > 0.25)
    bottom_zone = np.zeros_like(out, dtype=bool)
    if len(fg_y) >= 16:
        y_top, y_bot = int(fg_y.min()), int(fg_y.max())
        y_cut = int(y_bot - 0.16 * max(1, y_bot - y_top))
        bottom_zone[max(0, y_cut):, :] = True

    cand = (out < 0.08) | (bottom_zone & (sat < 0.085) & (luma > 0.34) & (out < 0.80))
    if bg_rgb is not None:
        bg_dist = np.linalg.norm(rgb - bg_rgb[None, None, :], axis=2)
        cand |= (sat < 0.07) & (luma > extra_neutral_luma) & (bg_dist < 0.18) & (out < extra_max_alpha)

    comp, n_comp = label(cand)
    if n_comp > 0:
        border_ids = np.unique(np.concatenate([comp[0, :], comp[-1, :], comp[:, 0], comp[:, -1]]))
        border_ids = border_ids[border_ids > 0]
        if len(border_ids):
            out[np.isin(comp, border_ids)] = 0.0
    return out


def clean_cutout_rgba(rgb_arr, alpha_raw):
    """Strip exterior paper mist, bottom ground-shadow slabs, detached shadow crumbs, and halo color bleed."""
    import numpy as np
    from scipy.ndimage import binary_fill_holes, distance_transform_edt, label

    rgb = rgb_arr.astype(np.float32)
    raw = np.clip(alpha_raw.astype(np.float32), 0.0, 1.0)
    border = np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]], axis=0)
    bg_rgb = np.median(border, axis=0)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    bg_dist = np.linalg.norm(rgb - bg_rgb[None, None, :], axis=2)

    # Strip exterior paper mist & neutral floor cast shadows against raw u2netp confidence BEFORE ramping.
    cleaned_raw = strip_exterior_floor_shadow(rgb, raw, bg_rgb=bg_rgb, extra_neutral_luma=0.82, extra_max_alpha=0.35)
    alpha = np.clip((cleaned_raw - 0.18) / (0.72 - 0.18), 0.0, 1.0)

    # Seal any interior alpha dropout pocket enclosed inside ink outlines (e.g., white sleeve highlights).
    filled = binary_fill_holes(alpha > 0.25)
    interior_holes = filled & (alpha < 0.90)
    if interior_holes.any():
        alpha[interior_holes] = 1.0

    fg_comp, n_fg = label(alpha > 0.12)
    if n_fg > 1:
        counts = np.bincount(fg_comp.ravel())
        counts[0] = 0
        main_area = int(counts.max())
        keep_fg = counts >= max(48, int(main_area * 0.025))
        keep_fg[0] = True
        alpha = np.where(keep_fg[fg_comp], alpha, 0.0)

    solid = alpha >= 0.88
    if solid.any():
        dist_solid, near_rc = distance_transform_edt(~solid, return_indices=True)
        near_rgb = rgb[near_rc[0], near_rc[1]]
        fringe = (alpha > 0.0) & (alpha < 0.85) & (dist_solid <= 6.0) & ((bg_dist < 0.30) | (sat < 0.09))
        if fringe.any():
            blend = np.clip((0.85 - alpha[fringe]) / 0.85, 0.25, 1.0)[:, None]
            rgb[fringe] = rgb[fringe] * (1.0 - blend) + near_rgb[fringe] * blend

    return np.clip(rgb, 0.0, 1.0), np.clip(alpha, 0.0, 1.0)


def cutout(image, cache):
    import numpy as np
    import onnxruntime as ort
    from PIL import Image
    session = ort.InferenceSession(str(Path(snapshot("cutout", cache)) / "u2netp.onnx"),
                                   providers=["CPUExecutionProvider"])
    pixels = np.asarray(image.convert("RGB").resize((320, 320)), dtype=np.float32) / 255
    pixels = (pixels - np.array([.485, .456, .406], dtype=np.float32)) / np.array([.229, .224, .225], dtype=np.float32)
    mask = session.run(None, {session.get_inputs()[0].name: pixels.transpose(2, 0, 1)[None]})[0][0, 0]
    span = float(mask.max() - mask.min())
    if span < .01:
        raise WorkerError("art_cutout_failed")
    mask_img = Image.fromarray(np.uint8(np.clip((mask - mask.min()) / span, 0, 1) * 255)).resize(image.size, Image.Resampling.LANCZOS)
    alpha_raw = np.asarray(mask_img, dtype=np.float32) / 255.0
    rgb_clean, alpha_clean = clean_cutout_rgba(np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0, alpha_raw)
    mask = Image.fromarray(np.rint(alpha_clean * 255.0).astype(np.uint8))
    bounds = mask.point(lambda value: 255 if value > 32 else 0).getbbox()
    if bounds is None or (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) < image.width * image.height * .03:
        raise WorkerError("art_cutout_failed")
    rgba_uint8 = np.dstack([np.rint(rgb_clean * 255.0), np.rint(alpha_clean * 255.0)]).astype(np.uint8)
    cut = Image.fromarray(rgba_uint8, "RGBA").crop(bounds)
    # Fixed aspect canvas makes persisted mouth coordinates stable for the renderer.
    cut.thumbnail((920, 920), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (1024, 1024))
    canvas.alpha_composite(cut, ((1024 - cut.width) // 2, 972 - cut.height))
    return canvas


def generate(tier, cache, payload):
    report("art_loading")
    import torch
    from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline
    if not torch.cuda.is_available():
        raise WorkerError("art_gpu_required")
    started = time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    prompt = payload.get("prompt")
    seed = payload.get("seed")
    if not isinstance(prompt, str) or not 20 <= len(prompt) <= 2000 or type(seed) is not int or not 0 <= seed < 2**31:
        raise WorkerError("art_invalid_request")
    name, size, sequential = PRESETS[tier]
    pipeline_class = StableDiffusionPipeline if name == "sd15" else StableDiffusionXLPipeline
    pipe = pipeline_class.from_pretrained(snapshot(name, cache), torch_dtype=torch.float16,
                                          variant="fp16", use_safetensors=True, local_files_only=True)
    pipe.set_progress_bar_config(disable=True)
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()
    if sequential:
        pipe.enable_sequential_cpu_offload()
        pipe.enable_attention_slicing("max")
    else:
        pipe.enable_model_cpu_offload()
    composed = "solo, 1person, single full-body chibi character only, front view, isolated on pure white background, crisp clean shading. " + prompt
    report("art_sampling", 0, 32)
    with torch.inference_mode():
        output = pipe(prompt=composed,
                      negative_prompt="nsfw, nude, sexual, gore, logo, text, watermark, signature, cropped, frame, multiple characters, 2girls, 2boys, duo, pair, 2characters, multiple people, two people, twins, group, clone, companion, character sheet, reference sheet, turnaround sheet, multiple views, multiple poses, collage, montage, comic panels, duplicate bodies, portrait insets, pedestal, base, plinth, stand, platform, podium, ground shadow, drop shadow, floor shadow, shadow under feet, grey floor, ground plane, gradient background, blurry face, muddy colors, low contrast",
                      height=size, width=size, num_inference_steps=32, guidance_scale=7.5,
                      callback_on_step_end=sampling_progress,
                      generator=torch.Generator("cpu").manual_seed(seed))
    if any(getattr(output, "nsfw_content_detected", None) or []):
        raise WorkerError("art_output_blocked")
    image = output.images[0]
    peak = torch.cuda.max_memory_allocated() // (1024 * 1024)
    del pipe, output
    torch.cuda.empty_cache()
    report("art_scanning")
    scan(image, cache)
    report("art_cutting")
    image = cutout(image, cache)
    report("art_rigging")
    rig = make_rig(image, cache, tier=tier)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"png": base64.b64encode(buffer.getvalue()).decode("ascii"), "model": name, "seed": seed,
            "seconds": round(time.monotonic() - started, 1), "peak_allocated_mib": peak, "rig": rig}


def make_rig(image, cache, tier=None):
    try:
        from pose import suggest
        pose_path, _ = resolve_pose_snapshot(cache, tier=tier)
        return suggest(image, pose_path)
    except Exception:
        # Geometry is optional. Never bypass content checks or lose valid artwork
        # just because a helper cannot estimate a non-human/occluded limb.
        return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "generate", "check", "prepare-motion", "rig"))
    parser.add_argument("--tier", type=int, choices=PRESETS, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--accept-model-license", action="store_true")
    args = parser.parse_args()
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if args.action == "check":
                import torch
                result = {"cuda": torch.cuda.is_available(), "torch": torch.__version__}
            else:
                if not args.accept_model_license:
                    raise WorkerError("art_license_required")
                if args.action == "prepare":
                    pose_key = pose_key_for_vram(tier=args.tier)
                    model_labels = {
                        PRESETS[args.tier][0]: f"SD 1.5 ({PRESETS[args.tier][0]})" if "sd15" in PRESETS[args.tier][0] else f"SDXL ({PRESETS[args.tier][0]})",
                        "safety": "Safety Checker",
                        "cutout": "Cutout (u2netp)",
                        pose_key: f"ViTPose ({pose_key.replace('_', ' ')})",
                    }
                    for index, name in enumerate((PRESETS[args.tier][0], "safety", "cutout", pose_key)):
                        report("art_downloading", index, 4, item_name=model_labels.get(name, name))
                        snapshot(name, args.cache, download=True)
                    report("art_downloading", 4, 4)
                    result = {"ready": True}
                elif args.action == "prepare-motion":
                    pose_key = pose_key_for_vram(tier=args.tier)
                    report("art_pose_downloading", 0, 1, item_name=f"ViTPose ({pose_key.replace('_', ' ')})")
                    snapshot(pose_key, args.cache, download=True)
                    report("art_pose_downloading", 1, 1)
                    result = {"ready": True}
                else:
                    limit = 12 * 1024 * 1024 if args.action == "rig" else 16384
                    raw = sys.stdin.buffer.read(limit + 1)
                    if len(raw) > limit:
                        raise WorkerError("art_invalid_request")
                    payload = json.loads(raw)
                    if args.action == "rig":
                        from PIL import Image
                        data = base64.b64decode(payload["png"], validate=True)
                        if len(data) > 8 * 1024 * 1024:
                            raise WorkerError("art_invalid_request")
                        with Image.open(io.BytesIO(data)) as image:
                            if not 16 <= image.width <= 1024 or not 16 <= image.height <= 1024:
                                raise WorkerError("art_invalid_request")
                            report("art_rigging")
                            rig = make_rig(image, args.cache, tier=args.tier)
                        if rig is None:
                            raise WorkerError("art_pose_unavailable")
                        result = {"rig": rig}
                    else:
                        result = generate(args.tier, args.cache, payload)
        print(json.dumps(result))
        return 0
    except Exception as error:
        # Never echo prompts, absolute paths, access tokens or backend tracebacks.
        code = str(error) if isinstance(error, WorkerError) else (
            "model_memory_error" if "out of memory" in str(error).lower() else "art_runtime_failed")
        print(json.dumps({"error": code}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
