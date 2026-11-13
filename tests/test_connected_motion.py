import hashlib
import json
import os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from pathlib import Path
import shutil
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication
from pawzura import art_client, artwork, motion_client, motion_pack, model_jobs
from pawzura.characters import GenerationError
from pawzura.art_ui import ArtworkDialog, MotionWorker
from test_motion_pack import png, fixture


class ConnectedMotionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patches = [
            patch('pawzura.artwork.asset_root', return_value=self.root / 'art'),
            patch('pawzura.motion_pack.asset_root', return_value=self.root / 'motion'),
        ]
        for p in self.patches:
            p.start()
        self.source = artwork.store_artwork(png('#bd9922'))
        self.spec = {'kind': 'artwork', 'art_id': self.source, 'mouth_x': .5, 'mouth_y': .4, 'art_model': 'sdxl'}
        self.runtime = self.root / 'runtime'
        p = art_client.runtime_python(self.runtime)
        p.parent.mkdir(parents=True)
        p.touch()
        (self.runtime / 'uv.exe').touch()
        self.cache = self.root / 'jobs'
        self.calls = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
        motion_pack._PACKS.clear()
        motion_pack._FRAMES.clear()
        artwork._IMAGES.clear()
        self.temp.cleanup()

    def fake_worker(self, stage, job, root, payload, progress, cancel):
        self.calls.append(stage)
        if stage == 'prepare':
            return {'stage': stage}
        names = motion_client.STAGE_FILES.get(stage, {'surface.npz'})
        for name in names:
            (job / name).write_bytes(fixture(self.source) if name == 'motion.zip' else b'accepted synthetic stage')
        return {
            'stage': stage,
            'files': [{'name': n, 'sha256': hashlib.sha256((job / n).read_bytes()).hexdigest(), 'bytes': (job / n).stat().st_size} for n in names],
        }

    def prepare(self, spec=None, cancel=None, worker=None, quality_mode='standard', extra_views=None):
        with patch('pawzura.motion_client._worker', side_effect=worker or self.fake_worker), patch('pawzura.art_client._run', return_value=b'{}'):
            return motion_client.prepare_animation(
                spec or self.spec,
                root=self.runtime,
                cache=self.cache,
                cancel=cancel,
                quality_mode=quality_mode,
                extra_views=extra_views,
            )

    def _copy_source(self):
        source = self.root / 'source'
        source.mkdir(exist_ok=True)
        for name in ('three_d.py', 'motion_geometry.py', 'motion_bake.py', 'motion_library.py', 'motion_catalog.json', 'triposr-sources.json', 'requirements.txt', 'runner.py', 'motion_cache_legacy.json', 'catalog.json'):
            src = art_client.source_dir() / name
            if src.is_file():
                shutil.copy2(src, source / name)
        return source

    def test_cache_checks_actual_bytes_and_mouth_invalidates_downstream_only(self):
        result = self.prepare()
        self.assertIn('animation_id', result)
        self.assertEqual(self.calls, ['prepare', 'reconstruct', 'rig', 'bake'])
        self.calls.clear()
        self.assertEqual(self.prepare()['animation_id'], result['animation_id'])
        self.assertEqual(self.calls, [])
        self.prepare({**self.spec, 'mouth_x': .6})
        self.assertEqual(self.calls, ['rig', 'bake'])
        self.calls.clear()
        job = next(self.cache.iterdir())
        (job / 'surface.npz').write_bytes(b'corrupt')
        self.prepare({**self.spec, 'mouth_x': .6})
        self.assertEqual(self.calls[0], 'reconstruct')
        state = json.loads((job / 'state.json').read_text())
        self.assertEqual(state['status'], 'ready')

    def test_motion_only_code_change_reuses_reconstruction_and_rig(self):
        source = self._copy_source()
        with patch('pawzura.art_client.source_dir', return_value=source):
            self.prepare()
            self.calls.clear()
            before = motion_client.stage_signatures()
            file = source / 'motion_geometry.py'
            text = file.read_text()
            self.assertIn('math.radians(2)-rest_lean', text)
            file.write_text(text.replace('math.radians(2)-rest_lean', 'math.radians(3)-rest_lean'))
            after = motion_client.stage_signatures()
            self.assertEqual(before['reconstruct'], after['reconstruct'])
            self.assertEqual(before['rig'], after['rig'])
            self.assertNotEqual(before['bake'], after['bake'])
            self.prepare()
            self.assertEqual(self.calls, ['bake'])
            self.calls.clear()
            catalog = json.loads((source / 'catalog.json').read_text())
            catalog['pose']['revision'] = '0' * 40
            (source / 'catalog.json').write_text(json.dumps(catalog))
            changed = motion_client.stage_signatures()
            self.assertEqual(changed['reconstruct'], after['reconstruct'])
            self.assertNotEqual(changed['rig'], after['rig'])
            self.prepare()
            self.assertEqual(self.calls, ['prepare', 'rig', 'bake'])

    def test_obsolete_legacy_pins_are_not_adopted_but_matching_pinned_cache_is_adopted(self):
        # 1. Obsolete 8-view / 96^3 / 12-bone legacy pins must NOT bypass the upgraded pipeline.
        legacy = json.loads((art_client.source_dir() / 'motion_cache_legacy.json').read_text())
        old_rev = next(iter(legacy['backends']))
        old_job = self.cache / (self.source + '-' + old_rev[:16])
        old_job.mkdir(parents=True)
        files = self.fake_worker('reconstruct', old_job, self.runtime, {}, lambda e: None, threading.Event())['files']
        record = {'input': hashlib.sha256(json.dumps([self.source, old_rev, []]).encode()).hexdigest(), 'files': files}
        (old_job / 'state.json').write_text(json.dumps({'revision': old_rev, 'stages': {'reconstruct': record}}))
        self.calls.clear()
        self.prepare()
        self.assertIn('reconstruct', self.calls)

        # 2. A verified pin matching current stage signatures IS adopted without calling GPU worker.
        shutil.rmtree(self.cache)
        source = self._copy_source()
        with patch('pawzura.art_client.source_dir', return_value=source):
            sigs = motion_client.stage_signatures()
            pin_rev = '1' * 64
            (source / 'motion_cache_legacy.json').write_text(json.dumps({
                'version': 1,
                'backends': {pin_rev: {'reconstruct': sigs['reconstruct'], 'rig': sigs['rig'], 'bake': sigs['bake']}},
            }))
            pin_job = self.cache / (self.source + '-' + pin_rev[:16])
            pin_job.mkdir(parents=True)
            p_files = self.fake_worker('reconstruct', pin_job, self.runtime, {}, lambda e: None, threading.Event())['files']
            p_rec = {'input': hashlib.sha256(json.dumps([self.source, pin_rev, []]).encode()).hexdigest(), 'files': p_files}
            (pin_job / 'state.json').write_text(json.dumps({'revision': pin_rev, 'stages': {'reconstruct': p_rec}}))
            self.calls.clear()
            self.prepare()
            self.assertNotIn('reconstruct', self.calls)
            self.assertIn('rig', self.calls)

    def test_text_newlines_and_empty_ast_fields_do_not_invalidate_verified_stages(self):
        import ast
        source = self._copy_source()
        with patch('pawzura.art_client.source_dir', return_value=source):
            before = motion_client.stage_signatures()
            self.prepare()
            self.calls.clear()
            for path in source.glob('*'):
                if path.suffix in ('.py', '.json', '.txt'):
                    text = path.read_text(encoding='utf-8')
                    path.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
            self.assertEqual(motion_client.stage_signatures(), before)
            self.prepare()
            self.assertEqual(self.calls, [])
            parse = ast.parse

            def without_empty_fields(*args, **kwargs):
                tree = parse(*args, **kwargs)
                for node in ast.walk(tree):
                    node._fields = tuple(key for key in node._fields if getattr(node, key, None) is not None and getattr(node, key) != [])
                    if isinstance(node, (ast.Import, ast.ImportFrom)):
                        if 'is_lazy' not in node._fields:
                            node._fields = (*node._fields, 'is_lazy')
                        node.is_lazy = 0
                return tree

            with patch('pawzura.motion_client.ast.parse', side_effect=without_empty_fields):
                self.assertEqual(motion_client.stage_signatures(), before)

    def test_staged_legacy_adoption_requires_identical_preceding_scene(self):
        source = self._copy_source()
        with patch('pawzura.art_client.source_dir', return_value=source):
            sigs = motion_client.stage_signatures()
            revision = '2' * 64
            pin = {'format': 'staged', 'inputs': {'reconstruct': '3' * 64, 'rig': '4' * 64, 'bake': '5' * 64},
                   'reconstruct': sigs['reconstruct'], 'rig': sigs['rig'], 'bake': sigs['bake']}
            (source / 'motion_cache_legacy.json').write_text(json.dumps({'version': 1, 'backends': {revision: pin}}))
            job = self.cache / (self.source + '-staged-' + revision[:16])
            job.mkdir(parents=True)
            state = {'revision': revision, 'status': 'ready', 'stages': {}}
            previous = self.source
            for stage in motion_client.STAGE_FILES:
                files = self.fake_worker(stage, job, self.runtime, {}, lambda e: None, threading.Event())['files']
                params = [self.spec['mouth_x'], self.spec['mouth_y']] if stage == 'rig' else []
                record = {'input': hashlib.sha256(json.dumps([previous, pin['inputs'][stage], params]).encode()).hexdigest(), 'files': files}
                state['stages'][stage] = record
                previous = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
            (job / 'state.json').write_text(json.dumps(state))
            self.calls.clear()
            self.prepare()
            self.assertEqual(self.calls, ['prepare'])
            current = self.cache / (self.source + '-staged-' + sigs['reconstruct'][:16])
            (current / 'surface.npz').write_bytes(b'different scene')
            self.assertIsNone(motion_client._legacy_stage(current, self.cache, 'rig', 'a' * 64, sigs, self.spec, threading.Event()))

    def test_quality_modes_and_extra_angle_views_stage_cleanly(self):
        extra_left = artwork.store_artwork(png('#33aaee'))
        res = self.prepare(quality_mode='sdxl_multiview', extra_views={'facing_left': extra_left, 'invalid_key': 'x' * 64})
        self.assertIn('animation_id', res)
        self.assertEqual(self.calls, ['prepare', 'reconstruct', 'refine_views', 'rig', 'bake'])
        job = next(self.cache.iterdir())
        self.assertTrue((job / 'extra_facing_left.png').is_file())
        self.assertFalse((job / 'extra_back.png').exists())

        # Changing back to standard mode clears stale extra file and invalidates reconstruct.
        self.calls.clear()
        self.prepare(quality_mode='standard', extra_views=None)
        self.assertEqual(self.calls, ['reconstruct', 'rig', 'bake'])
        self.assertFalse((job / 'extra_facing_left.png').exists())

        # Missing/invalid extra view asset fails cleanly before worker runs.
        with self.assertRaisesRegex(GenerationError, 'motion_source_missing'):
            self.prepare(extra_views={'back': 'f' * 64})

    def test_dialog_quality_selector_and_extra_view_attachments(self):
        for language in ('en', 'ko'):
            d = ArtworkDialog(language, initial_spec=self.spec)
            self.assertEqual(d.motion_quality.count(), 3)
            self.assertEqual(d.motion_quality.currentData(), 'standard')
            self.assertFalse(d.extra_clear.isEnabled())
            bad_file = self.root / 'bad.png'
            bad_file.write_bytes(b'<svg>not a png</svg>')
            with patch('pawzura.art_ui.QFileDialog.getOpenFileName', return_value=(str(bad_file), 'PNG (*.png)')):
                d.attach_extra_view('back')
            self.assertEqual(d.extra_views, {})
            self.assertEqual(d.status.text(), d.t['motion_extra_invalid'])

            good_file = self.root / 'left.png'
            good_file.write_bytes(png('#44ccaa'))
            with patch('pawzura.art_ui.QFileDialog.getOpenFileName', return_value=(str(good_file), 'PNG (*.png)')):
                d.attach_extra_view('facing_left')
            self.assertIn('facing_left', d.extra_views)
            self.assertTrue(d.extra_clear.isEnabled())
            d.clear_extra_views()
            self.assertEqual(d.extra_views, {})
            d.preview.timer.stop()
            d.deleteLater()

    def test_cancellation_retains_verified_stage_and_never_returns_candidate(self):
        cancel = threading.Event()
        def worker(*args):
            result = self.fake_worker(*args)
            if args[0] == 'rig':
                cancel.set()
            return result
        with self.assertRaisesRegex(GenerationError, 'art_cancelled'):
            self.prepare(cancel=cancel, worker=worker)
        job = next(self.cache.iterdir())
        state = json.loads((job / 'state.json').read_text())
        self.assertEqual(state['status'], 'cancelled')
        self.assertEqual(set(state['stages']), {'reconstruct'})
        self.assertFalse((job / 'motion.zip').exists())
        self.calls.clear()
        self.prepare()
        self.assertEqual(self.calls, ['rig', 'bake'])

    def test_bad_stage_records_and_second_job_are_rejected(self):
        job = self.root / 'outputs'
        job.mkdir()
        for records in ([], [{'name': '../outside', 'bytes': 3, 'sha256': 'a' * 64}], None):
            self.assertFalse(motion_client._valid_outputs(job, 'bake', records))
        errors = []
        def competing():
            try:
                with model_jobs.model_job():
                    pass
            except GenerationError as e:
                errors.append(str(e))
        with model_jobs.model_job():
            t = threading.Thread(target=competing)
            t.start()
            t.join(2)
        self.assertEqual(errors, ['art_model_busy'])

    def test_dialog_rejects_late_cancelled_wrong_source_and_can_restore_original(self):
        result = self.prepare()
        for language in ('en', 'ko'):
            d = ArtworkDialog(language, initial_spec=self.spec)
            w = MotionWorker(self.spec, d)
            d.worker = w
            w.cancel_event.set()
            d.motion_succeeded(result)
            self.assertNotIn('animation_id', d.result_spec)
            w.cancel_event.clear()
            d.motion_succeeded({**result, 'art_id': 'a' * 64})
            self.assertNotIn('animation_id', d.result_spec)
            d.motion_succeeded(result)
            self.assertEqual(d.preview.spec['animation_id'], result['animation_id'])
            d.worker = None
            d.controls()
            self.assertFalse(d.motion_button.isEnabled())
            self.assertTrue(d.motion_view.isEnabled())
            chosen = []
            d.chosen.connect(chosen.append)
            self.assertEqual(chosen, [])
            d.restore_original()
            self.assertNotIn('animation_id', d.result_spec)
            self.assertEqual(d.result_spec['art_id'], self.source)
            d.preview.timer.stop()
            d.deleteLater()

    @unittest.skipUnless(os.name == 'nt', 'Windows process containment')
    def test_cancellation_reaps_owned_descendant_before_releasing_model_slot(self):
        pidfile = self.root / 'child.pid'
        cancel = threading.Event()
        script = "import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(30)']);Path(sys.argv[1]).write_text(str(p.pid));print('PAWZURA_PROGRESS {\\\"stage\\\":\\\"motion_rigging\\\"}',file=sys.stderr,flush=True);time.sleep(30)"
        script = script.replace('\\\"', '"')
        start = time.monotonic()
        with self.assertRaisesRegex(GenerationError, 'art_cancelled'):
            art_client._run([sys.executable, '-c', script, str(pidfile)], progress=lambda e: cancel.set(), cancel=cancel, contain=True, timeout=5)
        self.assertLess(time.monotonic() - start, 4)
        import ctypes
        api = ctypes.WinDLL('kernel32', use_last_error=True)
        api.OpenProcess.restype = ctypes.c_void_p
        handle = api.OpenProcess(0x100000, False, int(pidfile.read_text()))
        if handle:
            api.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
            api.CloseHandle.argtypes = [ctypes.c_void_p]
            try:
                self.assertEqual(api.WaitForSingleObject(handle, 0), 0)
            finally:
                api.CloseHandle(handle)
        self.assertEqual(json.loads(art_client._run([sys.executable, '-c', 'print("{}")'], contain=True, timeout=5)), {})

    def test_character_preview_and_draw_character_render_v2_motion_pack(self):
        from PySide6.QtGui import QImage, QPainter
        from pawzura import pet

        def v2_worker(stage, job, runtime, payload, progress, cancel):
            if stage == 'bake':
                data = fixture(payload['source_art_id'], change=lambda m: m.update({'backend': 'triposr-pose-v2'}))
                (job / 'motion.zip').write_bytes(data)
                return {'stage': 'bake', 'seconds': 0.1, 'files': [{'name': 'motion.zip', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}
            return self.fake_worker(stage, job, runtime, payload, progress, cancel)

        res = self.prepare(worker=v2_worker)
        spec = {**self.spec, **res}
        for clip_pose, facing, biting in (('walk', 1, False), ('wave', 1, False), ('cheer', -1, False), ('walk', -1, True)):
            canvas = QImage(144, 144, QImage.Format.Format_ARGB32_Premultiplied)
            canvas.fill(0)
            painter = QPainter(canvas)
            try:
                pet.draw_character(painter, spec, phase=1.2, facing=facing, biting=biting, pose=clip_pose)
            finally:
                painter.end()
            # Verify opaque foreground pixels rendered from the loaded v2 motion pack.
            self.assertGreater(canvas.pixelColor(72, 72).alpha(), 200)

        prev = pet.CharacterPreview(spec)
        prev.pose = 'cheer'
        prev.resize(200, 220)
        grabbed = prev.grab()
        self.assertFalse(grabbed.isNull())
        prev.timer.stop()
        prev.deleteLater()

    def test_pet_companion_pointer_drag_click_hover_and_bite_with_v2_pack(self):
        from PySide6.QtCore import QEvent, QPointF, Qt
        from PySide6.QtGui import QMouseEvent
        from pawzura import pet

        def v2_worker(stage, job, runtime, payload, progress, cancel):
            if stage == 'bake':
                data = fixture(payload['source_art_id'], change=lambda m: m.update({'backend': 'triposr-pose-v2'}))
                (job / 'motion.zip').write_bytes(data)
                return {'stage': 'bake', 'seconds': 0.1, 'files': [{'name': 'motion.zip', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}
            return self.fake_worker(stage, job, runtime, payload, progress, cancel)

        res = self.prepare(worker=v2_worker)
        spec = {**self.spec, **res}
        companion = pet.Pet(spec)
        companion.timer.stop()
        companion.show()
        try:
            def send_ptr(kind, gpos):
                left = Qt.MouseButton.LeftButton
                ev = QMouseEvent(
                    kind,
                    gpos - QPointF(companion.pos()),
                    gpos,
                    Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else left,
                    Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else left,
                    Qt.KeyboardModifier.NoModifier,
                )
                QApplication.sendEvent(companion, ev)

            for expected_reaction in ('wave', 'hop', 'cheer'):
                companion.reaction = None
                p0 = QPointF(companion.pos()) + QPointF(72, 72)
                send_ptr(QEvent.Type.MouseButtonPress, p0)
                send_ptr(QEvent.Type.MouseMove, p0 + QPointF(1, 1))
                send_ptr(QEvent.Type.MouseButtonRelease, p0 + QPointF(1, 1))
                self.assertEqual(companion.reaction['kind'], expected_reaction)
                self.assertFalse(companion.pinned)
                shot = companion.grab()
                self.assertGreater(shot.toImage().pixelColor(72, 72).alpha(), 180)

            start_pos = QPointF(companion.px, companion.py)
            companion.reaction = None
            p0 = QPointF(companion.pos()) + QPointF(72, 72)
            send_ptr(QEvent.Type.MouseButtonPress, p0)
            send_ptr(QEvent.Type.MouseMove, p0 + QPointF(36, -24))
            send_ptr(QEvent.Type.MouseButtonRelease, p0 + QPointF(36, -24))
            self.assertTrue(companion.pinned)
            self.assertEqual(QPointF(companion.px, companion.py), start_pos + QPointF(36, -24))
            companion.set_placement(False)

            for facing_dir in (-1, 1):
                companion.direction = facing_dir
                companion.hovered = False
                companion.reaction = None
                self.assertFalse(companion.grab().isNull())

            companion.hovered = True
            self.assertFalse(companion.grab().isNull())

            hits = []
            with patch('pawzura.pet.time.monotonic', return_value=100.0):
                companion.bite(QPointF(companion.px + 120, companion.py + 50), lambda: hits.append(True))
            with patch('pawzura.pet.time.monotonic', return_value=100.8):
                companion.tick()
            with patch('pawzura.pet.time.monotonic', return_value=102.0):
                companion.tick()
                companion.tick()
            self.assertEqual(hits, [True])
        finally:
            companion.dispose()

    def test_mixed_dpi_screen_crossing_keeps_logical_size_and_v2_motion(self):
        from types import SimpleNamespace
        from PySide6.QtCore import QPointF, QRect, QSize
        from PySide6.QtGui import QResizeEvent
        from pawzura import pet, windows

        def make_screen(name, geom_rect, dpr):
            return SimpleNamespace(
                name=lambda: name,
                geometry=lambda: geom_rect,
                availableGeometry=lambda: geom_rect,
                devicePixelRatio=lambda: dpr,
            )

        left_hi = make_screen('\\\\.\\DISPLAY2', QRect(-1536, 0, 1536, 960), 1.25)
        right_std = make_screen('\\\\.\\DISPLAY1', QRect(0, 0, 1920, 1040), 1.0)

        def fake_get_mon(hmon, ptr):
            import ctypes
            class RECT(ctypes.Structure):
                _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long), ('right', ctypes.c_long), ('bottom', ctypes.c_long)]
            class MON(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_ulong), ('rcMonitor', RECT), ('rcWork', RECT), ('dwFlags', ctypes.c_ulong), ('szDevice', ctypes.c_wchar * 32)]
            info = ctypes.cast(ptr, ctypes.POINTER(MON)).contents
            info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom = (-1920, 0, 0, 1200) if hmon == 2 else (0, 0, 1920, 1040)
            info.szDevice = '\\\\.\\DISPLAY2' if hmon == 2 else '\\\\.\\DISPLAY1'
            return 1

        with patch.object(windows.user, 'MonitorFromPoint', side_effect=lambda pt, _: 2 if pt.x < 0 else 1), \
             patch.object(windows.user, 'GetMonitorInfoW', side_effect=fake_get_mon):
            self.assertEqual(windows.physical_to_logical(-960, 600, [left_hi, right_std]), (-768.0, 480.0))
            self.assertEqual(windows.physical_to_logical(400, 200, [left_hi, right_std]), (400.0, 200.0))

        def v2_worker(stage, job, runtime, payload, progress, cancel):
            if stage == 'bake':
                data = fixture(payload['source_art_id'], change=lambda m: m.update({'backend': 'triposr-pose-v2'}))
                (job / 'motion.zip').write_bytes(data)
                return {'stage': 'bake', 'seconds': 0.1, 'files': [{'name': 'motion.zip', 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}]}
            return self.fake_worker(stage, job, runtime, payload, progress, cancel)

        res = self.prepare(worker=v2_worker)
        spec = {**self.spec, **res}
        companion = pet.Pet(spec)
        companion.timer.stop()
        companion.show()
        try:
            fake_handle = unittest.mock.MagicMock()
            fake_handle.screen.return_value = right_std
            with patch.object(companion, 'screens', return_value=[left_hi, right_std]), \
                 patch.object(companion, 'windowHandle', return_value=fake_handle):
                companion.place_at(QPointF(-300.0, 815.0))
            fake_handle.setScreen.assert_called_once_with(left_hi)
            self.assertLess(companion.px, 0.0)
            self.assertEqual((companion.width(), companion.height()), (144, 146))
            # Simulate native WM_DPICHANGED suggesting 1.25x scaled size; logical size must immediately snap back to 144x146.
            companion.resize(180, 182)
            companion.resizeEvent(QResizeEvent(QSize(180, 182), QSize(144, 146)))
            self.assertEqual((companion.width(), companion.height()), (144, 146))
            self.assertTrue(companion.has_motion())
            self.assertFalse(companion.grab().isNull())
        finally:
            companion.dispose()


if __name__ == '__main__':
    unittest.main()
