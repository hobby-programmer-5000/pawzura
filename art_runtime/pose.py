"""CPU joint estimation and conservative editable hand/foot cutout suggestions."""
import math
from collections import deque


def _component(mask, target):
    import numpy as np
    seen = np.zeros(mask.shape, dtype=bool)
    best, best_score = [], -1
    for y, x in zip(*np.where(mask)):
        if seen[y, x]:
            continue
        queue, points = deque([(int(x), int(y))]), []
        seen[y, x] = True
        while queue:
            px, py = queue.popleft()
            points.append((px, py))
            for nx, ny in ((px - 1, py), (px + 1, py), (px, py - 1), (px, py + 1)):
                if 0 <= nx < mask.shape[1] and 0 <= ny < mask.shape[0] and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True
                    queue.append((nx, ny))
        if len(points) < 6:
            continue
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        score = len(points) / (1 + math.hypot(cx - target[0], cy - target[1]) * .08)
        if score > best_score:
            best, best_score = points, score
    return best


def _hull(points):
    points = sorted(set(points))
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    low, high = [], []
    for sequence, result in ((points, low), (reversed(points), high)):
        for point in sequence:
            while len(result) >= 2 and cross(result[-2], result[-1], point) <= 0:
                result.pop()
            result.append(point)
    return low[:-1] + high[:-1]


def _simplify_hull(polygon, limit=24):
    """Reduce a convex polygon to at most `limit` vertices by dropping lowest-area corners."""
    pts = list(polygon)
    while len(pts) > limit:
        n = len(pts)
        drop = min(
            range(n),
            key=lambda i: abs(
                (pts[i][0] - pts[(i - 1) % n][0]) * (pts[(i + 1) % n][1] - pts[(i - 1) % n][1])
                - (pts[i][1] - pts[(i - 1) % n][1]) * (pts[(i + 1) % n][0] - pts[(i - 1) % n][0])
            ),
        )
        pts.pop(drop)
    return pts


def _foreground_box(rgba, margin=.14):
    """Return a padded COCO [x, y, w, h] box around opaque pixels."""
    import numpy as np
    yy, xx = np.where(np.asarray(rgba)[:, :, 3] > 20)
    width, height = rgba.size
    if len(xx) == 0:
        return [0, 0, width, height]
    x0, y0, x1, y1 = int(xx.min()), int(yy.min()), int(xx.max() + 1), int(yy.max() + 1)
    pad = max(8, int(max(x1 - x0, y1 - y0) * margin))
    bx0, by0 = max(0, x0 - pad), max(0, y0 - pad)
    bx1, by1 = min(width, x1 + pad), min(height, y1 + pad)
    return [bx0, by0, max(1, bx1 - bx0), max(1, by1 - by0)]


def _distal_interior_sample(rgb, mask, wx, wy, dx, dy, max_perp=None, max_proj=None):
    """Sample median RGB along the distal corridor of an opaque limb mask and return (rgb, anchor_xy)."""
    import numpy as np
    yy, xx = np.where(mask)
    if len(xx) == 0:
        return None, (wx, wy)
    ox, oy = xx - wx, yy - wy
    proj = ox * dx + oy * dy
    if max_perp is not None:
        perp = np.abs(ox * (-dy) + oy * dx)
        corridor = (perp <= max_perp) & (proj >= -1.0)
        if max_proj is not None:
            corridor &= (proj <= max_proj)
        if int(corridor.sum()) >= 6:
            xx, yy, proj = xx[corridor], yy[corridor], proj[corridor]
    max_p = float(proj.max())
    if max_p <= 1.0:
        idx = np.arange(len(xx))
    else:
        lo, hi = max(1.0, max_p * .35), max(2.0, max_p * .85)
        band = (proj >= lo) & (proj <= hi)
        if not band.any():
            band = proj >= max(0.5, max_p * .25)
        idx = np.where(band)[0]
    anchor = (float(np.median(xx[idx])), float(np.median(yy[idx])))
    return np.median(rgb[yy[idx], xx[idx]], axis=0), anchor


def _forearm_dir(points, wrist_i, elbow_i):
    """Return unit forearm vector pointing distally from elbow past wrist."""
    vx = float(points[wrist_i, 0] - points[elbow_i, 0])
    vy = float(points[wrist_i, 1] - points[elbow_i, 1])
    norm = math.hypot(vx, vy)
    if norm < .02:
        return 0.0, 1.0
    dx, dy = vx / norm, vy / norm
    if dy < .25:
        return 0.0, 1.0
    return dx, dy


def _dilate1(mask):
    """Expand a 2D boolean mask by 1 pixel in 4-neighborhood to retain ink outlines."""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def _hand_component(rgb, alpha, crop, crop_a, x, y, dx, dy, fg_h, x0, y0, x1, y1, skin, torso, torso_x, score, side):
    """Segment a bare, furry, or gloved hand distal to the wrist seam while rejecting hidden cloak/torso regions."""
    import numpy as np
    kx, ky = min(side - 1, max(0, int(x * side))), min(side - 1, max(0, int(y * side)))
    crop_area = max(1, (x1 - x0) * (y1 - y0))
    xa, xb = min(kx, torso_x), max(kx, torso_x)

    # Cut off above the wrist seam so cream/peach sleeves never steal the hand component,
    # unless the keypoint already sits near the bottom of the palm (too few distal pixels).
    yy, xx = np.indices(crop_a.shape)
    wx, wy = x * side - x0, y * side - y0
    distal_plane = ((xx - wx) * dx + (yy - wy) * dy) >= -2.0
    distal_a = crop_a & distal_plane
    min_distal = max(10, int((side / 256.0) ** 2 * 12))
    regions = (distal_a, crop_a) if int(distal_a.sum()) >= min_distal else (crop_a,)
    dist_skin_torso = float(np.linalg.norm(skin - torso)) if torso is not None else 999.0

    for work_a in regions:
        hand_px, target = _distal_interior_sample(
            crop, work_a, wx, wy, dx, dy,
            max_perp=max(4.5, side * .022),
            max_proj=max(14.0, fg_h * side * .12),
        )
        probe_y = min(side - 1, max(0, int(round(target[1] + y0))))
        has_gap = bool(
            (~alpha[max(0, ky - 4):min(side, ky + 5), xa:xb + 1]).any()
            or (~alpha[max(0, probe_y - 3):min(side, probe_y + 4), xa:xb + 1]).any()
        ) if xb > xa else False

        # 1. Try skin-toned hand first (anchored in distal interior so cuff colors above cannot win).
        skin_seed_mask = work_a & (np.linalg.norm(crop - skin, axis=-1) < 75)
        skin_comp = _component(skin_seed_mask, target)
        need_min = min_distal if work_a is distal_a and len(regions) > 1 else 8
        if len(skin_comp) >= need_min and not (len(skin_comp) > crop_area * .65 and not has_gap and dist_skin_torso < 45):
            seed_only = np.zeros(crop_a.shape, dtype=bool)
            for px, py in skin_comp:
                seed_only[py, px] = True
            min_proj = min((px - wx) * dx + (py - wy) * dy for px, py in skin_comp)
            outline = work_a & (crop.mean(axis=-1) < 130) & _dilate1(seed_only) & (((xx - wx) * dx + (yy - wy) * dy) >= min_proj - 1.5)
            full_comp = _component(seed_only | outline, target)
            if len(full_comp) >= need_min:
                return full_comp

        # 2. Non-skin furry paws / gloves / mittens: require gap or color contrast against torso (rejects cloaks).
        if hand_px is None:
            continue
        dist_torso = float(np.linalg.norm(hand_px - torso)) if torso is not None else 999.0
        dist_skin = float(np.linalg.norm(hand_px - skin))
        visible = has_gap or dist_torso >= 45 or dist_skin < 85
        if not visible:
            continue

        max_fill = .88 if has_gap else .68
        if score >= .30 and has_gap:
            sil_comp = _component(work_a, target)
            if need_min <= len(sil_comp) <= crop_area * .88:
                sil_dists = np.linalg.norm(crop[work_a] - hand_px, axis=-1)
                if float((sil_dists < 85).mean()) >= .50:
                    return sil_comp

        near = work_a & (np.linalg.norm(crop - hand_px, axis=-1) < 68)
        outline = work_a & (crop.mean(axis=-1) < 130) & _dilate1(near)
        comp = _component(near | outline, target)
        if need_min <= len(comp) <= crop_area * max_fill:
            return comp
    return []


def _foot_component(rgb, alpha, crop, crop_a, x, y, fg_h, hip_y, knee_y, x0, y0, side):
    """Segment an entire foot/shoe below the ankle while trimming differing trouser cuffs above it."""
    import numpy as np
    yy, _ = np.indices(crop_a.shape)
    ankle_cy = y * side - y0
    below_ankle = yy > (ankle_cy - 1.5)
    opaque_rows = np.where(crop_a)[0]
    if len(opaque_rows) >= 8:
        floor_y = float(opaque_rows.max())
        sample_y_min = max(ankle_cy + 2.0, floor_y - max(6.0, (floor_y - ankle_cy) * 0.65))
        sample_mask = crop_a & (yy >= sample_y_min)
        if int(sample_mask.sum()) < 6:
            sample_mask = crop_a & below_ankle
    else:
        sample_mask = crop_a & (yy >= max(0.0, ankle_cy + 1.0))
        if int(sample_mask.sum()) < 8:
            sample_mask = crop_a
    wx = x * side - x0
    shoe_px, target = _distal_interior_sample(crop, sample_mask, wx, ankle_cy, 0.0, 1.0)
    if shoe_px is None:
        return []
    upper_step = max(.012, fg_h * .020)
    uy = min(side - 1, max(0, int((y - upper_step) * side)))
    ux = min(side - 1, max(0, int(x * side)))
    up_a = alpha[max(0, uy - 2):min(side, uy + 3), max(0, ux - 3):min(side, ux + 4)]
    upper_px = np.median(rgb[max(0, uy - 2):min(side, uy + 3), max(0, ux - 3):min(side, ux + 4)][up_a], axis=0) if up_a.any() else None

    above_ankle = ~below_ankle
    shoe_dist = np.linalg.norm(crop - shoe_px, axis=-1)
    upper_match = shoe_dist < 62
    if upper_px is not None and float(np.linalg.norm(upper_px - shoe_px)) >= 48:
        # Clear trouser/shoe color seam at ankle: keep upper pixels only if much closer to shoe than pants.
        upper_dist = np.linalg.norm(crop - upper_px, axis=-1)
        upper_match = upper_match & (shoe_dist + 12 < upper_dist)
    if knee_y is not None:
        above_ankle = above_ankle & (yy >= max(0.0, ((hip_y + knee_y) * .5 if knee_y < y else hip_y) * side - y0))

    # Below the ankle keypoint inside the bounded crop, retain the full shoe/boot (uppers, white sole, dark outline).
    mask = (crop_a & below_ankle) | (crop_a & above_ankle & upper_match)
    return _component(mask, target)


def _extract_rig(points, scores, rgb, alpha, side):
    """Build bounded four-limb polygons/pivots from normalized ViTPose landmarks."""
    import numpy as np
    if any(scores[index] < .25 for index in (9, 10, 15, 16)) or not np.isfinite(points).all():
        return None
    fy, fx = np.where(alpha)
    fg_w = max(.15, (float(fx.max() - fx.min() + 1) / side)) if len(fx) else 1.0
    fg_h = max(.25, (float(fy.max() - fy.min() + 1) / side)) if len(fy) else 1.0
    nose = np.clip(points[0] * side, 4, side - 5).astype(int)
    skin = np.median(rgb[nose[1] - 3:nose[1] + 4, nose[0] - 3:nose[0] + 4], axis=(0, 1))
    torso_xy = np.mean(points[[5, 6, 11, 12]], axis=0)
    mid_x = float(torso_xy[0])
    left_sho, right_sho = float(min(points[5, 0], points[6, 0])), float(max(points[5, 0], points[6, 0]))
    sho_span = right_sho - left_sho
    hip_span = abs(float(points[11, 0] - points[12, 0]))
    torso_hw = max(sho_span, hip_span, .08) * .5
    hip_y = float((points[11, 1] + points[12, 1]) * .5)
    foot_mid_x = float((points[15, 0] + points[16, 0]) * .5)
    torso_x = int(np.clip(torso_xy[0] * side, 4, side - 5))
    torso_y = int(np.clip(torso_xy[1] * side, 4, side - 5))
    torso_a = alpha[torso_y - 4:torso_y + 5, torso_x - 4:torso_x + 5]
    torso = np.median(rgb[torso_y - 4:torso_y + 5, torso_x - 4:torso_x + 5][torso_a], axis=0) if torso_a.any() else None
    parts = {}
    for kind, indices in (("hand", (9, 10)), ("foot", (15, 16))):
        for label, index in zip(("left", "right"), sorted(indices, key=lambda i: points[i][0])):
            x, y = points[index]
            if not .08 <= x <= .92 or not (.35 if kind == "hand" else .60) <= y <= .99:
                return None
            if kind == "hand":
                elbow_i = 7 if index == 9 else 8
                top_sho_y = float(min(points[5, 1], points[6, 1]))
                if y < top_sho_y - .010 and (scores[elbow_i] < .25 or float(points[elbow_i, 1]) < top_sho_y + .020):
                    return None
                dx, dy = _forearm_dir(points, index, elbow_i) if scores[elbow_i] >= .25 else (0.0, 1.0)
                rx = min(.068, max(.028, torso_hw * .66))
                above = min(.015, max(.007, fg_h * .016))
                below = min(.095, max(.042, fg_h * .095))
                x0, x1 = max(0, int((x - rx) * side)), min(side, int((x + rx) * side))
                y0, y1 = max(0, int((y - above) * side)), min(side, int((y + below) * side))
                # Prevent limb crops from invading across the chest/vest seam regardless of wide tails.
                if label == "left" and x < mid_x:
                    wall = min(mid_x - torso_hw * .95, left_sho - .010) if x < left_sho - .020 else mid_x - torso_hw * .95
                    x1 = min(x1, max(int((x + .012) * side), int(wall * side)))
                elif label == "right" and x > mid_x:
                    wall = max(mid_x + torso_hw * .95, right_sho + .010) if x > right_sho + .020 else mid_x + torso_hw * .95
                    x0 = max(x0, min(int((x - .012) * side), int(wall * side)))
            else:
                rx = min(.078, max(.032, torso_hw * .76))
                above = min(.028, max(.012, fg_h * .030))
                below = min(.120, max(.055, fg_h * .125))
                x0, x1 = max(0, int((x - rx) * side)), min(side, int((x + rx) * side))
                y0 = max(int(max(0.0, hip_y + .020) * side), int((y - above) * side))
                y1 = min(side, int((y + below) * side))
                col_sub = alpha[:, max(0, int((x - rx * 0.75) * side)):min(side, int((x + rx * 0.75) * side))]
                if col_sub.any():
                    foot_floor = int(np.where(col_sub)[0].max())
                    y1 = min(side, max(y1, foot_floor + 2))
                if label == "left" and x < foot_mid_x:
                    x1 = min(x1, max(int((x + .015) * side), int((foot_mid_x - .005) * side)))
                elif label == "right" and x > foot_mid_x:
                    x0 = max(x0, min(int((x - .015) * side), int((foot_mid_x + .005) * side)))
            if x1 <= x0 + 4 or y1 <= y0 + 4:
                return None
            crop, crop_a = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
            if kind == "hand":
                component = _hand_component(
                    rgb, alpha, crop, crop_a, x, y, dx, dy, fg_h, x0, y0, x1, y1, skin, torso, torso_x, float(scores[index]), side)
            else:
                knee_i = 13 if index == 15 else 14
                knee_y = float(points[knee_i, 1]) if scores[knee_i] >= .30 else None
                component = _foot_component(rgb, alpha, crop, crop_a, x, y, fg_h, hip_y, knee_y, x0, y0, side)
            if len(component) < 8:
                if kind == "hand":
                    # A hidden hand must not silently become a moving cape/torso.
                    return None
                # Editable rectangle fallback; no invented pixels or opaque model code.
                polygon = [[x - rx * .65, y], [x + rx * .65, y],
                           [x + rx * .65, min(.98, y + below)], [x - rx * .65, min(.98, y + below)]]
            else:
                hull = _hull([(px + x0, py + y0) for px, py in component])
                cx = sum(p[0] for p in hull) / len(hull)
                cy = sum(p[1] for p in hull) / len(hull)
                min_nx, max_nx = x0 / side, x1 / side
                polygon = [[max(min_nx, min(max_nx, (cx + (px - cx) * 1.06) / side)),
                            max(0.0, min(1.0, (cy + (py - cy) * 1.05) / side))] for px, py in hull]
                polygon = _simplify_hull(polygon, 24)
            if not 3 <= len(polygon) <= 32:
                return None
            top = min(p[1] for p in polygon)
            near_top = [p[0] for p in polygon if p[1] <= top + .015]
            pivot = [sum(near_top) / len(near_top), top + .004]
            if kind == "hand":
                elbow_i = 7 if index == 9 else 8
                elbow = points[elbow_i]
                center = np.mean(np.asarray(polygon), axis=0)
                delta = center - elbow
                distance = float(np.linalg.norm(delta))
                ex, ey = int(np.clip(elbow[0] * side, 2, side - 3)), int(np.clip(elbow[1] * side, 2, side - 3))
                ep_a = alpha[ey - 2:ey + 3, ex - 2:ex + 3]
                kx, ky = min(side - 1, max(0, int(x * side))), min(side - 1, max(0, int(y * side)))
                wp_a = alpha[max(0, ky - 2):min(side, ky + 3), max(0, kx - 2):min(side, kx + 3)]
                same_arm_color = (
                    ep_a.any() and wp_a.any()
                    and float(np.linalg.norm(np.median(rgb[ey - 2:ey + 3, ex - 2:ex + 3][ep_a], axis=0)
                                             - np.median(rgb[max(0, ky - 2):min(side, ky + 3), max(0, kx - 2):min(side, kx + 3)][wp_a], axis=0))) < 50
                )
                xa_e, xb_e = min(ex, torso_x), max(ex, torso_x)
                elbow_gap = bool((~alpha[max(0, ey - 2):min(side, ey + 3), xa_e:xb_e + 1]).any()) if xb_e > xa_e else False
                if (.035 <= distance <= .20 and scores[elbow_i] > .45
                        and abs(float(elbow[0]) - mid_x) > torso_hw * 1.15
                        and float(elbow[1]) >= float(min(points[5, 1], points[6, 1])) + .02
                        and (elbow_gap or same_arm_color)):
                    perpendicular = np.array([-delta[1], delta[0]]) / distance
                    radius = min(.028, max(.014, (max(p[0] for p in polygon) - min(p[0] for p in polygon)) * .50))
                    polygon = _hull([tuple(p) for p in polygon] +
                                    [tuple(float(v) for v in np.clip(elbow + perpendicular * radius, 0, 1)),
                                     tuple(float(v) for v in np.clip(elbow - perpendicular * radius, 0, 1))])
                    polygon = _simplify_hull(polygon, 24)
                    pivot = [float(elbow[0]), float(elbow[1])]
            parts[f"{label}_{kind}"] = {"polygon": [[float(p[0]), float(p[1])] for p in polygon],
                                        "pivot": [float(pivot[0]), float(pivot[1])]}
    return {"version": 1, "parts": parts}


def load_pose_model(model_path):
    """Load ViTPose processor and model on CUDA fp16 when available, else CPU fp32."""
    import torch
    from transformers import VitPoseForPoseEstimation, VitPoseImageProcessor
    torch.set_num_threads(4)
    processor = VitPoseImageProcessor.from_pretrained(model_path, local_files_only=True)
    if torch.cuda.is_available():
        try:
            model = VitPoseForPoseEstimation.from_pretrained(
                model_path, local_files_only=True, use_safetensors=True
            ).to(device="cuda", dtype=torch.float16).eval()
            return processor, model
        except RuntimeError:
            torch.cuda.empty_cache()
    model = VitPoseForPoseEstimation.from_pretrained(
        model_path, local_files_only=True, use_safetensors=True
    ).eval()
    return processor, model


def predict_pose(processor, model, rgb_image, boxes):
    """Run ViTPose inference supporting both simple and MoE (vitpose-plus) heads."""
    import numpy as np
    import torch
    device = next(model.parameters()).device
    dtype = next(model.parameters()).dtype
    inputs = processor(rgb_image, boxes=boxes, return_tensors="pt")
    inputs = {k: (v.to(device=device, dtype=dtype) if torch.is_floating_point(v) else v.to(device))
              for k, v in inputs.items()}
    if getattr(getattr(model.config, "backbone_config", None), "num_experts", 1) > 1:
        inputs["dataset_index"] = torch.zeros(inputs["pixel_values"].shape[0], dtype=torch.long, device=device)
    with torch.inference_mode():
        output = model(**inputs)
    # VitPoseImageProcessor passes heatmaps to SciPy gaussian_filter, which rejects fp16.
    output.heatmaps = output.heatmaps.detach().float().cpu()
    pose = processor.post_process_pose_estimation(output, boxes=boxes)[0][0]
    width, height = rgb_image.size
    points = pose["keypoints"].detach().cpu().numpy() / np.array([width, height])
    scores = pose["scores"].detach().cpu().numpy()
    return points, scores


def release_pose_model(model):
    """Free GPU pose model memory before worker handoff or exit."""
    import torch
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


def suggest(image, model_path):
    """Estimate conservative editable four-limb regions using padded foreground boxing."""
    import numpy as np
    from PIL import Image
    rgba = image.convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    white = white.convert("RGB")
    width, height = white.size
    full_box = [0, 0, width, height]
    fg_box = _foreground_box(rgba)
    candidates = [full_box]
    if fg_box != full_box:
        candidates = ([fg_box, full_box]
                      if fg_box[2] < int(width * .88) or fg_box[3] < int(height * .88)
                      else [full_box, fg_box])
    processor, model = load_pose_model(model_path)
    side = 384
    pixels = np.asarray(rgba.resize((side, side)), dtype=np.float32)
    rgb, alpha = pixels[:, :, :3], pixels[:, :, 3] > 80
    try:
        for box in candidates:
            points, scores = predict_pose(processor, model, white, [[box]])
            rig = _extract_rig(points, scores, rgb, alpha, side)
            if rig is not None:
                return rig
    finally:
        release_pose_model(model)
    return None
