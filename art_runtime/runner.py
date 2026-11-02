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


def report(stage, completed=None, total=None):
    event = {"stage": stage}
    if completed is not None:
        event.update(completed=completed, total=total)
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
                else ["config.json", "preprocessor_config.json", "model.safetensors"] if name in ("safety", "pose")
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
    mask = Image.fromarray(np.uint8(np.clip((mask - mask.min()) / span, 0, 1) * 255)).resize(image.size, Image.Resampling.LANCZOS)
    bounds = mask.point(lambda value: 255 if value > 50 else 0).getbbox()
    if bounds is None or (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]) < image.width * image.height * .03:
        raise WorkerError("art_cutout_failed")
    image = image.convert("RGBA")
    image.putalpha(mask)
    image = image.crop(bounds)
    # Fixed aspect canvas makes persisted mouth coordinates stable for the renderer.
    image.thumbnail((920, 920), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (1024, 1024))
    canvas.alpha_composite(image, ((1024 - image.width) // 2, 972 - image.height))
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
    composed = "Single original full-body chibi character, isolated on white background, " + prompt
    report("art_sampling", 0, 30)
    with torch.inference_mode():
        output = pipe(prompt=composed,
                      negative_prompt="nsfw, nude, sexual, gore, logo, text, watermark, signature, cropped, frame, multiple characters",
                      height=size, width=size, num_inference_steps=30, guidance_scale=7,
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
    rig = make_rig(image, cache)
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return {"png": base64.b64encode(buffer.getvalue()).decode("ascii"), "model": name, "seed": seed,
            "seconds": round(time.monotonic() - started, 1), "peak_allocated_mib": peak, "rig": rig}


def make_rig(image, cache):
    try:
        from pose import suggest
        return suggest(image, snapshot("pose", cache))
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
                    for index, name in enumerate((PRESETS[args.tier][0], "safety", "cutout", "pose")):
                        report("art_downloading", index, 4)
                        snapshot(name, args.cache, download=True)
                    report("art_downloading", 4, 4)
                    result = {"ready": True}
                elif args.action == "prepare-motion":
                    report("art_pose_downloading", 0, 1)
                    snapshot("pose", args.cache, download=True)
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
                            rig = make_rig(image, args.cache)
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
