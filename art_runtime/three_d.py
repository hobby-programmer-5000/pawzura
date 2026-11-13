"""Pinned TripoSR -> optional sequential SDXL view refiner -> CPU ViTPose -> articulated geodesic/DQS rig -> baked PNG clips.

Each invocation performs one stage and exits. No GUI, generated code, persisted prompt, or close API.
"""
import os
os.environ.update(
    OPENBLAS_NUM_THREADS="4",
    OMP_NUM_THREADS="4",
    HF_HUB_DISABLE_TELEMETRY="1",
    HF_HUB_DISABLE_IMPLICIT_TOKEN="1",
    TOKENIZERS_PARALLELISM="false",
)
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from urllib.request import urlopen
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "motion_catalog.json").read_text())
SOURCES = json.loads((HERE / "triposr-sources.json").read_text())

EXTRA_VIEW_ANGLES = {
    "facing_right": 270.0,
    "facing_left": 90.0,
    "back": 180.0,
    "right_3q": 315.0,
    "left_3q": 45.0,
}


def report(stage, completed=None, total=None):
    data = {"stage": stage}
    if completed is not None:
        data.update(completed=completed, total=total)
    print("PAWZURA_PROGRESS " + json.dumps(data), file=sys.stderr, flush=True)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(cache):
    from huggingface_hub import hf_hub_download
    report("motion_downloading", 0, 3)
    for index, key in enumerate(("triposr", "dino_config")):
        item = CATALOG[key]
        for name, sha in item["files"].items():
            p = Path(hf_hub_download(item["repo"], name, revision=item["revision"], cache_dir=cache / "hf", token=False))
            if digest(p) != sha:
                raise RuntimeError("motion_download_failed")
        report("motion_downloading", index + 1, 3)
    from runner import pose_key_for_vram, snapshot
    snapshot(pose_key_for_vram(), cache, download=True)
    source = cache.parent / "motion-source" / "triposr"
    for name, sha in SOURCES["files"].items():
        p = source / name
        # Original files are immutable; adapted optional imports go in a separate tree.
        if not p.is_file() or digest(p) != sha:
            url = f"https://raw.githubusercontent.com/{SOURCES['repo']}/{SOURCES['revision']}/{name}"
            with urlopen(url, timeout=30) as response:
                data = response.read(512 * 1024 + 1)
            if len(data) > 512 * 1024 or hashlib.sha256(data).hexdigest() != sha:
                raise RuntimeError("motion_download_failed")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
    adapted = cache.parent / "motion-source" / "adapted"
    for name in SOURCES["files"]:
        data = (source / name).read_bytes()
        if name == "tsr/models/isosurface.py":
            text = data.decode().replace("from torchmcubes import marching_cubes\n", "")
            text = text.replace("self.mc_func: Callable = marching_cubes", "from torchmcubes import marching_cubes\n        self.mc_func: Callable = marching_cubes")
            data = text.encode()
        elif name == "tsr/utils.py":
            text = data.decode().replace("import rembg\n", "")
            text = text.replace("image = rembg.remove(image, session=rembg_session, **rembg_kwargs)", "import rembg\n        image = rembg.remove(image, session=rembg_session, **rembg_kwargs)")
            data = text.encode()
        p = adapted / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    record = {
        "version": 1,
        "source_revision": SOURCES["revision"],
        "adaptations": "Defer unused rembg/torchmcubes imports; own extraction used",
        "files": {name: digest(adapted / name) for name in SOURCES["files"]},
    }
    (adapted / "provenance.json").write_text(json.dumps(record, indent=2))
    report("motion_downloading", 3, 3)


def model_path(key, name, cache):
    from huggingface_hub import hf_hub_download
    item = CATALOG[key]
    p = Path(hf_hub_download(item["repo"], name, revision=item["revision"], cache_dir=cache / "hf", local_files_only=True, token=False))
    if digest(p) != item["files"][name]:
        raise RuntimeError("motion_not_prepared")
    return p


def _view_schedule(quality_mode):
    """Multi-elevation spherical camera schedule keeping equatorial view-0..7 compatible."""
    if quality_mode in ("high_multiview", "sdxl_multiview"):
        rings = ((0.0, 24, 1.15), (22.0, 6, 0.90), (-16.0, 6, 0.85))
    else:
        rings = ((0.0, 16, 1.15), (22.0, 4, 0.90), (-16.0, 4, 0.85))
    return rings


def _clean_bottom_cast_shadow(rgba):
    """Strip exterior-connected floor shadows using the shared runner boundary helper."""
    from runner import strip_exterior_floor_shadow

    out = rgba.astype("float32", copy=True)
    out[:, :, 3] = strip_exterior_floor_shadow(out[:, :, :3], out[:, :, 3])
    return out


def _load_extra_ref_views(job, payload):
    import numpy as np
    from PIL import Image
    ref_views = []
    # High-resolution original front artwork strongly anchors front facial & outfit clarity even in standard 24-view mode.
    orig_rgba = _clean_bottom_cast_shadow(np.asarray(Image.open(job / "source.png").convert("RGBA"), dtype=np.float32) / 255.0)
    ref_views.append({"rgba": orig_rgba, "az": 0.0, "el": 0.0, "weight": 11.0})
    for key, az_deg in EXTRA_VIEW_ANGLES.items():
        if key not in (payload.get("extra_views") or {}):
            continue
        p = job / f"extra_{key}.png"
        if p.is_file():
            rgba = _clean_bottom_cast_shadow(np.asarray(Image.open(p).convert("RGBA"), dtype=np.float32) / 255.0)
            ref_views.append({"rgba": rgba, "az": az_deg, "el": 0.0, "weight": 4.0})
    return ref_views


def reconstruct(cache, job, payload=None):
    import numpy as np
    from PIL import Image
    import torch
    from motion_geometry import (
        extract,
        fair_mesh_taubin,
        compute_vertex_normals,
        project_multiview_colors,
        bake_texture_atlas,
        classify_art_texture,
        inflate_2_5d_mesh,
    )

    payload = payload or {}
    quality_mode = payload.get("quality_mode", "standard")
    source = cache.parent / "motion-source" / "adapted"
    record = json.loads((source / "provenance.json").read_text())
    if record.get("source_revision") != SOURCES["revision"] or any(digest(source / name) != sha for name, sha in record["files"].items()):
        raise RuntimeError("motion_not_prepared")
    if not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory < 7.5 * 1024**3:
        raise RuntimeError("motion_gpu_required")
    if torch.cuda.mem_get_info()[0] < 2.5 * 1024**3:
        raise RuntimeError("model_memory_error")
    sys.path.insert(0, str(source))
    from tsr.system import TSR
    from tsr.utils import resize_foreground, get_spherical_cameras

    report("motion_reconstructing")
    config = model_path("triposr", "config.yaml", cache)
    model_path("triposr", "model.ckpt", cache)
    dino = model_path("dino_config", "config.json", cache)
    torch.set_num_threads(4)
    torch.cuda.reset_peak_memory_stats()
    with patch("tsr.models.tokenizers.image.hf_hub_download", return_value=str(dino)):
        model = TSR.from_pretrained(str(config.parent), "config.yaml", "model.ckpt")
    model.renderer.set_chunk_size(4096)
    model.to("cuda").eval()

    raw_rgba = _clean_bottom_cast_shadow(np.asarray(Image.open(job / "source.png").convert("RGBA"), dtype=np.float32) / 255.0)
    shading_style, style_metrics = classify_art_texture(raw_rgba[:, :, :3], raw_rgba[:, :, 3])
    cleaned_src = Image.fromarray(np.rint(np.clip(raw_rgba, 0.0, 1.0) * 255.0).astype(np.uint8), "RGBA")
    rgba = np.asarray(resize_foreground(cleaned_src, 0.85)).astype(np.float32) / 255
    image = Image.fromarray(np.round((rgba[:, :, :3] * rgba[:, :, 3:4] + (1 - rgba[:, :, 3:4]) * 0.5) * 255).astype(np.uint8))
    image.save(job / "reference.png")
    with torch.inference_mode():
        scene = model([image], device="cuda")
    if not torch.isfinite(scene).all():
        raise RuntimeError("motion_reconstruction_failed")

    rings = _view_schedule(quality_mode)
    total_views = sum(r[1] for r in rings)
    view_specs = []
    done_views = 0
    render_side = 256
    report("motion_views", 0, total_views)

    with torch.inference_mode():
        for el_deg, n_az, weight in rings:
            rays_o, rays_d = get_spherical_cameras(n_az, el_deg, 1.9, 40, render_side, render_side)
            for i in range(n_az):
                rgb = model.renderer(model.decoder, scene[0], rays_o[i].cuda(), rays_d[i].cuda()).cpu().numpy()
                if not np.isfinite(rgb).all():
                    raise RuntimeError("motion_reconstruction_failed")
                az_deg = i * 360.0 / n_az
                view_specs.append({"rgb": rgb, "az": az_deg, "el": el_deg, "dist": 1.9, "fovy": 40.0, "weight": weight})
                # Preserve canonical 8 equatorial preview images view-0..7.png for stage contract.
                if abs(el_deg) < 1e-3 and i % (n_az // 8) == 0:
                    slot = i // (n_az // 8)
                    Image.fromarray(np.round(np.clip(rgb, 0, 1) * 255).astype(np.uint8)).save(job / f"view-{slot}.png")
                done_views += 1
                report("motion_views", done_views, total_views)

        # Query 128^3 density grid in Z-slices so peak CUDA allocation stays <= ~2.1 GiB on 8 GB cards.
        radius = float(model.renderer.cfg.radius)
        vertices = faces = points = None
        for n in (128, 112, 96):
            axis = np.linspace(-radius, radius, n, dtype=np.float32)
            density = np.empty((n, n, n), dtype=np.float32)
            gx, gy = np.meshgrid(axis, axis, indexing="ij")
            slice_step = 8
            for z0 in range(0, n, slice_step):
                z1 = min(n, z0 + slice_step)
                gz = axis[z0:z1]
                grid = np.stack([
                    np.broadcast_to(gx[:, :, None], (n, n, z1 - z0)),
                    np.broadcast_to(gy[:, :, None], (n, n, z1 - z0)),
                    np.broadcast_to(gz[None, None, :], (n, n, z1 - z0)),
                ], axis=-1)
                dens_chunk = model.renderer.query_triplane(
                    model.decoder, torch.from_numpy(grid.reshape(-1, 3)).cuda(), scene[0]
                )["density_act"].cpu().numpy().reshape(n, n, z1 - z0)
                density[:, :, z0:z1] = dens_chunk
            try:
                vertices, faces, points = extract(density, radius)
                grid_n = n
                break
            except ValueError as err:
                if "Surface too large" not in str(err) or n == 96:
                    raise

    # 2.5D Volumetric Inflation: If character has flat 2D anime/cel-shaded texture, or requested,
    # expand collapsed body depth into an anatomical cylinder so it doesn't collapse like a wafer.
    if shading_style == "flat_2d" or payload.get("force_2_5d", False):
        vertices, points = inflate_2_5d_mesh(vertices, faces, points=points)

    vertices = fair_mesh_taubin(vertices, faces, iterations=4, lam=0.45, mu=-0.47, front_weight=0.35)
    normals = compute_vertex_normals(vertices, faces)
    ref_views = _load_extra_ref_views(job, payload)
    vertex_colors = project_multiview_colors(vertices, view_specs, normals=normals, ref_views=ref_views)
    # Also project onto points when surface points differ from vertices (e.g., if legacy tools read points).
    point_colors = project_multiview_colors(points, view_specs, ref_views=ref_views)
    atlas, face_uvs = bake_texture_atlas(vertices, faces, normals, view_specs, ref_views=ref_views)

    np.savez_compressed(
        job / "surface.npz",
        vertices=vertices,
        faces=faces,
        normals=normals,
        points=points,
        vertex_colors=vertex_colors,
        colors=point_colors,
        atlas=atlas,
        face_uvs=face_uvs,
    )
    metrics = {
        "vertices": len(vertices),
        "triangles": len(faces),
        "samples": len(points),
        "grid_n": int(grid_n),
        "views_rendered": total_views,
        "extra_ref_views": len(ref_views) - 1,
        "atlas_size": [int(atlas.shape[1]), int(atlas.shape[0])],
        "peak_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20, 2),
        "shading_style": shading_style,
        "representation": "2.5d_volumetric" if shading_style == "flat_2d" else "3d_mesh",
        "method": f"{'2.5D Volumetric' if shading_style == 'flat_2d' else 'TripoSR 3D'} {total_views}-snapshot multi-elevation + {grid_n}^3 Taubin fairing + overlap-free 6-dir UV atlas",
    }
    (job / "reconstruction.json").write_text(json.dumps(metrics))
    del model, scene
    torch.cuda.empty_cache()


def refine_views(cache, job, payload=None):
    """Optional sequential SDXL multi-view texture detail pass run after TripoSR exits."""
    import numpy as np
    from PIL import Image
    import torch
    from runner import snapshot
    from motion_geometry import project_multiview_colors, bake_texture_atlas
    from motion_bake import render_mesh

    payload = payload or {}
    if not torch.cuda.is_available() or torch.cuda.get_device_properties(0).total_memory < 7.5 * 1024**3:
        raise RuntimeError("motion_gpu_required")
    if torch.cuda.mem_get_info()[0] < 2.5 * 1024**3:
        raise RuntimeError("model_memory_error")

    with np.load(job / "surface.npz", allow_pickle=False) as surf:
        vertices = surf["vertices"]
        faces = surf["faces"]
        normals = surf["normals"]
        points = surf["points"]
        vertex_colors = surf["vertex_colors"]
        point_colors = surf["colors"]
        old_atlas = surf["atlas"] if "atlas" in surf else None
        old_face_uvs = surf["face_uvs"] if "face_uvs" in surf else None

    floor = float(vertices[:, 2].min())
    top = float(vertices[:, 2].max())
    dummy_mouth = np.array([float(vertices[:, 0].max()), 0.0, 0.5 * (floor + top)], dtype=np.float32)

    from diffusers import StableDiffusionXLImg2ImgPipeline
    sdxl_path = snapshot("sdxl", Path(cache), download=False)
    pipe = StableDiffusionXLImg2ImgPipeline.from_pretrained(
        sdxl_path, torch_dtype=torch.float16, variant="fp16", use_safetensors=True, local_files_only=True
    )
    pipe.set_progress_bar_config(disable=True)
    pipe.enable_vae_slicing()
    pipe.enable_vae_tiling()
    if torch.cuda.mem_get_info()[0] < 5.8 * 1024**3:
        pipe.enable_sequential_cpu_offload()
        pipe.enable_attention_slicing("max")
    else:
        pipe.enable_model_cpu_offload()

    angles = [
        ("left_3q", 45.0, "Three-quarter angle view, consistent head shape, fur or hair texture, and clothing colors, crisp clean painted chibi illustration, plain white background."),
        ("right_3q", 315.0, "Three-quarter angle view, consistent head shape, fur or hair texture, and clothing colors, crisp clean painted chibi illustration, plain white background."),
        ("facing_left", 90.0, "Clean side profile view showing head silhouette, sleeve, and clothing edge consistently, crisp painted illustration, plain white background."),
        ("facing_right", 270.0, "Clean side profile view showing head silhouette, sleeve, and clothing edge consistently, crisp painted illustration, plain white background."),
        ("back", 180.0, "Rear back view of head and clothing from behind, facing completely away from viewer, plain white background."),
    ]
    report("motion_refining", 0, len(angles))
    ref_views = _load_extra_ref_views(job, payload)
    user_hint = (payload.get("style_hint") or "").strip()
    base_neg = "extra faces, front face on back of head, pedestal, base, plinth, ground shadow, drop shadow, grey floor, text, logo, watermark, frame, multiple characters, blur, noise"

    seed = int(payload.get("seed", 42))
    for idx, (label, az_deg, angle_desc) in enumerate(angles):
        # render_mesh rotates points by yaw around +Z and views from +X: yaw=-radians(az) places az camera at +X.
        rendered, _ = render_mesh(
            vertices, faces, vertex_colors, normals, -math.radians(az_deg), floor, top, dummy_mouth,
            out_size=512, atlas=old_atlas, face_uvs=old_face_uvs,
        )
        arr = np.asarray(rendered, dtype=np.float32) / 255.0
        alpha = arr[:, :, 3]
        fg = alpha > 0.5
        if int(fg.sum()) < 64:
            report("motion_refining", idx + 1, len(angles))
            continue
        from scipy.ndimage import binary_erosion, distance_transform_edt

        prompt = f"{angle_desc} {user_hint}".strip()[:280]
        neg = f"eyes, mouth, nose, face, {base_neg}" if label == "back" else base_neg
        # Pad silhouette notches with a soft 4-px foreground color fringe before encoding through 8x VAE blocks.
        solid = alpha > 0.85
        if solid.any():
            bg_dist, near_bg = distance_transform_edt(~solid, return_indices=True)
            nearest_fg = arr[:, :, :3][near_bg[0], near_bg[1]]
            fringe = np.clip(1.0 - bg_dist / 4.5, 0.0, 1.0)[:, :, None]
            bg_pad = nearest_fg * fringe + (1.0 - fringe)
            rgb_white = np.clip(arr[:, :, :3] * alpha[:, :, None] + bg_pad * (1.0 - alpha[:, :, None]), 0.0, 1.0)
        else:
            rgb_white = np.clip(arr[:, :, :3] * alpha[:, :, None] + (1.0 - alpha[:, :, None]), 0.0, 1.0)
        init_img = Image.fromarray(np.rint(rgb_white * 255.0).astype(np.uint8), "RGB").resize((768, 768), Image.Resampling.LANCZOS)
        view_strength = 0.24 if "3q" in label else 0.30
        with torch.inference_mode():
            refined = pipe(
                prompt=prompt,
                negative_prompt=neg,
                image=init_img,
                strength=view_strength,
                num_inference_steps=28,
                guidance_scale=5.5,
                generator=torch.Generator("cpu").manual_seed(seed + idx + 1),
            ).images[0].resize((512, 512), Image.Resampling.LANCZOS)
        ref_rgb = np.asarray(refined, dtype=np.float32) / 255.0
        for c in range(3):
            src_fg = arr[fg, c]
            ref_fg = ref_rgb[fg, c]
            std_ratio = float(src_fg.std()) / max(1e-4, float(ref_fg.std()))
            matched = (ref_rgb[:, :, c] - ref_fg.mean()) * min(1.3, max(0.75, std_ratio)) + src_fg.mean()
            ref_rgb[:, :, c] = np.clip(matched, 0.0, 1.0)
        # Reject spurious bright desaturated VAE ringing spikes near silhouette indentations vs source render.
        rim_zone = (alpha > 0.20) & (~binary_erosion(alpha > 0.94, iterations=5))
        ref_lum = ref_rgb.mean(axis=2)
        src_lum = arr[:, :, :3].mean(axis=2)
        ref_sat = ref_rgb.max(axis=2) - ref_rgb.min(axis=2)
        halo_spike = (rim_zone | (src_lum < 0.72)) & ((ref_lum - src_lum) > 0.14) & (ref_sat < 0.12)
        if halo_spike.any():
            ref_rgb[halo_spike] = arr[:, :, :3][halo_spike]
        fg_core = binary_erosion(alpha > 0.90, iterations=3)
        if fg_core.any():
            _, near_rc = distance_transform_edt(~fg_core, return_indices=True)
            ref_rgb = ref_rgb[near_rc[0], near_rc[1]]
        rgba_out = np.concatenate([ref_rgb, alpha[:, :, None]], axis=2)
        ref_views.append({"rgba": rgba_out, "az": az_deg, "el": 0.0, "weight": 2.4})
        report("motion_refining", idx + 1, len(angles))

    del pipe
    torch.cuda.empty_cache()

    # Re-project keeping original front reference dominant + saved base equatorial views so top/crown creases never starve.
    base_views = []
    for slot in range(8):
        vp = job / f"view-{slot}.png"
        if vp.is_file():
            base_views.append({
                "rgb": np.asarray(Image.open(vp).convert("RGB"), dtype=np.float32) / 255.0,
                "az": slot * 45.0,
                "el": 0.0,
                "dist": 1.9,
                "fovy": 40.0,
                "weight": 0.75,
            })
    new_vc = project_multiview_colors(vertices, base_views, normals=normals, ref_views=ref_views)
    blended_vc = np.clip(0.35 * vertex_colors + 0.65 * new_vc, 0.0, 1.0).astype(np.float32)
    new_pc = project_multiview_colors(points, base_views, ref_views=ref_views)
    blended_pc = np.clip(0.35 * point_colors + 0.65 * new_pc, 0.0, 1.0).astype(np.float32)
    new_atlas, new_face_uvs = bake_texture_atlas(vertices, faces, normals, base_views, ref_views=ref_views)
    uvs_match = (
        old_face_uvs is not None
        and new_face_uvs.shape == old_face_uvs.shape
        and float(np.max(np.abs(old_face_uvs - new_face_uvs))) < 1e-4
    )
    if old_atlas is not None and old_atlas.shape == new_atlas.shape and uvs_match:
        blended_atlas = np.rint(np.clip(0.35 * old_atlas.astype(np.float32) + 0.65 * new_atlas.astype(np.float32), 0.0, 255.0)).astype(np.uint8)
    else:
        blended_atlas = new_atlas
    np.savez_compressed(
        job / "surface.npz",
        vertices=vertices,
        faces=faces,
        normals=normals,
        points=points,
        vertex_colors=blended_vc,
        colors=blended_pc,
        atlas=blended_atlas,
        face_uvs=new_face_uvs,
    )


def rig(cache, job, payload):
    import numpy as np
    from PIL import Image
    from runner import CATALOG as ART_CATALOG, resolve_pose_snapshot
    from pose import load_pose_model, predict_pose, release_pose_model
    from motion_geometry import _find_neck_pinch, fit, fit_articulated

    report("motion_rigging")
    path, pose_key = resolve_pose_snapshot(cache)
    pose_model_name = ART_CATALOG.get(pose_key, {}).get("repo", "usyd-community/vitpose-base-simple").split("/")[-1]
    processor, model = load_pose_model(path)
    try:
        image = Image.open(job / "reference.png").convert("RGB")
        width, height = image.size
        keypoints, scores = predict_pose(processor, model, image, [[[0, 0, width, height]]])
        if scores.shape != (17,) or not np.isfinite(keypoints).all() or scores[[5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]].min() < 0.15:
            raise RuntimeError("motion_pose_uncertain")

        with np.load(job / "surface.npz", allow_pickle=False) as data:
            points = data["points"]
            has_mesh = "vertices" in data and "faces" in data
            vertices = data["vertices"] if has_mesh else None
            faces = data["faces"] if has_mesh else None
            vertex_colors = data["vertex_colors"] if "vertex_colors" in data else None

        # Chibi/stylized second pass: if mesh neck-pinch reveals oversized head (or shoulders crushed above neck),
        # re-run ViTPose on a torso-and-lower-face crop normalized toward COCO body proportions.
        keypoint_candidates = [keypoints]
        if has_mesh and vertices is not None and len(vertices) >= 64:
            pinch = _find_neck_pinch(vertices)
            if pinch is not None:
                z_neck, _ = pinch
                focal = 0.5 / math.tan(math.radians(20))
                med_depth = max(0.3, 1.9 - float(np.median(vertices[:, 0])))
                v_neck = 0.5 - z_neck * focal / med_depth
                v_top = 0.5 - float(vertices[:, 2].max()) * focal / med_depth
                v_bot = 0.5 - float(vertices[:, 2].min()) * focal / med_depth
                body_verts = vertices[vertices[:, 2] <= z_neck + float(np.ptp(vertices[:, 2])) * 0.04]
                if len(body_verts) >= 32:
                    u_all = 0.5 + body_verts[:, 1] * focal / np.maximum(0.3, 1.9 - body_verts[:, 0])
                    u_min = max(0.0, float(u_all.min()) - 0.08)
                    u_max = min(1.0, float(u_all.max()) + 0.08)
                else:
                    u_min, u_max = 0.12, 0.88
                sho_v_full = min(float(keypoints[5, 1]), float(keypoints[6, 1]))
                head_frac = (v_neck - v_top) / max(0.05, v_bot - v_top)
                if head_frac > 0.30 or sho_v_full < v_neck - 0.03:
                    body_h = max(0.20, v_bot - v_neck)
                    x_b = int(u_min * width)
                    w_b = max(int(0.30 * width), int((u_max - u_min) * width))
                    y_b = max(0, int((v_neck - 0.37 * body_h) * height))
                    h_b = min(height - y_b, max(int(0.36 * height), int((v_bot + 0.04) * height) - y_b))
                    kp_b, sc_b = predict_pose(processor, model, image, [[[x_b, y_b, w_b, h_b]]])
                    if sc_b.shape == (17,) and np.isfinite(kp_b).all() and sc_b[[5, 6, 11, 12, 15, 16]].min() >= 0.25:
                        cropped_keypoints = keypoints.copy()
                        cropped_keypoints[5:] = kp_b[5:]
                        if sc_b[[0, 1, 2]].min() >= 0.45 and kp_b[1, 1] > v_neck - 0.25:
                            cropped_keypoints[:5] = kp_b[:5]
                        keypoint_candidates = [cropped_keypoints, keypoints]
    finally:
        release_pose_model(model)

    # Transform the approved source mouth point through the same foreground crop/pad.
    original = Image.open(job / "source.png").convert("RGBA")
    alpha = np.asarray(original)[:, :, 3]
    yy, xx = np.where(alpha > 0)
    x1, y1, x2, y2 = xx.min(), yy.min(), xx.max() + 1, yy.max() + 1
    side = max(x2 - x1, y2 - y1)
    padded = int(side / 0.85)
    mouth = [
        (payload["mouth"][0] * original.width - x1 + (side - (x2 - x1)) // 2 + (padded - side) // 2) / padded,
        (payload["mouth"][1] * original.height - y1 + (side - (y2 - y1)) // 2 + (padded - side) // 2) / padded,
    ]

    if has_mesh:
        for cand_keypoints in keypoint_candidates:
            try:
                rig_out = fit_articulated(vertices, faces, cand_keypoints, mouth, colors=vertex_colors)
                save_kwargs = {
                    "bones": rig_out["bones"],
                    "parents": rig_out["parents"],
                    "bone_names": np.asarray(rig_out["bone_names"]),
                    "weights": rig_out["weights"],
                    "joints": rig_out["joints"],
                    "mouth": rig_out["mouth"],
                    "normals": rig_out["normals"],
                    "arm_mobility": rig_out.get("arm_mobility", np.float32(1.0)),
                    "detached_limbs": np.bool_(rig_out.get("detached_limbs", False)),
                    "base_face_count": np.int32(rig_out.get("base_face_count", len(faces))),
                }
                if rig_out.get("detached_limbs", False):
                    save_kwargs["mesh_vertices"] = rig_out["vertices"]
                    save_kwargs["mesh_faces"] = rig_out["faces"]
                    if "colors" in rig_out:
                        save_kwargs["mesh_colors"] = rig_out["colors"]
                np.savez_compressed(job / "rig.npz", **save_kwargs)
                springs = [n for n in rig_out["bone_names"] if n.startswith("spring_")]
                (job / "rig.json").write_text(json.dumps({
                    "backend": "pose-assisted-geodesic-v2",
                    "model": pose_model_name,
                    "minimum_score": round(float(scores.min()), 4),
                    "bones": len(rig_out["bones"]),
                    "springs": springs,
                    "detached_limbs": bool(rig_out.get("detached_limbs", False)),
                    "arm_mobility": round(float(rig_out.get("arm_mobility", 1.0)), 3),
                    "skinning": "mesh-graph-geodesic-heat+dqs",
                    "limits": "Pose-lifted medial humanoid + seam-detached capped limbs + geodesic bone-heat + DQS",
                }))
                return
            except (ValueError, IndexError):
                pass

    for cand_keypoints in keypoint_candidates:
        try:
            bones, weights, joints, mouth3d = fit(points, cand_keypoints, mouth)
            break
        except (ValueError, IndexError):
            pass
    else:
        raise RuntimeError("motion_pose_uncertain") from None
    np.savez_compressed(job / "rig.npz", bones=bones, weights=weights, joints=joints, mouth=mouth3d)
    (job / "rig.json").write_text(json.dumps({
        "backend": "pose-assisted",
        "model": pose_model_name,
        "minimum_score": round(float(scores.min()), 4),
        "bones": len(bones),
        "limits": "Humanoid pose lifting and computed weights; not a learned 3D rigging/facial model",
    }))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "reconstruct", "refine_views", "rig", "bake"])
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    args = parser.parse_args()
    payload = json.load(sys.stdin)
    start = time.monotonic()
    if not isinstance(payload, dict):
        raise RuntimeError("motion_runtime_failed")
    if args.action == "prepare":
        prepare(args.cache)
        names = []
    elif args.action == "reconstruct":
        reconstruct(args.cache, args.job, payload)
        names = ["surface.npz", "reference.png", "reconstruction.json"] + [f"view-{i}.png" for i in range(8)]
    elif args.action == "refine_views":
        refine_views(args.cache, args.job, payload)
        names = ["surface.npz"]
    elif args.action == "rig":
        rig(args.cache, args.job, payload)
        names = ["rig.npz", "rig.json"]
    else:
        from motion_bake import bake
        bake(args.job, payload, report)
        names = ["motion.zip"]
    result = {
        "stage": args.action,
        "seconds": round(time.monotonic() - start, 3),
        "files": [{"name": name, "sha256": digest(args.job / name), "bytes": (args.job / name).stat().st_size} for name in names],
    }
    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        allowed = {
            "motion_not_prepared",
            "motion_download_failed",
            "motion_reconstruction_failed",
            "motion_gpu_required",
            "model_memory_error",
            "motion_pose_uncertain",
        }
        code = str(error)
        if isinstance(error, MemoryError) or "out of memory" in code.lower():
            code = "model_memory_error"
        print(json.dumps({"error": code if code in allowed else "motion_runtime_failed"}))
        raise SystemExit(1)
