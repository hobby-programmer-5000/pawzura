"""Clean-room stylized 3D motion library, reverse-foot IK, spring-bone physics, and BVH retargeting.

References:
- Proportion-aware IK scaling (Yang 2002; Korner et al. 2025)
- Analytical footskate cleanup (Kovar et al., SCA 2002)
- Stylized locomotion phase & secondary spring-bone dynamics (100STYLE / VRMSpringBone)
"""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np


def _smoothstep(a: float, b: float, x: float) -> float:
    if abs(b - a) < 1e-9:
        return 1.0 if x >= b else 0.0
    u = max(0.0, min(1.0, (x - a) / (b - a)))
    return u * u * (3.0 - 2.0 * u)


def _rx(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=np.float32)


def _ry(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=np.float32)


def _rz(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32)


def _euler_xyz(rx_a: float, ry_a: float, rz_a: float) -> np.ndarray:
    return (_rz(rz_a) @ _ry(ry_a) @ _rx(rx_a)).astype(np.float32)


def rodrigues_axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return 3x3 rotation matrix around unit axis by angle radians."""
    norm = float(np.linalg.norm(axis))
    if norm < 1e-8 or abs(angle) < 1e-8:
        return np.eye(3, dtype=np.float32)
    k = axis / norm
    kx, ky, kz = float(k[0]), float(k[1]), float(k[2])
    skew = np.array([[0.0, -kz, ky], [kz, 0.0, -kx], [-ky, kx, 0.0]], dtype=np.float32)
    return (np.eye(3, dtype=np.float32) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)).astype(np.float32)


def rotation_between(v_from: np.ndarray, v_to: np.ndarray, twist: float = 0.0) -> np.ndarray:
    """Minimal-arc SO(3) rotation aligning v_from to v_to, plus optional axial twist."""
    n1 = float(np.linalg.norm(v_from))
    n2 = float(np.linalg.norm(v_to))
    if n1 < 1e-8 or n2 < 1e-8:
        return np.eye(3, dtype=np.float32)
    a = v_from / n1
    b = v_to / n2
    dot = float(np.clip(np.dot(a, b), -1.0, 1.0))
    if dot > 0.999999:
        rot = np.eye(3, dtype=np.float32)
    elif dot < -0.999999:
        ortho = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        if abs(float(np.dot(a, ortho))) > 0.9:
            ortho = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        axis = np.cross(a, ortho)
        rot = rodrigues_axis_angle(axis, math.pi)
    else:
        axis = np.cross(a, b)
        rot = rodrigues_axis_angle(axis, math.acos(dot))
    if abs(twist) > 1e-6:
        rot = (rodrigues_axis_angle(b, twist) @ rot).astype(np.float32)
    return rot


def solve_two_bone_ik(
    root: np.ndarray,
    target: np.ndarray,
    len1: float,
    len2: float,
    pole_dir: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """3D analytical 2-bone IK with pole-vector plane alignment and safe reach clamping."""
    delta = target - root
    dist = float(np.linalg.norm(delta))
    max_reach = max(1e-4, (len1 + len2) * 0.996)
    min_reach = max(1e-4, abs(len1 - len2) + 1e-4)
    if dist < 1e-6:
        forward = delta + np.array([1e-4, 0.0, -1.0], dtype=np.float32)
        direction = forward / float(np.linalg.norm(forward))
        dist = min_reach
    else:
        direction = delta / dist
    clamped_dist = min(max_reach, max(min_reach, dist))
    clamped_target = (root + direction * clamped_dist).astype(np.float32)

    bend_dir = pole_dir - float(np.dot(pole_dir, direction)) * direction
    bend_norm = float(np.linalg.norm(bend_dir))
    if bend_norm < 1e-6:
        fallback = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        bend_dir = fallback - float(np.dot(fallback, direction)) * direction
        bend_norm = float(np.linalg.norm(bend_dir))
    bend_dir = (bend_dir / max(1e-6, bend_norm)).astype(np.float32)

    along = (len1 * len1 - len2 * len2 + clamped_dist * clamped_dist) / (2.0 * clamped_dist)
    perp = math.sqrt(max(0.0, len1 * len1 - along * along))
    mid = (root + direction * along + bend_dir * perp).astype(np.float32)
    return mid, clamped_target


def reverse_foot_targets(
    rest_ankle: np.ndarray,
    rest_ball: np.ndarray,
    rest_toe: np.ndarray,
    stride: float,
    lift_height: float,
    phase_u: float,
    gait: float,
    tucked: float,
    crouch_shift: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute ankle, ball, and toe positions with heel-strike, flat lock, and toe-off roll."""
    ball_vec = rest_ball - rest_ankle
    toe_vec = rest_toe - rest_ball
    floor_ball_z = float(rest_ball[2])
    floor_toe_z = float(rest_toe[2])

    if gait <= 1e-4:
        # Non-walking clips: keep feet grounded or tucked smoothly during jumps/bites.
        lift_z = tucked * lift_height * 1.15
        pitch = math.radians(14.0 * tucked)
        ankle = rest_ankle + crouch_shift + np.array([-tucked * stride * 0.2, 0.0, lift_z], dtype=np.float32)
        ball = ankle + _ry(pitch) @ ball_vec
        toe = ball + _ry(pitch * 1.1) @ toe_vec
        return ankle.astype(np.float32), ball.astype(np.float32), toe.astype(np.float32)

    u = phase_u % 1.0
    if u < 0.5:
        # Stance phase: ball/foot travels backward at constant ground speed from +stride to -stride.
        s = u * 2.0  # 0..1 across stance
        dx = stride * (1.0 - 2.0 * s)
        # Heel-strike (0..0.14): ball slightly raised, pivots down to flat.
        strike = 1.0 - _smoothstep(0.0, 0.16, s)
        # Push-off (0.68..1.0): heel/ankle lifts while toe/ball stay locked on floor!
        push = _smoothstep(0.68, 1.0, s)
        foot_pitch = math.radians(-12.0 * strike + 24.0 * push)
        ball = np.array([rest_ball[0] + dx, rest_ball[1], floor_ball_z + strike * lift_height * 0.22], dtype=np.float32)
        ankle = ball - (_ry(foot_pitch) @ ball_vec)
        toe_bend = math.radians(-22.0 * push)
        toe = ball + (_ry(foot_pitch + toe_bend) @ toe_vec)
        if push > 0.01:
            toe[2] = max(floor_toe_z, float(toe[2]))
    else:
        # Swing phase: smooth arc forward with toe clearance.
        f = (u - 0.5) * 2.0  # 0..1 across swing
        dx = -stride * math.cos(math.pi * f)
        swing_z = lift_height * (math.sin(math.pi * f) ** 0.85)
        pitch = math.radians(18.0 * (1.0 - _smoothstep(0.0, 0.35, f)) - 12.0 * _smoothstep(0.55, 1.0, f))
        ankle = np.array([rest_ankle[0] + dx, rest_ankle[1], rest_ankle[2] + swing_z], dtype=np.float32)
        ball = ankle + (_ry(pitch) @ ball_vec)
        toe = ball + (_ry(pitch * 0.8) @ toe_vec)

    return ankle.astype(np.float32), ball.astype(np.float32), toe.astype(np.float32)


def extract_proportions(bones: np.ndarray, bone_names: list[str]) -> dict[str, float]:
    """Measure character bone lengths so animations adapt cleanly to chibi or tall proportions."""
    idx = {name: i for i, name in enumerate(bone_names)}
    def length(name: str, default: float) -> float:
        i = idx.get(name)
        if i is None:
            return default
        return max(1e-4, float(np.linalg.norm(bones[i, 1] - bones[i, 0])))

    height = max(0.1, float(np.ptp(bones[:, :, 2])))
    leg_len = (length("left_thigh", height * 0.16) + length("left_shin", height * 0.16) +
               length("right_thigh", height * 0.16) + length("right_shin", height * 0.16)) * 0.5
    arm_len = (length("left_arm", height * 0.14) + length("left_forearm", height * 0.14) +
               length("right_arm", height * 0.14) + length("right_forearm", height * 0.14)) * 0.5
    torso_len = length("spine_lower", height * 0.14) + length("chest", height * 0.14)
    head_len = length("head", height * 0.25)
    foot_len = length("left_foot", height * 0.06) + length("left_toe", height * 0.04)
    return {
        "height": height,
        "leg_len": leg_len,
        "arm_len": arm_len,
        "torso_len": torso_len,
        "head_len": head_len,
        "foot_len": foot_len,
        "chibi_ratio": head_len / max(1e-4, height),
    }


def _pose_single_frame(
    bones: np.ndarray,
    parents: np.ndarray,
    bone_names: list[str],
    props: dict[str, float],
    params: dict[str, float],
) -> tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray]:
    """Compute articulated rigid bone transforms (R, t) and target segments for one frame."""
    idx = {name: i for i, name in enumerate(bone_names)}
    targets = bones.copy()
    height = props["height"]
    leg_len = props["leg_len"]

    gait = params.get("gait", 0.0)
    phase = params.get("phase", 0.0)
    crouch = params.get("crouch", 0.0)
    tucked = params.get("tucked", 0.0)
    bite = params.get("bite", 0.0)
    wave = params.get("wave", 0.0)
    cheer = params.get("cheer", 0.0)
    breath = params.get("breath", 0.0)
    head_tilt = params.get("head_tilt", 0.0)
    head_yaw = params.get("head_yaw", 0.0)
    turn_lean = params.get("turn_lean", 0.0)
    hop_z = params.get("hop_z", 0.0)

    # Proportion-aware stride capped strictly below leg reach so knees never lock or snap.
    raw_stride = 42.0 * 0.8 / (4.0 * 144.0 * 0.9) * height
    stride = min(raw_stride, leg_len * 0.34)
    lift_height = min(height * 0.052, leg_len * 0.22)

    # Pelvis dynamics: double-frequency vertical bounce, lateral sway toward stance leg, yaw & roll.
    walk_rad = phase * 2.0 * math.pi
    bob_z = (-math.cos(walk_rad * 2.0) * 0.014 * height) * gait
    sway_y = (-math.sin(walk_rad) * 0.018 * height) * gait + params.get("idle_sway_y", 0.0) * height
    pelvis_yaw = (math.sin(walk_rad) * math.radians(6.5)) * gait + params.get("pelvis_yaw", 0.0)
    pelvis_roll = (math.cos(walk_rad) * math.radians(3.5)) * gait

    pelvis_i = idx["pelvis"]
    pelvis_origin = bones[pelvis_i, 0].copy()

    # Maintain torso lean within safe bounds around +2 degrees forward.
    spine_vec = bones[idx["chest"], 1] - bones[idx["spine_lower"], 0]
    rest_lean = math.atan2(float(spine_vec[0]), float(spine_vec[2]))
    upright = float(np.clip(math.radians(2.0) - rest_lean, -math.radians(22.0), math.radians(22.0)))

    # Compute leg-reach vertical drop so short chibi legs never hyperextend on stride/crouch.
    drop = 0.0
    for side in ("left", "right"):
        h_pt = bones[idx[f"{side}_thigh"], 0]
        a_pt = bones[idx[f"{side}_shin"], 1]
        l_tot = float(np.linalg.norm(bones[idx[f"{side}_thigh"], 1] - h_pt) +
                      np.linalg.norm(bones[idx[f"{side}_shin"], 1] - bones[idx[f"{side}_shin"], 0]))
        reach = math.sqrt(max(1e-4, l_tot * l_tot - (abs(float(a_pt[0] - h_pt[0])) + stride) ** 2)) * 0.975
        drop = min(drop, float(a_pt[2]) + reach - float(h_pt[2]))
    pelvis_shift = np.array([
        crouch * height * -0.02 + params.get("pelvis_x", 0.0) * height,
        sway_y,
        drop * gait + bob_z - height * 0.055 * crouch + hop_z * height,
    ], dtype=np.float32)

    # Hierarchical rotation accumulation for spine/chest/neck/head/clavicles.
    pelvis_rot = _euler_xyz(pelvis_roll, upright * 0.25 + crouch * math.radians(10.0), pelvis_yaw)
    spine_rot = _euler_xyz(-pelvis_roll * 0.5, upright * 0.45 + turn_lean - cheer * math.radians(8.0) + bite * math.radians(10.0), -pelvis_yaw * 0.6)
    chest_rot = _euler_xyz(-pelvis_roll * 0.4 + math.radians(3.5) * wave, upright * 0.30 - cheer * math.radians(6.0) + breath * math.radians(2.0), -pelvis_yaw * 0.8)
    neck_rot = _euler_xyz(head_tilt * 0.35, -bite * math.radians(5.0) + breath * math.radians(1.0), head_yaw * 0.4)
    head_rot = _euler_xyz(head_tilt * 0.65, -bite * math.radians(8.0) - cheer * math.radians(6.0), head_yaw * 0.6)

    chain_rot: dict[int, np.ndarray] = {}
    chain_rot[pelvis_i] = pelvis_rot
    targets[pelvis_i, 0] = pelvis_origin + pelvis_shift
    targets[pelvis_i, 1] = targets[pelvis_i, 0] + pelvis_rot @ (bones[pelvis_i, 1] - pelvis_origin)

    # Propagate Spine Lower -> Chest -> Neck -> Head with true hierarchical world rotations.
    for b_name, local_r in (("spine_lower", spine_rot), ("chest", chest_rot), ("neck", neck_rot), ("head", head_rot)):
        bi = idx[b_name]
        pi = int(parents[bi])
        if b_name == "spine_lower":
            world_r = local_r.astype(np.float32)
            targets[bi, 0] = targets[pelvis_i, 0]
        else:
            world_r = (chain_rot[pi] @ local_r).astype(np.float32)
            targets[bi, 0] = targets[pi, 1] + world_r @ (bones[bi, 0] - bones[pi, 1])
        chain_rot[bi] = world_r
        targets[bi, 1] = targets[bi, 0] + world_r @ (bones[bi, 1] - bones[bi, 0])

    # Jaw hinges from TMJ pivot attached to head.
    jaw_i = idx["jaw"]
    head_i = idx["head"]
    head_r = chain_rot[head_i]
    jaw_local = _ry(bite * math.radians(24.0))
    jaw_world = (head_r @ jaw_local).astype(np.float32)
    chain_rot[jaw_i] = jaw_world
    targets[jaw_i, 0] = targets[head_i, 0] + head_r @ (bones[jaw_i, 0] - bones[head_i, 0])
    targets[jaw_i, 1] = targets[jaw_i, 0] + jaw_world @ (bones[jaw_i, 1] - bones[jaw_i, 0])

    # Clavicles -> Arms -> Forearms -> Hands, and Thighs -> Shins -> Feet -> Toes.
    chest_top = targets[idx["chest"], 1]
    chest_base_ref = bones[idx["chest"], 1]
    chest_r = chain_rot[idx["chest"]]

    for side_sign, offset, label in ((1.0, 0.0, "left"), (-1.0, 0.5, "right")):
        u = (phase + offset) % 1.0
        arm_phase = u * 2.0 * math.pi

        # Clavicle elevation & protraction.
        clav_i = idx[f"{label}_clavicle"]
        shrug = (0.14 * wave if label == "right" else 0.03 * wave) + 0.16 * cheer + 0.04 * breath
        clav_yaw = math.sin(arm_phase) * math.radians(4.0) * gait
        clav_roll = side_sign * math.radians(7.0 * shrug)
        clav_r = (chest_r @ _euler_xyz(clav_roll, 0.0, clav_yaw)).astype(np.float32)
        chain_rot[clav_i] = clav_r
        targets[clav_i, 0] = chest_top + chest_r @ (bones[clav_i, 0] - chest_base_ref)
        targets[clav_i, 1] = targets[clav_i, 0] + clav_r @ (bones[clav_i, 1] - bones[clav_i, 0])

        # Upper arm + phase-lagged forearm + wrist follow-through.
        arm_i = idx[f"{label}_arm"]
        fore_i = idx[f"{label}_forearm"]
        hand_i = idx[f"{label}_hand"]

        arm_rest_u = bones[arm_i, 1] - bones[arm_i, 0]
        arm_rest_u = arm_rest_u / max(1e-6, float(np.linalg.norm(arm_rest_u)))
        fore_rest_u = bones[fore_i, 1] - bones[fore_i, 0]
        fore_rest_u = fore_rest_u / max(1e-6, float(np.linalg.norm(fore_rest_u)))

        def _blend_dir(u0: np.ndarray, u1: np.ndarray, alpha: float) -> np.ndarray:
            u0n = u0 / max(1e-6, float(np.linalg.norm(u0)))
            u1n = u1 / max(1e-6, float(np.linalg.norm(u1)))
            mid = u0n * (1.0 - alpha) + u1n * alpha
            if float(np.linalg.norm(mid)) < 1e-3:
                mid = np.array([0.1, side_sign, 0.1], dtype=np.float32)
            return (mid / max(1e-6, float(np.linalg.norm(mid)))).astype(np.float32)

        arm_mob = float(np.clip(params.get("arm_mobility", 1.0), 0.20, 1.0))
        if (label == "right" and wave > 0.01) or cheer > 0.01:
            is_wave = label == "right" and wave > 0.01
            act = wave if is_wave else cheer
            eff = act * (0.42 + 0.58 * arm_mob)
            rest_elev = math.atan2(max(0.0, side_sign * float(arm_rest_u[1])), max(1e-4, -float(arm_rest_u[2])))
            target_elev = math.radians(28.0 + 58.0 * arm_mob)
            delta_elev = max(0.0, target_elev - rest_elev) * eff
            fwd_tilt = -math.radians((18.0 - 4.0 * arm_mob) * eff)
            arm_r = (chest_r @ _euler_xyz(side_sign * delta_elev, fwd_tilt, 0.0)).astype(np.float32)
            chain_rot[arm_i] = arm_r
            targets[arm_i, 0] = targets[clav_i, 1]
            targets[arm_i, 1] = targets[arm_i, 0] + arm_r @ (bones[arm_i, 1] - bones[arm_i, 0])

            osc_val = math.sin(phase * 4.0 * math.pi)
            flex = math.radians((54.0 + 22.0 * arm_mob) * eff)
            if is_wave:
                flex += side_sign * math.radians(-16.0 * osc_val * act)
            else:
                flex += math.radians(10.0 * osc_val * act)
            fore_fwd = -math.radians(14.0 * eff)
            fore_r = (arm_r @ _euler_xyz(side_sign * flex, fore_fwd, 0.0)).astype(np.float32)
            chain_rot[fore_i] = fore_r
            targets[fore_i, 0] = targets[arm_i, 1]
            targets[fore_i, 1] = targets[fore_i, 0] + fore_r @ (bones[fore_i, 1] - bones[fore_i, 0])

            wrist_wave = math.radians(14.0 * osc_val * act) if is_wave else 0.0
            hand_r = (fore_r @ _euler_xyz(wrist_wave, 0.0, 0.0)).astype(np.float32)
        else:
            swing = math.radians(28.0 * math.sin(arm_phase) * gait - 26.0 * tucked - 18.0 * bite + 26.0 * crouch)
            abduct = side_sign * math.radians(5.0 * gait + 8.0 * tucked)
            arm_r = (chest_r @ _euler_xyz(abduct, swing, 0.0)).astype(np.float32)
            chain_rot[arm_i] = arm_r
            targets[arm_i, 0] = targets[clav_i, 1]
            targets[arm_i, 1] = targets[arm_i, 0] + arm_r @ (bones[arm_i, 1] - bones[arm_i, 0])

            # Forearm lags behind upper arm during walk and bends naturally.
            lag_swing = math.radians(18.0 * math.sin(arm_phase - 0.62) * gait - 16.0 * gait - 34.0 * tucked - 12.0 * bite)
            fore_r = (arm_r @ _euler_xyz(0.0, lag_swing, 0.0)).astype(np.float32)
            chain_rot[fore_i] = fore_r
            targets[fore_i, 0] = targets[arm_i, 1]
            targets[fore_i, 1] = targets[fore_i, 0] + fore_r @ (bones[fore_i, 1] - bones[fore_i, 0])

            hand_lag = math.radians(8.0 * math.sin(arm_phase - 1.1) * gait)
            hand_r = (fore_r @ _euler_xyz(hand_lag * 0.6, hand_lag * 0.4, 0.0)).astype(np.float32)
        chain_rot[hand_i] = hand_r
        targets[hand_i, 0] = targets[fore_i, 1]
        targets[hand_i, 1] = targets[hand_i, 0] + hand_r @ (bones[hand_i, 1] - bones[hand_i, 0])

        # Lower body: 3D analytical IK + Reverse Foot Roll.
        thigh_i = idx[f"{label}_thigh"]
        shin_i = idx[f"{label}_shin"]
        foot_i = idx[f"{label}_foot"]
        toe_i = idx[f"{label}_toe"]

        hip_pt = targets[pelvis_i, 0] + pelvis_rot @ (bones[thigh_i, 0] - pelvis_origin)
        l1 = float(np.linalg.norm(bones[thigh_i, 1] - bones[thigh_i, 0]))
        l2 = float(np.linalg.norm(bones[shin_i, 1] - bones[shin_i, 0]))

        foot_crouch_shift = np.array([0.0, 0.0, max(0.0, hop_z) * height], dtype=np.float32)
        ankle_t, ball_t, toe_t = reverse_foot_targets(
            bones[shin_i, 1], bones[foot_i, 1], bones[toe_i, 1],
            stride, lift_height, u, gait, tucked, foot_crouch_shift,
        )
        pole = np.array([1.0, side_sign * 0.14, 0.05], dtype=np.float32)
        knee_pt, ankle_t = solve_two_bone_ik(hip_pt, ankle_t, l1, l2, pole)

        targets[thigh_i] = (hip_pt, knee_pt)
        targets[shin_i] = (knee_pt, ankle_t)
        targets[foot_i] = (ankle_t, ball_t)
        targets[toe_i] = (ball_t, toe_t)

    # Convert every segment pair (rest -> target) to an SO(3) rigid transform (R, t).
    transforms: list[tuple[np.ndarray, np.ndarray]] = []
    for i in range(len(bone_names)):
        a, b = bones[i, 0], bones[i, 1]
        pa, pb = targets[i, 0], targets[i, 1]
        if i in chain_rot:
            r = chain_rot[i]
        else:
            r = rotation_between(b - a, pb - pa)
        transforms.append((r.astype(np.float32), (pa - r @ a).astype(np.float32)))
    return transforms, targets


def _clip_params(clip: str, i: int, count: int) -> dict[str, float]:
    """Parameterized stylized motion curves across all 12 Pawzura clips."""
    t = i / 30.0
    u = i / max(1, count - 1)
    loop_u = i / max(1, count)
    gait = 1.0 if clip.startswith("walk_") else 0.0
    yaw = -math.pi / 2.0 if clip.endswith("left") else math.pi / 2.0 if clip.endswith("right") else 0.0
    if clip.startswith("turn_"):
        yaw *= _smoothstep(0.0, 1.0, u)
    elif clip.startswith("return_"):
        yaw *= 1.0 - _smoothstep(0.0, 1.0, u)

    blink = math.exp(-((t - (count / 30.0) * 0.70) / 0.065) ** 2) if clip.startswith(("walk_", "idle_")) else 0.0
    smile = 0.28 + 0.12 * math.sin(loop_u * 2.0 * math.pi)
    gaze_y = 0.0
    brow = 0.0
    crouch = 0.0
    tucked = 0.0
    hop_z = 0.0
    wave = 0.0
    cheer = 0.0
    bite = 0.0
    breath = 0.0
    head_tilt = 0.0
    head_yaw = 0.0
    turn_lean = 0.0
    idle_sway_y = 0.0
    pelvis_yaw = 0.0

    if clip == "idle_front":
        breath = 0.5 + 0.5 * math.sin(loop_u * 4.0 * math.pi)
        idle_sway_y = 0.008 * math.sin(loop_u * 2.0 * math.pi)
        head_tilt = math.radians(3.5) * math.sin(loop_u * 2.0 * math.pi + 0.6)
        head_yaw = math.radians(4.5) * math.sin(loop_u * 2.0 * math.pi)
        gaze_y = 0.18 * math.sin(loop_u * 2.0 * math.pi)
    elif clip.startswith("walk_"):
        breath = 0.3 * math.sin(t / 0.8 * 2.0 * math.pi)
        head_yaw = math.radians(-3.0) * math.sin(t / 0.8 * 2.0 * math.pi)
        smile = 0.35 + 0.1 * math.sin(t * 2.0)
    elif clip.startswith(("turn_", "return_")):
        # Anticipation + lead-and-follow: head leads chest/hips during a pivot turn.
        dir_sign = -1.0 if clip.endswith("left") else 1.0
        lead = math.sin(math.pi * u)
        crouch = 0.22 * lead
        turn_lean = math.radians(4.0) * lead
        head_yaw = dir_sign * math.radians(14.0) * lead * (1.0 if clip.startswith("turn_") else -1.0)
        pelvis_yaw = -head_yaw * 0.35
    elif clip == "wave":
        wave = math.sin(math.pi * u) ** 1.3
        head_tilt = math.radians(7.0) * wave
        smile = 0.55 + 0.25 * wave
        brow = 0.35 * wave
    elif clip == "hop":
        # Anticipation (0..0.22) -> Launch/Apex (0.22..0.68) -> Landing squash (0.68..0.88) -> Settle.
        if u < 0.22:
            crouch = 0.68 * math.sin(math.pi * (u / 0.22) * 0.5)
        elif u < 0.68:
            f = (u - 0.22) / 0.46
            hop_z = 0.085 * math.sin(math.pi * f)
            tucked = 0.72 * math.sin(math.pi * f)
            crouch = 0.15 * (1.0 - math.sin(math.pi * f))
        elif u < 0.88:
            f = (u - 0.68) / 0.20
            crouch = 0.52 * math.sin(math.pi * f)
        brow = 0.3 * math.sin(math.pi * u)
        smile = 0.45 + 0.3 * math.sin(math.pi * u)
    elif clip == "cheer":
        cheer = math.sin(math.pi * u) ** 1.15
        if u < 0.18:
            crouch = 0.5 * (u / 0.18)
        elif u < 0.72:
            f = (u - 0.18) / 0.54
            hop_z = 0.065 * math.sin(math.pi * f)
            tucked = 0.55 * math.sin(math.pi * f)
        else:
            f = (u - 0.72) / 0.28
            crouch = 0.32 * math.sin(math.pi * f)
        smile = 0.65 + 0.25 * cheer
        brow = 0.55 * cheer
    elif clip.startswith("bite_"):
        # Anticipate crouch -> pounce with open TMJ jaw -> bite snap -> recoil -> landing recover.
        if u < 0.20:
            crouch = 0.58 * math.sin(math.pi * (u / 0.20) * 0.5)
        elif u < 0.72:
            f = (u - 0.20) / 0.52
            tucked = 0.65 * math.sin(math.pi * min(1.0, f * 1.1))
            hop_z = 0.03 * math.sin(math.pi * f)
        else:
            f = (u - 0.72) / 0.28
            crouch = 0.42 * math.sin(math.pi * f)
        bite = _smoothstep(0.32, 0.58, t) * (1.0 - _smoothstep(0.68, 0.88, t))
        blink = 0.35 * _smoothstep(0.64, 0.76, t) * (1.0 - _smoothstep(0.84, 0.96, t))
        brow = -0.35 * bite

    return {
        "phase": t / 0.8,
        "gait": gait,
        "yaw": yaw,
        "blink": blink,
        "opening": bite,
        "smile": smile,
        "gaze_y": gaze_y,
        "brow": brow,
        "crouch": crouch,
        "tucked": tucked,
        "hop_z": hop_z,
        "wave": wave,
        "cheer": cheer,
        "bite": bite,
        "breath": breath,
        "head_tilt": head_tilt,
        "head_yaw": head_yaw,
        "turn_lean": turn_lean,
        "idle_sway_y": idle_sway_y,
        "pelvis_yaw": pelvis_yaw,
    }


def simulate_spring_chains(
    primary_frames: list[tuple[list[tuple[np.ndarray, np.ndarray]], np.ndarray]],
    bones: np.ndarray,
    parents: np.ndarray,
    spring_indices: list[int],
    fps: int = 30,
    loop: bool = True,
    stiffness: float = 68.0,
    drag: float = 11.5,
    gravity: float = 0.45,
) -> list[list[tuple[np.ndarray, np.ndarray]]]:
    """Semi-implicit damped spring-bone simulation (VRMSpringBone-inspired) for hair/ears/tails."""
    all_transforms = [list(tr) for tr, _ in primary_frames]
    if not spring_indices or not primary_frames:
        return all_transforms

    dt = 1.0 / max(1, fps)
    n_frames = len(primary_frames)
    passes = 2 if loop else 1

    # Maintain angular state (pitch/roll angle offset around parent anchor) per spring bone.
    angles = {bi: np.zeros(2, dtype=np.float32) for bi in spring_indices}
    vel = {bi: np.zeros(2, dtype=np.float32) for bi in spring_indices}
    prev_anchor: dict[int, np.ndarray] = {}

    for pass_idx in range(passes):
        for f_idx in range(n_frames):
            tr_list = all_transforms[f_idx]
            for bi in spring_indices:
                pi = int(parents[bi])
                p_rot, p_trans = tr_list[pi] if pi >= 0 else (np.eye(3, dtype=np.float32), np.zeros(3, dtype=np.float32))
                rest_a, rest_b = bones[bi, 0], bones[bi, 1]
                anchor = p_rot @ rest_a + p_trans
                if bi not in prev_anchor:
                    prev_anchor[bi] = anchor.copy()
                anchor_vel = (anchor - prev_anchor[bi]) / dt
                prev_anchor[bi] = anchor.copy()

                # Project parent linear velocity into spring-chain lateral/sagittal axes for lag impulse.
                local_v = p_rot.T @ anchor_vel
                height = max(0.2, float(np.ptp(bones[:, :, 2])))
                impulse_x = float(np.clip(-local_v[0] / (height * 1.4), -1.4, 1.4))
                impulse_y = float(np.clip(local_v[1] / (height * 1.4), -1.4, 1.4))
                grav_bias_x = -gravity * 0.05 * float(local_v[2] / max(0.1, height))

                cur = angles[bi]
                v_cur = vel[bi]
                acc = np.array([
                    -stiffness * cur[0] - drag * v_cur[0] + impulse_x * 7.5 + grav_bias_x,
                    -stiffness * cur[1] - drag * v_cur[1] + impulse_y * 7.5,
                ], dtype=np.float32)
                v_next = np.clip(v_cur + acc * dt, -3.5, 3.5)
                a_next = np.clip(cur + v_next * dt, -math.radians(9.0), math.radians(9.0))
                vel[bi] = v_next
                angles[bi] = a_next

                if pass_idx == passes - 1:
                    spring_rot = (p_rot @ _euler_xyz(float(a_next[1]), float(a_next[0]), 0.0)).astype(np.float32)
                    tr_list[bi] = (spring_rot, (anchor - spring_rot @ rest_a).astype(np.float32))
    return all_transforms


def generate_clip_poses(
    clip: str,
    count: int,
    bones: np.ndarray,
    parents: np.ndarray,
    bone_names: list[str],
    fps: int = 30,
    arm_mobility: float = 1.0,
) -> tuple[list[list[tuple[np.ndarray, np.ndarray]]], list[dict[str, float]]]:
    """Generate complete articulated + spring-bone pose sequence and face track for one clip."""
    props = extract_proportions(bones, bone_names)
    primary = []
    face_tracks = []
    for i in range(count):
        params = _clip_params(clip, i, count)
        params["arm_mobility"] = float(arm_mobility)
        tr, tg = _pose_single_frame(bones, parents, bone_names, props, params)
        primary.append((tr, tg))
        face_tracks.append(params)

    spring_indices = [i for i, name in enumerate(bone_names) if name.startswith("spring_")]
    loop = clip in ("idle_front", "walk_left", "walk_right", "wave", "cheer")
    final_transforms = simulate_spring_chains(primary, bones, parents, spring_indices, fps=fps, loop=loop)
    return final_transforms, face_tracks


# --- Clean-room BVH Parser & Proportion-Aware Retargeting ---

_BVH_ALIASES = {
    "hips": "pelvis", "root": "pelvis", "pelvis": "pelvis",
    "spine": "spine_lower", "spine1": "chest", "spine2": "chest", "chest": "chest", "upperchest": "chest",
    "neck": "neck", "head": "head",
    "leftshoulder": "left_clavicle", "clavicle_l": "left_clavicle", "shoulder_l": "left_clavicle",
    "leftarm": "left_arm", "leftupperarm": "left_arm", "upperarm_l": "left_arm",
    "leftforearm": "left_forearm", "leftlowerarm": "left_forearm", "lowerarm_l": "left_forearm",
    "lefthand": "left_hand", "hand_l": "left_hand",
    "rightshoulder": "right_clavicle", "clavicle_r": "right_clavicle", "shoulder_r": "right_clavicle",
    "rightarm": "right_arm", "rightupperarm": "right_arm", "upperarm_r": "right_arm",
    "rightforearm": "right_forearm", "rightlowerarm": "right_forearm", "lowerarm_r": "right_forearm",
    "righthand": "right_hand", "hand_r": "right_hand",
    "leftupleg": "left_thigh", "leftthigh": "left_thigh", "thigh_l": "left_thigh",
    "leftleg": "left_shin", "leftshin": "left_shin", "calf_l": "left_shin",
    "leftfoot": "left_foot", "foot_l": "left_foot",
    "lefttoebase": "left_toe", "lefttoe": "left_toe",
    "rightupleg": "right_thigh", "rightthigh": "right_thigh", "thigh_r": "right_thigh",
    "rightleg": "right_shin", "rightshin": "right_shin", "calf_r": "right_shin",
    "rightfoot": "right_foot", "foot_r": "right_foot",
    "righttoebase": "right_toe", "righttoe": "right_toe",
}


def _canon_bvh_name(raw: str) -> str:
    cleaned = raw.split(":")[-1].replace(" ", "").replace(".", "").replace("_", "").lower()
    return _BVH_ALIASES.get(cleaned, cleaned)


def parse_bvh(source: str | Path) -> dict:
    """Parse a standard ASCII BVH motion file (e.g., 100STYLE / Mixamo / Bandai Namco BVH)."""
    text = Path(source).read_text(encoding="utf-8", errors="replace") if isinstance(source, Path) or "\n" not in source else source
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joints: list[dict] = []
    stack: list[int] = []
    i = 0
    frame_time = 1.0 / 30.0
    motion_frames: list[list[float]] = []
    in_motion = False

    while i < len(lines):
        line = lines[i]
        if not in_motion:
            tokens = line.split()
            head = tokens[0]
            if head in ("ROOT", "JOINT"):
                name = tokens[1]
                parent = stack[-1] if stack else -1
                joints.append({"name": name, "canon": _canon_bvh_name(name), "parent": parent,
                               "offset": np.zeros(3, dtype=np.float32), "channels": []})
                stack.append(len(joints) - 1)
            elif head == "End":
                # Skip End Site block cleanly without creating a rigged joint.
                i += 1
                depth = 0
                while i < len(lines):
                    if "{" in lines[i]:
                        depth += 1
                    if "}" in lines[i]:
                        depth -= 1
                        if depth <= 0:
                            break
                    i += 1
            elif head == "OFFSET" and stack:
                joints[stack[-1]]["offset"] = np.array([float(tokens[1]), float(tokens[2]), float(tokens[3])], dtype=np.float32)
            elif head == "CHANNELS" and stack:
                n_ch = int(tokens[1])
                joints[stack[-1]]["channels"] = tokens[2:2 + n_ch]
            elif head == "}":
                if stack:
                    stack.pop()
            elif head == "MOTION":
                in_motion = True
        else:
            if line.startswith("Frame Time:"):
                frame_time = max(1e-4, float(line.split(":")[1].strip()))
            elif not line.startswith("Frames:"):
                motion_frames.append([float(v) for v in line.split()])
        i += 1

    return {"joints": joints, "frame_time": frame_time, "frames": np.asarray(motion_frames, dtype=np.float32)}


def retarget_bvh(
    bvh: dict,
    bones: np.ndarray,
    bone_names: list[str],
    lock_feet: bool = True,
) -> list[list[tuple[np.ndarray, np.ndarray]]]:
    """Retarget parsed BVH motion onto Pawzura's skeleton with proportion scaling and footskate cleanup."""
    joints = bvh["joints"]
    frames = bvh["frames"]
    if len(frames) == 0 or not joints:
        raise ValueError("Empty BVH motion")

    # Forward kinematics in BVH Y-up space, then convert to Pawzura (+X front, +Y left, +Z up).
    bvh_to_paw = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]], dtype=np.float32)
    channel_offsets = []
    cursor = 0
    for j in joints:
        channel_offsets.append((cursor, j["channels"]))
        cursor += len(j["channels"])

    # Compute rest leg length in BVH space for Yang (2002) anthropometric scaling.
    bvh_rest = np.zeros((len(joints), 3), dtype=np.float32)
    for ji, j in enumerate(joints):
        p = j["parent"]
        bvh_rest[ji] = (bvh_rest[p] if p >= 0 else 0.0) + j["offset"]
    bvh_by_canon = {j["canon"]: ji for ji in range(len(joints))}
    bvh_leg = 1.0
    if "left_thigh" in bvh_by_canon and "left_foot" in bvh_by_canon:
        bvh_leg = max(1e-4, float(abs(bvh_rest[bvh_by_canon["left_thigh"], 1] - bvh_rest[bvh_by_canon["left_foot"], 1])))
    props = extract_proportions(bones, bone_names)
    leg_scale = props["leg_len"] / bvh_leg

    idx = {name: i for i, name in enumerate(bone_names)}
    floor_z = float(min(bones[idx["left_toe"], 1, 2], bones[idx["right_toe"], 1, 2]))

    # Evaluate world joint positions for every BVH frame.
    world_seqs = []
    for row in frames:
        world_rot = [np.eye(3, dtype=np.float32) for _ in joints]
        world_pos = [np.zeros(3, dtype=np.float32) for _ in joints]
        for ji, j in enumerate(joints):
            start, chs = channel_offsets[ji]
            local_t = j["offset"].copy()
            local_r = np.eye(3, dtype=np.float32)
            for ci, ch in enumerate(chs):
                val = float(row[start + ci])
                if ch == "Xposition":
                    local_t[0] = val
                elif ch == "Yposition":
                    local_t[1] = val
                elif ch == "Zposition":
                    local_t[2] = val
                elif ch == "Xrotation":
                    local_r = (local_r @ _rx(math.radians(val))).astype(np.float32)
                elif ch == "Yrotation":
                    local_r = (local_r @ _ry(math.radians(val))).astype(np.float32)
                elif ch == "Zrotation":
                    local_r = (local_r @ _rz(math.radians(val))).astype(np.float32)
            p = j["parent"]
            if p >= 0:
                world_pos[ji] = world_pos[p] + world_rot[p] @ local_t
                world_rot[ji] = (world_rot[p] @ local_r).astype(np.float32)
            else:
                world_pos[ji] = local_t
                world_rot[ji] = local_r
        # Map BVH coords to Pawzura coords and scale relative to frame-0 root.
        paw_pos = (np.stack(world_pos) @ bvh_to_paw.T) * leg_scale
        world_seqs.append((paw_pos, [bvh_to_paw @ r @ bvh_to_paw.T for r in world_rot]))

    origin_offset = world_seqs[0][0][0] - bones[idx["pelvis"], 0]
    retargeted: list[list[tuple[np.ndarray, np.ndarray]]] = []
    prev_foot = {"left": None, "right": None}

    for paw_pos, paw_rots in world_seqs:
        paw_pos = paw_pos - origin_offset
        targets = bones.copy()
        transforms: list[tuple[np.ndarray, np.ndarray]] = []
        # Map core torso/head/arms from BVH orientations while preserving target bone lengths.
        for b_i, b_name in enumerate(bone_names):
            ji = bvh_by_canon.get(b_name)
            if ji is not None:
                r = paw_rots[ji]
                anchor = targets[b_i, 0]
                if ji == 0:
                    anchor = paw_pos[0]
                targets[b_i, 0] = anchor
                targets[b_i, 1] = anchor + r @ (bones[b_i, 1] - bones[b_i, 0])
            else:
                r = np.eye(3, dtype=np.float32)
            transforms.append((r.astype(np.float32), (targets[b_i, 0] - r @ bones[b_i, 0]).astype(np.float32)))

        # Proportion-aware leg IK + Kovar-style foot-plant locking when foot is near floor & slow.
        if lock_feet:
            for side_sign, label in ((1.0, "left"), (-1.0, "right")):
                ji_foot = bvh_by_canon.get(f"{label}_foot")
                if ji_foot is None:
                    continue
                thigh_i = idx[f"{label}_thigh"]
                shin_i = idx[f"{label}_shin"]
                foot_i = idx[f"{label}_foot"]
                hip_pt = paw_pos[bvh_by_canon.get(f"{label}_thigh", 0)] if f"{label}_thigh" in bvh_by_canon else bones[thigh_i, 0]
                ankle_target = paw_pos[ji_foot].copy()
                if ankle_target[2] < floor_z + props["height"] * 0.045:
                    if prev_foot[label] is not None and float(np.linalg.norm(ankle_target[:2] - prev_foot[label][:2])) < props["height"] * 0.015:
                        ankle_target[:2] = prev_foot[label][:2]
                    ankle_target[2] = max(float(bones[shin_i, 1, 2]), ankle_target[2])
                prev_foot[label] = ankle_target.copy()
                l1 = float(np.linalg.norm(bones[thigh_i, 1] - bones[thigh_i, 0]))
                l2 = float(np.linalg.norm(bones[shin_i, 1] - bones[shin_i, 0]))
                knee_pt, ankle_target = solve_two_bone_ik(hip_pt, ankle_target, l1, l2, np.array([1.0, side_sign * 0.14, 0.05], dtype=np.float32))
                for bi, pa, pb in ((thigh_i, hip_pt, knee_pt), (shin_i, knee_pt, ankle_target)):
                    r = rotation_between(bones[bi, 1] - bones[bi, 0], pb - pa)
                    transforms[bi] = (r, (pa - r @ bones[bi, 0]).astype(np.float32))
                # Connect foot anchor smoothly.
                r_f = transforms[foot_i][0]
                transforms[foot_i] = (r_f, (ankle_target - r_f @ bones[foot_i, 0]).astype(np.float32))
        retargeted.append(transforms)
    return retargeted
