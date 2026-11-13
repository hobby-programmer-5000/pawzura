"""Bounded mesh extraction, multi-view normal-aware projection, geodesic heat skinning, and DQS."""
import math
import numpy as np


def smooth(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1)
    return u * u * (3 - 2 * u)


def rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def rz(points, a):
    c, s = math.cos(a), math.sin(a)
    return points @ np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]], np.float32)


def compute_vertex_normals(vertices, faces):
    """Compute area-weighted unit vertex normals from triangle mesh."""
    normals = np.zeros_like(vertices, dtype=np.float32)
    if len(faces) == 0:
        normals[:, 0] = 1.0
        return normals
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    face_normals = np.cross(v1 - v0, v2 - v0)
    np.add.at(normals, faces[:, 0], face_normals)
    np.add.at(normals, faces[:, 1], face_normals)
    np.add.at(normals, faces[:, 2], face_normals)
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    bad = norms[:, 0] < 1e-8
    normals[~bad] /= norms[~bad]
    normals[bad] = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    return normals


def fair_mesh_taubin(vertices, faces, iterations=4, lam=0.45, mu=-0.47, front_weight=0.35):
    """Volume-preserving Taubin (λ/μ) smoothing with thickness protection removing ripples."""
    from scipy import sparse

    n_verts = len(vertices)
    if n_verts < 16 or len(faces) < 16 or iterations <= 0:
        return vertices.astype(np.float32, copy=True)

    e0 = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    e1 = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    rows = np.concatenate([e0, e1])
    cols = np.concatenate([e1, e0])
    keys = rows.astype(np.int64) * n_verts + cols.astype(np.int64)
    _, uniq = np.unique(keys, return_index=True)
    rows, cols = rows[uniq], cols[uniq]
    adj = sparse.csr_matrix((np.ones(len(rows), dtype=np.float64), (rows, cols)), shape=(n_verts, n_verts))
    deg = np.maximum(np.asarray(adj.sum(axis=1)).ravel(), 1.0)
    avg_op = sparse.diags(1.0 / deg) @ adj

    n0 = compute_vertex_normals(vertices, faces)
    # Preserve crisp +X front artwork silhouette/eyes while fully smoothing unobserved side/back ripples.
    smooth_w = np.where(n0[:, 0] > 0.65, float(front_weight), 1.0).astype(np.float64)[:, None]

    # Thickness protection: if opposing surfaces are very thin, damp Laplacian factor to prevent pinching.
    height = float(np.ptp(vertices[:, 2]))
    if height > 0.05:
        yz_key = (np.round(vertices[:, 1] / (height * 0.05)).astype(np.int32) * 10000 +
                  np.round(vertices[:, 2] / (height * 0.05)).astype(np.int32))
        uniq_yz, inv_yz = np.unique(yz_key, return_inverse=True)
        min_x = np.full(len(uniq_yz), np.inf, dtype=np.float32)
        max_x = np.full(len(uniq_yz), -np.inf, dtype=np.float32)
        np.minimum.at(min_x, inv_yz, vertices[:, 0])
        np.maximum.at(max_x, inv_yz, vertices[:, 0])
        cell_thick = (max_x - min_x)[inv_yz]
        thick_damp = np.clip(cell_thick / max(1e-4, height * 0.06), 0.35, 1.0)[:, None]
        smooth_w = smooth_w * thick_damp.astype(np.float64)

    out = vertices.astype(np.float64, copy=True)
    for _ in range(int(iterations)):
        for k in (float(lam), float(mu)):
            lap = avg_op @ out - out
            out += (k * smooth_w) * lap
    return out.astype(np.float32)


def classify_art_texture(rgb_arr, alpha_arr):
    """Classify character texture into 'flat_2d' (anime/cel-shaded lineart) vs 'shaded_3d' (volumetric/fur/soft-gradient).

    Returns (style: str, metrics: dict).
    """
    import numpy as np
    from scipy.ndimage import binary_erosion, uniform_filter

    rgb = np.asarray(rgb_arr, dtype=np.float32)
    if rgb.max() > 1.5:
        rgb = rgb / 255.0
    alpha = np.asarray(alpha_arr, dtype=np.float32)
    if alpha.max() > 1.5:
        alpha = alpha / 255.0

    fg = alpha > 0.35
    if int(fg.sum()) < 64:
        return "flat_2d", {"style": "flat_2d", "flat_ratio": 1.0, "interior_std": 0.0}

    interior = binary_erosion(fg, iterations=3)
    if int(interior.sum()) < 32:
        interior = fg

    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    dy = np.abs(lum[2:, 1:-1] - lum[:-2, 1:-1])
    dx = np.abs(lum[1:-1, 2:] - lum[1:-1, :-2])
    grad = np.pad(np.sqrt(dx * dx + dy * dy), ((1, 1), (1, 1)), mode="constant")
    interior_grads = grad[interior]
    flat_pixels = (interior_grads < 0.030).sum()
    flat_ratio = float(flat_pixels) / max(1, len(interior_grads))

    mean_lum = uniform_filter(lum, size=5)
    mean_sq = uniform_filter(lum * lum, size=5)
    local_std = np.sqrt(np.maximum(0.0, mean_sq - mean_lum * mean_lum))
    interior_std = float(np.mean(local_std[interior]))

    is_flat_2d = bool(flat_ratio >= 0.46 or interior_std < 0.036)
    style = "flat_2d" if is_flat_2d else "shaded_3d"

    return style, {
        "style": style,
        "flat_ratio": round(flat_ratio, 4),
        "interior_std": round(interior_std, 4),
        "mean_grad": round(float(np.mean(interior_grads)), 4),
    }


def inflate_2_5d_mesh(vertices, faces, points=None, min_depth_ratio=0.52):
    """Inflate collapsed paper-thin 2D/chibi meshes into a natural 2.5D rounded cylinder volume.

    Preserves exact front-view projection (Y and Z coordinates are invariant), while expanding
    depth (X) bilaterally along the local medial axis into an anatomical cylinder/ellipsoid.
    """
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    v_out = vertices.astype(np.float32, copy=True)
    height = float(np.ptp(v_out[:, 2]))
    if height < 0.1 or len(v_out) < 32:
        return (v_out, points.astype(np.float32, copy=True)) if points is not None else v_out

    zmin = float(v_out[:, 2].min())
    zmax = float(v_out[:, 2].max())

    pinch = _find_neck_pinch(v_out)
    z_neck = pinch[0] if pinch is not None else (zmin + height * 0.55)

    head_mask = v_out[:, 2] >= z_neck
    if head_mask.any():
        head_depth = float(np.ptp(v_out[head_mask, 0]))
    else:
        head_depth = height * 0.38
    head_depth = max(height * 0.22, head_depth)

    body_mask = v_out[:, 2] < z_neck
    if not body_mask.any():
        return (v_out, points.astype(np.float32, copy=True)) if points is not None else v_out

    num_slices = 36
    z_bins = np.linspace(zmin, zmax, num_slices + 1)
    dz = (zmax - zmin) / num_slices
    half_band = dz * 1.25

    slice_centers_x = np.zeros(num_slices, dtype=np.float32)
    slice_scales = np.ones(num_slices, dtype=np.float32)
    slice_z = 0.5 * (z_bins[:-1] + z_bins[1:])

    for i in range(num_slices):
        zc = slice_z[i]
        in_band = np.abs(v_out[:, 2] - zc) <= half_band
        if not in_band.any():
            slice_centers_x[i] = float(np.median(v_out[:, 0]))
            continue
        sub = v_out[in_band]
        x_min, x_max = float(sub[:, 0].min()), float(sub[:, 0].max())
        curr_thick = max(1e-4, x_max - x_min)
        slice_centers_x[i] = 0.5 * (x_min + x_max)

        if zc >= z_neck:
            slice_scales[i] = 1.0
        else:
            t_frac = (zc - zmin) / max(1e-4, z_neck - zmin)
            d_profile = 0.62 if t_frac > 0.65 else (0.56 if t_frac > 0.40 else (0.44 if t_frac > 0.15 else 0.50))
            width_sub = max(0.04, float(np.ptp(sub[:, 1])))
            target_depth = max(curr_thick, min(head_depth * d_profile, width_sub * 0.72))
            target_depth = max(target_depth, head_depth * min_depth_ratio * (0.82 + 0.18 * t_frac))
            slice_scales[i] = max(1.0, target_depth / curr_thick)

    smooth_scales = gaussian_filter1d(slice_scales, sigma=1.8, mode="nearest")
    smooth_centers = gaussian_filter1d(slice_centers_x, sigma=2.0, mode="nearest")

    vz = np.clip((v_out[:, 2] - zmin) / (zmax - zmin) * (num_slices - 1), 0.0, num_slices - 1.001)
    iz = vz.astype(np.int32)
    fz = vz - iz
    v_scale = (1.0 - fz) * smooth_scales[iz] + fz * smooth_scales[iz + 1]
    v_center = (1.0 - fz) * smooth_centers[iz] + fz * smooth_centers[iz + 1]
    neck_transition = np.clip((z_neck + dz * 2.0 - v_out[:, 2]) / (dz * 4.0), 0.0, 1.0)

    for i in range(num_slices):
        zc = slice_z[i]
        in_band = np.abs(v_out[:, 2] - zc) <= half_band
        if in_band.any() and slice_scales[i] > 1.02:
            sub_y = v_out[in_band, 1]
            y_mid = 0.5 * (float(sub_y.min()) + float(sub_y.max()))
            y_half_w = max(1e-4, 0.5 * float(np.ptp(sub_y)))
            rel_y = np.clip(np.abs(sub_y - y_mid) / y_half_w, 0.0, 1.0)
            lateral_weight = np.sqrt(np.maximum(0.04, 1.0 - rel_y * rel_y * 0.90))

            dx = v_out[in_band, 0] - v_center[in_band]
            eff_scale = 1.0 + (v_scale[in_band] - 1.0) * lateral_weight * neck_transition[in_band]
            v_out[in_band, 0] = v_center[in_band] + dx * eff_scale

    if points is not None:
        p_out = points.astype(np.float32, copy=True)
        pz = np.clip((p_out[:, 2] - zmin) / (zmax - zmin) * (num_slices - 1), 0.0, num_slices - 1.001)
        ipz = pz.astype(np.int32)
        fpz = pz - ipz
        p_scale = (1.0 - fpz) * smooth_scales[ipz] + fpz * smooth_scales[ipz + 1]
        p_center = (1.0 - fpz) * smooth_centers[ipz] + fpz * smooth_centers[ipz + 1]
        p_neck_tr = np.clip((z_neck + dz * 2.0 - p_out[:, 2]) / (dz * 4.0), 0.0, 1.0)
        p_dx = p_out[:, 0] - p_center
        p_out[:, 0] = p_center + p_dx * (1.0 + (p_scale - 1.0) * p_neck_tr)
        return v_out, p_out

    return v_out


def extract(density, radius=1.0, threshold=25.0):
    """Extract clean watertight-style triangle mesh and surface sample points via marching tetrahedra."""
    n = density.shape[0]
    if density.shape != (n, n, n) or not 32 <= n <= 160 or not np.isfinite(density).all():
        raise ValueError("Invalid density grid")
    axis = np.linspace(-radius, radius, n, dtype=np.float32)
    offsets = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]])
    base = np.stack(np.meshgrid(*[np.arange(n - 1)] * 3, indexing="ij"), -1).reshape(-1, 3)
    values = np.stack([density[base[:, 0] + o[0], base[:, 1] + o[1], base[:, 2] + o[2]] for o in offsets], 1)
    active = (values.min(1) < threshold) & (values.max(1) >= threshold)
    base, values = base[active], values[active]
    positions = axis[base[:, None, :] + offsets[None, :, :]]
    triangles = []
    for tet in ((0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6)):
        val, pos = values[:, tet], positions[:, tet]
        bits = ((val >= threshold) * [1, 2, 4, 8]).sum(1)
        for case in range(1, 15):
            hit = bits == case
            if not hit.any():
                continue
            q, d = pos[hit], val[hit]
            inside = [i for i in range(4) if case & (1 << i)]
            outside = [i for i in range(4) if not case & (1 << i)]

            def edge(a, b):
                t = (threshold - d[:, a]) / (d[:, b] - d[:, a])
                return q[:, a] + t[:, None] * (q[:, b] - q[:, a])

            if len(inside) in (1, 3):
                one, rest = (inside[0], outside) if len(inside) == 1 else (outside[0], inside)
                triangles.append(np.stack([edge(one, j) for j in rest], 1))
            else:
                a, b = inside
                c, d_ = outside
                quad = [edge(a, c), edge(a, d_), edge(b, d_), edge(b, c)]
                triangles += [np.stack([quad[0], quad[1], quad[2]], 1), np.stack([quad[0], quad[2], quad[3]], 1)]
    if not triangles:
        raise ValueError("Empty surface")
    tri = np.concatenate(triangles).astype(np.float32)
    vertices, inverse = np.unique(np.round(tri.reshape(-1, 3), 6), axis=0, return_inverse=True)
    faces = inverse.reshape(-1, 3).astype(np.int32)

    # Prune tiny disconnected mesh islands (e.g., floor shadow crumbs) keeping >= 2% components.
    if len(faces) > 64:
        from scipy import sparse
        from scipy.sparse.csgraph import connected_components
        e0 = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
        e1 = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
        adj = sparse.csr_matrix((np.ones(len(e0) * 2, dtype=np.int8), (np.concatenate([e0, e1]), np.concatenate([e1, e0]))), shape=(len(vertices), len(vertices)))
        n_comp, labels = connected_components(adj, directed=False)
        if n_comp > 1:
            counts = np.bincount(labels)
            keep_comp = counts >= max(24, int(counts.max() * 0.02))
            if not keep_comp.any():
                keep_comp[int(np.argmax(counts))] = True
            keep_v = keep_comp[labels]
            face_keep = keep_v[faces[:, 0]] & keep_v[faces[:, 1]] & keep_v[faces[:, 2]]
            if face_keep.any():
                faces = faces[face_keep]
                used_v, new_inv = np.unique(faces.ravel(), return_inverse=True)
                vertices = vertices[used_v]
                faces = new_inv.reshape(-1, 3).astype(np.int32)
    # Keep triangle orientation consistent with outward density gradient when possible.
    v0 = vertices[faces[:, 0]]
    v1 = vertices[faces[:, 1]]
    v2 = vertices[faces[:, 2]]
    centers = (v0 + v1 + v2) / 3.0
    step = (2.0 * radius) / (n - 1)
    idx_f = np.clip((centers + radius) / step, 0.0, n - 1.001)
    ix = idx_f.astype(np.int32)
    fx = idx_f - ix
    def trilinear(gx, gy, gz):
        return density[gx, gy, gz]
    gx0, gy0, gz0 = ix[:, 0], ix[:, 1], ix[:, 2]
    gx1, gy1, gz1 = np.minimum(gx0 + 1, n - 1), np.minimum(gy0 + 1, n - 1), np.minimum(gz0 + 1, n - 1)
    grad = np.stack([
        trilinear(gx1, gy0, gz0) - trilinear(gx0, gy0, gz0),
        trilinear(gx0, gy1, gz0) - trilinear(gx0, gy0, gz0),
        trilinear(gx0, gy0, gz1) - trilinear(gx0, gy0, gz0),
    ], 1)
    # Density decreases outward, so outward normal points along -grad.
    fn = np.cross(v1 - v0, v2 - v0)
    flip = np.sum(fn * (-grad), axis=1) < 0
    if flip.any():
        faces[flip] = faces[flip][:, [0, 2, 1]]

    if len(tri) <= 42000:
        cloud = [tri[:, 0] * (i / 3) + tri[:, 1] * (j / 3) + tri[:, 2] * ((3 - i - j) / 3) for i in range(4) for j in range(4 - i)]
        points = np.unique(np.round(np.concatenate(cloud), 6), axis=0).astype(np.float32)
    else:
        # Dense meshes (e.g., 128^3) keep vertices + centroids under the 300k safety cap.
        points = np.unique(np.round(np.concatenate([vertices, centers]), 6), axis=0).astype(np.float32)
    if len(points) > 300000 or len(vertices) > 120000 or len(faces) > 240000:
        raise ValueError("Surface too large")
    return vertices, faces, points


def _spherical_camera_basis(az_deg, el_deg, dist):
    """Return camera origin, unit forward (camera->origin), right, up matching tsr.utils.get_spherical_cameras."""
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    cam_dir = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)], dtype=np.float32)
    cam_pos = cam_dir * float(dist)
    lookat = -cam_dir
    world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    right = np.cross(lookat, world_up)
    rn = float(np.linalg.norm(right))
    if rn < 1e-6:
        right = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    else:
        right = (right / rn).astype(np.float32)
    up = np.cross(right, lookat)
    up = (up / max(1e-6, float(np.linalg.norm(up)))).astype(np.float32)
    return cam_pos, cam_dir, right, up


def _visibility_mask(points, u, v, depth, side):
    """Per-view adaptive Z-buffer visibility check with 3x3 continuity to block back-surface bleed without 1-px aliasing dropouts."""
    from scipy.ndimage import minimum_filter

    margin = max(2, side // 96)
    zbuf_side = max(side, min(768, int(round(max(256.0, math.sqrt(max(1, len(points))) * 1.4)))))
    scale = zbuf_side / float(side)
    ui = np.clip(np.rint(u * scale).astype(np.int32), 0, zbuf_side - 1)
    vi = np.clip(np.rint(v * scale).astype(np.int32), 0, zbuf_side - 1)
    valid = (u >= margin) & (u < side - margin) & (v >= margin) & (v < side - margin) & (depth > 0.2)
    zbuf = np.full(zbuf_side * zbuf_side, np.inf, dtype=np.float32)
    hit_idx = np.flatnonzero(valid)
    if len(hit_idx) == 0:
        return np.zeros(len(points), dtype=bool)
    flat = vi[hit_idx] * zbuf_side + ui[hit_idx]
    np.minimum.at(zbuf, flat, depth[hit_idx])
    z2d = minimum_filter(zbuf.reshape(zbuf_side, zbuf_side), size=3)
    visible = np.zeros(len(points), dtype=bool)
    tol = 0.035
    visible[hit_idx] = depth[hit_idx] <= (z2d.ravel()[flat] + tol)
    return visible


def project_multiview_colors(points, views, normals=None, ref_views=None):
    """Project multi-elevation TripoSR views and high-res reference RGBA images onto points/vertices.

    - `views`: either legacy list of equatorial RGB arrays or list of dicts
      `{"rgb": array, "az": deg, "el": deg, "dist": float, "fovy": float, "weight": float}`.
    - `ref_views`: optional list of `{"rgba": array, "az": deg, "el": deg, "weight": float}` for crisp
      silhouette-aligned projection from original 1024px artwork and user/staged angle snapshots.
    """
    from scipy.ndimage import distance_transform_edt, map_coordinates
    from scipy.spatial import cKDTree

    if normals is None:
        normals = np.zeros_like(points, dtype=np.float32)
        normals[:, 0] = 1.0
        horiz = np.hypot(points[:, 0], points[:, 1])
        nz = points[:, 2]
        nvec = np.stack([points[:, 0], points[:, 1], nz * 0.4], 1)
        nlen = np.linalg.norm(nvec, axis=1, keepdims=True)
        normals = np.where(nlen > 1e-5, nvec / np.maximum(nlen, 1e-5), normals).astype(np.float32)

    view_specs = []
    if views and not isinstance(views[0], dict):
        count = len(views)
        for i, rgb in enumerate(views):
            view_specs.append({"rgb": rgb, "az": i * 360.0 / count, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0})
    else:
        view_specs = list(views or [])

    accum = np.zeros((len(points), 3), dtype=np.float32)
    weight_sum = np.zeros(len(points), dtype=np.float32)

    for spec in view_specs:
        rgb_img = spec["rgb"]
        side = rgb_img.shape[0]
        is_bg = (rgb_img.min(axis=2) > 0.93) & ((rgb_img.max(axis=2) - rgb_img.min(axis=2)) < 0.06)
        d_bg_map = distance_transform_edt(~is_bg).astype(np.float32) if is_bg.any() else np.full((side, side), 8.0, dtype=np.float32)
        focal = side * 0.5 / math.tan(math.radians(spec.get("fovy", 40.0) * 0.5))
        cam_pos, cam_dir, right, up = _spherical_camera_basis(spec["az"], spec.get("el", 0.0), spec.get("dist", 1.9))
        rel = points - cam_pos[None, :]
        depth = rel @ (-cam_dir)
        x_cam = rel @ right
        y_cam = rel @ up
        u = side * 0.5 - 0.5 + x_cam * focal / np.maximum(depth, 0.1)
        v = side * 0.5 - 0.5 - y_cam * focal / np.maximum(depth, 0.1)
        vis = _visibility_mask(points, u, v, depth, side)
        ndot = np.clip(normals @ cam_dir, 0.0, 1.0)
        vis &= ndot > 0.08
        if not vis.any():
            continue
        uv_idx = np.flatnonzero(vis)
        sampled = np.stack([map_coordinates(rgb_img[:, :, c], [v[uv_idx], u[uv_idx]], order=1, mode="nearest") for c in range(3)], 1)
        d_bg_s = map_coordinates(d_bg_map, [v[uv_idx], u[uv_idx]], order=1, mode="nearest")
        # Suppress paper-white background halo pixels near silhouette rims without starving cream/ivory clothes.
        sat = sampled.max(1) - sampled.min(1)
        bg_neutral = 1.0 - np.clip(sat / 0.09, 0.0, 1.0)
        bg_likeness = np.clip((sampled.min(1) - 0.85) / 0.11, 0.0, 1.0) * bg_neutral
        rim_interior = np.clip((d_bg_s - 1.2) / 1.5, 0.0, 1.0)
        edge_conf = np.clip((ndot[uv_idx] - 0.08) / 0.35, 0.05, 1.0) * np.where(ndot[uv_idx] < 0.65, rim_interior, np.maximum(0.25, rim_interior))
        drop_rim = (
            (d_bg_s <= 1.05) & (ndot[uv_idx] < 0.58)
            | ((sampled.min(1) > 0.85) & (bg_neutral > 0.45) & (ndot[uv_idx] < 0.32))
            | ((sampled.min(1) > 0.90) & (bg_neutral > 0.55) & (ndot[uv_idx] < 0.38))
        )
        w = np.where(drop_rim, 0.0, (ndot[uv_idx] ** 2.4) * edge_conf * float(spec.get("weight", 1.0)) * (1.0 - 0.85 * bg_likeness * (1.0 - ndot[uv_idx])))
        accum[uv_idx] += sampled * w[:, None]
        weight_sum[uv_idx] += w

    # High-resolution silhouette-aligned reference image projection (e.g., original 1024px front drawing + side/back snapshots).
    for ref in (ref_views or ()):
        rgba = np.asarray(ref["rgba"], dtype=np.float32)
        if rgba.max() > 1.5:
            rgba = rgba / 255.0
        h_img, w_img = rgba.shape[:2]
        alpha = rgba[:, :, 3] if rgba.shape[2] == 4 else (rgba.min(2) < 0.96).astype(np.float32)
        d_alpha = distance_transform_edt(alpha > 0.85).astype(np.float32)
        # Use solid opaque silhouette (ignoring faint ground shadows) to align bounding boxes accurately.
        fg_y, fg_x = np.where(alpha > 0.72)
        if len(fg_x) < 16:
            fg_y, fg_x = np.where(alpha > 0.25)
        if len(fg_x) < 16:
            continue
        x0, x1 = float(fg_x.min()), float(fg_x.max())
        y0, y1 = float(fg_y.min()), float(fg_y.max())

        _, cam_dir, right, up = _spherical_camera_basis(ref["az"], ref.get("el", 0.0), 1.9)
        cam_pos = cam_dir * 1.9
        rel = points - cam_pos[None, :]
        depth = rel @ (-cam_dir)
        # Use orthographic-like mesh bounds in (right, up) plane aligned cleanly to reference foreground bbox.
        px_r = points @ right
        px_u = points @ up
        ndot = np.clip(normals @ cam_dir, 0.0, 1.0)
        front_pts = ndot > 0.28
        if not front_pts.any():
            continue
        r_min, r_max = float(px_r.min()), float(px_r.max())
        u_min, u_max = float(px_u.min()), float(px_u.max())
        u_norm = (px_r - r_min) / max(1e-5, r_max - r_min)
        v_norm = 1.0 - (px_u - u_min) / max(1e-5, u_max - u_min)
        u_img = x0 + u_norm * (x1 - x0)
        v_img = y0 + v_norm * (y1 - y0)

        vis = _visibility_mask(points, u_norm * 256.0, v_norm * 256.0, depth, 256)
        vis &= front_pts & (u_img >= 0) & (u_img < w_img - 1) & (v_img >= 0) & (v_img < h_img - 1)
        if not vis.any():
            continue
        idx = np.flatnonzero(vis)
        a_sample = map_coordinates(alpha, [v_img[idx], u_img[idx]], order=1, mode="nearest")
        keep = a_sample > 0.94
        if not keep.any():
            continue
        idx = idx[keep]
        a_sample = a_sample[keep]
        d_edge = map_coordinates(d_alpha, [v_img[idx], u_img[idx]], order=1, mode="nearest")
        # Prevent outer 2-px dark ink border on front 2D artwork from smearing across grazing temple/jaw/arm sides.
        ink_taper = np.where(ndot[idx] < 0.55, np.clip((d_edge - 1.8) / 2.2, 0.0, 1.0), 1.0)
        rgb_sample = np.stack([map_coordinates(rgba[:, :, c], [v_img[idx], u_img[idx]], order=1, mode="nearest") for c in range(3)], 1)
        boost = float(ref.get("weight", 4.5))
        w = boost * (ndot[idx] ** 2.6) * a_sample * ink_taper
        accum[idx] += rgb_sample * w[:, None]
        weight_sum[idx] += w

    # Fill any tiny unhit crevices via nearest colored neighbor.
    unhit = weight_sum < 1e-5
    colors = np.zeros((len(points), 3), dtype=np.float32)
    hit = ~unhit
    if hit.any():
        colors[hit] = accum[hit] / weight_sum[hit, None]
    if unhit.any() and hit.any():
        _, near = cKDTree(points[hit]).query(points[unhit])
        colors[unhit] = colors[hit][near]

    # Backside clean-fill pass: Prevent front facial features or chest zippers from mirroring onto back surface
    # when no dedicated rear camera view is available.
    has_back = any(abs(float(v.get("az", 0.0)) - 180.0) < 45.0 for v in (views or ())) or any(
        abs(float(r.get("az", 0.0)) - 180.0) < 45.0 for r in (ref_views or ())
    )
    height = float(np.ptp(points[:, 2]))
    zmin = float(points[:, 2].min())
    x_med = float(np.median(points[:, 0]))
    is_back = (normals[:, 0] < -0.15) & (points[:, 0] < x_med)

    if not has_back and is_back.any() and hit.any():
        pinch = _find_neck_pinch(points)
        z_neck = pinch[0] if pinch is not None else (zmin + height * 0.55)

        # 1. Back of head: must be clean hair color, suppressing any front facial bleed
        back_head = is_back & (points[:, 2] >= z_neck)
        if back_head.any():
            crown = (points[:, 2] > zmin + height * 0.82) & hit
            if crown.any():
                hair_color = np.median(colors[crown], axis=0)
                colors[back_head] = colors[back_head] * 0.25 + hair_color * 0.75

        # 2. Back of torso: must be clean coat/shirt color, suppressing front zippers/badges
        back_torso = is_back & (points[:, 2] < z_neck) & (points[:, 2] > zmin + height * 0.25)
        if back_torso.any():
            side_torso = (points[:, 2] < z_neck) & (points[:, 2] > zmin + height * 0.30) & (abs(points[:, 1] - float(np.median(points[:, 1]))) > height * 0.08) & hit
            if side_torso.any():
                coat_color = np.median(colors[side_torso], axis=0)
                colors[back_torso] = colors[back_torso] * 0.30 + coat_color * 0.70

    # Localized cleanup for isolated neutral/tinted white halo specks on head rim, rear seam, and boot soles (never front torso/sleeves).
    sat_col = colors.max(1) - colors.min(1)
    back_side = points[:, 0] < x_med - height * 0.02
    region = (points[:, 2] > zmin + height * 0.64) | (points[:, 2] < zmin + height * 0.25) | back_side
    neutral_white = (
        ((colors.min(1) > 0.86) & (sat_col < 0.08))
        | ((colors.min(1) > 0.78) & (sat_col < 0.065) & ((points[:, 0] < x_med + height * 0.03) | (points[:, 2] < zmin + height * 0.25)))
        | (back_side & (colors.min(1) > 0.66) & (sat_col < 0.14))
    )
    bad = region & neutral_white
    good = region & (colors.min(1) < 0.70)
    if good.any() and bad.any():
        distances, near = cKDTree(points[good]).query(points[bad])
        use = distances < height * 0.032
        colors[np.flatnonzero(bad)[use]] = colors[good][near[use]]
    sole_bad = (points[:, 2] < zmin + height * 0.045) & (colors.min(1) > 0.72) & (sat_col < 0.095)
    sole_good = (points[:, 2] < zmin + height * 0.15) & (colors.min(1) < 0.65)
    if sole_good.any() and sole_bad.any():
        distances, near = cKDTree(points[sole_good]).query(points[sole_bad])
        use = distances < height * 0.065
        colors[np.flatnonzero(sole_bad)[use]] = colors[sole_good][near[use]]
    return np.clip(colors, 0.0, 1.0).astype(np.float32)


def projected_colors(points, views):
    """Backwards-compatible entry point delegating to normal-aware multiview projection."""
    return project_multiview_colors(points, views)


def _rasterize_subchart_uv(fx, fy, fz, tw, th, accept_margin=-0.015, skirt_margin=-0.25):
    """Vectorized barycentric chart rasterizer returning packed zbuf and valid indices."""
    xmin = np.clip(np.floor(np.minimum(np.minimum(fx[:, 0], fx[:, 1]), fx[:, 2])).astype(np.int32), 0, tw - 1)
    xmax = np.clip(np.ceil(np.maximum(np.maximum(fx[:, 0], fx[:, 1]), fx[:, 2])).astype(np.int32), 0, tw - 1)
    ymin = np.clip(np.floor(np.minimum(np.minimum(fy[:, 0], fy[:, 1]), fy[:, 2])).astype(np.int32), 0, th - 1)
    ymax = np.clip(np.ceil(np.maximum(np.maximum(fy[:, 0], fy[:, 1]), fy[:, 2])).astype(np.int32), 0, th - 1)
    area2 = (fx[:, 1] - fx[:, 0]) * (fy[:, 2] - fy[:, 0]) - (fy[:, 1] - fy[:, 0]) * (fx[:, 2] - fx[:, 0])
    inv_a = np.where(np.abs(area2) > 1e-5, 1.0 / np.where(np.abs(area2) > 1e-5, area2, 1.0), 0.0)
    max_b = np.maximum(xmax - xmin + 1, ymax - ymin + 1)

    zbuf = np.zeros(th * tw, dtype=np.uint64)
    z0, z1, z2 = fz[:, 0], fz[:, 1], fz[:, 2]
    for limit, prev in ((4, 0), (8, 4), (16, 8), (32, 16), (64, 32), (128, 64)):
        mask = (max_b > prev) & (max_b <= limit) & (np.abs(area2) > 1e-5)
        if not mask.any():
            continue
        ii = np.flatnonzero(mask)
        gx, gy = np.meshgrid(np.arange(limit, dtype=np.float32), np.arange(limit, dtype=np.float32))
        px = xmin[ii, None] + gx.ravel()[None, :].astype(np.int32)
        py = ymin[ii, None] + gy.ravel()[None, :].astype(np.int32)
        in_b = (px <= xmax[ii, None]) & (py <= ymax[ii, None]) & (px < tw) & (py < th)
        cx = px.astype(np.float32) + 0.5
        cy = py.astype(np.float32) + 0.5
        ia = inv_a[ii, None]
        w0 = ((fx[ii, 1:2] - cx) * (fy[ii, 2:3] - cy) - (fy[ii, 1:2] - cy) * (fx[ii, 2:3] - cx)) * ia
        w1 = ((fx[ii, 2:3] - cx) * (fy[ii, 0:1] - cy) - (fy[ii, 2:3] - cy) * (fx[ii, 0:1] - cx)) * ia
        w2 = 1.0 - w0 - w1
        inside = in_b & (w0 >= accept_margin) & (w1 >= accept_margin) & (w2 >= accept_margin)
        if skirt_margin is not None:
            skirt = in_b & (~inside) & (w0 >= skirt_margin) & (w1 >= skirt_margin) & (w2 >= skirt_margin)
            tiers = ((2, inside), (1, skirt))
        else:
            tiers = ((2, inside),)
        for tier_flag, hit in tiers:
            if not hit.any():
                continue
            ti, pi = np.where(hit)
            w0h = np.clip(w0[ti, pi], 0.0, 1.0)
            w1h = np.clip(w1[ti, pi], 0.0, 1.0)
            w2h = np.clip(w2[ti, pi], 0.0, 1.0)
            wsum = np.maximum(w0h + w1h + w2h, 1e-6)
            zh = (w0h * z0[ii[ti]] + w1h * z1[ii[ti]] + w2h * z2[ii[ti]]) / wsum
            zq = np.clip(np.rint((zh + 4.0) * 1e5), 0, (1 << 21) - 1).astype(np.uint64)
            packed = (np.uint64(tier_flag) << 43) | (zq << 22) | (np.uint64(1) << 21) | ii[ti].astype(np.uint64)
            np.maximum.at(zbuf, py[ti, pi] * tw + px[ti, pi], packed)

    # Fallback for giant single faces (>128px) if tiny atlas grid scales up cleanly.
    large = np.flatnonzero((max_b > 128) & (np.abs(area2) > 1e-5))
    for ti in large:
        xs = np.arange(xmin[ti], xmax[ti] + 1, dtype=np.float32) + 0.5
        ys = np.arange(ymin[ti], ymax[ti] + 1, dtype=np.float32) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        ia = inv_a[ti]
        w0 = ((fx[ti, 1] - gx) * (fy[ti, 2] - gy) - (fy[ti, 1] - gy) * (fx[ti, 2] - gx)) * ia
        w1 = ((fx[ti, 2] - gx) * (fy[ti, 0] - gy) - (fy[ti, 2] - gy) * (fx[ti, 0] - gx)) * ia
        w2 = 1.0 - w0 - w1
        inside = (w0 >= accept_margin) & (w1 >= accept_margin) & (w2 >= accept_margin)
        if not inside.any():
            continue
        w0h, w1h, w2h = np.clip(w0[inside], 0.0, 1.0), np.clip(w1[inside], 0.0, 1.0), np.clip(w2[inside], 0.0, 1.0)
        wsum = np.maximum(w0h + w1h + w2h, 1e-6)
        zh = (w0h * z0[ti] + w1h * z1[ti] + w2h * z2[ti]) / wsum
        zq = np.clip(np.rint((zh + 4.0) * 1e5), 0, (1 << 21) - 1).astype(np.uint64)
        packed = (np.uint64(2) << 43) | (zq << 22) | (np.uint64(1) << 21) | np.uint64(ti)
        px_h = np.clip(np.rint(gx[inside] - 0.5).astype(np.int32), 0, tw - 1)
        py_h = np.clip(np.rint(gy[inside] - 0.5).astype(np.int32), 0, th - 1)
        np.maximum.at(zbuf, py_h * tw + px_h, packed)

    # Tier-0 subpixel centroid splat guarantees even sub-texel slivers get covered in cov_mask.
    c_px = np.clip(np.rint(fx.mean(axis=1) - 0.5).astype(np.int32), 0, tw - 1)
    c_py = np.clip(np.rint(fy.mean(axis=1) - 0.5).astype(np.int32), 0, th - 1)
    c_zq = np.clip(np.rint((fz.mean(axis=1) + 4.0) * 1e5), 0, (1 << 21) - 1).astype(np.uint64)
    c_packed = (c_zq << 22) | (np.uint64(1) << 21) | np.arange(len(fx), dtype=np.uint64)
    np.maximum.at(zbuf, c_py * tw + c_px, c_packed)
    return zbuf, inv_a


def _peel_nonoverlapping_subcharts(f_global, pu, pv, pz, faces, grid_n=320):
    """Peel a directional face subset into non-overlapping depth layers using interior texel collision detection."""
    if len(f_global) == 0:
        return []
    margin = 2
    fv = faces[f_global].ravel()
    u_min, u_max = float(pu[fv].min()), float(pu[fv].max())
    v_min, v_max = float(pv[fv].min()), float(pv[fv].max())
    scale_g = (grid_n - 2 * margin) / max(1e-4, u_max - u_min, v_max - v_min)
    gx_v = (margin + (pu - u_min) * scale_g).astype(np.float32)
    gy_v = (margin + (pv - v_min) * scale_g).astype(np.float32)

    rem = np.arange(len(f_global), dtype=np.int32)
    layers = []
    for peel_idx in range(4):
        if len(rem) == 0:
            break
        fr = faces[f_global[rem]]
        fx = gx_v[fr]
        fy = gy_v[fr]
        fz = pz[fr]
        xmin = np.clip(np.floor(fx.min(axis=1)).astype(np.int32), 0, grid_n - 1)
        xmax = np.clip(np.ceil(fx.max(axis=1)).astype(np.int32), 0, grid_n - 1)
        ymin = np.clip(np.floor(fy.min(axis=1)).astype(np.int32), 0, grid_n - 1)
        ymax = np.clip(np.ceil(fy.max(axis=1)).astype(np.int32), 0, grid_n - 1)
        area2 = (fx[:, 1] - fx[:, 0]) * (fy[:, 2] - fy[:, 0]) - (fy[:, 1] - fy[:, 0]) * (fx[:, 2] - fx[:, 0])
        inv_a = np.where(np.abs(area2) > 1e-4, 1.0 / np.where(np.abs(area2) > 1e-4, area2, 1.0), 0.0)
        max_b = np.maximum(xmax - xmin + 1, ymax - ymin + 1)

        zbuf = np.zeros(grid_n * grid_n, dtype=np.uint64)
        # Collect interior fragment checks to identify faces occluded by an overhang in the same direction.
        frag_loc = []
        frag_flat = []
        frag_zq = []
        for limit, prev in ((4, 0), (8, 4), (16, 8), (32, 16), (64, 32)):
            mask = (max_b > prev) & (max_b <= limit) & (np.abs(area2) > 1e-4)
            if not mask.any():
                continue
            ii = np.flatnonzero(mask)
            ggrid_x, ggrid_y = np.meshgrid(np.arange(limit, dtype=np.float32), np.arange(limit, dtype=np.float32))
            px = xmin[ii, None] + ggrid_x.ravel()[None, :].astype(np.int32)
            py = ymin[ii, None] + ggrid_y.ravel()[None, :].astype(np.int32)
            in_b = (px <= xmax[ii, None]) & (py <= ymax[ii, None]) & (px < grid_n) & (py < grid_n)
            cx = px.astype(np.float32) + 0.5
            cy = py.astype(np.float32) + 0.5
            ia = inv_a[ii, None]
            w0 = ((fx[ii, 1:2] - cx) * (fy[ii, 2:3] - cy) - (fy[ii, 1:2] - cy) * (fx[ii, 2:3] - cx)) * ia
            w1 = ((fx[ii, 2:3] - cx) * (fy[ii, 0:1] - cy) - (fy[ii, 2:3] - cy) * (fx[ii, 0:1] - cx)) * ia
            w2 = 1.0 - w0 - w1
            hit = in_b & (w0 >= 0.02) & (w1 >= 0.02) & (w2 >= 0.02)
            if not hit.any():
                continue
            ti, pi = np.where(hit)
            w0h, w1h, w2h = np.clip(w0[ti, pi], 0.0, 1.0), np.clip(w1[ti, pi], 0.0, 1.0), np.clip(w2[ti, pi], 0.0, 1.0)
            wsum = np.maximum(w0h + w1h + w2h, 1e-6)
            zh = (w0h * fz[ii[ti], 0] + w1h * fz[ii[ti], 1] + w2h * fz[ii[ti], 2]) / wsum
            zq = np.clip(np.rint((zh + 4.0) * 1e5), 0, (1 << 21) - 1).astype(np.uint64)
            loc_i = ii[ti].astype(np.uint64)
            packed = (zq << 21) | (np.uint64(1) << 20) | loc_i
            flat_p = (py[ti, pi] * grid_n + px[ti, pi]).astype(np.int32)
            np.maximum.at(zbuf, flat_p, packed)
            frag_loc.append(loc_i)
            frag_flat.append(flat_p)
            frag_zq.append(zq)

        # Also probe subpixel centroids of tiny faces so thin slivers under overhangs are caught cleanly.
        c_px = np.clip(np.rint(fx.mean(axis=1) - 0.5).astype(np.int32), 0, grid_n - 1)
        c_py = np.clip(np.rint(fy.mean(axis=1) - 0.5).astype(np.int32), 0, grid_n - 1)
        c_flat = (c_py * grid_n + c_px).astype(np.int32)
        c_loc = np.arange(len(rem), dtype=np.uint64)
        c_zq = np.clip(np.rint((fz.mean(axis=1) + 4.0) * 1e5), 0, (1 << 21) - 1).astype(np.uint64)
        np.maximum.at(zbuf, c_flat, (c_zq << 21) | (np.uint64(1) << 20) | c_loc)
        frag_loc.append(c_loc)
        frag_flat.append(c_flat)
        frag_zq.append(c_zq)

        all_loc = np.concatenate(frag_loc)
        all_flat = np.concatenate(frag_flat)
        all_zq = np.concatenate(frag_zq)
        win_pack = zbuf[all_flat]
        win_loc = (win_pack & np.uint64((1 << 20) - 1)).astype(np.int64)
        win_zq = win_pack >> 21
        lose = (win_loc != all_loc.astype(np.int64)) & ((win_zq > all_zq + 1) | ((win_zq >= all_zq) & (win_loc < all_loc.astype(np.int64))))
        occluded = np.zeros(len(rem), dtype=bool)
        if lose.any():
            l_me = all_loc[lose].astype(np.int32)
            l_win = win_loc[lose].astype(np.int32)
            shares_v = (fr[l_me, :, None] == fr[l_win, None, :]).any(axis=(1, 2))
            conflict_me = l_me[~shares_v]
            if len(conflict_me):
                occluded[conflict_me] = True

        acc = ~occluded
        if acc.any():
            layers.append((peel_idx, f_global[rem[acc]]))
        rem = rem[occluded]
        if len(rem) < 12:
            break
    if len(rem) > 0:
        layers.append((len(layers), f_global[rem]))
    return layers


def bake_texture_atlas(vertices, faces, normals, views, ref_views=None, atlas_w=1280, atlas_h=1280):
    """Pack a non-overlapping 6-direction depth-peeled UV atlas with shelf bin-packing & bounded EDT gutters."""
    from scipy.ndimage import distance_transform_edt, median_filter

    n_faces = len(faces)
    face_uvs = np.full((n_faces, 3, 2), -1.0, dtype=np.float32)
    atlas = np.zeros((atlas_h, atlas_w, 3), dtype=np.uint8)
    if n_faces == 0 or len(vertices) < 3:
        return atlas, face_uvs

    # 6 orthographic axes: +X/+Y/-X/-Y side envelope plus +Z/-Z crown & soles; front +X gets boosted texel priority.
    charts_cfg = [
        (np.array([1.0, 0.0, 0.0], np.float32), np.array([0.0, 1.0, 0.0], np.float32), np.array([0.0, 0.0, -1.0], np.float32), 1.40),
        (np.array([-1.0, 0.0, 0.0], np.float32), np.array([0.0, -1.0, 0.0], np.float32), np.array([0.0, 0.0, -1.0], np.float32), 1.08),
        (np.array([0.0, 1.0, 0.0], np.float32), np.array([-1.0, 0.0, 0.0], np.float32), np.array([0.0, 0.0, -1.0], np.float32), 1.15),
        (np.array([0.0, -1.0, 0.0], np.float32), np.array([1.0, 0.0, 0.0], np.float32), np.array([0.0, 0.0, -1.0], np.float32), 1.15),
        (np.array([0.0, 0.0, 1.0], np.float32), np.array([0.0, 1.0, 0.0], np.float32), np.array([-1.0, 0.0, 0.0], np.float32), 0.92),
        (np.array([0.0, 0.0, -1.0], np.float32), np.array([0.0, 1.0, 0.0], np.float32), np.array([1.0, 0.0, 0.0], np.float32), 0.78),
    ]
    dirs = np.stack([c[0] for c in charts_cfg], axis=0)

    n_sm = normals.astype(np.float32).copy()
    for _ in range(3):
        acc = np.zeros_like(n_sm)
        fn_avg = n_sm[faces].mean(axis=1)
        for corner in range(3):
            np.add.at(acc, faces[:, corner], fn_avg)
        ln = np.linalg.norm(acc, axis=1, keepdims=True)
        n_sm = np.where(ln > 1e-6, acc / np.maximum(ln, 1e-6), n_sm).astype(np.float32)

    sn = n_sm[faces].mean(axis=1)
    sn_len = np.linalg.norm(sn, axis=1, keepdims=True)
    sn = np.where(sn_len > 1e-8, sn / np.maximum(sn_len, 1e-8), np.array([1.0, 0.0, 0.0], np.float32))
    v0_all = vertices[faces[:, 0]]
    v1_all = vertices[faces[:, 1]]
    v2_all = vertices[faces[:, 2]]
    fn_raw = np.cross(v1_all - v0_all, v2_all - v0_all)
    fn_len = np.linalg.norm(fn_raw, axis=1, keepdims=True)
    fn_unit = np.where(fn_len > 1e-10, fn_raw / np.maximum(fn_len, 1e-10), sn)

    dots_sm = sn @ dirs.T
    dots_raw = fn_unit @ dirs.T
    # Keep every triangle strictly front-facing inside its assigned direction so UV islands never fold inside out.
    score = np.where(dots_raw > 0.02, dots_sm, -2.0 + dots_raw)
    chart_of_face = np.argmax(score, axis=1)

    subcharts = []
    for k, (view_d, ax_u, ax_v, base_prio) in enumerate(charts_cfg):
        f_dir = np.flatnonzero(chart_of_face == k)
        if not len(f_dir):
            continue
        pu = (vertices @ ax_u).astype(np.float32)
        pv = (vertices @ ax_v).astype(np.float32)
        pz = (vertices @ view_d).astype(np.float32)
        layers = _peel_nonoverlapping_subcharts(f_dir, pu, pv, pz, faces)
        for layer_idx, layer_faces in layers:
            if layer_idx == 0:
                fv = faces[layer_faces].ravel()
                u_min, u_max = float(pu[fv].min()), float(pu[fv].max())
                v_min, v_max = float(pv[fv].min()), float(pv[fv].max())
                subcharts.append({
                    "k": k, "layer": 0, "faces": layer_faces, "pu": pu, "pv": pv, "pz": pz,
                    "u_min": u_min, "u_max": u_max, "v_min": v_min, "v_max": v_max, "prio": base_prio,
                })
            else:
                # Partition sparse peel layers into a 3x3 spatial grid to eliminate empty atlas dead-space.
                fc_u = pu[faces[layer_faces]].mean(axis=1)
                fc_v = pv[faces[layer_faces]].mean(axis=1)
                lu0, lu1 = float(fc_u.min()), float(fc_u.max())
                lv0, lv1 = float(fc_v.min()), float(fc_v.max())
                du_l = max(1e-4, lu1 - lu0)
                dv_l = max(1e-4, lv1 - lv0)
                bu = np.clip(((fc_u - lu0) / du_l * 3.0).astype(np.int32), 0, 2)
                bv = np.clip(((fc_v - lv0) / dv_l * 3.0).astype(np.int32), 0, 2)
                cell_ids = bv * 3 + bu
                for cid in range(9):
                    cf = layer_faces[cell_ids == cid]
                    if not len(cf):
                        continue
                    fv = faces[cf].ravel()
                    subcharts.append({
                        "k": k, "layer": layer_idx, "faces": cf, "pu": pu, "pv": pv, "pz": pz,
                        "u_min": float(pu[fv].min()), "u_max": float(pu[fv].max()),
                        "v_min": float(pv[fv].min()), "v_max": float(pv[fv].max()),
                        "prio": max(0.75, base_prio * (0.78 if layer_idx == 1 else 0.68)),
                    })

    if not subcharts:
        return atlas, face_uvs

    pad = max(3, min(6, min(atlas_w, atlas_h) // 256))
    min_inner = max(8, min(atlas_w, atlas_h) // 96)

    def _try_shelf_pack(scale_val):
        items = []
        for idx_s, sc in enumerate(subcharts):
            du = max(1e-4, sc["u_max"] - sc["u_min"])
            dv = max(1e-4, sc["v_max"] - sc["v_min"])
            iw = max(min_inner, int(math.ceil(du * sc["prio"] * scale_val)))
            ih = max(min_inner, int(math.ceil(dv * sc["prio"] * scale_val)))
            bw = iw + 2 * pad
            bh = ih + 2 * pad
            if bw > atlas_w or bh > atlas_h:
                return None
            items.append((bh, bw, iw, ih, idx_s))
        items.sort(key=lambda x: (-x[0], -x[1]))
        cx, cy, shelf_h = 0, 0, 0
        placed = [None] * len(subcharts)
        for bh, bw, iw, ih, idx_s in items:
            if cx + bw > atlas_w:
                cy += shelf_h
                cx = 0
                shelf_h = 0
            if cy + bh > atlas_h:
                return None
            placed[idx_s] = (cx, cy, bw, bh, iw, ih)
            cx += bw
            if bh > shelf_h:
                shelf_h = bh
        return placed

    lo, hi = 1.0, float(max(atlas_w, atlas_h)) * 3.0
    best_placed = _try_shelf_pack(lo)
    if best_placed is None:
        lo = 0.25
        best_placed = _try_shelf_pack(lo)
    for _ in range(14):
        mid = 0.5 * (lo + hi)
        trial = _try_shelf_pack(mid)
        if trial is not None:
            best_placed = trial
            lo = mid
        else:
            hi = mid
    if best_placed is None:
        return atlas, face_uvs

    cov_mask = np.zeros((atlas_h, atlas_w), dtype=bool)
    tex_pts_map = np.zeros((atlas_h, atlas_w, 3), dtype=np.float32)
    tex_nrm_map = np.zeros((atlas_h, atlas_w, 3), dtype=np.float32)
    tex_nrm_map[:, :, 0] = 1.0
    placed_boxes = []

    for sc, box in zip(subcharts, best_placed):
        bx, by, bw, bh, iw, ih = box
        f_own = sc["faces"]
        pu, pv, pz = sc["pu"], sc["pv"], sc["pz"]
        u_min, u_max = sc["u_min"], sc["u_max"]
        v_min, v_max = sc["v_min"], sc["v_max"]
        sx_s = iw / max(1e-4, u_max - u_min)
        sy_s = ih / max(1e-4, v_max - v_min)

        lx_v = (pad + (pu - u_min) * sx_s).astype(np.float32)
        ly_v = (pad + (pv - v_min) * sy_s).astype(np.float32)
        fr = faces[f_own]
        fx = lx_v[fr]
        fy = ly_v[fr]
        fz = pz[fr]

        # Record exact UV corners normalized to global atlas [0, 1].
        face_uvs[f_own, :, 0] = (bx + fx) / float(atlas_w)
        face_uvs[f_own, :, 1] = (by + fy) / float(atlas_h)

        zbuf, inv_a = _rasterize_subchart_uv(fx, fy, fz, bw, bh, accept_margin=-0.015, skirt_margin=-0.08)
        valid_p = np.flatnonzero(zbuf > 0)
        if not len(valid_p):
            continue
        win_loc = (zbuf[valid_p] & np.uint64((1 << 21) - 1)).astype(np.int32)
        py_v = (valid_p // bw).astype(np.float32) + 0.5
        px_v = (valid_p % bw).astype(np.float32) + 0.5
        ia_v = inv_a[win_loc]
        w0v = ((fx[win_loc, 1] - px_v) * (fy[win_loc, 2] - py_v) - (fy[win_loc, 1] - py_v) * (fx[win_loc, 2] - px_v)) * ia_v
        w1v = ((fx[win_loc, 2] - px_v) * (fy[win_loc, 0] - py_v) - (fy[win_loc, 2] - py_v) * (fx[win_loc, 0] - px_v)) * ia_v
        w2v = 1.0 - w0v - w1v
        w0v, w1v, w2v = np.clip(w0v, 0.0, 1.0), np.clip(w1v, 0.0, 1.0), np.clip(w2v, 0.0, 1.0)
        ws = np.maximum(w0v + w1v + w2v, 1e-6)
        w0v /= ws
        w1v /= ws
        w2v /= ws

        f_win = fr[win_loc]
        pts_v = w0v[:, None] * vertices[f_win[:, 0]] + w1v[:, None] * vertices[f_win[:, 1]] + w2v[:, None] * vertices[f_win[:, 2]]
        nrm_v = w0v[:, None] * normals[f_win[:, 0]] + w1v[:, None] * normals[f_win[:, 1]] + w2v[:, None] * normals[f_win[:, 2]]
        nlen = np.linalg.norm(nrm_v, axis=1, keepdims=True)
        nrm_v = nrm_v / np.maximum(nlen, 1e-6)

        ay = by + (valid_p // bw)
        ax = bx + (valid_p % bw)
        cov_mask[ay, ax] = True
        tex_pts_map[ay, ax] = pts_v
        tex_nrm_map[ay, ax] = nrm_v
        placed_boxes.append((sc["k"], sc["layer"], bx, by, bw, bh))

    yy_c, xx_c = np.where(cov_mask)
    if len(yy_c):
        tex_colors = project_multiview_colors(tex_pts_map[yy_c, xx_c], views, normals=tex_nrm_map[yy_c, xx_c], ref_views=ref_views)
        atlas_f = np.zeros((atlas_h, atlas_w, 3), dtype=np.float32)
        atlas_f[yy_c, xx_c] = tex_colors
        # Bounded per-subchart EDT dilation BEFORE median despeckle prevents black border bleeding and inter-chart leakage.
        for k, layer_idx, bx, by, bw, bh in placed_boxes:
            tile = atlas_f[by:by + bh, bx:bx + bw]
            tcov = cov_mask[by:by + bh, bx:bx + bw]
            if not tcov.any():
                continue
            if not (k == 0 and layer_idx == 0) and int(tcov.sum()) >= 6:
                # Despeckle bright rim outliers BEFORE gutter dilation so boundary specks never replicate into ~tcov.
                lum = tile.mean(axis=2)
                w_cov = tcov.astype(np.float32)
                from scipy.ndimage import uniform_filter
                cnt5 = uniform_filter(w_cov, size=5, mode="constant") * 25.0
                sum5 = np.stack([uniform_filter(tile[:, :, c] * w_cov, size=5, mode="constant") * 25.0 for c in range(3)], axis=2)
                avg5 = sum5 / np.maximum(cnt5[:, :, None], 1.0)
                rim_spike = tcov & (cnt5 >= 4.0) & ((lum - avg5.mean(axis=2)) > 0.16)
                if rim_spike.any():
                    tile[rim_spike] = avg5[rim_spike]
            if not tcov.all():
                _, nearest_rc = distance_transform_edt(~tcov, return_indices=True)
                tile_filled = tile[nearest_rc[0], nearest_rc[1]]
            else:
                tile_filled = tile.copy()
            med = median_filter(tile_filled, size=(3, 3, 1))
            thresh = 0.20 if (k == 0 and layer_idx == 0) else 0.13
            spike = tcov & (np.abs(tile_filled - med).mean(axis=2) > thresh)
            if spike.any():
                tile_filled[spike] = med[spike]
            tile[:] = tile_filled
        atlas = np.rint(np.clip(atlas_f, 0.0, 1.0) * 255.0).astype(np.uint8)
    return atlas, face_uvs


def lift(points, uv):
    from scipy.spatial import cKDTree
    depth = 1.9 - points[:, 0]
    focal = 0.5 / math.tan(math.radians(20))
    projected = np.stack([0.5 + points[:, 1] * focal / depth, 0.5 - points[:, 2] * focal / depth], 1)
    _, nearest = cKDTree(projected).query(np.asarray(uv), k=48)
    return np.median(points[nearest], axis=1).astype(np.float32)


def lift_medial(points, uv):
    """Lift 2D normalized landmarks and center each joint inside local mesh front/back thickness."""
    from scipy.spatial import cKDTree
    front = lift(points, uv)
    height = max(0.1, float(np.ptp(points[:, 2])))
    yz = points[:, 1:3]
    tree = cKDTree(yz)
    centered = front.copy()
    radius = height * 0.045
    max_thick = height * 0.22
    for i, pt in enumerate(front):
        neighbors = tree.query_ball_point(pt[1:3], r=radius)
        if len(neighbors) >= 6:
            xs = points[neighbors, 0]
            x_front = float(np.percentile(xs, 92))
            x_back = float(np.percentile(xs, 8))
            # Clamp excessive back depth (e.g., long flowing cape/ponytail behind torso).
            if x_front - x_back > max_thick:
                x_back = max(x_back, x_front - max_thick)
            centered[i, 0] = 0.5 * (x_front + x_back)
        else:
            centered[i, 0] = float(np.median(points[:, 0]) * 0.6 + pt[0] * 0.4)
    return centered.astype(np.float32)


def _find_neck_pinch(vertices):
    """Locate the narrowest neck/chin waist between wide cranium above and shoulders/torso below."""
    height = float(np.ptp(vertices[:, 2]))
    if height < 0.1 or len(vertices) < 64:
        return None
    zmin = float(vertices[:, 2].min())
    zs = np.linspace(zmin + height * 0.15, zmin + height * 0.90, 30)
    widths = np.zeros(len(zs), dtype=np.float32)
    half_band = height * 0.025
    for idx_z, zc in enumerate(zs):
        sub = vertices[abs(vertices[:, 2] - zc) < half_band]
        if len(sub) >= 12:
            widths[idx_z] = float(np.percentile(sub[:, 1], 99) - np.percentile(sub[:, 1], 1))
    valid = widths > 0
    if valid.sum() < 10:
        return None
    top_half = zs >= zmin + height * 0.48
    if not (top_half & valid).any():
        return None
    head_peak_idx = int(np.flatnonzero(top_half)[int(np.argmax(widths[top_half]))])
    w_head = float(widths[head_peak_idx])
    search_mask = (zs >= zmin + height * 0.30) & (zs < zs[head_peak_idx] - height * 0.08) & valid
    if not search_mask.any():
        return None
    cand = np.flatnonzero(search_mask)
    pinch_idx = int(cand[int(np.argmin(widths[cand]))])
    w_neck = float(widths[pinch_idx])
    if w_neck > w_head * 0.82 or w_neck < height * 0.06:
        return None
    return float(zs[pinch_idx]), w_neck * 0.5


def _refine_chibi_joints(vertices, joints):
    """Correct chibi torso/arm limbs using 3D mesh neck-pinch and hanging sleeve silhouette."""
    pinch = _find_neck_pinch(vertices)
    if pinch is None:
        return joints
    z_neck, neck_hw = pinch
    height = max(0.1, float(np.ptp(vertices[:, 2])))
    mid_y = float(np.median(vertices[:, 1]))
    joints = joints.copy()

    # Clamp ViTPose shoulders down to the physical torso collar below the neck pinch when crushed into hair.
    if max(float(joints[5, 2]), float(joints[6, 2])) > z_neck + height * 0.025:
        z_sho = z_neck - height * 0.008
        joints[5, 2] = min(float(joints[5, 2]), z_sho)
        joints[6, 2] = min(float(joints[6, 2]), z_sho)
        for s_i, sign in ((5, 1.0), (6, -1.0)):
            lat = max(height * 0.08, min(abs(float(joints[s_i, 1]) - mid_y), neck_hw * 0.92))
            joints[s_i, 1] = mid_y + sign * max(lat, neck_hw * 0.88)
            near_s = vertices[(abs(vertices[:, 2] - joints[s_i, 2]) < height * 0.03) & (abs(vertices[:, 1] - joints[s_i, 1]) < height * 0.04)]
            if len(near_s) >= 6:
                joints[s_i, 0] = 0.5 * float(np.percentile(near_s[:, 0], 90) + np.percentile(near_s[:, 0], 10))

    # Fix hanging A-pose chibi sleeves/wrists that pose estimators pull up into side curls or ears.
    hip_z = 0.5 * float(joints[11, 2] + joints[12, 2])
    for s_i, e_i, w_i, sign in ((5, 7, 9, 1.0), (6, 8, 10, -1.0)):
        sho = joints[s_i]
        wri = joints[w_i]
        if float(wri[2]) < float(sho[2]) - height * 0.04:
            continue
        z_hi = float(sho[2]) - height * 0.035
        z_lo = max(float(vertices[:, 2].min()) + height * 0.10, hip_z - height * 0.08, float(sho[2]) - height * 0.36)
        if z_hi - z_lo < height * 0.10:
            continue
        slices = np.linspace(z_lo, z_hi, 14)
        exts = np.zeros(len(slices), dtype=np.float32)
        for k_z, zc in enumerate(slices):
            sub = vertices[(abs(vertices[:, 2] - zc) < height * 0.025) & ((vertices[:, 1] - mid_y) * sign > 0.0)]
            if len(sub) >= 8:
                y_out = float(np.percentile(sub[:, 1], 99 if sign > 0 else 1))
                exts[k_z] = (y_out - mid_y) * sign
        if float(exts.max()) <= neck_hw * 1.10:
            continue
        peak_k = int(np.argmax(exts[:max(1, len(exts) - 2)]))
        z_wri = float(slices[peak_k]) - height * 0.015
        z_elb = 0.5 * (float(sho[2]) + z_wri)
        for target_i, zt, frac in ((e_i, z_elb, 0.78), (w_i, z_wri, 0.80)):
            sub = vertices[(abs(vertices[:, 2] - zt) < height * 0.028) & ((vertices[:, 1] - mid_y) * sign > 0.0)]
            if len(sub) >= 8:
                y_out = float(np.percentile(sub[:, 1], 99 if sign > 0 else 1))
                span_y = max(height * 0.04, (y_out - mid_y) * sign)
                arm_pts = sub[(sub[:, 1] - mid_y) * sign >= span_y * frac]
                if len(arm_pts) >= 4:
                    joints[target_i] = np.array([
                        0.5 * float(np.percentile(arm_pts[:, 0], 88) + np.percentile(arm_pts[:, 0], 12)),
                        float(np.median(arm_pts[:, 1])),
                        zt,
                    ], dtype=np.float32)
    return joints


def _segments_distances(points, bones):
    distances = []
    for a, b in bones:
        ab = b - a
        denom = max(1e-9, float(np.dot(ab, ab)))
        t = np.clip(((points - a) @ ab) / denom, 0.0, 1.0)
        distances.append(np.linalg.norm(points - (a + t[:, None] * ab), axis=1))
    return np.stack(distances, 1)


def _geodesic_heat_weights(vertices, faces, normals, bones, bone_names, neck_z, height):
    """Compute mesh-graph geodesic distances + crease penalties + screened Poisson bone-heat diffusion."""
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra
    from scipy.sparse.linalg import spsolve

    n_verts = len(vertices)
    n_bones = len(bones)
    euclid = _segments_distances(vertices, bones)
    sigma = max(1e-4, height * 0.048)

    if len(faces) == 0 or n_verts < 16:
        w = np.exp(-((euclid - euclid.min(1, keepdims=True)) / sigma) ** 2)
        w /= np.maximum(w.sum(1, keepdims=True), 1e-9)
        return w.astype(np.float32)

    # Build sparse undirected weighted mesh graph with unique edges and concave-crease penalties.
    e0 = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    e1 = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    rows = np.concatenate([e0, e1])
    cols = np.concatenate([e1, e0])
    keys = rows.astype(np.int64) * n_verts + cols.astype(np.int64)
    _, uniq_idx = np.unique(keys, return_index=True)
    rows, cols = rows[uniq_idx], cols[uniq_idx]
    edge_len = np.linalg.norm(vertices[rows] - vertices[cols], axis=1)
    ndot = np.sum(normals[rows] * normals[cols], axis=1)
    crease_penalty = 1.0 + 4.8 * np.clip(0.42 - ndot, 0.0, 1.0)
    costs = np.maximum(edge_len * crease_penalty, 1e-6)
    graph = sparse.csr_matrix((costs, (rows, cols)), shape=(n_verts, n_verts))
    graph = graph.minimum(graph.T)

    # Anatomical region masks keep seeds clean across head/neck vs torso/arms.
    name_to_idx = {name: i for i, name in enumerate(bone_names)}
    geo_dists = np.full((n_verts, n_bones), np.inf, dtype=np.float64)
    seed_mask = np.zeros(n_verts, dtype=bool)
    seed_owner = np.full(n_verts, -1, dtype=np.int32)

    mid_y = float(np.median(vertices[:, 1]))
    sho_half = height * 0.08
    if "left_arm" in name_to_idx and "right_arm" in name_to_idx:
        ls = bones[name_to_idx["left_arm"], 0]
        rs = bones[name_to_idx["right_arm"], 0]
        mid_y = 0.5 * float(ls[1] + rs[1])
        sho_half = max(height * 0.04, 0.5 * abs(float(ls[1] - rs[1])))

    nearest_euclid = np.argmin(euclid, axis=1)
    arm_names = ("left_clavicle", "right_clavicle", "left_arm", "left_forearm", "left_hand", "right_arm", "right_forearm", "right_hand")
    leg_core_names = ("chest", "pelvis", "spine_lower", "left_thigh", "right_thigh")
    torso_core_names = ("chest",)
    for b_i, name in enumerate(bone_names):
        d_b = euclid[:, b_i]
        rad = height * (0.38 if name == "head" else 0.22 if name in torso_core_names else 0.14)
        cand = (nearest_euclid == b_i) & (d_b < rad)
        if name == "head":
            cand &= vertices[:, 2] >= neck_z - height * 0.01
        elif name in arm_names:
            cand &= vertices[:, 2] < neck_z - height * 0.008
            if name in ("left_arm", "left_forearm", "left_hand"):
                lat = cand & (vertices[:, 1] >= mid_y + sho_half * 0.96)
                if lat.sum() >= 4:
                    cand = lat
            elif name in ("right_arm", "right_forearm", "right_hand"):
                lat = cand & (vertices[:, 1] <= mid_y - sho_half * 0.96)
                if lat.sum() >= 4:
                    cand = lat
        elif name in leg_core_names:
            inner = (d_b < rad) & (abs(vertices[:, 1] - mid_y) <= sho_half * 0.94) & (vertices[:, 2] < neck_z - height * 0.01)
            if name == "chest":
                inner &= vertices[:, 2] >= bones[b_i, 0, 2] - height * 0.05
            else:
                inner &= (nearest_euclid == b_i)
                if name in ("pelvis", "spine_lower"):
                    inner &= vertices[:, 2] <= bones[b_i, 1, 2] + height * 0.04
            if inner.sum() >= 6:
                cand = inner
        if not cand.any():
            if name in arm_names:
                below_neck = np.flatnonzero(vertices[:, 2] < neck_z - height * 0.008)
                pool = below_neck if len(below_neck) >= 8 else np.arange(n_verts)
                seeds = pool[np.argsort(d_b[pool])[:max(4, min(16, len(pool)))]]
            elif name == "head":
                above = np.flatnonzero(vertices[:, 2] >= neck_z - height * 0.01)
                pool = above if len(above) >= 8 else np.arange(n_verts)
                seeds = pool[np.argsort(d_b[pool])[:max(4, min(32, len(pool)))]]
            else:
                seeds = np.argsort(d_b)[:max(4, min(16, n_verts // 200))]
        else:
            idx_cand = np.flatnonzero(cand)
            cap = 128 if name in ("head", "chest", "pelvis", "spine_lower") else 96
            if len(idx_cand) > cap:
                if name in ("head", "chest", "pelvis", "spine_lower"):
                    step = np.linspace(0, len(idx_cand) - 1, cap, dtype=np.int32)
                    idx_cand = idx_cand[step]
                else:
                    idx_cand = idx_cand[np.argsort(d_b[idx_cand])[:cap]]
            seeds = idx_cand
        seed_mask[seeds] = True
        seed_owner[seeds] = b_i
        dist_b = dijkstra(graph, directed=False, indices=seeds, min_only=True)
        geo_dists[:, b_i] = dist_b

    # Fall back smoothly to Euclidean distance for disconnected floating mesh islands.
    inf_mask = ~np.isfinite(geo_dists)
    if inf_mask.any():
        geo_dists[inf_mask] = euclid[inf_mask] * 1.45

    # Restrict jaw weights strictly to the front lower-chin region around the mouth so it never grabs neck/nose.
    if "jaw" in name_to_idx and "head" in name_to_idx:
        ji = name_to_idx["jaw"]
        mouth_ref = bones[ji, 1] + np.array([0.0, 0.0, height * 0.045], dtype=np.float32)
        dz_m = vertices[:, 2] - mouth_ref[2]
        dy_m = abs(vertices[:, 1] - mouth_ref[1])
        in_chin = (vertices[:, 0] > mouth_ref[0] - height * 0.08) & (dz_m < height * 0.004) & (dz_m > -height * 0.07) & (dy_m < height * 0.055)
        geo_dists[~in_chin, ji] += height * 1.25

    # Convert geodesic distance to initial bone-heat distribution.
    d_min = geo_dists.min(axis=1, keepdims=True)
    w_init = np.exp(-((geo_dists - d_min) / sigma) ** 2)
    w_init /= np.maximum(w_init.sum(axis=1, keepdims=True), 1e-9)

    # Screened Poisson / Laplacian heat diffusion for smooth joint transitions without bleeding across gaps.
    adj = graph.copy()
    adj.data = 1.0 / np.maximum(adj.data, 1e-4)
    adj = 0.5 * (adj + adj.T)
    deg = np.asarray(adj.sum(axis=1)).ravel()
    lap = sparse.diags(deg) - adj
    alpha = np.full(n_verts, 1.8, dtype=np.float64)
    alpha[seed_mask] = 18.0
    system = (lap + sparse.diags(alpha)).tocsc()
    rhs = alpha[:, None] * w_init
    w_diffused = spsolve(system, rhs)
    w_diffused = np.clip(w_diffused, 0.0, None)

    # Head/hair preservation strictly above neck; clamp limb bleed when rest arms hang below neck.
    if "head" in name_to_idx and "chest" in name_to_idx:
        hi = name_to_idx["head"]
        ci = name_to_idx["chest"]
        geo_head = geo_dists[:, hi]
        arm_indices = [name_to_idx[n] for n in arm_names if n in name_to_idx]
        geo_body = geo_dists[:, ci]
        if arm_indices:
            geo_body = np.minimum(geo_body, geo_dists[:, arm_indices].min(axis=1))
        head_dom = smooth(-height * 0.01, height * 0.05, geo_body - geo_head)
        spring_head = [i for i, n in enumerate(bone_names) if n.startswith("spring_hair")]
        non_head = np.ones(n_bones, dtype=bool)
        non_head[hi] = False
        if "neck" in name_to_idx:
            non_head[name_to_idx["neck"]] = False
        if "jaw" in name_to_idx:
            non_head[name_to_idx["jaw"]] = False
        for si in spring_head:
            non_head[si] = False

        arm_top_z = float(bones[arm_indices, :, 2].max()) if arm_indices else neck_z
        if arm_top_z < neck_z + height * 0.015:
            above_lock = smooth(neck_z - height * 0.008, neck_z + height * 0.025, vertices[:, 2])
            w_diffused[:, non_head] *= (1.0 - 0.995 * above_lock[:, None])
            below_body = smooth(neck_z - height * 0.015, neck_z - height * 0.065, vertices[:, 2])
            body_dom = smooth(-height * 0.01, height * 0.03, geo_head - geo_body)
            head_group = [hi] + ([name_to_idx["jaw"]] if "jaw" in name_to_idx else [])
            w_diffused[:, head_group] *= (1.0 - 0.98 * (below_body * body_dom)[:, None])
            # Protect the flared torso jacket/vest core from arm/forearm pull when sleeves hang laterally.
            free_arm_idx = [name_to_idx[n] for n in ("left_arm", "left_forearm", "left_hand", "right_arm", "right_forearm", "right_hand") if n in name_to_idx]
            if free_arm_idx:
                hip_z_ref = float(bones[name_to_idx["pelvis"], 0, 2]) if "pelvis" in name_to_idx else (neck_z - height * 0.28)
                t_down = np.clip((neck_z - vertices[:, 2]) / max(height * 0.08, neck_z - hip_z_ref), 0.0, 1.0)
                flare_hw = sho_half * (0.90 + 0.36 * t_down)
                below_sho = (vertices[:, 2] < neck_z - height * 0.012).astype(np.float32)
                norm_lat = abs(vertices[:, 1] - mid_y) / np.maximum(1e-4, flare_hw)
                inner_torso = (1.0 - smooth(0.84, 1.06, norm_lat)) * below_sho
                w_diffused[:, free_arm_idx] *= (1.0 - 0.96 * inner_torso[:, None])
        else:
            above_neck = vertices[:, 2] > neck_z - height * 0.012
            boost = head_dom * above_neck.astype(np.float32) * 0.92
            w_diffused[:, non_head] *= (1.0 - boost[:, None])

    row_sum = w_diffused.sum(axis=1, keepdims=True)
    bad_rows = row_sum[:, 0] < 1e-9
    if bad_rows.any():
        w_diffused[bad_rows] = w_init[bad_rows]
        row_sum = w_diffused.sum(axis=1, keepdims=True)
    w_diffused /= np.maximum(row_sum, 1e-9)
    return w_diffused.astype(np.float32)


def _detect_secondary_springs(vertices, faces, normals, bones, bone_names, neck, pelvis_top):
    """Detect protruding hair/ear/tail tips via geodesic distance from skull and spine cores."""
    from scipy import sparse
    from scipy.sparse.csgraph import dijkstra

    if len(faces) == 0 or len(vertices) < 32:
        return [], [], []
    height = max(0.1, float(np.ptp(vertices[:, 2])))
    e0 = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    e1 = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    rows = np.concatenate([e0, e1])
    cols = np.concatenate([e1, e0])
    keys = rows.astype(np.int64) * len(vertices) + cols.astype(np.int64)
    _, uniq_idx = np.unique(keys, return_index=True)
    rows, cols = rows[uniq_idx], cols[uniq_idx]
    costs = np.maximum(np.linalg.norm(vertices[rows] - vertices[cols], axis=1), 1e-6)
    graph = sparse.csr_matrix((costs, (rows, cols)), shape=(len(vertices), len(vertices)))

    head_i = bone_names.index("head")
    skull_center = 0.5 * (bones[head_i, 0] + bones[head_i, 1])
    crown = bones[head_i, 1]
    skull_seeds = np.argsort(np.linalg.norm(vertices - skull_center[None, :], axis=1))[:12]
    geo_skull = dijkstra(graph, directed=False, indices=skull_seeds, min_only=True)

    spring_bones, spring_parents, spring_names = [], [], []
    # Only promote slender protruding ears (hollow gap above crown) or very back-swept tails/twintails behind torso.
    max_cluster = max(24, int(len(vertices) * 0.06))
    back_limit = min(float(pelvis_top[0]), float(neck[0])) - height * 0.16
    above_crown = vertices[vertices[:, 2] > crown[2] + height * 0.045]
    has_split_ears = len(above_crown) >= 24 and float((abs(above_crown[:, 1] - skull_center[1]) < height * 0.035).mean()) < 0.08
    candidates = [
        (
            "spring_hair_l",
            head_i,
            (((vertices[:, 2] > crown[2] + height * 0.045) & has_split_ears) | ((vertices[:, 2] < neck[2] - height * 0.03) & (vertices[:, 0] < back_limit)))
            & (vertices[:, 2] > pelvis_top[2] + height * 0.05)
            & (vertices[:, 1] > skull_center[1] + height * 0.13),
            skull_center,
            0.65,
            height * 0.16,
        ),
        (
            "spring_hair_r",
            head_i,
            (((vertices[:, 2] > crown[2] + height * 0.045) & has_split_ears) | ((vertices[:, 2] < neck[2] - height * 0.03) & (vertices[:, 0] < back_limit)))
            & (vertices[:, 2] > pelvis_top[2] + height * 0.05)
            & (vertices[:, 1] < skull_center[1] - height * 0.13),
            skull_center,
            0.65,
            height * 0.16,
        ),
        (
            "spring_back_tail",
            bone_names.index("pelvis"),
            (vertices[:, 0] < pelvis_top[0] - height * 0.14)
            & (vertices[:, 2] < float(neck[2]) - height * 0.06)
            & (vertices[:, 2] > vertices[:, 2].min() + height * 0.14),
            pelvis_top,
            0.62,
            height * 0.14,
        ),
    ]
    for s_name, parent_i, mask, anchor_ref, root_frac, min_span in candidates:
        cand = np.flatnonzero(mask & np.isfinite(geo_skull))
        if len(cand) < 12 or len(cand) > max_cluster:
            continue
        tip_idx = cand[int(np.argmax(np.linalg.norm(vertices[cand] - anchor_ref[None, :], axis=1)))]
        tip_pt = vertices[tip_idx]
        span = float(np.linalg.norm(tip_pt - anchor_ref))
        if span > min_span:
            root_pt = anchor_ref + (tip_pt - anchor_ref) * root_frac
            spring_bones.append((root_pt.astype(np.float32), tip_pt.astype(np.float32)))
            spring_parents.append(parent_i)
            spring_names.append(s_name)
    return spring_bones, spring_parents, spring_names


def fit(points, keypoints, mouth_uv):
    """Legacy 12-bone pose-assisted fitting preserved for compatibility probes."""
    joints = lift(points, keypoints)
    # Apply the same depth regularization before deriving every body/limb pivot.
    joints[:, 0] = np.median(points[:, 0]) * 0.65 + joints[:, 0] * 0.35
    height = float(np.ptp(points[:, 2]))
    shoulder = (joints[5] + joints[6]) / 2
    hip = (joints[11] + joints[12]) / 2
    if height < 0.1 or shoulder[2] <= hip[2] or np.linalg.norm(joints[5] - joints[6]) < height * 0.08:
        raise ValueError("Unsupported pose")
    # Place joints inside the limbs rather than on the front texture surface.
    neck = shoulder.copy()
    neck[2] += height * 0.035
    head = (joints[1] + joints[2]) / 2
    bones = [(neck, head), (hip, neck)]
    for shoulder_i, elbow_i, wrist_i, hip_i, knee_i, ankle_i, label in ((5, 7, 9, 11, 13, 15, "left"), (6, 8, 10, 12, 14, 16, "right")):
        s, e, w, h, k, a = joints[[shoulder_i, elbow_i, wrist_i, hip_i, knee_i, ankle_i]]
        if min(s[2] - w[2], h[2] - a[2]) < height * 0.08:
            raise ValueError("Hidden or crossed limbs")
        toe = a + np.array([height * 0.075, 0, -height * 0.015])
        bones += [(s, e), (e, w), (h, k), (k, a), (a, toe)]
    bones = np.asarray(bones, np.float32)
    lengths = np.linalg.norm(bones[:, 1] - bones[:, 0], axis=1)
    if not np.isfinite(bones).all() or lengths.min() < height * 0.025:
        raise ValueError("Uncertain joints")
    distances = _segments_distances(points, bones)
    weights = np.exp(-((distances - distances.min(1, keepdims=True)) / (height * 0.045)) ** 2)
    # Rigid head, with a smooth neck seam; prevents hair being assigned to arms.
    head_weight = smooth(neck[2] - height * 0.015, neck[2] + height * 0.045, points[:, 2])
    weights[:, 0] = 0
    weights /= np.maximum(weights.sum(1, keepdims=True), 1e-9)
    weights *= 1 - head_weight[:, None]
    weights[:, 0] = head_weight
    weights /= weights.sum(1, keepdims=True)
    mouth = lift(points, [mouth_uv])[0]
    mouth[0] = np.percentile(points[(abs(points[:, 1] - mouth[1]) < height * 0.025) & (abs(points[:, 2] - mouth[2]) < height * 0.02), 0], 95)
    return bones, weights.astype(np.float32), joints, mouth


def _cap_cut_boundary(edge_list, outward_vec, keep_cols, verts_list, w_list, c_list, new_faces_list, height, interior_pool=None, recess_scale=0.008, tone_scale=1.0):
    """Seal an open cut loop watertightly with a concentric rim ring + Z-tiered spine fan and local perimeter colors."""
    if len(edge_list) < 3:
        return
    arr_v = np.asarray(verts_list, dtype=np.float32)
    b_verts = np.unique(np.asarray(edge_list, dtype=np.int32).ravel())
    if len(b_verts) < 3:
        return
    zs = arr_v[b_verts, 2]
    z_lo, z_hi = float(zs.min()), float(zs.max())
    n_tiers = 6 if (z_hi - z_lo) > height * 0.06 else 1
    edges = np.linspace(z_lo - 1e-5, z_hi + 1e-5, n_tiers + 1)

    tier_nodes = {}
    band_of_vert = {}
    for bv in b_verts:
        t = int(np.clip(np.searchsorted(edges[1:-1], float(arr_v[bv, 2])), 0, n_tiers - 1))
        band_of_vert[int(bv)] = t

    pool_arr = np.asarray(list(interior_pool), dtype=np.int32) if interior_pool else None

    for t in range(n_tiers):
        members = [int(bv) for bv in b_verts if band_of_vert[int(bv)] == t]
        if not members:
            continue
        pts_t = arr_v[members]
        pos_c = pts_t.mean(axis=0) - outward_vec * (height * float(recess_scale))
        w_raw = np.stack([w_list[m] for m in members], axis=0).mean(axis=0)
        w_masked = np.zeros_like(w_raw)
        w_masked[keep_cols] = w_raw[keep_cols]
        ws = float(w_masked.sum())
        if ws < 1e-6:
            w_masked[keep_cols[0]] = 1.0
        else:
            w_masked /= ws
        if pool_arr is not None and len(pool_arr):
            z_band_lo = float(edges[t])
            z_band_hi = float(edges[t + 1])
            in_z = pool_arr[(arr_v[pool_arr, 2] >= z_band_lo) & (arr_v[pool_arr, 2] <= z_band_hi)]
            src_idx = in_z if len(in_z) >= 4 else pool_arr
        else:
            src_idx = np.asarray(members, dtype=np.int32)
        dists = np.linalg.norm(arr_v[src_idx] - pos_c[None, :], axis=1)
        order = np.argsort(dists)[:min(16, len(src_idx))]
        top_k = src_idx[order]
        idw = 1.0 / np.maximum(dists[order], height * 0.005)
        idw /= max(1e-9, float(idw.sum()))
        cols_k = np.stack([c_list[int(m)] for m in top_k], axis=0)
        col_c = np.clip((cols_k * idw[:, None]).sum(axis=0) * float(tone_scale), 0.0, 1.0).astype(np.float32)

        node_idx = len(verts_list)
        verts_list.append(pos_c.astype(np.float32))
        w_list.append(w_masked.astype(np.float32))
        c_list.append(col_c)
        tier_nodes[t] = node_idx

    if not tier_nodes:
        return

    # Concentric intermediate ring blends local boundary coat/collar hues smoothly into the socket hub without open edges.
    ring_map = {}
    for bv in b_verts:
        bi = int(bv)
        cu = tier_nodes[band_of_vert[bi]]
        r_pos = (0.55 * verts_list[bi] + 0.45 * verts_list[cu] - outward_vec * (height * float(recess_scale) * 0.35)).astype(np.float32)
        w_r = np.zeros_like(w_list[bi])
        w_r[keep_cols] = 0.65 * w_list[bi][keep_cols] + 0.35 * w_list[cu][keep_cols]
        ws_r = float(w_r.sum())
        if ws_r < 1e-6:
            w_r[keep_cols[0]] = 1.0
        else:
            w_r /= ws_r
        r_col = np.clip(0.80 * c_list[bi] * float(tone_scale) + 0.20 * c_list[cu], 0.0, 1.0).astype(np.float32)
        r_idx = len(verts_list)
        verts_list.append(r_pos)
        w_list.append(w_r.astype(np.float32))
        c_list.append(r_col)
        ring_map[bi] = r_idx

    def _add_oriented(i0, i1, i2):
        p0, p1, p2 = verts_list[i0], verts_list[i1], verts_list[i2]
        n = np.cross(p1 - p0, p2 - p0)
        if float(np.dot(n, outward_vec)) < 0.0:
            new_faces_list.append([i0, i2, i1])
        else:
            new_faces_list.append([i0, i1, i2])

    for u, v in edge_list:
        tu = band_of_vert[u]
        tv = band_of_vert[v]
        ru = ring_map[u]
        rv = ring_map[v]
        cu = tier_nodes[tu]
        cv = tier_nodes[tv]
        _add_oriented(u, v, rv)
        _add_oriented(u, rv, ru)
        _add_oriented(ru, rv, cu)
        if cu != cv:
            _add_oriented(rv, cv, cu)


def _detach_and_cap_limbs(vertices, faces, normals, colors, weights, bones, bone_names, arm_joints, height):
    """Sever fused below-armpit arm/torso bridge triangles preserving full tubular sleeve volume and recessed sockets."""
    n_base_faces = len(faces)
    if n_base_faces == 0 or len(vertices) < 32:
        return vertices, faces, normals, colors, weights, n_base_faces, False

    idx = {name: i for i, name in enumerate(bone_names)}
    l_cols = [idx[n] for n in ("left_arm", "left_forearm", "left_hand") if n in idx]
    r_cols = [idx[n] for n in ("right_arm", "right_forearm", "right_hand") if n in idx]
    body_cols = [i for i in range(len(bone_names)) if i not in l_cols and i not in r_cols]
    if not l_cols or not r_cols or not body_cols:
        return vertices, faces, normals, colors, weights, n_base_faces, False

    l_s, l_e, l_w, r_s, r_e, r_w = arm_joints
    l_ht = bones[idx["left_hand"], 1] if "left_hand" in idx else (l_w + (l_w - l_e) * 0.36)
    r_ht = bones[idx["right_hand"], 1] if "right_hand" in idx else (r_w + (r_w - r_e) * 0.36)
    z_armpit = min(float(l_s[2]), float(r_s[2])) - height * 0.032
    mid_y = 0.5 * float(l_s[1] + r_s[1])

    # Avoid wide chin-level curly hair inflating torso half-width beyond actual shoulder/hip anatomy.
    pinch = _find_neck_pinch(vertices)
    sho_half = 0.5 * abs(float(l_s[1] - r_s[1]))
    hip_half = (0.5 * abs(float(bones[idx["left_thigh"], 0, 1] - bones[idx["right_thigh"], 0, 1]))) if ("left_thigh" in idx and "right_thigh" in idx) else sho_half * 0.72
    anat_torso_hw = max(height * 0.08, sho_half * 0.94, hip_half * 1.12)
    torso_hw = min(pinch[1], anat_torso_hw) if pinch is not None else anat_torso_hw
    t_down = np.clip((z_armpit - vertices[:, 2]) / (height * 0.25), 0.0, 1.0)
    front_floor_x = min(float(l_s[0]), float(r_s[0])) - height * 0.12

    def _estimate_sleeve_r(s_pt, e_pt, w_pt, sign):
        zs = np.array([float(w_pt[2]), float(e_pt[2]), float(s_pt[2])], dtype=np.float32)
        ys = np.array([abs(float(w_pt[1]) - mid_y), abs(float(e_pt[1]) - mid_y), abs(float(s_pt[1]) - mid_y)], dtype=np.float32)
        radii = []
        for z_val, ay_val in zip(zs, ys):
            band = (np.abs(vertices[:, 2] - z_val) < height * 0.025) & ((vertices[:, 1] - mid_y) * sign > 0.0)
            if int(band.sum()) >= 8:
                y_out = float(np.percentile((vertices[band, 1] - mid_y) * sign, 98))
                radii.append(y_out - ay_val)
        if not radii:
            return height * 0.042
        return float(np.clip(np.median(radii), height * 0.028, height * 0.056))

    l_sr = _estimate_sleeve_r(l_s, l_e, l_w, 1.0)
    r_sr = _estimate_sleeve_r(r_s, r_e, r_w, -1.0)

    def _side_seam_y(s_pt, e_pt, w_pt, sleeve_r):
        zs = np.array([float(w_pt[2]) - height * 0.06, float(w_pt[2]), float(e_pt[2]), float(s_pt[2])], dtype=np.float32)
        ys = np.array([abs(float(w_pt[1]) - mid_y), abs(float(w_pt[1]) - mid_y), abs(float(e_pt[1]) - mid_y), abs(float(s_pt[1]) - mid_y)], dtype=np.float32)
        arm_lat = np.interp(vertices[:, 2], zs, ys)
        # Carve at medial sleeve radius so the full cylindrical sleeve lifts instead of a thin front strip.
        inner = arm_lat - max(height * 0.026, sleeve_r * 0.96)
        floor_lim = torso_hw * (0.94 + 0.14 * t_down)
        return np.maximum(inner, floor_lim)

    w_l = weights[:, l_cols].sum(axis=1)
    w_r = weights[:, r_cols].sum(axis=1)
    w_b = weights[:, body_cols].sum(axis=1)

    flank_mask = (
        (vertices[:, 2] >= min(float(l_w[2]), float(r_w[2])) - height * 0.04)
        & (vertices[:, 2] <= z_armpit - height * 0.03)
        & (np.abs(vertices[:, 1] - mid_y) >= torso_hw * 0.35)
        & (np.abs(vertices[:, 1] - mid_y) <= torso_hw * 0.88)
        & (vertices[:, 0] >= min(float(l_s[0]), float(r_s[0])) - height * 0.02)
    )
    flank_rgb = np.median(colors[flank_mask], axis=0) if (colors is not None and int(flank_mask.sum()) >= 8) else None

    def _refined_side(s_pt, e_pt, w_pt, h_tip, sleeve_r, sign, w_side):
        zs = np.array([float(w_pt[2]) - height * 0.05, float(w_pt[2]), float(e_pt[2]), float(s_pt[2])], dtype=np.float32)
        xs = np.array([float(w_pt[0]), float(w_pt[0]), float(e_pt[0]), float(s_pt[0])], dtype=np.float32)
        arm_x = np.interp(vertices[:, 2], zs, xs)
        lat = (vertices[:, 1] - mid_y) * sign
        cut_y = _side_seam_y(s_pt, e_pt, w_pt, sleeve_r)
        arm_y = np.interp(vertices[:, 2], zs, np.array([abs(float(w_pt[1]) - mid_y), abs(float(w_pt[1]) - mid_y), abs(float(e_pt[1]) - mid_y), abs(float(s_pt[1]) - mid_y)], dtype=np.float32))
        max_lat = arm_y + max(height * 0.058, sleeve_r * 1.75)
        max_dx = max(height * 0.056, sleeve_r * 1.65)
        in_arm_tube = (
            (vertices[:, 2] < z_armpit)
            & (vertices[:, 0] >= np.maximum(front_floor_x, arm_x - max_dx))
            & (vertices[:, 0] <= arm_x + max_dx)
            & (lat <= max_lat)
        )
        m = in_arm_tube & (w_side > w_b * 0.34) & (lat > cut_y)

        # Full distal fist/paw capsule below wrist: never leave inner thumb/palm glued to torso/thigh.
        hw = h_tip - w_pt
        h_den = max(1e-8, float(np.dot(hw, hw)))
        t_h = np.clip(((vertices - w_pt) @ hw) / h_den, 0.0, 1.0)
        d_hand = np.linalg.norm(vertices - (w_pt + t_h[:, None] * hw), axis=1)
        below_w = vertices[:, 2] < float(w_pt[2]) - height * 0.006
        inner_hand_floor = max(
            hip_half * 1.15,
            torso_hw * 0.88,
            abs(float(w_pt[1]) - mid_y) - max(height * 0.038, sleeve_r * 1.15),
        )
        hand_tube = (
            (d_hand <= max(height * 0.046, sleeve_r * 1.32))
            & (lat >= inner_hand_floor)
            & (lat <= max_lat)
            & (vertices[:, 2] >= float(h_tip[2]) - height * 0.036)
            & (vertices[:, 2] <= float(w_pt[2]) + height * 0.025)
            & (vertices[:, 0] >= float(w_pt[0]) - height * 0.056)
            & (vertices[:, 0] <= float(w_pt[0]) + height * 0.058)
        )
        m &= (~below_w) | hand_tube
        # Claim whole hanging fist/paw near/below wrist even when chest/thigh weights bled into fused seam.
        m |= hand_tube & (w_side > 0.12) & ((below_w) | (lat >= abs(float(w_pt[1]) - mid_y) - sleeve_r * 1.05))

        # Separate exposed outer sleeve from overlapping vest pocket flaps without slicing off shadow sleeve walls.
        if flank_rgb is not None and colors is not None:
            core_sl = (
                (vertices[:, 2] >= float(w_pt[2]))
                & (vertices[:, 2] <= float(e_pt[2]) + height * 0.02)
                & (lat >= arm_y - height * 0.002)
                & (vertices[:, 0] >= arm_x + height * 0.022)
            )
            if int(core_sl.sum()) >= 6:
                dists_flank = np.linalg.norm(colors[core_sl] - flank_rgb[None, :], axis=1)
                distinct = dists_flank > 0.18
                if int(distinct.sum()) >= max(6, len(dists_flank) // 5):
                    sl_rgb = np.median(colors[core_sl][distinct], axis=0)
                    d_t = np.linalg.norm(colors - flank_rgb[None, :], axis=1)
                    d_s = np.linalg.norm(colors - sl_rgb[None, :], axis=1)
                    outer_hand_hint = (
                        (vertices[:, 2] < float(e_pt[2]) + height * 0.02)
                        & (vertices[:, 2] >= float(h_tip[2]) - height * 0.036)
                        & (lat >= arm_y - height * 0.004)
                        & (lat <= max_lat)
                        & (vertices[:, 0] >= arm_x - max_dx)
                        & (d_t > 0.14)
                        & (w_side > 0.14)
                    )
                    m |= outer_hand_hint & ((~below_w) | hand_tube)
                    vest_flap = (
                        (vertices[:, 2] < z_armpit - height * 0.006)
                        & (lat < arm_y + height * 0.004)
                        & (d_t < 0.17)
                        & (d_t < d_s * 0.72)
                        & (vertices[:, 0] >= arm_x - height * 0.022)
                    )
                    m &= (~vest_flap)
        return m

    v_side = np.zeros(len(vertices), dtype=np.int8)
    is_l = _refined_side(l_s, l_e, l_w, l_ht, l_sr, 1.0, w_l) & (w_l >= w_r)
    is_r = _refined_side(r_s, r_e, r_w, r_ht, r_sr, -1.0, w_r) & (w_r > w_l)
    v_side[is_l] = 1
    v_side[is_r] = 2

    tri_z = vertices[faces, 2].mean(axis=1)
    below_tri = tri_z < z_armpit
    f_sides = v_side[faces]
    bridge_l = below_tri & (f_sides == 1).any(axis=1) & (f_sides == 0).any(axis=1)
    bridge_r = below_tri & (f_sides == 2).any(axis=1) & (f_sides == 0).any(axis=1)
    active_sides = []
    if int(bridge_l.sum()) >= 8:
        active_sides.append((1, l_cols, 1.0))
    if int(bridge_r.sum()) >= 8:
        active_sides.append((2, r_cols, -1.0))
    if not active_sides:
        return vertices, faces, normals, colors, weights, n_base_faces, False

    edge_map = {}
    tri_adj = {}
    for fi in np.flatnonzero(below_tri):
        a, b, c = int(faces[fi, 0]), int(faces[fi, 1]), int(faces[fi, 2])
        for u, v in ((a, b), (b, c), (c, a)):
            key = (u, v) if u < v else (v, u)
            edge_map.setdefault(key, []).append((int(fi), u, v))
    for entries in edge_map.values():
        if len(entries) == 2:
            f0, f1 = entries[0][0], entries[1][0]
            tri_adj.setdefault(f0, []).append(f1)
            tri_adj.setdefault(f1, []).append(f0)

    tri_owner = np.full(n_base_faces, -1, dtype=np.int8)
    tri_owner[below_tri] = 0
    for side_id, cols, _ in active_sides:
        cnt_s = (f_sides == side_id).sum(axis=1)
        cnt_b = (f_sides == 0).sum(axis=1)
        w_s_face = weights[faces][:, :, cols].sum(axis=(1, 2)) / 3.0
        w_b_face = weights[faces][:, :, body_cols].sum(axis=(1, 2)) / 3.0
        claim = below_tri & ((cnt_s >= 2) | ((cnt_s == 1) & (cnt_b <= 2) & (w_s_face > w_b_face)))
        tri_owner[claim] = side_id

    # Boundary-length majority regularization (Zhang et al., 2012) removes jagged 1-triangle teeth along cut loops.
    cut_z_ceil = z_armpit - height * 0.004
    reg_z_lim = cut_z_ceil - height * 0.014
    for _ in range(3):
        updates = []
        for fi, nbrs in tri_adj.items():
            if float(tri_z[fi]) >= reg_z_lim or len(nbrs) < 2:
                continue
            cur = int(tri_owner[fi])
            if cur < 0:
                continue
            n_vals = [int(tri_owner[nf]) for nf in nbrs if int(tri_owner[nf]) >= 0]
            if not n_vals:
                continue
            same = sum(1 for x in n_vals if x == cur)
            other = len(n_vals) - same
            if same == 0 or (len(n_vals) >= 3 and other >= 2 and same <= 1):
                cand = max((x for x in set(n_vals) if x != cur), key=lambda x: n_vals.count(x), default=cur)
                if cand != cur:
                    updates.append((fi, cand))
        for fi, cand in updates:
            tri_owner[fi] = cand

    v_colors = colors.copy() if colors is not None else np.full((len(vertices), 3), 0.7, dtype=np.float32)
    verts_list = [vertices[i].copy() for i in range(len(vertices))]
    w_list = [weights[i].copy() for i in range(len(vertices))]
    c_list = [v_colors[i].copy() for i in range(len(vertices))]
    faces_out = faces.copy()
    new_caps = []

    def _renorm_side(w_arr, cols, pos=None):
        out_w = np.zeros_like(w_arr)
        out_w[cols] = w_arr[cols]
        s = float(out_w.sum())
        if s < 1e-4 and pos is not None:
            d_seg = _segments_distances(pos[None, :], bones[cols])[0]
            sig_loc = max(1e-4, height * 0.05)
            w_loc = np.exp(-((d_seg - d_seg.min()) / sig_loc) ** 2)
            w_loc /= max(1e-9, float(w_loc.sum()))
            out_w[cols] = w_loc.astype(np.float32)
        elif s < 1e-6:
            out_w[cols[0]] = 1.0
        else:
            out_w /= s
        return out_w

    for side_id, cols, side_sign in active_sides:
        body_seam_edges = []
        arm_seam_edges = []
        touched_by_body = set()
        touched_by_arm = set()
        for fi in np.flatnonzero(tri_owner == 0):
            touched_by_body.update(int(x) for x in faces_out[fi])
        for fi in np.flatnonzero(tri_owner == -1):
            touched_by_body.update(int(x) for x in faces_out[fi])
        for fi in np.flatnonzero(tri_owner == side_id):
            touched_by_arm.update(int(x) for x in faces_out[fi])

        for entries in edge_map.values():
            if len(entries) != 2:
                continue
            (f0, u0, v0), (f1, u1, v1) = entries
            o0, o1 = int(tri_owner[f0]), int(tri_owner[f1])
            if o0 == 0 and o1 == side_id:
                body_seam_edges.append((u0, v0))
                arm_seam_edges.append((u1, v1))
            elif o1 == 0 and o0 == side_id:
                body_seam_edges.append((u1, v1))
                arm_seam_edges.append((u0, v0))

        shared_cut = touched_by_body & touched_by_arm
        arm_remap = {}
        for v_idx in shared_cut:
            if float(verts_list[v_idx][2]) >= cut_z_ceil:
                continue
            v_new = len(verts_list)
            pos_arm = verts_list[v_idx].copy()
            verts_list.append(pos_arm)
            w_list.append(_renorm_side(w_list[v_idx], cols, pos_arm))
            c_list.append(c_list[v_idx].copy())
            arm_remap[v_idx] = v_new
            w_list[v_idx] = _renorm_side(w_list[v_idx], body_cols, verts_list[v_idx])

        for v_idx in touched_by_arm:
            if v_idx not in shared_cut and float(verts_list[v_idx][2]) < cut_z_ceil - height * 0.004:
                w_list[v_idx] = _renorm_side(w_list[v_idx], cols, verts_list[v_idx])
        for v_idx in touched_by_body:
            if v_idx not in shared_cut and float(verts_list[v_idx][2]) < cut_z_ceil - height * 0.004:
                w_list[v_idx] = _renorm_side(w_list[v_idx], body_cols, verts_list[v_idx])

        out_body = np.array([0.0, side_sign, 0.0], dtype=np.float32)
        out_arm = np.array([0.0, -side_sign, 0.0], dtype=np.float32)
        if arm_remap:
            arm_faces = np.flatnonzero(tri_owner == side_id)
            for fi in arm_faces:
                for corner in range(3):
                    ov = int(faces_out[fi, corner])
                    if ov in arm_remap:
                        faces_out[fi, corner] = arm_remap[ov]
            remapped_arm_edges = [(arm_remap.get(u, u), arm_remap.get(v, v)) for u, v in arm_seam_edges]
            # Unified shrinkage-free Taubin boundary curve fairing (Taubin 1995; Li et al., 2004).
            loop_nbrs = {}
            for eu, ev in body_seam_edges:
                loop_nbrs.setdefault(eu, set()).add(ev)
                loop_nbrs.setdefault(ev, set()).add(eu)
            for lam in (0.42, -0.44, 0.42, -0.44):
                pos_snap = {vi: verts_list[vi].copy() for vi in arm_remap}
                for vi, vclone in arm_remap.items():
                    if float(pos_snap[vi][2]) >= cut_z_ceil - height * 0.015:
                        continue
                    nbrs = [nv for nv in loop_nbrs.get(vi, ()) if nv in pos_snap]
                    if len(nbrs) < 2:
                        continue
                    avg = np.mean([pos_snap[nv] for nv in nbrs], axis=0)
                    new_p = (pos_snap[vi] + lam * (avg - pos_snap[vi])).astype(np.float32)
                    verts_list[vi] = new_p
                    verts_list[vclone] = new_p.copy()
            # Gently recess the detached torso socket border medially inside the sleeve crease so swings never clip.
            for vi in arm_remap:
                z_v = float(verts_list[vi][2])
                tuck = float(smooth(cut_z_ceil - height * 0.010, cut_z_ceil - height * 0.045, z_v))
                if tuck > 0.0:
                    verts_list[vi] = (verts_list[vi] - out_body * (height * 0.0055 * tuck)).astype(np.float32)
        else:
            remapped_arm_edges = arm_seam_edges

        arm_raw = [v_i for v_i in touched_by_arm if v_i not in shared_cut and float(verts_list[v_i][2]) < cut_z_ceil]
        if len(arm_raw) >= 12:
            lum_arm = np.asarray([float(c_list[v_i].mean()) for v_i in arm_raw], dtype=np.float32)
            thresh_lum = float(np.percentile(lum_arm, 45))
            arm_interior = [v_i for v_i, lv in zip(arm_raw, lum_arm) if lv >= thresh_lum]
        else:
            arm_interior = arm_raw
        _cap_cut_boundary(body_seam_edges, out_body, body_cols, verts_list, w_list, c_list, new_caps, height, interior_pool=None, recess_scale=0.028, tone_scale=0.80)
        _cap_cut_boundary(remapped_arm_edges, out_arm, cols, verts_list, w_list, c_list, new_caps, height, interior_pool=arm_interior, recess_scale=0.008, tone_scale=1.0)

    final_v = np.asarray(verts_list, dtype=np.float32)
    final_f = np.concatenate([faces_out, np.asarray(new_caps, dtype=np.int32)], axis=0) if new_caps else faces_out
    final_w = np.asarray(w_list, dtype=np.float32)
    final_c = np.asarray(c_list, dtype=np.float32)
    final_n = compute_vertex_normals(final_v, final_f)
    return final_v, final_f, final_n, final_c, final_w, n_base_faces, True


def fit_articulated(vertices, faces, keypoints, mouth_uv, colors=None):
    """Articulated 22+ bone humanoid + spring-bone rig with volumetric centering & geodesic heat weights."""
    joints = _refine_chibi_joints(vertices, lift_medial(vertices, keypoints))
    height = float(np.ptp(vertices[:, 2]))
    pinch = _find_neck_pinch(vertices)
    shoulder_mid = (joints[5] + joints[6]) * 0.5
    hip_mid = (joints[11] + joints[12]) * 0.5
    if height < 0.1 or shoulder_mid[2] <= hip_mid[2] or np.linalg.norm(joints[5] - joints[6]) < height * 0.08:
        raise ValueError("Unsupported pose")

    torso_span = float(shoulder_mid[2] - hip_mid[2])
    pelvis_top = hip_mid + np.array([0.0, 0.0, max(height * 0.025, torso_span * 0.18)], dtype=np.float32)
    waist = hip_mid + (shoulder_mid - hip_mid) * 0.48
    sternum = shoulder_mid.copy()
    sternum[2] += height * 0.012
    eye_mid = (joints[1] + joints[2]) * 0.5
    neck_base = sternum.copy()
    neck_anchor_z = float(pinch[0]) if pinch is not None and float(shoulder_mid[2]) <= float(pinch[0]) + height * 0.01 else float(sternum[2])
    neck_top_z = max(float(sternum[2]) + height * 0.022, neck_anchor_z + height * 0.032, min(float(eye_mid[2]) - height * 0.015, float(sternum[2]) + height * 0.055))
    neck_top = np.array([float(sternum[0]), float(sternum[1]), neck_top_z], dtype=np.float32)
    head_crown_z = max(float(eye_mid[2]) + height * 0.11, float(vertices[:, 2].max()) - height * 0.09)
    head_crown = np.array([float(eye_mid[0]), float(eye_mid[1]), head_crown_z], dtype=np.float32)

    # Validate limb spans cleanly, stabilizing chibi sleeves where ViTPose merges elbow and wrist.
    limb_data = {}
    for s_i, e_i, w_i, h_i, k_i, a_i, side_sign, label in ((5, 7, 9, 11, 13, 15, 1.0, "left"), (6, 8, 10, 12, 14, 16, -1.0, "right")):
        s, e, w, h, k, a = joints[[s_i, e_i, w_i, h_i, k_i, a_i]]
        if min(s[2] - w[2], h[2] - a[2]) < height * 0.075:
            raise ValueError("Hidden or crossed limbs")
        if float(np.linalg.norm(w - s)) < height * 0.055:
            raise ValueError("Hidden or crossed limbs")
        if float(np.linalg.norm(w - e)) < height * 0.030 or float(np.linalg.norm(e - s)) < height * 0.030:
            e = (s + (w - s) * 0.5 + np.array([0.0, side_sign * height * 0.012, 0.0], dtype=np.float32)).astype(np.float32)
        if float(np.linalg.norm(a - k)) < height * 0.030 or float(np.linalg.norm(k - h)) < height * 0.030:
            # Stabilize stubby chibi legs when ViTPose merges knee and ankle landmarks.
            k = (h + (a - h) * 0.5 + np.array([height * 0.012, 0.0, 0.0], dtype=np.float32)).astype(np.float32)
        fore_dir = w - e
        fore_len = max(1e-4, float(np.linalg.norm(fore_dir)))
        hand_tip = w + (fore_dir / fore_len) * max(height * 0.038, fore_len * 0.36)
        ball = a + np.array([height * 0.048, 0.0, -height * 0.012], dtype=np.float32)
        toe = ball + np.array([height * 0.034, 0.0, -height * 0.004], dtype=np.float32)
        limb_data[label] = (s, e, w, hand_tip, h, k, a, ball, toe)

    # Mouth landmark on front face & TMJ jaw pivot tucked back near ear depth.
    mouth = lift(vertices, [mouth_uv])[0]
    mouth_hits = vertices[(abs(vertices[:, 1] - mouth[1]) < height * 0.025) & (abs(vertices[:, 2] - mouth[2]) < height * 0.02)]
    if len(mouth_hits):
        mouth[0] = float(np.percentile(mouth_hits[:, 0], 95))
    ear_mid = 0.5 * (joints[3] + joints[4])
    tmj_pivot = np.array([min(float(ear_mid[0]), float(mouth[0]) - height * 0.11), float(mouth[1]), float(mouth[2]) + height * 0.025], dtype=np.float32)
    chin_tip = mouth + np.array([0.0, 0.0, -height * 0.045], dtype=np.float32)

    l_s, l_e, l_w, l_ht, l_h, l_k, l_a, l_b, l_t = limb_data["left"]
    r_s, r_e, r_w, r_ht, r_h, r_k, r_a, r_b, r_t = limb_data["right"]

    # Indices 0..11 mirror classic humanoid part order; 12..21 add fine anatomical articulation.
    bone_defs = [
        ("head", neck_top, head_crown, 14),             # 0
        ("spine_lower", hip_mid, waist, 12),            # 1
        ("left_arm", l_s, l_e, 15),                     # 2
        ("left_forearm", l_e, l_w, 2),                  # 3
        ("left_thigh", l_h, l_k, 12),                   # 4
        ("left_shin", l_k, l_a, 4),                     # 5
        ("left_foot", l_a, l_b, 5),                     # 6
        ("right_arm", r_s, r_e, 16),                    # 7
        ("right_forearm", r_e, r_w, 7),                 # 8
        ("right_thigh", r_h, r_k, 12),                  # 9
        ("right_shin", r_k, r_a, 9),                    # 10
        ("right_foot", r_a, r_b, 10),                   # 11
        ("pelvis", hip_mid, pelvis_top, -1),            # 12
        ("chest", waist, sternum, 1),                   # 13
        ("neck", neck_base, neck_top, 13),              # 14
        ("left_clavicle", sternum, l_s, 13),            # 15
        ("right_clavicle", sternum, r_s, 13),           # 16
        ("left_hand", l_w, l_ht, 3),                    # 17
        ("right_hand", r_w, r_ht, 8),                   # 18
        ("left_toe", l_b, l_t, 6),                      # 19
        ("right_toe", r_b, r_t, 11),                    # 20
        ("jaw", tmj_pivot, chin_tip, 0),                # 21
    ]
    bone_names = [b[0] for b in bone_defs]
    bones_list = [(b[1], b[2]) for b in bone_defs]
    parents_list = [b[3] for b in bone_defs]

    normals = compute_vertex_normals(vertices, faces)
    sp_bones, sp_parents, sp_names = _detect_secondary_springs(
        vertices, faces, normals, np.asarray(bones_list, np.float32), bone_names, neck_top, pelvis_top
    )
    bones_list.extend(sp_bones)
    parents_list.extend(sp_parents)
    bone_names.extend(sp_names)

    bones = np.asarray(bones_list, dtype=np.float32)
    parents = np.asarray(parents_list, dtype=np.int32)
    lengths = np.linalg.norm(bones[:, 1] - bones[:, 0], axis=1)
    if not np.isfinite(bones).all() or lengths.min() < height * 0.012:
        raise ValueError("Uncertain joints")

    weights = _geodesic_heat_weights(vertices, faces, normals, bones, bone_names, float(neck_top[2]), height)
    vertices_out, faces_out, normals_out, colors_out, weights, base_face_count, detached_limbs = _detach_and_cap_limbs(
        vertices, faces, normals, colors, weights, bones, bone_names, (l_s, l_e, l_w, r_s, r_e, r_w), height
    )
    # Measure residual topological fusion below the shoulder crease after optional seam detachment.
    arm_mobility = 1.0
    if len(faces_out):
        dom = weights.argmax(1)
        lower_arm_ids = [bone_names.index(n) for n in ("left_forearm", "left_hand", "right_forearm", "right_hand") if n in bone_names]
        torso_ids = [bone_names.index(n) for n in ("chest", "pelvis", "spine_lower", "left_thigh", "right_thigh") if n in bone_names]
        z_elbow_ref = 0.5 * (float(l_e[2]) + float(r_e[2]))
        below_elbow_tris = (vertices_out[faces_out, 2].mean(axis=1) < z_elbow_ref)
        arm_tris = np.isin(dom[faces_out], lower_arm_ids).any(axis=1) & below_elbow_tris
        if arm_tris.any():
            f_arm = faces_out[arm_tris]
            bridged = np.isin(dom[f_arm], torso_ids).any(axis=1)
            bleed_verts = (weights[f_arm.ravel()][:, torso_ids].sum(axis=1) > 0.08).mean()
            bridge_frac = float(bridged.mean())
            if bridge_frac > 0.015 or bleed_verts > 0.25:
                arm_mobility = float(np.clip(1.0 - max(bridge_frac / 0.08, bleed_verts / 0.55) * 0.78, 0.22, 1.0))
        if detached_limbs:
            arm_mobility = min(arm_mobility, 0.78)

    result = {
        "vertices": vertices_out,
        "faces": faces_out,
        "base_face_count": int(base_face_count),
        "detached_limbs": bool(detached_limbs),
        "bones": bones,
        "parents": parents,
        "bone_names": bone_names,
        "weights": weights,
        "joints": joints,
        "mouth": mouth,
        "normals": normals_out,
        "arm_mobility": np.float32(arm_mobility),
    }
    if colors_out is not None and colors is not None:
        result["colors"] = colors_out
    return result


def _rot_to_quat(rot):
    """Convert a batch or single 3x3 rotation matrix to unit quaternion (w, x, y, z)."""
    m00, m01, m02 = rot[0, 0], rot[0, 1], rot[0, 2]
    m10, m11, m12 = rot[1, 0], rot[1, 1], rot[1, 2]
    m20, m21, m22 = rot[2, 0], rot[2, 1], rot[2, 2]
    tr = float(m00 + m11 + m22)
    if tr > 0.0:
        s = math.sqrt(tr + 1.0) * 2.0
        q = np.array([0.25 * s, (m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s], dtype=np.float32)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(max(1e-8, 1.0 + m00 - m11 - m22)) * 2.0
        q = np.array([(m21 - m12) / s, 0.25 * s, (m01 + m10) / s, (m02 + m20) / s], dtype=np.float32)
    elif m11 > m22:
        s = math.sqrt(max(1e-8, 1.0 + m11 - m00 - m22)) * 2.0
        q = np.array([(m02 - m20) / s, (m01 + m10) / s, 0.25 * s, (m12 + m21) / s], dtype=np.float32)
    else:
        s = math.sqrt(max(1e-8, 1.0 + m22 - m00 - m11)) * 2.0
        q = np.array([(m10 - m01) / s, (m02 + m20) / s, (m12 + m21) / s, 0.25 * s], dtype=np.float32)
    return (q / max(1e-8, float(np.linalg.norm(q)))).astype(np.float32)


def dual_quaternion_skinning(vertices, normals, weights, transforms):
    """Volume-preserving Dual Quaternion Skinning (Kavan et al., I3D 2007)."""
    n_bones = len(transforms)
    qr = np.zeros((n_bones, 4), dtype=np.float32)
    qd = np.zeros((n_bones, 4), dtype=np.float32)
    for b, (rot, tr) in enumerate(transforms):
        q = _rot_to_quat(rot)
        tx, ty, tz = float(tr[0]), float(tr[1]), float(tr[2])
        # q_d = 0.5 * (0, tx, ty, tz) * q
        w, x, y, z = float(q[0]), float(q[1]), float(q[2]), float(q[3])
        qr[b] = q
        qd[b] = 0.5 * np.array([
            -(tx * x + ty * y + tz * z),
            tx * w + ty * z - tz * y,
            -tx * z + ty * w + tz * x,
            tx * y - ty * x + tz * w,
        ], dtype=np.float32)

    # Align every bone quaternion to the dominant bone's hemisphere per vertex to prevent antipodal flip.
    dom = np.argmax(weights, axis=1)
    q_dom = qr[dom]  # (V, 4)
    dots = np.einsum("vi,bi->vb", q_dom, qr)  # (V, B)
    signed_w = np.where(dots < 0.0, -weights, weights)

    blend_r = signed_w @ qr
    blend_d = signed_w @ qd
    norm_r = np.maximum(np.linalg.norm(blend_r, axis=1, keepdims=True), 1e-8)
    blend_r /= norm_r
    blend_d /= norm_r
    # Plucker orthogonalization for exact rigid translation recovery.
    dot_rd = np.sum(blend_r * blend_d, axis=1, keepdims=True)
    blend_d -= dot_rd * blend_r

    w, x, y, z = blend_r[:, 0:1], blend_r[:, 1:2], blend_r[:, 2:3], blend_r[:, 3:4]
    dw, dx, dy, dz = blend_d[:, 0:1], blend_d[:, 1:2], blend_d[:, 2:3], blend_d[:, 3:4]
    tx = 2.0 * (-dw * x + dx * w - dy * z + dz * y)
    ty = 2.0 * (-dw * y + dx * z + dy * w - dz * x)
    tz = 2.0 * (-dw * z - dx * y + dy * x + dz * w)
    trans = np.concatenate([tx, ty, tz], axis=1)

    def rotate_vec(v):
        q_xyz = blend_r[:, 1:4]
        t_vec = 2.0 * np.cross(q_xyz, v)
        return v + w * t_vec + np.cross(q_xyz, t_vec)

    deformed_v = rotate_vec(vertices) + trans
    deformed_n = rotate_vec(normals)
    n_len = np.maximum(np.linalg.norm(deformed_n, axis=1, keepdims=True), 1e-8)
    deformed_n /= n_len
    return deformed_v.astype(np.float32), deformed_n.astype(np.float32)


def knee_at(hip, ankle, l1, l2):
    delta = ankle - hip
    dy = delta[1]
    distance = math.hypot(delta[0], delta[2])
    limit = l1 + l2
    if distance > limit + 1e-4:
        raise ValueError("Unreachable leg target")
    distance = max(1e-6, min(distance, limit - 1e-6))
    direction = np.array([delta[0], 0, delta[2]]) / max(1e-6, math.hypot(delta[0], delta[2]))
    along = (l1 * l1 - l2 * l2 + distance * distance) / (2 * distance)
    p = hip + direction * along + np.array([-direction[2], 0, direction[0]]) * math.sqrt(max(0, l1 * l1 - along * along))
    p[1] += dy * 0.5
    return p


def pose(bones, phase=0.0, gait=0.0, crouch=0.0, tucked=0.0, bite=0.0, wave=0.0, height=1.0):
    targets = bones.copy()
    stride = 42 * 0.8 / (4 * 144 * 0.9) * height
    # Single-image reconstruction often leans the torso backwards. Repose the
    # upper body around the shared pelvis, preserving lengths and connections.
    pelvis = bones[1, 0]
    spine = bones[1, 1] - pelvis
    rest_lean = math.atan2(float(spine[0]), float(spine[2]))
    upright = float(np.clip(math.radians(2)-rest_lean, -math.radians(20), math.radians(20)))
    upper = ry(upright)
    drop = 0.0
    for i in (4, 9):
        hip = bones[i, 0]
        ankle = bones[i + 1, 1]
        length = sum(np.linalg.norm(bones[j, 1] - bones[j, 0]) for j in (i, i + 1))
        reach = math.sqrt(max(0.001, length * length - (abs(ankle[0] - hip[0]) + stride) ** 2)) * 0.98
        drop = min(drop, ankle[2] + reach - hip[2])
    shift = np.array([0, 0, drop * gait - height * 0.05 * crouch])
    targets[:2] = (bones[:2] - pelvis) @ upper.T + pelvis + shift
    for offset, start in ((0, 2), (0.5, 7)):
        u = (phase + offset) % 1
        swing = math.radians(25 * math.sin(u * 2 * math.pi) * gait - 30 * tucked - 18 * bite - 45 * wave * (1 if start == 7 else 0))
        targets[start, 0] = (bones[start, 0] - pelvis) @ upper.T + pelvis + shift
        targets[start, 1] = targets[start, 0] + ry(swing + upright) @ (bones[start, 1] - bones[start, 0])
        targets[start + 1, 0] = targets[start, 1]
        targets[start + 1, 1] = targets[start + 1, 0] + ry(swing + upright - math.radians(12 * gait + 35 * tucked)) @ (bones[start + 1, 1] - bones[start + 1, 0])
        hip = bones[start + 2, 0] + shift
        ankle = bones[start + 3, 1].copy()
        if u < 0.5:
            dx = stride * (1 - 4 * u)
            lift_z = 0
        else:
            f = (u - 0.5) * 2
            dx = -stride * math.cos(math.pi * f)
            lift_z = height * 0.045 * math.sin(math.pi * f)
        ankle += np.array([gait * dx, 0, gait * lift_z + tucked * height * 0.06])
        l1 = np.linalg.norm(bones[start + 2, 1] - bones[start + 2, 0])
        l2 = np.linalg.norm(bones[start + 3, 1] - bones[start + 3, 0])
        knee = knee_at(hip, ankle, l1, l2)
        targets[start + 2] = (hip, knee)
        targets[start + 3] = (knee, ankle)
        targets[start + 4] = (ankle, ankle + ry(math.radians(12 * tucked)) @ (bones[start + 4, 1] - bones[start + 4, 0]))
    matrices = []
    for index, ((a, b), (pa, pb)) in enumerate(zip(bones, targets)):
        v = b - a
        nv = pb - pa
        angle = math.atan2(-nv[0], -nv[2]) - math.atan2(-v[0], -v[2])
        if index == 0:
            angle = upright - math.radians(7 * bite)
        r = ry(angle)
        matrices.append((r, pa - r @ a))
    return matrices, targets


def _make_uv_sphere(center, radius, rings=10, sectors=12):
    verts = []
    faces = []
    cx, cy, cz = float(center[0]), float(center[1]), float(center[2])
    verts.append([cx, cy, cz + radius])
    for r in range(1, rings):
        phi = math.pi * r / rings
        z = cz + radius * math.cos(phi)
        r_ring = radius * math.sin(phi)
        for s in range(sectors):
            theta = 2.0 * math.pi * s / sectors
            x = cx + r_ring * math.cos(theta)
            y = cy + r_ring * math.sin(theta)
            verts.append([x, y, z])
    verts.append([cx, cy, cz - radius])
    bot_idx = len(verts) - 1

    for s in range(sectors):
        s_next = (s + 1) % sectors
        faces.append([0, 1 + s, 1 + s_next])
    for r in range(rings - 2):
        row_cur = 1 + r * sectors
        row_next = 1 + (r + 1) * sectors
        for s in range(sectors):
            s_next = (s + 1) % sectors
            a = row_cur + s
            b = row_cur + s_next
            c = row_next + s_next
            d = row_next + s
            faces.append([a, d, b])
            faces.append([b, d, c])
    row_bot = 1 + (rings - 2) * sectors
    for s in range(sectors):
        s_next = (s + 1) % sectors
        faces.append([row_bot + s, bot_idx, row_bot + s_next])

    return np.asarray(verts, dtype=np.float32), np.asarray(faces, dtype=np.int32)


def _make_cylinder(p0, p1, radius, rings=4, sectors=8):
    p0 = np.asarray(p0, dtype=np.float32)
    p1 = np.asarray(p1, dtype=np.float32)
    axis = p1 - p0
    length = float(np.linalg.norm(axis))
    dir_z = axis / length if length >= 1e-5 else np.array([0.0, 0.0, 1.0], dtype=np.float32)

    ref = np.array([1.0, 0.0, 0.0], dtype=np.float32) if abs(dir_z[0]) < 0.8 else np.array([0.0, 1.0, 0.0], dtype=np.float32)
    dir_x = np.cross(dir_z, ref)
    dir_x /= max(1e-6, float(np.linalg.norm(dir_x)))
    dir_y = np.cross(dir_z, dir_x)
    dir_y /= max(1e-6, float(np.linalg.norm(dir_y)))

    verts = []
    faces = []
    for r in range(rings):
        t = r / max(1, rings - 1)
        center = p0 + axis * t
        for s in range(sectors):
            theta = 2.0 * math.pi * s / sectors
            offset = dir_x * (radius * math.cos(theta)) + dir_y * (radius * math.sin(theta))
            verts.append(center + offset)

    for r in range(rings - 1):
        row_cur = r * sectors
        row_next = (r + 1) * sectors
        for s in range(sectors):
            s_next = (s + 1) % sectors
            a = row_cur + s
            b = row_cur + s_next
            c = row_next + s_next
            d = row_next + s
            faces.append([a, d, b])
            faces.append([b, d, c])

    return np.asarray(verts, dtype=np.float32), np.asarray(faces, dtype=np.int32)


def generate_parametric_chibi_template(height=1.0):
    """Step 4: Watertight, non-collapsed parametric 3D chibi template with separated limbs and analytical bone weights."""
    h = float(height)
    head_r = h * 0.22
    head_c = np.array([0.0, 0.0, h * 0.74], dtype=np.float32)
    torso_p0 = np.array([0.0, 0.0, h * 0.38], dtype=np.float32)
    torso_p1 = np.array([0.0, 0.0, h * 0.58], dtype=np.float32)
    torso_r = h * 0.14

    bone_names = [
        "head", "spine_lower", "chest", "pelvis",
        "left_arm", "left_forearm", "left_hand",
        "right_arm", "right_forearm", "right_hand",
        "left_thigh", "left_shin", "left_foot",
        "right_thigh", "right_shin", "right_foot"
    ]
    b_idx = {name: i for i, name in enumerate(bone_names)}
    n_bones = len(bone_names)

    parts = []
    v_h, f_h = _make_uv_sphere(head_c, head_r, rings=12, sectors=14)
    w_h = np.zeros((len(v_h), n_bones), dtype=np.float32)
    w_h[:, b_idx["head"]] = 1.0
    parts.append((v_h, f_h, w_h))

    v_t, f_t = _make_cylinder(torso_p0, torso_p1, torso_r, rings=6, sectors=12)
    w_t = np.zeros((len(v_t), n_bones), dtype=np.float32)
    t_z = (v_t[:, 2] - float(torso_p0[2])) / max(1e-4, float(torso_p1[2] - torso_p0[2]))
    w_t[:, b_idx["pelvis"]] = np.clip(1.0 - t_z * 2.0, 0.0, 1.0)
    w_t[:, b_idx["spine_lower"]] = np.clip(1.0 - abs(t_z - 0.5) * 2.5, 0.0, 1.0)
    w_t[:, b_idx["chest"]] = np.clip((t_z - 0.4) * 2.0, 0.0, 1.0)
    s_t = np.maximum(1e-6, w_t.sum(axis=1, keepdims=True))
    w_t /= s_t
    parts.append((v_t, f_t, w_t))

    limb_specs = [
        ("left_arm", np.array([0.0, h * 0.16, h * 0.54], dtype=np.float32), np.array([0.0, h * 0.22, h * 0.44], dtype=np.float32), h * 0.045),
        ("left_forearm", np.array([0.0, h * 0.22, h * 0.44], dtype=np.float32), np.array([0.0, h * 0.25, h * 0.33], dtype=np.float32), h * 0.042),
        ("right_arm", np.array([0.0, -h * 0.16, h * 0.54], dtype=np.float32), np.array([0.0, -h * 0.22, h * 0.44], dtype=np.float32), h * 0.045),
        ("right_forearm", np.array([0.0, -h * 0.22, h * 0.44], dtype=np.float32), np.array([0.0, -h * 0.25, h * 0.33], dtype=np.float32), h * 0.042),
        ("left_thigh", np.array([0.0, h * 0.08, h * 0.38], dtype=np.float32), np.array([0.0, h * 0.08, h * 0.21], dtype=np.float32), h * 0.052),
        ("left_shin", np.array([0.0, h * 0.08, h * 0.21], dtype=np.float32), np.array([0.0, h * 0.08, h * 0.06], dtype=np.float32), h * 0.048),
        ("right_thigh", np.array([0.0, -h * 0.08, h * 0.38], dtype=np.float32), np.array([0.0, -h * 0.08, h * 0.21], dtype=np.float32), h * 0.052),
        ("right_shin", np.array([0.0, -h * 0.08, h * 0.21], dtype=np.float32), np.array([0.0, -h * 0.08, h * 0.06], dtype=np.float32), h * 0.048),
    ]
    for b_name, p0, p1, r in limb_specs:
        v_l, f_l = _make_cylinder(p0, p1, r, rings=4, sectors=8)
        w_l = np.zeros((len(v_l), n_bones), dtype=np.float32)
        w_l[:, b_idx[b_name]] = 1.0
        parts.append((v_l, f_l, w_l))

    all_verts = []
    all_faces = []
    all_weights = []
    v_offset = 0
    for v, f, w in parts:
        all_verts.append(v)
        all_faces.append(f + v_offset)
        all_weights.append(w)
        v_offset += len(v)

    vertices = np.concatenate(all_verts, axis=0).astype(np.float32)
    faces = np.concatenate(all_faces, axis=0).astype(np.int32)
    weights = np.concatenate(all_weights, axis=0).astype(np.float32)
    return vertices, faces, weights, bone_names


def morph_chibi_template_to_landmarks(template_verts, template_faces, template_weights, bone_names, target_joints, height=1.0):
    """Morph parametric chibi template mesh onto detected 3D landmarks while preserving watertight tubular geometry."""
    morphed = template_verts.copy()
    b_idx = {name: i for i, name in enumerate(bone_names)}
    h = float(height)

    # 1. Morph Head
    head_mask = template_weights[:, b_idx["head"]] > 0.5
    if head_mask.any() and len(target_joints) > 2:
        eye_mid = (target_joints[1] + target_joints[2]) * 0.5
        head_c_tgt = eye_mid.copy()
        head_c_tgt[2] += h * 0.03
        head_c_src = template_verts[head_mask].mean(axis=0)
        morphed[head_mask] += (head_c_tgt - head_c_src)[None, :]

    # 2. Morph Arms (Shoulder -> Elbow -> Wrist)
    for side_sign, prefix, s_i, e_i, w_i in ((1.0, "left", 5, 7, 9), (-1.0, "right", 6, 8, 10)):
        if len(target_joints) > max(s_i, e_i, w_i):
            s_t, e_t, w_t = target_joints[[s_i, e_i, w_i]]
            arm_name = f"{prefix}_arm"
            fore_name = f"{prefix}_forearm"
            for b_name, (p0_t, p1_t) in ((arm_name, (s_t, e_t)), (fore_name, (e_t, w_t))):
                mask = template_weights[:, b_idx[b_name]] > 0.5
                if mask.any():
                    p0_s = template_verts[mask].min(axis=0)
                    p1_s = template_verts[mask].max(axis=0)
                    c_src = 0.5 * (p0_s + p1_s)
                    c_tgt = 0.5 * (p0_t + p1_t)
                    morphed[mask] += (c_tgt - c_src)[None, :]

    # 3. Morph Legs (Hip -> Knee -> Ankle)
    for side_sign, prefix, h_i, k_i, a_i in ((1.0, "left", 11, 13, 15), (-1.0, "right", 12, 14, 16)):
        if len(target_joints) > max(h_i, k_i, a_i):
            h_t, k_t, a_t = target_joints[[h_i, k_i, a_i]]
            thigh_name = f"{prefix}_thigh"
            shin_name = f"{prefix}_shin"
            for b_name, (p0_t, p1_t) in ((thigh_name, (h_t, k_t)), (shin_name, (k_t, a_t))):
                mask = template_weights[:, b_idx[b_name]] > 0.5
                if mask.any():
                    c_src = template_verts[mask].mean(axis=0)
                    c_tgt = 0.5 * (p0_t + p1_t)
                    morphed[mask] += (c_tgt - c_src)[None, :]

    return morphed

