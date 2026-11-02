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


def suggest(image, model_path):
    import numpy as np
    import torch
    from PIL import Image
    from transformers import VitPoseForPoseEstimation, VitPoseImageProcessor
    torch.set_num_threads(4)
    rgba = image.convert("RGBA")
    white = Image.new("RGBA", rgba.size, "white")
    white.alpha_composite(rgba)
    white = white.convert("RGB")
    width, height = white.size
    boxes = [[[0, 0, width, height]]]
    processor = VitPoseImageProcessor.from_pretrained(model_path, local_files_only=True)
    model = VitPoseForPoseEstimation.from_pretrained(model_path, local_files_only=True, use_safetensors=True).eval()
    with torch.inference_mode():
        output = model(**processor(white, boxes=boxes, return_tensors="pt"))
    pose = processor.post_process_pose_estimation(output, boxes=boxes)[0][0]
    points = pose["keypoints"].numpy() / np.array([width, height])
    scores = pose["scores"].numpy()
    if any(scores[index] < .25 for index in (9, 10, 15, 16)) or not np.isfinite(points).all():
        return None
    side = 256
    pixels = np.asarray(rgba.resize((side, side)), dtype=np.float32)
    rgb, alpha = pixels[:, :, :3], pixels[:, :, 3] > 80
    nose = np.clip(points[0] * side, 4, side - 5).astype(int)
    skin = np.median(rgb[nose[1] - 3:nose[1] + 4, nose[0] - 3:nose[0] + 4], axis=(0, 1))
    parts = {}
    for kind, indices in (("hand", (9, 10)), ("foot", (15, 16))):
        for label, index in zip(("left", "right"), sorted(indices, key=lambda i: points[i][0])):
            x, y = points[index]
            if not .08 <= x <= .92 or not (.35 if kind == "hand" else .60) <= y <= .97:
                return None
            rx, above, below = (.075, .025, .10) if kind == "hand" else (.08, .06, .08)
            x0, x1 = max(0, int((x - rx) * side)), min(side, int((x + rx) * side))
            y0, y1 = max(0, int((y - above) * side)), min(side, int((y + below) * side))
            crop = rgb[y0:y1, x0:x1]
            sample = skin if kind == "hand" else rgb[int(y * side), int(x * side)]
            color_distance = np.linalg.norm(crop - sample, axis=-1)
            mask = alpha[y0:y1, x0:x1] & (color_distance < (95 if kind == "hand" else 90))
            component = _component(mask, (x * side - x0, (y + .025) * side - y0))
            if len(component) < 8:
                if kind == "hand":
                    # A hidden hand must not silently become a moving cape/torso.
                    # Gloved/non-human hands may need the manual editor instead.
                    return None
                # Editable rectangle fallback; no invented pixels or opaque model code.
                polygon = [[x - rx * .65, y], [x + rx * .65, y],
                           [x + rx * .65, min(.98, y + below)], [x - rx * .65, min(.98, y + below)]]
            else:
                hull = _hull([(px + x0, py + y0) for px, py in component])
                cx = sum(p[0] for p in hull) / len(hull)
                cy = sum(p[1] for p in hull) / len(hull)
                polygon = [[max(0, min(1, (cx + (px - cx) * 1.15) / side)),
                            max(0, min(1, (cy + (py - cy) * 1.10) / side))] for px, py in hull]
            if not 3 <= len(polygon) <= 32:
                return None
            top = min(p[1] for p in polygon)
            near_top = [p[0] for p in polygon if p[1] <= top + .015]
            pivot = [sum(near_top) / len(near_top), top + .004]
            if kind == "hand":
                elbow = points[7 if index == 9 else 8]
                center = np.mean(np.asarray(polygon), axis=0)
                delta = center - elbow
                distance = float(np.linalg.norm(delta))
                if .035 <= distance <= .25 and scores[7 if index == 9 else 8] > .3:
                    perpendicular = np.array([-delta[1], delta[0]]) / distance
                    radius = min(.032, max(.017, (max(p[0] for p in polygon) - min(p[0] for p in polygon)) * .55))
                    polygon = _hull([tuple(p) for p in polygon] +
                                    [tuple(np.clip(elbow + perpendicular * radius, 0, 1)),
                                     tuple(np.clip(elbow - perpendicular * radius, 0, 1))])
                    pivot = [float(elbow[0]), float(elbow[1])]
            parts[f"{label}_{kind}"] = {"polygon": [list(p) for p in polygon], "pivot": pivot}
    return {"version": 1, "parts": parts}
