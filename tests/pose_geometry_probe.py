"""Optional isolated-runtime math, rigging, DQS, BVH, and rasterization regressions."""
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "art_runtime"))
import numpy as np
import motion_bake as mb
import motion_geometry as g
import motion_library as ml


def _synthetic_humanoid_mesh():
    """Build a watertight multi-capsule humanoid triangle mesh (torso, head, hair, separated arms/legs)."""
    gx, gy, gz = np.meshgrid(
        np.linspace(-0.35, 0.35, 36, dtype=np.float32),
        np.linspace(-0.35, 0.35, 36, dtype=np.float32),
        np.linspace(-0.68, 0.68, 48, dtype=np.float32),
        indexing="ij",
    )
    def ellipsoid(cx, cy, cz, rx, ry, rz):
        return ((gx - cx) / rx) ** 2 + ((gy - cy) / ry) ** 2 + ((gz - cz) / rz) ** 2

    def capsule(ax, ay, az, bx, by, bz, rad):
        p = np.stack([gx, gy, gz], axis=-1)
        a = np.array([ax, ay, az], dtype=np.float32)
        b = np.array([bx, by, bz], dtype=np.float32)
        ab = b - a
        t = np.clip(np.sum((p - a) * ab, axis=-1) / np.dot(ab, ab), 0.0, 1.0)
        dist = np.linalg.norm(p - (a + t[..., None] * ab), axis=-1)
        return (dist / rad) ** 2

    field = np.minimum.reduce([
        ellipsoid(0.0, 0.0, 0.42, 0.22, 0.22, 0.20),          # head
        ellipsoid(0.0, 0.26, 0.35, 0.08, 0.07, 0.14),         # protruding left hair/ear tuft
        ellipsoid(0.0, -0.26, 0.35, 0.08, 0.07, 0.14),        # protruding right hair/ear tuft
        ellipsoid(0.02, 0.0, 0.04, 0.12, 0.14, 0.24),         # torso
        capsule(0.0, 0.16, 0.18, 0.02, 0.24, -0.22, 0.055),   # left arm (separated from torso)
        capsule(0.0, -0.16, 0.18, 0.02, -0.24, -0.22, 0.055), # right arm (separated from torso)
        capsule(0.0, 0.09, -0.14, 0.02, 0.09, -0.56, 0.065),  # left leg
        capsule(0.0, -0.09, -0.14, 0.02, -0.09, -0.56, 0.065),# right leg
    ])
    # Convert SDF-like inside (<1) to density > 25.
    density = np.clip(50.0 * (1.2 - field), 0.0, 60.0).astype(np.float32)
    # Build cubic-indexed marching tetrahedra on uniform grid via extract(): use uniform cube grid if isotropic.
    # Resample onto uniform cube grid 40^3 for extract(density, radius=0.70).
    u = np.linspace(-0.70, 0.70, 40, dtype=np.float32)
    cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
    def ell(px, py, pz, rx, ry, rz):
        return ((cx - px) / rx) ** 2 + ((cy - py) / ry) ** 2 + ((cz - pz) / rz) ** 2
    def cap(ax, ay, az, bx, by, bz, rad):
        p = np.stack([cx, cy, cz], axis=-1)
        a = np.array([ax, ay, az], dtype=np.float32)
        b = np.array([bx, by, bz], dtype=np.float32)
        ab = b - a
        t = np.clip(np.sum((p - a) * ab, axis=-1) / np.dot(ab, ab), 0.0, 1.0)
        return (np.linalg.norm(p - (a + t[..., None] * ab), axis=-1) / rad) ** 2
    f2 = np.minimum.reduce([
        ell(0.0, 0.0, 0.42, 0.20, 0.20, 0.19),
        ell(0.0, 0.25, 0.36, 0.08, 0.08, 0.14),
        ell(0.0, -0.25, 0.36, 0.08, 0.08, 0.14),
        ell(0.01, 0.0, 0.04, 0.12, 0.12, 0.22),
        cap(0.0, 0.15, 0.18, 0.02, 0.24, -0.22, 0.065),
        cap(0.0, -0.15, 0.18, 0.02, -0.24, -0.22, 0.065),
        cap(0.0, 0.09, -0.14, 0.02, 0.09, -0.55, 0.07),
        cap(0.0, -0.09, -0.14, 0.02, -0.09, -0.55, 0.07),
    ])
    dens = np.clip(50.0 * (1.2 - f2), 0.0, 60.0).astype(np.float32)
    vertices, faces, points = g.extract(dens, radius=0.70, threshold=25.0)
    joints = np.array([
        [0.20, 0.0, 0.40], [0.18, 0.06, 0.44], [0.18, -0.06, 0.44], [0.10, 0.14, 0.40], [0.10, -0.14, 0.40],
        [0.05, 0.15, 0.18], [0.05, -0.15, 0.18], [0.06, 0.21, -0.02], [0.06, -0.21, -0.02], [0.07, 0.24, -0.20], [0.07, -0.24, -0.20],
        [0.06, 0.09, -0.14], [0.06, -0.09, -0.14], [0.06, 0.09, -0.35], [0.06, -0.09, -0.35], [0.06, 0.09, -0.54], [0.06, -0.09, -0.54],
    ], dtype=np.float32)
    return vertices, faces, points, joints


class PoseGeometryTests(unittest.TestCase):
    def fixture(self):
        joints = np.array([
            [.3, 0, .35], [.28, .06, .4], [.28, -.06, .4], [.2, .12, .4], [.2, -.12, .4],
            [.12, .15, .2], [.12, -.15, .2], [.15, .24, -.05], [.15, -.24, -.05], [.2, .25, -.25], [.2, -.25, -.25],
            [.3, .1, -.15], [.3, -.1, -.15], [.22, .1, -.35], [.22, -.1, -.35], [.2, .1, -.56], [.2, -.1, -.56],
        ], np.float32)
        points = np.random.default_rng(123).uniform([-.25, -.3, -.65], [.35, .3, .6], (6000, 3)).astype(np.float32)
        points = np.concatenate([points, np.array([[.25, 0, .32], [.26, .01, .32]], np.float32)])
        with patch.object(g, "lift", side_effect=[joints.copy(), np.array([[.25, 0, .32]], np.float32)]):
            b, w, j, m = g.fit(points, np.zeros((17, 2)), [.5, .4])
        return b, w, j, m, float(np.ptp(points[:, 2]))

    def test_body_and_limb_pivots_share_regularized_joint_depths(self):
        b, w, j, m, h = self.fixture()
        np.testing.assert_allclose(b[1, 0], (j[11] + j[12]) / 2, atol=1e-6)
        neck = (j[5] + j[6]) / 2
        neck[2] += h * .035
        np.testing.assert_allclose(b[1, 1], neck, atol=1e-6)
        np.testing.assert_allclose(b[0, 0], b[1, 1], atol=1e-6)
        self.assertTrue(np.isfinite(w).all())
        self.assertGreaterEqual(w.min(), 0)
        np.testing.assert_allclose(w.sum(1), 1, atol=1e-6)

    def test_upright_cycle_preserves_spine_head_and_leg_lengths(self):
        b, w, j, m, h = self.fixture()
        lengths = np.linalg.norm(b[:, 1] - b[:, 0], axis=1)
        for phase in np.linspace(0, 1, 25):
            matrices, t = g.pose(b, phase=phase, gait=1, height=h)
            v = t[1, 1] - t[1, 0]
            self.assertAlmostEqual(math.degrees(math.atan2(v[0], v[2])), 2, places=4)
            np.testing.assert_allclose(np.linalg.norm(t[:, 1] - t[:, 0], axis=1), lengths, atol=1e-5)
            np.testing.assert_allclose(t[0, 0], t[1, 1], atol=1e-6)
            self.assertTrue(all(np.isfinite(r).all() and np.isfinite(p).all() for r, p in matrices))

    def test_ankle_stance_stays_planted_and_upper_body_fix_is_bounded(self):
        b, w, j, m, h = self.fixture()
        for phase in (0, .1, .25, .49):
            _, t = g.pose(b, phase=phase, gait=1, height=h)
            self.assertAlmostEqual(t[5, 1, 2], b[5, 1, 2], places=6)
        for gait in (0, 1):
            _, t = g.pose(b, gait=gait, height=h)
            old = math.atan2(*(b[1, 1] - b[1, 0])[[0, 2]])
            new = math.atan2(*(t[1, 1] - t[1, 0])[[0, 2]])
            self.assertLessEqual(abs(new - old), math.radians(20) + 1e-6)

    def test_articulated_rig_geodesic_weights_dqs_and_all_clips(self):
        vertices, faces, points, joints = _synthetic_humanoid_mesh()
        with patch.object(g, "lift", side_effect=[joints.copy(), np.array([[0.20, 0.0, 0.36]], np.float32)]):
            rig = g.fit_articulated(vertices, faces, np.zeros((17, 2)), [.5, .3])
        bones = rig["bones"]
        parents = rig["parents"]
        names = rig["bone_names"]
        weights = rig["weights"]
        mesh_verts = rig.get("vertices", vertices)
        self.assertGreaterEqual(len(bones), 22)
        self.assertEqual(names[:4], ["head", "spine_lower", "left_arm", "left_forearm"])
        self.assertIn("left_clavicle", names)
        self.assertIn("left_toe", names)
        self.assertIn("jaw", names)
        self.assertTrue(np.isfinite(weights).all())
        self.assertGreaterEqual(weights.min(), 0.0)
        np.testing.assert_allclose(weights.sum(1), 1.0, atol=1e-5)

        # Geodesic separation: left arm extremity vertices should have negligible right-arm/leg bleed.
        left_arm_tip = (mesh_verts[:, 1] > 0.21) & (mesh_verts[:, 2] < -0.10)
        self.assertTrue(left_arm_tip.any())
        self.assertLess(weights[left_arm_tip, names.index("right_arm")].mean(), 0.02)
        self.assertLess(weights[left_arm_tip, names.index("chest")].mean(), 0.15)

        # Verify all 12 clips bake finite DQS + spring poses and reverse-foot ball grounding.
        for clip, count in mb.COUNTS.items():
            frames_tr, tracks = ml.generate_clip_poses(clip, min(12, count), bones, parents, names, fps=30)
            self.assertEqual(len(frames_tr), min(12, count))
            def_v, def_n = g.dual_quaternion_skinning(mesh_verts, rig["normals"], weights, frames_tr[len(frames_tr) // 2])
            self.assertTrue(np.isfinite(def_v).all() and np.isfinite(def_n).all())
            np.testing.assert_allclose(np.linalg.norm(def_n, axis=1), 1.0, atol=1e-4)

        # Reverse foot check: during flat mid-stance (s in [0.16..0.68]), ball Z stays on floor_ball_z.
        rest_a = bones[names.index("left_shin"), 1]
        rest_b = bones[names.index("left_foot"), 1]
        rest_t = bones[names.index("left_toe"), 1]
        for u in (0.12, 0.20, 0.30):
            _, ball_pt, _ = ml.reverse_foot_targets(rest_a, rest_b, rest_t, stride=0.05, lift_height=0.04, phase_u=u, gait=1.0, tucked=0.0, crouch_shift=np.zeros(3, np.float32))
            self.assertAlmostEqual(float(ball_pt[2]), float(rest_b[2]), places=5)

    def test_triangle_rasterizer_and_multiview_projection_and_bvh_retarget(self):
        vertices, faces, _, joints = _synthetic_humanoid_mesh()
        normals = g.compute_vertex_normals(vertices, faces)
        # Render synthetic front/back views and crisp front RGBA reference.
        front_view = np.tile(np.array([0.2, 0.6, 0.9], dtype=np.float32), (128, 128, 1))
        back_view = np.tile(np.array([0.8, 0.3, 0.2], dtype=np.float32), (128, 128, 1))
        views = [
            {"rgb": front_view, "az": 0.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0},
            {"rgb": back_view, "az": 180.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0},
        ]
        rgba_ref = np.zeros((128, 128, 4), dtype=np.float32)
        rgba_ref[16:112, 32:96] = [0.1, 0.7, 0.95, 1.0]
        colors = g.project_multiview_colors(vertices, views, normals=normals, ref_views=[{"rgba": rgba_ref, "az": 0.0, "el": 0.0, "weight": 4.0}])
        self.assertEqual(colors.shape, vertices.shape)
        self.assertTrue(np.isfinite(colors).all())
        # Back-facing vertices should retain back-view red hue instead of bleeding front blue.
        back_verts = normals[:, 0] < -0.7
        self.assertTrue(back_verts.any())
        self.assertGreater(colors[back_verts, 0].mean(), colors[back_verts, 2].mean())

        mouth = np.array([0.20, 0.0, 0.36], dtype=np.float32)
        img, anchor = mb.render_mesh(vertices, faces, colors, normals, 0.0, float(vertices[:, 2].min()), float(vertices[:, 2].max()), mouth, out_size=256)
        self.assertEqual(img.size, (256, 256))
        arr = np.asarray(img)
        self.assertGreater((arr[:, :, 3] > 200).sum(), 2000)
        self.assertTrue(all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in anchor))

        # BVH parse + proportion-aware retargeting smoke test.
        bvh_text = """HIERARCHY
ROOT Hips
{
  OFFSET 0 0 0
  CHANNELS 6 Xposition Yposition Zposition Zrotation Xrotation Yrotation
  JOINT Spine
  {
    OFFSET 0 0.3 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT Head
    {
      OFFSET 0 0.4 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      End Site { OFFSET 0 0.2 0 }
    }
  }
  JOINT LeftUpLeg
  {
    OFFSET 0.1 0 0
    CHANNELS 3 Zrotation Xrotation Yrotation
    JOINT LeftLeg
    {
      OFFSET 0 -0.4 0
      CHANNELS 3 Zrotation Xrotation Yrotation
      JOINT LeftFoot
      {
        OFFSET 0 -0.4 0
        CHANNELS 3 Zrotation Xrotation Yrotation
        End Site { OFFSET 0 -0.1 0.1 }
      }
    }
  }
}
MOTION
Frames: 2
Frame Time: 0.0333333
0 0.8 0 0 0 0 5 0 0 0 0 0 15 0 0 -20 0 0 5 0 0
0 0.8 0.1 0 0 0 4 0 0 0 0 0 10 0 0 -15 0 0 5 0 0
"""
        parsed = ml.parse_bvh(bvh_text)
        self.assertEqual(len(parsed["frames"]), 2)
        with patch.object(g, "lift", side_effect=[joints.copy(), mouth[None]]):
            rig = g.fit_articulated(vertices, faces, np.zeros((17, 2)), [.5, .3])
        ret = ml.retarget_bvh(parsed, rig["bones"], rig["bone_names"], lock_feet=True)
        self.assertEqual(len(ret), 2)
        self.assertEqual(len(ret[0]), len(rig["bones"]))

    def test_chibi_neck_pinch_silhouette_arms_and_head_isolation(self):
        # Synthetic chibi mesh: oversized cranial hair dome, narrow neck pinch, and flared sleeves.
        u = np.linspace(-0.70, 0.70, 38, dtype=np.float32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        def ell(px, py, pz, rx, ry, rz):
            return ((cx - px) / rx) ** 2 + ((cy - py) / ry) ** 2 + ((cz - pz) / rz) ** 2
        f = np.minimum.reduce([
            ell(0.0, 0.0, 0.30, 0.26, 0.30, 0.25),   # large chibi head/hair
            ell(0.0, 0.0, 0.02, 0.09, 0.09, 0.14),   # narrow neck bridge
            ell(0.02, 0.0, -0.16, 0.12, 0.13, 0.20), # torso
            ell(0.02, 0.19, -0.22, 0.07, 0.07, 0.15),# fused left hanging sleeve
            ell(0.02, -0.19, -0.22, 0.07, 0.07, 0.15),# fused right hanging sleeve
            ell(0.02, 0.08, -0.42, 0.07, 0.06, 0.14),# left leg
            ell(0.02, -0.08, -0.42, 0.07, 0.06, 0.14),# right leg
        ])
        verts, faces, _ = g.extract(np.clip(50.0 * (1.2 - f), 0.0, 60.0).astype(np.float32), radius=0.70, threshold=25.0)
        pinch = g._find_neck_pinch(verts)
        self.assertIsNotNone(pinch)
        z_neck, _ = pinch
        self.assertGreater(z_neck, -0.12)
        self.assertLess(z_neck, 0.12)

        # Simulate ViTPose crushing shoulders and wrists up inside the hair above z_neck.
        bad_joints = np.array([
            [0.15, 0.0, 0.22], [0.15, 0.06, 0.24], [0.15, -0.06, 0.24], [0.10, 0.14, 0.22], [0.10, -0.14, 0.22],
            [0.10, 0.12, z_neck + 0.14], [0.10, -0.12, z_neck + 0.14],
            [0.08, 0.20, z_neck + 0.10], [0.08, -0.20, z_neck + 0.10],
            [0.08, 0.19, z_neck + 0.09], [0.08, -0.19, z_neck + 0.09],
            [0.08, 0.08, -0.32], [0.08, -0.08, -0.32],
            [0.08, 0.08, -0.44], [0.08, -0.08, -0.44],
            [0.08, 0.08, -0.56], [0.08, -0.08, -0.56],
        ], dtype=np.float32)
        with patch.object(g, "lift", side_effect=[bad_joints.copy(), np.array([[0.22, 0.0, 0.16]], np.float32)]):
            rig = g.fit_articulated(verts, faces, np.zeros((17, 2)), [0.5, 0.45])
        w = rig["weights"]
        names = rig["bone_names"]
        arm_cols = [names.index(n) for n in ("left_arm", "left_forearm", "left_hand", "right_arm", "right_forearm", "right_hand")]
        v_rig = rig["vertices"]
        f_rig = rig["faces"]
        upper_hair = v_rig[:, 2] > z_neck + 0.12
        self.assertTrue(upper_hair.any())
        self.assertLess(w[upper_hair][:, arm_cols].sum(axis=1).max(), 0.03)
        self.assertTrue(rig["detached_limbs"])
        self.assertGreater(len(f_rig), len(faces))
        self.assertGreaterEqual(float(rig["arm_mobility"]), 0.70)
        trs, _ = ml.generate_clip_poses("wave", 8, rig["bones"], rig["parents"], names, fps=30, arm_mobility=float(rig["arm_mobility"]))
        self.assertEqual(len(trs), 8)

        # Verify 4-chart UV atlas baking + bilinear textured mesh rendering on detached limbs.
        front_view = np.tile(np.array([0.2, 0.6, 0.9], dtype=np.float32), (128, 128, 1))
        atlas, face_uvs = g.bake_texture_atlas(verts, faces, g.compute_vertex_normals(verts, faces), [{"rgb": front_view, "az": 0.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0}], atlas_w=512, atlas_h=512)
        self.assertEqual(atlas.shape, (512, 512, 3))
        self.assertEqual(face_uvs.shape, (len(faces), 3, 2))
        dv, dn = g.dual_quaternion_skinning(v_rig, rig["normals"], w, trs[4])
        c_rig = np.full_like(v_rig, 0.7)
        rendered, _ = mb.render_mesh(dv, f_rig, c_rig, dn, 0.0, float(v_rig[:, 2].min()), float(v_rig[:, 2].max()), rig["mouth"], out_size=128, atlas=atlas.astype(np.float32) / 255.0, face_uvs=face_uvs)
        self.assertEqual(rendered.size, (128, 128))

    def test_overlap_free_six_direction_atlas_preserves_occluded_overhang_colors(self):
        # Two stacked slabs both facing +X (front overhang occludes rear slab in orthographic +X view):
        # overlap-free depth-peeled atlas must keep front blue AND rear green distinct instead of overwriting rear texels!
        u = np.linspace(-0.55, 0.55, 34, dtype=np.float32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        def slab(px, py, pz, rx, ry, rz):
            return ((cx - px) / rx) ** 2 + ((cy - py) / ry) ** 2 + ((cz - pz) / rz) ** 2
        f = np.minimum(
            slab(0.18, 0.0, 0.0, 0.07, 0.16, 0.18),   # small front shield in +X
            slab(-0.14, 0.0, 0.0, 0.08, 0.34, 0.34),  # wide rear backdrop also with +X normal faces
        )
        verts, faces, _ = g.extract(np.clip(50.0 * (1.2 - f), 0.0, 60.0).astype(np.float32), radius=0.55, threshold=25.0)
        normals = g.compute_vertex_normals(verts, faces)
        front_view = np.tile(np.array([0.1, 0.3, 0.95], dtype=np.float32), (128, 128, 1))
        side_view = np.tile(np.array([0.15, 0.85, 0.25], dtype=np.float32), (128, 128, 1))
        views = [
            {"rgb": front_view, "az": 0.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 2.0},
            {"rgb": side_view, "az": 65.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 2.0},
            {"rgb": side_view, "az": 295.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 2.0},
        ]
        atlas, fuv = g.bake_texture_atlas(verts, faces, normals, views, atlas_w=640, atlas_h=640)
        self.assertEqual(atlas.shape, (640, 640, 3))
        self.assertTrue((fuv[:, 0, 0] >= 0.0).all())
        f_c = verts[faces].mean(axis=1)
        f_n = normals[faces].mean(axis=1)
        occluded_front_facing = (f_c[:, 0] < -0.04) & (f_n[:, 0] > 0.6) & (np.abs(f_c[:, 1]) < 0.12) & (np.abs(f_c[:, 2]) < 0.12)
        front_shield = (f_c[:, 0] > 0.18) & (f_n[:, 0] > 0.6)
        self.assertTrue(occluded_front_facing.any() and front_shield.any())
        uc = fuv.mean(axis=1)
        px = np.clip((uc[:, 0] * 640).astype(int), 0, 639)
        py = np.clip((uc[:, 1] * 640).astype(int), 0, 639)
        sampled = atlas[py, px].astype(np.float32) / 255.0
        # Front shield stays blue (B > G), while occluded +X rear wall behind shield keeps green (G > B).
        self.assertGreater(sampled[front_shield, 2].mean(), sampled[front_shield, 1].mean())
        self.assertGreater(sampled[occluded_front_facing, 1].mean(), sampled[occluded_front_facing, 2].mean())

    def test_taubin_fairing_and_full_cylindrical_sleeve_detach(self):
        vertices, faces, _, joints = _synthetic_humanoid_mesh()
        rng = np.random.default_rng(7)
        noisy = vertices + rng.normal(0.0, 0.004, vertices.shape).astype(np.float32)
        faired = g.fair_mesh_taubin(noisy, faces, iterations=4, lam=0.45, mu=-0.47, front_weight=0.35)
        self.assertEqual(faired.shape, vertices.shape)
        self.assertLess(np.linalg.norm(faired - vertices, axis=1).mean(), np.linalg.norm(noisy - vertices, axis=1).mean())
        self.assertLess(np.linalg.norm(faired.mean(axis=0) - vertices.mean(axis=0)), 0.005)

    def test_cutout_strips_bottom_neutral_cast_shadow_without_eroding_boots(self):
        import runner
        rgb = np.ones((128, 128, 3), dtype=np.float32)
        alpha = np.zeros((128, 128), dtype=np.float32)
        # Body + two separated teal boots with full opacity:
        rgb[24:92, 42:86] = [0.55, 0.35, 0.22]
        alpha[24:92, 42:86] = 0.98
        rgb[92:114, 42:56] = [0.10, 0.52, 0.55]
        alpha[92:114, 42:56] = 0.98
        rgb[92:114, 72:86] = [0.10, 0.52, 0.55]
        alpha[92:114, 72:86] = 0.98
        # Neutral grey floor shadow slab connecting between and under the boots (u2netp false foreground):
        rgb[108:120, 32:96] = [0.76, 0.76, 0.76]
        alpha[108:120, 32:96] = 0.55
        # Detached tiny warm shadow droplet off to the bottom-left:
        rgb[114:120, 10:20] = [0.68, 0.63, 0.60]
        alpha[114:120, 10:20] = 0.80
        _, clean_a = runner.clean_cutout_rgba(rgb, alpha)
        self.assertGreater(clean_a[100, 48], 0.90)
        self.assertGreater(clean_a[100, 78], 0.90)
        self.assertEqual(float(clean_a[116, 64]), 0.0)
        self.assertEqual(float(clean_a[116, 14]), 0.0)

    def test_pose_suggest_accepts_non_skin_paws_and_rejects_hidden_cloak_hands(self):
        import pose
        from PIL import Image

        side = 256
        # Cream muzzle at nose (dist >> 95 from brown paws), mint vest torso, separated brown paws & boots.
        rgb = np.zeros((side, side, 3), dtype=np.float32)
        alpha = np.zeros((side, side), dtype=bool)
        rgb[55:115, 98:158] = [248.0, 236.0, 220.0]
        alpha[55:115, 98:158] = True
        rgb[115:175, 102:154] = [45.0, 170.0, 162.0]
        alpha[115:175, 102:154] = True
        # Separated cream sleeves + dark brown paws
        rgb[120:145, 76:96] = [238.0, 230.0, 218.0]
        alpha[120:145, 76:96] = True
        rgb[145:166, 72:92] = [92.0, 56.0, 36.0]
        alpha[145:166, 72:92] = True
        rgb[120:145, 160:180] = [238.0, 230.0, 218.0]
        alpha[120:145, 160:180] = True
        rgb[145:166, 164:184] = [92.0, 56.0, 36.0]
        alpha[145:166, 164:184] = True
        # Feet
        rgb[180:220, 106:124] = [52.0, 130.0, 140.0]
        alpha[180:220, 106:124] = True
        rgb[180:220, 132:150] = [52.0, 130.0, 140.0]
        alpha[180:220, 132:150] = True

        pts = np.zeros((17, 2), dtype=np.float32)
        pts[0] = [0.50, 0.34]
        pts[5], pts[6] = [0.42, 0.47], [0.58, 0.47]
        pts[7], pts[8] = [0.35, 0.53], [0.65, 0.53]
        pts[9], pts[10] = [0.32, 0.60], [0.68, 0.60]
        pts[11], pts[12] = [0.45, 0.68], [0.55, 0.68]
        pts[15], pts[16] = [0.45, 0.80], [0.55, 0.80]
        scs = np.full(17, 0.85, dtype=np.float32)

        rig = pose._extract_rig(pts, scs, rgb, alpha, side)
        self.assertIsNotNone(rig)
        self.assertEqual(set(rig["parts"]), {"left_hand", "right_hand", "left_foot", "right_foot"})
        # Tight torso/shoulder inward walls keep brown paws off the vest seam, and coordinates are pure JSON floats.
        import json
        self.assertIsInstance(json.dumps(rig), str)
        self.assertLess(max(p[0] for p in rig["parts"]["left_hand"]["polygon"]), 0.42)
        self.assertGreater(min(p[0] for p in rig["parts"]["right_hand"]["polygon"]), 0.58)
        # Padded foreground box stays [x, y, w, h] around opaque region rather than full canvas.
        canvas = np.zeros((512, 512, 4), dtype=np.uint8)
        canvas[160:352, 192:320, 3] = 255
        fg_box = pose._foreground_box(Image.fromarray(canvas, "RGBA"))
        self.assertLess(fg_box[2], 300)
        self.assertLess(fg_box[3], 300)

        # Hidden hands buried inside a solid monochromatic purple cloak (no alpha gap, matches torso) must reject.
        rgb_cloak = rgb.copy()
        alpha_cloak = alpha.copy()
        rgb_cloak[115:185, 65:191] = [70.0, 50.0, 125.0]
        alpha_cloak[115:185, 65:191] = True
        self.assertIsNone(pose._extract_rig(pts, scs, rgb_cloak, alpha_cloak, side))

    def test_fit_articulated_stabilizes_stubby_chibi_knees_merged_with_ankles(self):
        verts, faces, _, joints = _synthetic_humanoid_mesh()
        kps = np.zeros((17, 2), dtype=np.float32)
        for idx, pt in enumerate(joints):
            kps[idx] = [0.5 + float(pt[1]) * 0.4, 0.5 - float(pt[2]) * 0.4]
        kps[13] = kps[15].copy()
        kps[14] = kps[16].copy()
        merged_joints = joints.copy()
        merged_joints[13] = merged_joints[15].copy()
        merged_joints[14] = merged_joints[16].copy()
        with patch.object(g, "lift_medial", return_value=merged_joints), \
             patch.object(g, "lift", return_value=np.array([[0.20, 0.0, 0.34]], np.float32)):
            rig = g.fit_articulated(verts, faces, kps, [0.5, 0.36])
        self.assertGreater(len(rig["bones"]), 15)
        self.assertTrue(np.isfinite(rig["weights"]).all())

    def test_predict_pose_passes_dataset_index_for_moe_and_casts_float32_heatmaps(self):
        from types import SimpleNamespace
        from PIL import Image
        import pose
        import torch

        seen = {}

        class FakeModel:
            config = SimpleNamespace(backbone_config=SimpleNamespace(num_experts=6))
            _param = torch.zeros(1, dtype=torch.float16)

            def parameters(self):
                return iter([self._param])

            def __call__(self, **kwargs):
                seen["kwargs"] = kwargs
                return SimpleNamespace(heatmaps=torch.zeros((1, 17, 64, 48), dtype=torch.float16))

        class FakeProcessor:
            def __call__(self, images, boxes, return_tensors):
                return {"pixel_values": torch.zeros((len(boxes[0]), 3, 256, 192), dtype=torch.float32)}

            def post_process_pose_estimation(self, output, boxes=None, threshold=0.3):
                seen["heatmap_dtype"] = output.heatmaps.dtype
                return [[{"keypoints": torch.zeros((17, 2), dtype=torch.float32), "scores": torch.ones((17,), dtype=torch.float32)}]]

        pts, scs = pose.predict_pose(
            FakeProcessor(),
            FakeModel(),
            Image.new("RGB", (128, 128)),
            [[[10, 10, 100, 110]]],
        )
        self.assertIn("dataset_index", seen["kwargs"])
        self.assertEqual(seen["kwargs"]["dataset_index"].tolist(), [0])
        self.assertEqual(seen["kwargs"]["pixel_values"].dtype, torch.float16)
        self.assertEqual(seen["heatmap_dtype"], torch.float32)
        self.assertEqual(pts.shape, (17, 2))
        self.assertEqual(scs.shape, (17,))

    def test_pose_captures_distal_hands_and_two_tone_shoes_below_cuffs(self):
        import pose

        side = 384
        rgb = np.zeros((side, side, 3), dtype=np.float32)
        alpha = np.zeros((side, side), dtype=bool)
        # Head skin, torso jacket, cream sleeves, dark wrist cuff seams, peach fists below cuffs.
        rgb[70:145, 145:239] = [246.0, 210.0, 190.0]
        alpha[70:145, 145:239] = True
        rgb[145:265, 145:239] = [225.0, 215.0, 195.0]
        alpha[145:265, 145:239] = True
        # Upper sleeves meet the jacket torso (as in real standing coats), then cuffs & fists separate distally.
        rgb[160:220, 136:145] = [248.0, 242.0, 222.0]
        alpha[160:220, 136:145] = True
        rgb[160:220, 239:248] = [248.0, 242.0, 222.0]
        alpha[160:220, 239:248] = True
        # Cream cuffs right above wrist y=244 (0.635), dark ink wrist seam y=242..249, fists y=249..278.
        for x0, x1 in ((108, 136), (248, 276)):
            rgb[160:242, x0:x1] = [248.0, 242.0, 222.0]
            alpha[160:242, x0:x1] = True
            rgb[242:249, x0:x1] = [155.0, 110.0, 90.0]
            alpha[242:249, x0:x1] = True
            rgb[249:278, x0 + 2:x1 - 2] = [253.0, 222.0, 200.0]
            alpha[249:278, x0 + 2:x1 - 2] = True
        # Rolled blue-grey trouser cuffs y=275..336 (ankle=336 -> 0.875), brown shoes y=337..356 + white sole y=356..366.
        for x0, x1 in ((144, 182), (202, 240)):
            rgb[265:336, x0:x1] = [110.0, 125.0, 165.0]
            alpha[265:336, x0:x1] = True
            rgb[336:356, x0 - 6:x1 + 6] = [185.0, 125.0, 75.0]
            alpha[336:356, x0 - 6:x1 + 6] = True
            rgb[356:364, x0 - 6:x1 + 6] = [242.0, 237.0, 234.0]
            alpha[356:364, x0 - 6:x1 + 6] = True
            rgb[364:368, x0 - 6:x1 + 6] = [68.0, 42.0, 52.0]
            alpha[364:368, x0 - 6:x1 + 6] = True

        pts = np.zeros((17, 2), dtype=np.float32)
        pts[0] = [0.50, 0.30]
        pts[5], pts[6] = [0.60, 0.45], [0.40, 0.45]
        pts[7], pts[8] = [0.68, 0.54], [0.32, 0.54]
        pts[9], pts[10] = [0.68, 0.635], [0.32, 0.635]
        pts[11], pts[12] = [0.58, 0.68], [0.42, 0.68]
        pts[13], pts[14] = [0.58, 0.78], [0.42, 0.78]
        pts[15], pts[16] = [0.575, 0.875], [0.425, 0.875]
        scs = np.full(17, 0.92, dtype=np.float32)

        rig = pose._extract_rig(pts, scs, rgb, alpha, side)
        self.assertIsNotNone(rig)
        for side_hand in ("left_hand", "right_hand"):
            ys = [p[1] for p in rig["parts"][side_hand]["polygon"]]
            self.assertGreaterEqual(min(ys), 0.625)
            self.assertGreater(max(ys), 0.70)  # full fist down to ~0.724, not stuck at cuff 0.64
        for side_foot in ("left_foot", "right_foot"):
            ys = [p[1] for p in rig["parts"][side_foot]["polygon"]]
            self.assertGreaterEqual(min(ys), 0.85)  # does not climb up trouser legs
            self.assertGreater(max(ys), 0.94)  # captures brown shoe AND white sole to ~0.958
        self.assertLessEqual(len(pose._simplify_hull([(float(i), float(i * i)) for i in range(40)], 24)), 24)

    def test_detect_secondary_springs_ignores_high_hair_nape_and_keeps_low_tail(self):
        # Hair nape bulb just under neck stays rigid on head/torso; real lower tail below torso promotes spring_back_tail.
        u = np.linspace(-0.60, 0.60, 36, dtype=np.float32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        def ell(px, py, pz, rx, ry, rz):
            return ((cx - px) / rx) ** 2 + ((cy - py) / ry) ** 2 + ((cz - pz) / rz) ** 2
        neck = np.array([0.0, 0.0, 0.04], dtype=np.float32)
        pelvis_top = np.array([0.0, 0.0, -0.22], dtype=np.float32)
        head = np.array([0.0, 0.0, 0.36], dtype=np.float32)
        base_field = np.minimum.reduce([
            ell(0.0, 0.0, 0.24, 0.16, 0.18, 0.16),      # head
            ell(0.0, 0.0, 0.04, 0.07, 0.07, 0.10),      # neck
            ell(0.0, 0.0, -0.14, 0.10, 0.11, 0.18),     # torso
            ell(0.0, 0.17, -0.14, 0.06, 0.06, 0.15),    # left arm
            ell(0.0, -0.17, -0.14, 0.06, 0.06, 0.15),   # right arm
            ell(0.0, 0.06, -0.34, 0.055, 0.05, 0.12),   # left leg
            ell(0.0, -0.06, -0.34, 0.055, 0.05, 0.12),  # right leg
            ell(-0.09, 0.0, 0.06, 0.09, 0.09, 0.045),    # hair nape bulb strictly above neck_z - 0.06*h
        ])
        verts_hair, faces_hair, _ = g.extract(np.clip(50.0 * (1.2 - base_field), 0.0, 60.0).astype(np.float32), radius=0.60, threshold=25.0)
        normals_hair = g.compute_vertex_normals(verts_hair, faces_hair)
        bones = np.array([[neck, head], [pelvis_top, neck]], dtype=np.float32)
        names = ["head", "pelvis"]
        _, _, s_names = g._detect_secondary_springs(verts_hair, faces_hair, normals_hair, bones, names, neck, pelvis_top)
        self.assertNotIn("spring_back_tail", s_names)

        tail_field = np.minimum(base_field, ell(-0.15, 0.0, -0.14, 0.125, 0.042, 0.045))
        verts_tail, faces_tail, _ = g.extract(np.clip(50.0 * (1.2 - tail_field), 0.0, 60.0).astype(np.float32), radius=0.60, threshold=25.0)
        normals_tail = g.compute_vertex_normals(verts_tail, faces_tail)
        _, _, t_names = g._detect_secondary_springs(verts_tail, faces_tail, normals_tail, bones, names, neck, pelvis_top)
        self.assertIn("spring_back_tail", t_names)

    def test_detach_and_cap_limbs_claims_distal_fist_and_excludes_rear_tail(self):
        # Fused left hanging arm + slightly inward fist near thigh, plus rear tail protruding behind torso.
        u = np.linspace(-0.65, 0.65, 36, dtype=np.float32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        def ell(px, py, pz, rx, ry, rz):
            return ((cx - px) / rx) ** 2 + ((cy - py) / ry) ** 2 + ((cz - pz) / rz) ** 2
        f = np.minimum.reduce([
            ell(0.0, 0.0, 0.28, 0.18, 0.20, 0.18),      # head
            ell(0.0, 0.0, 0.04, 0.08, 0.08, 0.12),      # neck
            ell(0.0, 0.0, -0.14, 0.10, 0.11, 0.18),     # torso
            ell(0.0, 0.16, -0.14, 0.06, 0.06, 0.14),    # left fused sleeve/arm
            ell(0.0, 0.12, -0.27, 0.055, 0.055, 0.055), # slight inward fist next to thigh
            ell(0.0, -0.16, -0.14, 0.06, 0.06, 0.14),   # right fused sleeve/arm
            ell(-0.18, 0.08, -0.22, 0.11, 0.045, 0.05), # rear tail toward +Y behind torso
            ell(0.0, 0.06, -0.38, 0.06, 0.05, 0.12),    # left leg
            ell(0.0, -0.06, -0.38, 0.06, 0.05, 0.12),   # right leg
        ])
        verts, faces, _ = g.extract(np.clip(50.0 * (1.2 - f), 0.0, 60.0).astype(np.float32), radius=0.65, threshold=25.0)
        norms = g.compute_vertex_normals(verts, faces)
        cols = np.full_like(verts, 0.5)
        names = ["chest", "spine_lower", "left_arm", "left_forearm", "left_hand", "right_arm", "right_forearm", "right_hand", "left_thigh", "right_thigh"]
        bones = np.zeros((len(names), 2, 3), dtype=np.float32)
        bones[names.index("left_hand")] = [[0.0, 0.14, -0.23], [0.0, 0.13, -0.30]]
        bones[names.index("right_hand")] = [[0.0, -0.14, -0.23], [0.0, -0.13, -0.30]]
        bones[names.index("left_thigh")] = [[0.0, 0.06, -0.28], [0.0, 0.06, -0.44]]
        bones[names.index("right_thigh")] = [[0.0, -0.06, -0.28], [0.0, -0.06, -0.44]]
        arm_joints = [
            np.array([0.0, 0.14, -0.02], np.float32), np.array([0.0, 0.15, -0.13], np.float32), np.array([0.0, 0.14, -0.23], np.float32),
            np.array([0.0, -0.14, -0.02], np.float32), np.array([0.0, -0.15, -0.13], np.float32), np.array([0.0, -0.14, -0.23], np.float32),
        ]
        # Start with modest left-arm weight on the hanging sleeve/fist and test body vs arm partitioning + rear tail exclusion.
        weights = np.zeros((len(verts), len(names)), dtype=np.float32)
        l_arm_region = (verts[:, 1] > 0.09) & (verts[:, 2] < 0.02) & (verts[:, 2] > -0.33) & (verts[:, 0] > -0.09)
        r_arm_region = (verts[:, 1] < -0.09) & (verts[:, 2] < 0.02) & (verts[:, 2] > -0.33) & (verts[:, 0] > -0.09)
        weights[l_arm_region, names.index("left_arm")] = 0.65
        weights[l_arm_region, names.index("chest")] = 0.35
        weights[r_arm_region, names.index("right_arm")] = 0.65
        weights[r_arm_region, names.index("chest")] = 0.35
        other = ~(l_arm_region | r_arm_region)
        weights[other, names.index("spine_lower")] = 1.0
        v2, f2, n2, c2, w2, _, detached = g._detach_and_cap_limbs(verts, faces, norms, cols, weights, bones, names, arm_joints, float(np.ptp(verts[:, 2])))
        self.assertTrue(detached)
        # No rear tail vertex should belong to left arm/hand after limb detach.
        rear_tail = (v2[:len(verts), 0] < -0.15) & (v2[:len(verts), 1] > 0.04)
        self.assertTrue(rear_tail.any())
        self.assertLess(w2[:len(verts)][rear_tail, names.index("left_arm")].max(), 0.05)

    def test_bake_texture_atlas_despeckles_bright_rim_outliers_before_dilation(self):
        # Sphere baked from back view with dark interior + bright white rim stripe; back chart pre-dilation despeckle must suppress pure-white bleed.
        u = np.linspace(-0.45, 0.45, 32, dtype=np.float32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        f = (cx / 0.30) ** 2 + (cy / 0.30) ** 2 + (cz / 0.30) ** 2
        verts, faces, _ = g.extract(np.clip(50.0 * (1.2 - f), 0.0, 60.0).astype(np.float32), radius=0.45, threshold=25.0)
        normals = g.compute_vertex_normals(verts, faces)
        back_view = np.tile(np.array([0.22, 0.14, 0.36], dtype=np.float32), (128, 128, 1))
        # Inject an isolated bright white 1-px rim dot near center/silhouette in the back view.
        back_view[64, 64] = [1.0, 1.0, 1.0]
        front_view = np.tile(np.array([0.85, 0.72, 0.62], dtype=np.float32), (128, 128, 1))
        views = [
            {"rgb": front_view, "az": 0.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0},
            {"rgb": back_view, "az": 180.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 2.0},
        ]
        atlas, fuv = g.bake_texture_atlas(verts, faces, normals, views, atlas_w=512, atlas_h=512)
        back_faces = normals[faces].mean(axis=1)[:, 0] < -0.55
        self.assertTrue(back_faces.any())
        uc = fuv[back_faces].mean(axis=1)
        px = np.clip((uc[:, 0] * 512).astype(int), 0, 511)
        py = np.clip((uc[:, 1] * 512).astype(int), 0, 511)
        max_lum = float(atlas[py, px].mean(axis=1).max()) / 255.0
        self.assertLess(max_lum, 0.60)

    def test_classify_art_texture_identifies_flat_cel_vs_fur_texture(self):
        # 1. Flat 2D anime character: solid color blocks (cream vest, blue pants, lavender hair)
        side = 128
        flat_rgb = np.zeros((side, side, 3), dtype=np.float32)
        flat_alpha = np.zeros((side, side), dtype=np.float32)
        # Head (lavender)
        flat_rgb[20:55, 35:93] = [0.72, 0.65, 0.85]
        flat_alpha[20:55, 35:93] = 1.0
        # Torso jacket (white/cream)
        flat_rgb[55:90, 40:88] = [0.95, 0.94, 0.92]
        flat_alpha[55:90, 40:88] = 1.0
        # Pants (dark blue)
        flat_rgb[90:120, 42:86] = [0.22, 0.28, 0.45]
        flat_alpha[90:120, 42:86] = 1.0

        style_flat, metrics_flat = g.classify_art_texture(flat_rgb, flat_alpha)
        self.assertEqual(style_flat, "flat_2d")
        self.assertGreaterEqual(metrics_flat["flat_ratio"], 0.46)

        # 2. Volumetric / fur textured character (e.g. otter explorer): continuous gradient & micro-texture
        fur_rgb = np.zeros((side, side, 3), dtype=np.float32)
        fur_alpha = np.zeros((side, side), dtype=np.float32)
        gy, gx = np.meshgrid(np.linspace(0, 1, 90), np.linspace(0, 1, 60), indexing="ij")
        base_fur = 0.45 + 0.25 * gy + 0.15 * np.sin(gx * 12.0)
        rng = np.random.default_rng(42)
        noise = rng.normal(0.0, 0.08, (90, 60)).astype(np.float32)
        fur_pattern = np.clip(base_fur + noise, 0.1, 0.9)
        fur_rgb[20:110, 34:94, 0] = fur_pattern * 0.75
        fur_rgb[20:110, 34:94, 1] = fur_pattern * 0.55
        fur_rgb[20:110, 34:94, 2] = fur_pattern * 0.38
        fur_alpha[20:110, 34:94] = 1.0

        style_fur, metrics_fur = g.classify_art_texture(fur_rgb, fur_alpha)
        self.assertEqual(style_fur, "shaded_3d")
        self.assertLess(metrics_fur["flat_ratio"], 0.40)
        self.assertGreater(metrics_fur["interior_std"], 0.040)

    def test_inflate_2_5d_mesh_expands_collapsed_body_depth_while_preserving_front_silhouette(self):
        verts, faces, points, _ = _synthetic_humanoid_mesh()
        # Artificially collapse the body vertices below neck (z < 0.20) into a wafer (X depth ~ 0.03)
        body = verts[:, 2] < 0.20
        verts_collapsed = verts.copy()
        verts_collapsed[body, 0] = verts_collapsed[body, 0] * 0.12
        pre_body_depth = float(np.ptp(verts_collapsed[body, 0]))
        self.assertLess(pre_body_depth, 0.06)

        inflated = g.inflate_2_5d_mesh(verts_collapsed, faces)

        # 1. Front view projection invariance: Y and Z coordinates MUST be identical
        np.testing.assert_allclose(inflated[:, 1], verts_collapsed[:, 1], atol=1e-6)
        np.testing.assert_allclose(inflated[:, 2], verts_collapsed[:, 2], atol=1e-6)

        # 2. Body depth must be significantly expanded from paper-thin (<0.06) to healthy (>0.15)
        post_body_depth = float(np.ptp(inflated[body, 0]))
        self.assertGreater(post_body_depth, 0.16)

        # 3. Thickness-aware Taubin smoothing must not crush the newly inflated volume
        smoothed = g.fair_mesh_taubin(inflated, faces, iterations=4)
        smoothed_body_depth = float(np.ptp(smoothed[body, 0]))
        self.assertGreater(smoothed_body_depth, 0.14)

    def test_chibi_foot_component_with_trouser_cuff_captures_shoe_floor(self):
        import pose
        crop_h, crop_w = 48, 36
        rgb = np.zeros((crop_h, crop_w, 3), dtype=np.float32)
        alpha = np.zeros((crop_h, crop_w), dtype=bool)

        # Trouser cuff: dark blue at top (y=6..18)
        rgb[6:18, 6:30] = [35.0, 50.0, 110.0]
        alpha[6:18, 6:30] = True
        # Rolled-up cuff edge (light blue) at y=18..24
        rgb[18:24, 7:29] = [120.0, 150.0, 210.0]
        alpha[18:24, 7:29] = True
        # Brown sneaker/shoe at y=24..44
        rgb[24:44, 5:31] = [140.0, 85.0, 45.0]
        alpha[24:44, 5:31] = True

        comp = pose._foot_component(
            rgb, alpha, rgb, alpha,
            x=0.5, y=0.45, fg_h=0.7, hip_y=0.2, knee_y=0.35,
            x0=0, y0=0, side=crop_h
        )
        self.assertGreater(len(comp), 16)
        # The shoe component must reach the bottom floor of the shoe (y >= 40)
        max_y = max(p[1] for p in comp)
        self.assertGreaterEqual(max_y, 40)

    def test_backside_clean_fill_suppresses_facial_mirroring(self):
        u = np.linspace(-0.5, 0.5, 32)
        cx, cy, cz = np.meshgrid(u, u, u, indexing="ij")
        f = (cx / 0.35) ** 2 + (cy / 0.35) ** 2 + (cz / 0.50) ** 2
        verts, faces, _ = g.extract(np.clip(50.0 * (1.2 - f), 0.0, 60.0).astype(np.float32), radius=0.5, threshold=25.0)
        normals = g.compute_vertex_normals(verts, faces)

        # Reference front view: top is purple hair [0.35, 0.15, 0.55], middle is peach face [0.95, 0.80, 0.70]
        rgba_front = np.zeros((128, 128, 4), dtype=np.float32)
        # Hair at y=10..40
        rgba_front[10:40, 20:108] = [0.35, 0.15, 0.55, 1.0]
        # Face at y=40..75
        rgba_front[40:75, 30:98] = [0.95, 0.80, 0.70, 1.0]
        # Torso at y=75..115
        rgba_front[75:115, 25:103] = [0.20, 0.25, 0.30, 1.0]

        # Single front view only (no rear camera)
        ref_views = [{"rgba": rgba_front, "az": 0.0, "el": 0.0, "weight": 4.0}]
        views = [{"rgb": rgba_front[:, :, :3], "az": 0.0, "el": 0.0, "dist": 1.9, "fovy": 40.0, "weight": 1.0}]

        colors = g.project_multiview_colors(verts, views, normals=normals, ref_views=ref_views)
        height = float(np.ptp(verts[:, 2]))
        zmin = float(verts[:, 2].min())
        x_med = float(np.median(verts[:, 0]))

        # Back of head: normal points backward, x behind median, z in upper half
        back_head = (normals[:, 0] < -0.2) & (verts[:, 0] < x_med) & (verts[:, 2] > zmin + height * 0.55)
        self.assertTrue(back_head.any())

        # The back of the head should NOT mirror the bright peach face (lum > 0.8), but instead have purple hair hue (red < 0.6)
        self.assertLess(colors[back_head, 0].mean(), 0.65)
        # Blue channel should be strong (purple hair)
        self.assertGreater(colors[back_head, 2].mean(), 0.35)

    def test_parametric_chibi_template_generation_and_morphing(self):
        v, f, w, bones = g.generate_parametric_chibi_template(height=1.0)
        self.assertGreater(len(v), 300)
        self.assertGreater(len(f), 500)
        self.assertEqual(w.shape, (len(v), len(bones)))
        self.assertTrue(np.isfinite(v).all())
        self.assertTrue((f >= 0).all() and (f < len(v)).all())

        # Bone weights must sum to 1.0 for every vertex
        self.assertTrue(np.allclose(w.sum(axis=1), 1.0, atol=1e-4))

        # Check chibi volume: non-collapsed 3D depth in X and Y
        x_span = float(np.ptp(v[:, 0]))
        y_span = float(np.ptp(v[:, 1]))
        z_span = float(np.ptp(v[:, 2]))
        self.assertGreater(x_span, 0.35)
        self.assertGreater(y_span, 0.40)
        self.assertGreater(z_span, 0.85)

        # Test morphing onto dummy 3D landmarks
        joints = np.zeros((17, 3), dtype=np.float32)
        joints[1] = [0.0, 0.05, 0.75]  # Left eye
        joints[2] = [0.0, -0.05, 0.75] # Right eye
        joints[5] = [0.0, 0.18, 0.55]  # Left shoulder
        joints[7] = [0.0, 0.25, 0.45]  # Left elbow
        joints[9] = [0.0, 0.30, 0.35]  # Left wrist
        joints[6] = [0.0, -0.18, 0.55] # Right shoulder
        joints[8] = [0.0, -0.25, 0.45] # Right elbow
        joints[10] = [0.0, -0.30, 0.35]# Right wrist

        morphed = g.morph_chibi_template_to_landmarks(v, f, w, bones, joints, height=1.0)
        self.assertEqual(morphed.shape, v.shape)
        self.assertTrue(np.isfinite(morphed).all())
        # Morphed left wrist vertices should be translated toward target wrist
        b_idx = {name: i for i, name in enumerate(bones)}
        l_fore = w[:, b_idx["left_forearm"]] > 0.5
        self.assertGreater(float(morphed[l_fore, 1].mean()), float(v[l_fore, 1].mean()))


if __name__ == "__main__":
    unittest.main()
