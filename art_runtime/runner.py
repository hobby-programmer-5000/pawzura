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

    # Split touching multi-view turnaround figures (e.g., front + back views whose hands/cuffs touch across a narrow bridge).
    h_img, w_img = alpha.shape
    for _ in range(3):
        fg_tmp, n_tmp = label(alpha > 0.14)
        split_any = False
        for cid in range(1, n_tmp + 1):
            ys, xs = np.where(fg_tmp == cid)
            if len(ys) < int(h_img * w_img * 0.06):
                continue
            y0, y1 = int(ys.min()), int(ys.max())
            x0, x1 = int(xs.min()), int(xs.max())
            hc, wc = y1 - y0 + 1, x1 - x0 + 1
            if hc < int(h_img * 0.38) or wc < int(hc * 0.50):
                continue
            sub_m = (fg_tmp[y0 : y1 + 1, x0 : x1 + 1] == cid)
            col_full = sub_m.sum(axis=0).astype(np.float32)
            head_h = max(8, int(hc * 0.32))
            col_head = sub_m[:head_h, :].sum(axis=0).astype(np.float32)
            margin_x = max(8, int(wc * 0.18))
            if wc <= 2 * margin_x + 8:
                continue
            best_vx = -1
            best_v_ratio = 1.0
            for vx in range(margin_x, wc - margin_x):
                if col_head[vx] > hc * 0.26:
                    continue
                left_peak = float(col_full[:vx].max()) if vx > 0 else 0.0
                right_peak = float(col_full[vx + 1 :].max()) if vx + 1 < wc else 0.0
                if min(left_peak, right_peak) < hc * 0.50:
                    continue
                v_ratio = (float(col_full[vx]) + 0.35 * float(col_head[vx])) / max(1.0, min(left_peak, right_peak))
                if v_ratio < 0.56 and v_ratio < best_v_ratio:
                    best_v_ratio = v_ratio
                    best_vx = vx
            if best_vx >= 0:
                cut_x = x0 + best_vx
                alpha[y0 : y1 + 1, max(0, cut_x - 2) : min(w_img, cut_x + 3)] = 0.0
                split_any = True
        if not split_any:
            break

    fg_comp, n_fg = label(alpha > 0.14)
    if n_fg > 1:
        cy_img, cx_img = 0.5 * h_img, 0.5 * w_img
        sigma_c = 0.48 * max(h_img, w_img)
        counts = np.bincount(fg_comp.ravel())
        counts[0] = 0
        best_id = 1
        best_score = -1.0
        for cid in range(1, n_fg + 1):
            if counts[cid] < 32:
                continue
            ys, xs = np.where(fg_comp == cid)
            y0, y1 = int(ys.min()), int(ys.max())
            x0, x1 = int(xs.min()), int(xs.max())
            hc, wc = max(1, y1 - y0 + 1), max(1, x1 - x0 + 1)
            dy = float(ys.mean()) - cy_img
            dx = float(xs.mean()) - cx_img
            spatial_w = float(np.exp(-(dx * dx + dy * dy) / (2.0 * sigma_c * sigma_c)))
            aspect = float(wc) / float(hc)
            aspect_w = 1.0 if (0.26 <= aspect <= 0.52 and hc >= int(h_img * 0.42)) else 0.28
            # Penalize fused 2-headed turnaround blobs that have a bimodal crown notch in the top 18% or wide dual-head span.
            crown_h = max(6, int(hc * 0.18))
            col_crown = (fg_comp[y0 : y0 + crown_h, x0 : x1 + 1] == cid).sum(axis=0).astype(np.float32)
            head_band = fg_comp[y0 : y0 + int(hc * 0.30), x0 : x1 + 1] == cid
            head_xs = np.where(head_band.any(axis=0))[0]
            head_span_ratio = float(head_xs[-1] - head_xs[0] + 1) / float(hc) if len(head_xs) >= 2 else 0.0
            two_head_w = 0.15 if head_span_ratio > 0.43 else 1.0
            if wc > 24:
                c_margin = max(4, int(wc * 0.22))
                for cvx in range(c_margin, wc - c_margin):
                    lc = float(col_crown[:cvx].max()) if cvx > 0 else 0.0
                    rc = float(col_crown[cvx + 1 :].max()) if cvx + 1 < wc else 0.0
                    if min(lc, rc) >= crown_h * 0.45 and float(col_crown[cvx]) < 0.55 * min(lc, rc):
                        two_head_w = 0.12
                        break
            # Frontal face/eye contrast prior strictly in the head zone (above collar/chest) so cream jackets on back views never mimic face skin.
            fy0, fy1 = y0 + int(hc * 0.10), y0 + int(hc * 0.27)
            fx0, fx1 = x0 + int(wc * 0.24), x0 + int(wc * 0.76)
            face_bonus = 1.0
            if fy1 > fy0 + 4 and fx1 > fx0 + 4:
                f_mask = fg_comp[fy0:fy1, fx0:fx1] == cid
                f_fill = float(f_mask.mean())
                if f_fill < 0.18:
                    face_bonus = 0.20
                else:
                    f_rgb = rgb[fy0:fy1, fx0:fx1][f_mask]
                    f_lum = 0.299 * f_rgb[:, 0] + 0.587 * f_rgb[:, 1] + 0.114 * f_rgb[:, 2]
                    lum_span = float(np.percentile(f_lum, 92) - np.percentile(f_lum, 8)) if len(f_lum) >= 8 else 0.0
                    dark_eye_frac = float((f_lum < 0.28).mean())
                    skin_like = float(((f_rgb[:, 0] > 0.62) & (f_rgb[:, 0] > f_rgb[:, 1] * 1.03) & (f_rgb[:, 1] > f_rgb[:, 2] * 1.04) & ((f_rgb[:, 0] - f_rgb[:, 2]) > 0.08)).mean())
                    has_eyes_and_skin = 2.20 if (dark_eye_frac >= 0.020 and skin_like >= 0.14) else 0.35
                    face_bonus = has_eyes_and_skin * (1.0 + 1.15 * np.clip(lum_span, 0.0, 0.75) + 1.25 * skin_like)
            score = float(counts[cid]) * spatial_w * aspect_w * two_head_w * float(face_bonus)
            if score > best_score:
                best_score = score
                best_id = cid
        main_mask = fg_comp == best_id
        main_area = max(1, int(counts[best_id]))
        dist_to_main = distance_transform_edt(~main_mask)
        keep_fg = np.zeros(n_fg + 1, dtype=bool)
        keep_fg[best_id] = True
        for cid in range(1, n_fg + 1):
            if cid == best_id or counts[cid] < 24:
                continue
            # Only keep tiny nearby silhouette tufts (e.g., hair/ear tips <= 8px from main body), never detached secondary bodies/props.
            if counts[cid] <= int(main_area * 0.06) and float(dist_to_main[fg_comp == cid].min()) <= 8.0:
                keep_fg[cid] = True
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
    prefix = "1person, " if prompt.lower().startswith("solo ") else "solo, 1person, centered single chibi character looking at viewer, full-body standing on plain white background. "
    composed = prefix + prompt
    report("art_sampling", 0, 32)
    with torch.inference_mode():
        output = pipe(prompt=composed,
                      negative_prompt="multiple characters, 2girls, 2boys, 2views, 3views, front and back, turnaround, character sheet, reference sheet, multiple views, back view, from behind, outfit breakdown, split screen, duo, pair, twins, group, clone, nsfw, nude, sexual, gore, logo, text, watermark, signature, cropped, half body, bust, portrait, upper body only, cowboy shot, holding object, holding weapon, holding book, holding scroll, holding rose, hands in pockets, crossed arms, crossed legs, frame, border, furniture, bookshelf, wall, room, background scenery, collage, montage, comic panels, duplicate bodies, portrait insets, floating head, pedestal, base, plinth, stand, platform, podium, ground shadow, drop shadow, floor shadow, shadow under feet, grey floor, ground plane, gradient background, blurry face, muddy colors, low contrast",
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
