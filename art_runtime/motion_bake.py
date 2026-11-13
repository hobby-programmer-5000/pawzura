"""Articulated DQS/facial deformation and 2x-SSAA barycentric mesh rasterization."""
import hashlib
import io
import json
import math
import zipfile
import numpy as np
from PIL import Image
from motion_geometry import smooth, ry, rz, pose, compute_vertex_normals, dual_quaternion_skinning
from motion_library import generate_clip_poses

COUNTS = {
    "idle_front": 90,
    "walk_left": 72,
    "walk_right": 72,
    "turn_left": 8,
    "turn_right": 8,
    "return_left": 8,
    "return_right": 8,
    "wave": 48,
    "hop": 27,
    "cheer": 36,
    "bite_left": 30,
    "bite_right": 30,
}


def face(points, colors, joints, mouth, blink, opening, smile, height, gaze_y=0.0, brow=0.0, apply_jaw=True):
    """Apply smooth eyelid closure, subtle gaze/brow motion, smile lift, and recessed mouth interior."""
    p = points.copy()
    c = colors.copy()
    eyes = joints[[1, 2]].copy()
    distance = max(height * 0.08, abs(eyes[0, 1] - eyes[1, 1]))
    front = p[:, 0] > mouth[0] - height * 0.14
    skin_region = front & (abs(p[:, 1] - mouth[1]) < distance * 0.7) & (abs(p[:, 2] - mouth[2]) < height * 0.035)
    skin = c[skin_region & (c.mean(1) > 0.6)]
    skin = np.median(skin, 0) if len(skin) > 5 else np.array([0.93, 0.79, 0.65], dtype=np.float32)

    for eye in eyes:
        dy_e = p[:, 1] - eye[1]
        dz_e = p[:, 2] - eye[2]
        influence = (1 - smooth(distance * 0.34, distance * 0.58, abs(dy_e))) * (1 - smooth(distance * 0.16, distance * 0.27, abs(dz_e))) * front
        # Subtle eye gaze shift on pupil/iris pixels.
        if abs(gaze_y) > 1e-3:
            pupil = influence * smooth(0.35, 0.7, 1.0 - c.mean(1))
            p[:, 1] += pupil * gaze_y * distance * 0.06
        # Eyebrow subtle vertical lift/furrow just above eye band.
        if abs(brow) > 1e-3:
            brow_band = front * (1 - smooth(distance * 0.25, distance * 0.52, abs(dy_e))) * smooth(distance * 0.18, distance * 0.28, dz_e) * (1 - smooth(distance * 0.32, distance * 0.44, dz_e))
            p[:, 2] += brow_band * brow * height * 0.011
        aperture = distance * 0.19 * (1 - blink)
        lid = influence * smooth(aperture - 0.0015, aperture + 0.003, abs(dz_e)) * blink
        c = c * (1 - lid[:, None]) + skin * lid[:, None]
        curve = eye[2] + height * 0.003 * (dy_e / (distance * 0.36)) ** 2
        line = influence * (1 - smooth(height * 0.001, height * 0.003, abs(p[:, 2] - curve))) * smooth(0.72, 1.0, blink)
        c = c * (1 - line[:, None]) + np.array([0.23, 0.16, 0.13], dtype=np.float32) * line[:, None]

    dy = p[:, 1] - mouth[1]
    dz = p[:, 2] - mouth[2]
    if apply_jaw:
        jaw_weight = front * (1 - smooth(height * 0.0, height * 0.04, dz)) * smooth(-height * 0.08, -height * 0.04, dz) * (1 - smooth(distance * 0.42, distance * 0.8, abs(dy)))
        pivot = mouth + np.array([-height * 0.13, 0.0, height * 0.035], dtype=np.float32)
        jaw = (p - pivot) @ ry(opening * 0.22).T + pivot
        p += jaw_weight[:, None] * (jaw - p)
    corners = front * np.exp(-((abs(dy) - distance * 0.24) / (distance * 0.13)) ** 2 - (dz / (distance * 0.13)) ** 2)
    p[:, 2] += smile * height * 0.009 * corners
    cover = front & (abs(dy) < distance * 0.44) & (abs(dz) < height * 0.016)
    amount = float(smooth(0.08, 0.35, opening))
    c[cover] = c[cover] * (1 - amount) + skin * amount

    extra_v, extra_f, extra_c = [], [], []
    if opening > 0.01:
        rings = 10
        segs = 24
        grid_v, grid_c = [], []
        for r_i, radius in enumerate(np.linspace(0.0, 1.0, rings)):
            for s_i in range(segs):
                theta = 2.0 * math.pi * s_i / segs
                y = mouth[1] + distance * 0.40 * radius * math.cos(theta)
                z = mouth[2] - height * 0.006 * opening + (height * 0.005 + height * 0.022 * opening) * radius * math.sin(theta)
                # Slightly curved inner cavity behind lip profile so 3/4 views stay tucked cleanly.
                x = mouth[0] + height * 0.0015 - 2.0 * (y - mouth[1]) ** 2 / height - height * 0.007 * (1.0 - radius)
                col = np.array([0.19, 0.075, 0.09], dtype=np.float32)
                if radius > 0.89:
                    col = np.array([0.68, 0.37, 0.31], dtype=np.float32)
                elif radius < 0.78 and z > mouth[2] + opening * height * 0.011:
                    col = np.array([0.98, 0.95, 0.85], dtype=np.float32)
                elif radius < 0.70 and z < mouth[2] - opening * height * 0.011:
                    col = np.array([0.83, 0.31, 0.39], dtype=np.float32)
                grid_v.append([x, y, z])
                grid_c.append(col)
        extra_v = np.asarray(grid_v, dtype=np.float32)
        extra_c = np.asarray(grid_c, dtype=np.float32)
        faces_list = []
        for r_i in range(rings - 1):
            for s_i in range(segs):
                sn = (s_i + 1) % segs
                a = r_i * segs + s_i
                b = r_i * segs + sn
                d = (r_i + 1) * segs + s_i
                e = (r_i + 1) * segs + sn
                faces_list.append([a, b, e])
                faces_list.append([a, e, d])
        extra_f = np.asarray(faces_list, dtype=np.int32)
    else:
        extra_v = np.empty((0, 3), dtype=np.float32)
        extra_f = np.empty((0, 3), dtype=np.int32)
        extra_c = np.empty((0, 3), dtype=np.float32)
    return p, c, extra_v, extra_f, extra_c


def render_mesh(vertices, faces, colors, normals, yaw, floor, top, mouth, out_size=256, atlas=None, face_uvs=None, override_w=None):
    """2x-supersampled vectorized barycentric triangle rasterizer with bilinear UV atlas & Lanczos downsample."""
    ssaa = out_size * 2
    p = rz(vertices, yaw)
    n_rot = rz(normals, yaw)
    m = rz(mouth[None], yaw)[0]
    scale = ssaa * 0.90 / max(1e-4, top - floor)

    sx = (ssaa * 0.5 + p[:, 1] * scale).astype(np.float32)
    sy = (ssaa - 1.0 - (p[:, 2] - floor) * scale).astype(np.float32)
    sz = p[:, 0].astype(np.float32)

    # Gentle wrap directional shading along camera +X so 3D form reads cleanly without dulling artwork palette.
    shade = np.clip(0.91 + 0.11 * np.abs(n_rot[:, 0]) - 0.03 * (1.0 - np.abs(n_rot[:, 0])), 0.85, 1.04).astype(np.float32)
    lit_rgb = np.clip(colors * shade[:, None], 0.0, 1.0).astype(np.float32)

    atlas_f = None
    if atlas is not None and face_uvs is not None and len(face_uvs):
        atlas_f = atlas.astype(np.float32) * (1.0 / 255.0) if atlas.dtype == np.uint8 else np.asarray(atlas, dtype=np.float32)
        h_at, w_at = atlas_f.shape[:2]

    v0 = faces[:, 0]
    v1 = faces[:, 1]
    v2 = faces[:, 2]
    x0, y0, z0 = sx[v0], sy[v0], sz[v0]
    x1, y1, z1 = sx[v1], sy[v1], sz[v1]
    x2, y2, z2 = sx[v2], sy[v2], sz[v2]

    area2 = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
    keep = np.abs(area2) > 0.05
    keep_fidx = np.flatnonzero(keep)
    if len(keep_fidx):
        v0, v1, v2 = v0[keep_fidx], v1[keep_fidx], v2[keep_fidx]
        x0, y0, z0 = x0[keep_fidx], y0[keep_fidx], z0[keep_fidx]
        x1, y1, z1 = x1[keep_fidx], y1[keep_fidx], z1[keep_fidx]
        x2, y2, z2 = x2[keep_fidx], y2[keep_fidx], z2[keep_fidx]
        area2 = area2[keep_fidx]
    else:
        v0 = np.empty(0, dtype=np.int32)

    zcolor = np.zeros(ssaa * ssaa, dtype=np.uint64)

    def _pack_fragments(loc_ids, w0h, w1h, w2h, zh, px_flat, py_flat):
        v0_l, v1_l, v2_l = v0[loc_ids], v1[loc_ids], v2[loc_ids]
        ch = w0h[:, None] * lit_rgb[v0_l] + w1h[:, None] * lit_rgb[v1_l] + w2h[:, None] * lit_rgb[v2_l]
        if atlas_f is not None:
            orig_ids = keep_fidx[loc_ids]
            uv_ok = orig_ids < len(face_uvs)
            if uv_ok.any():
                u_ids = orig_ids[uv_ok]
                uv_tri = face_uvs[u_ids]
                uv_ok2 = uv_tri[:, 0, 0] >= 0.0
                if uv_ok2.any():
                    sub_pos = np.flatnonzero(uv_ok)[uv_ok2]
                    uv_t = uv_tri[uv_ok2]
                    uw0, uw1, uw2 = w0h[sub_pos], w1h[sub_pos], w2h[sub_pos]
                    u_pix = uw0 * uv_t[:, 0, 0] + uw1 * uv_t[:, 1, 0] + uw2 * uv_t[:, 2, 0]
                    v_pix = uw0 * uv_t[:, 0, 1] + uw1 * uv_t[:, 1, 1] + uw2 * uv_t[:, 2, 1]
                    fx = np.clip(u_pix * w_at - 0.5, 0.0, w_at - 1.001)
                    fy = np.clip(v_pix * h_at - 0.5, 0.0, h_at - 1.001)
                    ix = fx.astype(np.int32)
                    iy = fy.astype(np.int32)
                    tx = (fx - ix)[:, None]
                    ty = (fy - iy)[:, None]
                    tex = (1.0 - ty) * ((1.0 - tx) * atlas_f[iy, ix] + tx * atlas_f[iy, ix + 1]) + ty * ((1.0 - tx) * atlas_f[iy + 1, ix] + tx * atlas_f[iy + 1, ix + 1])
                    l_sub = loc_ids[sub_pos]
                    sh_h = (uw0 * shade[v0[l_sub]] + uw1 * shade[v1[l_sub]] + uw2 * shade[v2[l_sub]])[:, None]
                    tex_lit = tex * sh_h
                    if override_w is not None:
                        ow = (uw0 * override_w[v0[l_sub]] + uw1 * override_w[v1[l_sub]] + uw2 * override_w[v2[l_sub]])[:, None]
                        tex_lit = tex_lit * (1.0 - ow) + ch[sub_pos] * ow
                    ch[sub_pos] = tex_lit
        rgb8 = np.rint(np.clip(ch, 0.0, 1.0) * 255.0).astype(np.uint64)
        z_q = np.clip(np.rint((zh + 4.0) * 1e6), 0, (1 << 25) - 1).astype(np.uint64)
        packed = (z_q << 25) | (np.uint64(1) << 24) | (rgb8[:, 0] << 16) | (rgb8[:, 1] << 8) | rgb8[:, 2]
        np.maximum.at(zcolor, py_flat * ssaa + px_flat, packed)

    if len(v0):
        xmin = np.clip(np.floor(np.minimum(np.minimum(x0, x1), x2)).astype(np.int32), 0, ssaa - 1)
        xmax = np.clip(np.ceil(np.maximum(np.maximum(x0, x1), x2)).astype(np.int32), 0, ssaa - 1)
        ymin = np.clip(np.floor(np.minimum(np.minimum(y0, y1), y2)).astype(np.int32), 0, ssaa - 1)
        ymax = np.clip(np.ceil(np.maximum(np.maximum(y0, y1), y2)).astype(np.int32), 0, ssaa - 1)
        max_b = np.maximum(xmax - xmin + 1, ymax - ymin + 1)
        inv_area = 1.0 / area2

        # Vectorize triangles in tight bounding-box size buckets for fast CPU rasterization.
        prev = 0
        for limit in (3, 6, 12, 24):
            mask = (max_b > prev) & (max_b <= limit)
            prev = limit
            if not mask.any():
                continue
            idx = np.flatnonzero(mask)
            dx = np.arange(limit, dtype=np.float32)
            dy = np.arange(limit, dtype=np.float32)
            gx, gy = np.meshgrid(dx, dy)
            px = xmin[idx, None] + gx.ravel()[None, :].astype(np.int32)
            py = ymin[idx, None] + gy.ravel()[None, :].astype(np.int32)
            in_bounds = (px <= xmax[idx, None]) & (py <= ymax[idx, None]) & (px < ssaa) & (py < ssaa)
            cx = px.astype(np.float32) + 0.5
            cy = py.astype(np.float32) + 0.5

            ia = inv_area[idx, None]
            w0 = ((x1[idx, None] - cx) * (y2[idx, None] - cy) - (y1[idx, None] - cy) * (x2[idx, None] - cx)) * ia
            w1 = ((x2[idx, None] - cx) * (y0[idx, None] - cy) - (y2[idx, None] - cy) * (x0[idx, None] - cx)) * ia
            w2 = 1.0 - w0 - w1
            hit = in_bounds & (w0 >= -0.002) & (w1 >= -0.002) & (w2 >= -0.002)
            if not hit.any():
                continue
            ti, pi = np.where(hit)
            w0h = np.clip(w0[ti, pi], 0.0, 1.0)
            w1h = np.clip(w1[ti, pi], 0.0, 1.0)
            w2h = np.clip(w2[ti, pi], 0.0, 1.0)
            wsum = np.maximum(w0h + w1h + w2h, 1e-6)
            zh = (w0h * z0[idx[ti]] + w1h * z1[idx[ti]] + w2h * z2[idx[ti]]) / wsum
            _pack_fragments(idx[ti], w0h / wsum, w1h / wsum, w2h / wsum, zh, px[ti, pi], py[ti, pi])

        large = np.flatnonzero(max_b > prev)
        for ti in large:
            xs = np.arange(xmin[ti], xmax[ti] + 1, dtype=np.float32) + 0.5
            ys = np.arange(ymin[ti], ymax[ti] + 1, dtype=np.float32) + 0.5
            gx, gy = np.meshgrid(xs, ys)
            ia = inv_area[ti]
            w0 = ((x1[ti] - gx) * (y2[ti] - gy) - (y1[ti] - gy) * (x2[ti] - gx)) * ia
            w1 = ((x2[ti] - gx) * (y0[ti] - gy) - (y2[ti] - gy) * (x0[ti] - gx)) * ia
            w2 = 1.0 - w0 - w1
            hit = (w0 >= -0.002) & (w1 >= -0.002) & (w2 >= -0.002)
            if not hit.any():
                continue
            w0h = np.clip(w0[hit], 0.0, 1.0)
            w1h = np.clip(w1[hit], 0.0, 1.0)
            w2h = np.clip(w2[hit], 0.0, 1.0)
            wsum = np.maximum(w0h + w1h + w2h, 1e-6)
            loc = np.full(len(w0h), ti, dtype=np.int32)
            zh = (w0h * z0[ti] + w1h * z1[ti] + w2h * z2[ti]) / wsum
            px_h = np.clip(np.rint(gx[hit] - 0.5).astype(np.int32), 0, ssaa - 1)
            py_h = np.clip(np.rint(gy[hit] - 0.5).astype(np.int32), 0, ssaa - 1)
            _pack_fragments(loc, w0h / wsum, w1h / wsum, w2h / wsum, zh, px_h, py_h)

    rgba = np.zeros((ssaa * ssaa, 4), dtype=np.uint8)
    valid = zcolor > 0
    if valid.any():
        vals = zcolor[valid]
        rgba[valid, 0] = ((vals >> 16) & 0xFF).astype(np.uint8)
        rgba[valid, 1] = ((vals >> 8) & 0xFF).astype(np.uint8)
        rgba[valid, 2] = (vals & 0xFF).astype(np.uint8)
        rgba[valid, 3] = 255

    # Premultiplied alpha downsample prevents dark/white boundary halos.
    hi_img = Image.fromarray(rgba.reshape(ssaa, ssaa, 4), "RGBA").convert("RGBa")
    out_img = hi_img.resize((out_size, out_size), Image.Resampling.LANCZOS).convert("RGBA")

    anchor = [float((ssaa * 0.5 + m[1] * scale) / ssaa), float((ssaa - 1.0 - (m[2] - floor) * scale) / ssaa)]
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in anchor):
        raise ValueError("Invalid contact anchor")
    return out_img, anchor


def render(points, colors, yaw, floor, top, mouth):
    """Legacy point-cloud splat fallback when triangle faces are unavailable."""
    p = rz(points, yaw)
    m = rz(mouth[None], yaw)[0]
    size = 256
    scale = size * 0.90 / (top - floor)
    u = np.rint(size * 0.5 + p[:, 1] * scale).astype(np.int32)
    v = np.rint(size - 1 - (p[:, 2] - floor) * scale).astype(np.int32)
    n = len(p)
    rank = np.rint((3 - p[:, 0]) * 1e6).astype(np.int64) * n + np.arange(n, dtype=np.int64)
    sentinel = np.iinfo(np.int64).max
    buffer = np.full(size * size, sentinel, np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            x = u + dx
            y = v + dy
            hit = (x >= 0) & (x < size) & (y >= 0) & (y < size)
            np.minimum.at(buffer, y[hit] * size + x[hit], rank[hit])
    hit = buffer != sentinel
    rgba = np.zeros((size * size, 4), np.uint8)
    rgba[hit, :3] = np.round(np.clip(colors[(buffer[hit] % n).astype(np.int32)], 0, 1) * 255).astype(np.uint8)
    rgba[hit, 3] = 255
    anchor = [float((size * 0.5 + m[1] * scale) / size), float((size - 1 - (m[2] - floor) * scale) / size)]
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in anchor):
        raise ValueError("Invalid contact anchor")
    return Image.fromarray(rgba.reshape(size, size, 4), "RGBA"), anchor


def _bake_articulated(job, payload, report, surf_data, rig_data):
    """Bake articulated 22+ bone DQS + spring-bone + bilinear UV atlas + 2x-SSAA mesh frames."""
    has_detached = "mesh_vertices" in rig_data and "mesh_faces" in rig_data
    vertices = rig_data["mesh_vertices"] if has_detached else surf_data["vertices"]
    faces = rig_data["mesh_faces"] if has_detached else surf_data["faces"]
    if has_detached and "mesh_colors" in rig_data:
        colors = rig_data["mesh_colors"]
    else:
        colors = surf_data["vertex_colors"] if "vertex_colors" in surf_data else surf_data["colors"]
    normals = rig_data["normals"] if (has_detached and "normals" in rig_data) else (
        surf_data["normals"] if "normals" in surf_data else compute_vertex_normals(vertices, faces)
    )
    atlas = surf_data["atlas"] if "atlas" in surf_data else None
    face_uvs = surf_data["face_uvs"] if "face_uvs" in surf_data else None

    bones = rig_data["bones"]
    parents = rig_data["parents"]
    bone_names = [str(x) for x in rig_data["bone_names"].tolist()]
    weights = rig_data["weights"]
    joints = rig_data["joints"]
    mouth = rig_data["mouth"]
    arm_mobility = float(rig_data["arm_mobility"]) if "arm_mobility" in rig_data else 1.0

    n_bones = len(bones)
    if (
        vertices.ndim != 2 or vertices.shape[1] != 3 or len(vertices) > 140000
        or faces.ndim != 2 or faces.shape[1] != 3 or len(faces) > 280000
        or len(colors) != len(vertices)
        or not 12 <= n_bones <= 48 or bones.shape != (n_bones, 2, 3)
        or weights.shape != (len(vertices), n_bones)
        or not all(np.isfinite(x).all() for x in (vertices, colors, normals, bones, weights, joints, mouth))
        or np.max(abs(weights.sum(1) - 1.0)) > 1e-4 or weights.min() < 0
    ):
        raise ValueError("Invalid articulated rig")

    floor = float(vertices[:, 2].min())
    top = float(vertices[:, 2].max())
    height = top - floor
    manifest = {
        "version": 1,
        "source_art_id": payload["source_art_id"],
        "backend": "triposr-pose-v2",
        "size": 256,
        "fps": 30,
        "clips": {},
    }
    total = sum(COUNTS.values())
    done = 0
    report("motion_baking", 0, total)
    target = job / "motion.zip"
    temporary = job / "motion.tmp"
    head_idx = bone_names.index("head")
    atlas_f = atlas.astype(np.float32) * (1.0 / 255.0) if (atlas is not None and atlas.dtype == np.uint8) else atlas

    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for clip, count in COUNTS.items():
            manifest["clips"][clip] = []
            clip_transforms, face_tracks = generate_clip_poses(clip, count, bones, parents, bone_names, fps=30, arm_mobility=arm_mobility)
            for i in range(count):
                transforms = clip_transforms[i]
                ft = face_tracks[i]
                v_face, c_face, ex_v, ex_f, ex_c = face(
                    vertices, colors, joints, mouth,
                    ft["blink"], ft["opening"], ft["smile"], height,
                    gaze_y=ft.get("gaze_y", 0.0), brow=ft.get("brow", 0.0), apply_jaw=False,
                )
                deformed_v, deformed_n = dual_quaternion_skinning(v_face, normals, weights, transforms)
                r_head, tr_head = transforms[head_idx]
                mouth_now = mouth @ r_head.T + tr_head
                ov_w = None
                if atlas_f is not None and face_uvs is not None:
                    ov_base = np.clip(np.abs(c_face - colors).max(axis=1) * 4.0, 0.0, 1.0).astype(np.float32)
                    ov_w = np.concatenate([ov_base, np.ones(len(ex_v), dtype=np.float32)]) if len(ex_v) else ov_base
                if len(ex_v):
                    ex_v_def = ex_v @ r_head.T + tr_head
                    ex_n = compute_vertex_normals(ex_v_def, ex_f)
                    ex_f_off = ex_f + len(deformed_v)
                    render_v = np.concatenate([deformed_v, ex_v_def], axis=0)
                    render_f = np.concatenate([faces, ex_f_off], axis=0)
                    render_c = np.concatenate([c_face, ex_c], axis=0)
                    render_n = np.concatenate([deformed_n, ex_n], axis=0)
                else:
                    render_v, render_f, render_c, render_n = deformed_v, faces, c_face, deformed_n

                image, anchor = render_mesh(
                    render_v, render_f, render_c, render_n, ft["yaw"], floor, top, mouth_now,
                    out_size=256, atlas=atlas_f, face_uvs=face_uvs, override_w=ov_w,
                )
                output = io.BytesIO()
                image.save(output, "PNG")
                png = output.getvalue()
                name = f"frames/{clip}-{i:03}.png"
                archive.writestr(name, png)
                manifest["clips"][clip].append({"file": name, "sha256": hashlib.sha256(png).hexdigest(), "mouth": anchor})
                done += 1
                if done % 8 == 0 or done == total:
                    report("motion_baking", done, total)
        archive.writestr("manifest.json", json.dumps(manifest, separators=(",", ":")))
    temporary.replace(target)


def bake(job, payload, report):
    with np.load(job / "surface.npz", allow_pickle=False) as surf_data:
        with np.load(job / "rig.npz", allow_pickle=False) as rig_data:
            if "parents" in rig_data and "bone_names" in rig_data and "faces" in surf_data:
                return _bake_articulated(job, payload, report, surf_data, rig_data)
            points = surf_data["points"]
            colors = surf_data["colors"]
            bones = rig_data["bones"]
            weights = rig_data["weights"]
            joints = rig_data["joints"]
            mouth = rig_data["mouth"]

    if (
        points.ndim != 2 or points.shape[1] != 3 or len(points) > 300000 or weights.shape != (len(points), 12)
        or bones.shape != (12, 2, 3) or not all(np.isfinite(x).all() for x in (points, colors, bones, weights, joints, mouth))
        or np.max(abs(weights.sum(1) - 1)) > 1e-4 or weights.min() < 0
    ):
        raise ValueError("Invalid rig")
    floor = float(points[:, 2].min())
    top = float(points[:, 2].max())
    height = top - floor
    manifest = {"version": 1, "source_art_id": payload["source_art_id"], "backend": "triposr-pose-v1", "size": 256, "fps": 30, "clips": {}}
    total = sum(COUNTS.values())
    done = 0
    report("motion_baking", 0, total)
    target = job / "motion.zip"
    temporary = job / "motion.tmp"
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
        for clip, count in COUNTS.items():
            manifest["clips"][clip] = []
            for i in range(count):
                t = i / 30
                u = i / max(1, count - 1)
                gait = 1 if clip.startswith("walk_") else 0
                yaw = -math.pi / 2 if clip.endswith("left") else math.pi / 2 if clip.endswith("right") else 0
                if clip.startswith("turn_"):
                    yaw *= float(smooth(0, 1, u))
                elif clip.startswith("return_"):
                    yaw *= 1 - float(smooth(0, 1, u))
                blink = math.exp(-((t - count / 30 * 0.70) / 0.07) ** 2) if clip.startswith(("walk_", "idle_")) else 0
                opening = float(smooth(0.35, 0.65, t)) * (1 - float(smooth(0.72, 0.94, t))) if clip.startswith("bite_") else 0
                tucked = math.sin(math.pi * u) * 0.7 if clip in ("hop", "cheer") else math.sin(math.pi * min(t / 0.72, 1)) * 0.6 if clip.startswith("bite_") else 0
                matrices, _ = pose(
                    bones, phase=t / 0.8, gait=gait, crouch=math.sin(math.pi * u) * 0.4 if clip == "hop" else 0,
                    tucked=tucked, bite=opening, wave=math.sin(math.pi * u) ** 2 if clip in ("wave", "cheer") else 0, height=height,
                )
                p, c, extras, _, extra_colors = face(points, colors, joints, mouth, blink, opening, 0.3 + 0.15 * math.sin(t * 2), height)
                deformed = np.zeros_like(p)
                for number, (rot, trans) in enumerate(matrices):
                    hit = weights[:, number] > 1e-6
                    deformed[hit] += (p[hit] @ rot.T + trans) * weights[hit, number, None]
                r, tr = matrices[0]
                mouth_now = mouth @ r.T + tr
                if len(extras):
                    deformed = np.concatenate([deformed, extras @ r.T + tr])
                    c = np.concatenate([c, extra_colors])
                image, anchor = render(deformed, c, yaw, floor, top, mouth_now)
                output = io.BytesIO()
                image.save(output, "PNG")
                png = output.getvalue()
                name = f"frames/{clip}-{i:03}.png"
                archive.writestr(name, png)
                manifest["clips"][clip].append({"file": name, "sha256": hashlib.sha256(png).hexdigest(), "mouth": anchor})
                done += 1
                if done % 8 == 0 or done == total:
                    report("motion_baking", done, total)
        archive.writestr("manifest.json", json.dumps(manifest, separators=(",", ":")))
    temporary.replace(target)
