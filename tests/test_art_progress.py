import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import sys
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PySide6.QtWidgets import QApplication

from art_runtime.runner import sampling_progress
from pawzura import art_client
from pawzura.art_ui import ArtworkDialog
from pawzura.characters import GenerationError


class ArtProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_protocol_rejects_unknown_unbounded_or_private_backend_text(self):
        for line in (b"backend private description", b"PAWZURA_PROGRESS " + b"x" * 4097,
                     b'PAWZURA_PROGRESS {"stage":"untrusted"}',
                     b'PAWZURA_PROGRESS {"stage":"art_sampling","completed":true,"total":30}',
                     b'PAWZURA_PROGRESS {"stage":"art_sampling","completed":31,"total":30}',
                     b'PAWZURA_PROGRESS {"stage":[]}'):
            self.assertIsNone(art_client.progress_event(line))
        value = art_client.progress_event(b'PAWZURA_PROGRESS {"stage":"art_sampling","completed":3,"total":30,"prompt":"discard this"}')
        self.assertEqual(value, {"stage": "art_sampling", "completed": 3, "total": 30})

    def test_subprocess_delivers_progress_before_final_output_without_logs(self):
        script = ("import sys,json,time; "
                  "print('backend text',file=sys.stderr,flush=True); "
                  "print('PAWZURA_PROGRESS '+json.dumps({'stage':'art_sampling','completed':1,'total':30}),file=sys.stderr,flush=True); "
                  "time.sleep(.3); print(json.dumps({'ready':True}))")
        events, observed = [], []
        def receive(event):
            observed.append(time.monotonic())
            events.append(event)
        output = art_client._run([sys.executable, "-c", script], progress=receive, timeout=5)
        self.assertGreaterEqual(time.monotonic() - observed[0], .2)
        self.assertEqual(events, [{"stage": "art_sampling", "completed": 1, "total": 30}])
        self.assertEqual(json.loads(output), {"ready": True})

    def test_subprocess_timeout_reaps_own_process(self):
        with self.assertRaisesRegex(GenerationError, "art_timed_out"):
            art_client._run([sys.executable, "-c", "import time;time.sleep(20)"], timeout=.1)

    def test_timeout_also_covers_a_child_not_reading_its_input(self):
        with self.assertRaisesRegex(GenerationError, "art_timed_out"):
            art_client._run([sys.executable, "-c", "import time;time.sleep(20)"],
                            payload={"data": "x" * 200000}, timeout=.1)

    def test_request_payload_reaches_the_child_through_stdin(self):
        script = "import json,sys;d=json.load(sys.stdin);print(json.dumps({'size':len(d['data'])}))"
        result = art_client._run([sys.executable, "-c", script], payload={"data": "x" * 20000}, timeout=5)
        self.assertEqual(json.loads(result), {"size": 20000})

    def test_subprocess_error_retains_safe_code_only(self):
        script = "import sys;print('{\"error\":\"art_output_blocked\"}');sys.exit(1)"
        with self.assertRaisesRegex(GenerationError, "art_output_blocked"):
            art_client._run([sys.executable, "-c", script], timeout=5)

    def test_subprocess_output_is_bounded(self):
        script = "import sys;sys.stdout.write('x'*(13*1024*1024))"
        with self.assertRaisesRegex(GenerationError, "art_runtime_failed"):
            art_client._run([sys.executable, "-c", script], timeout=5)

    def test_sampling_callback_reports_actual_scheduler_length_and_decoding(self):
        callback_data = {"latents": object()}
        pipeline = SimpleNamespace(scheduler=SimpleNamespace(timesteps=[1] * 31))
        with patch("art_runtime.runner.report") as report:
            result = sampling_progress(pipeline, 30, None, callback_data)
        self.assertIs(result, callback_data)
        self.assertEqual(report.call_args_list[0].args, ("art_sampling", 31, 31))
        self.assertEqual(report.call_args_list[1].args, ("art_decoding",))

    def test_elapsed_last_report_notice_and_terminal_state_in_both_languages(self):
        for lang in ("en", "ko"):
            dialog = ArtworkDialog(lang)
            with patch("pawzura.art_ui.time.monotonic", return_value=100):
                dialog.started_at = dialog.stage_started_at = dialog.last_report_at = 100
                dialog.progress_timer.start()
                dialog.set_progress({"stage": "art_sampling", "completed": 12, "total": 30})
            self.assertEqual((dialog.progress_bar.value(), dialog.progress_bar.maximum()), (12, 30))
            with patch("pawzura.art_ui.time.monotonic", return_value=165):
                dialog.update_timing()
            self.assertIn("1:05", dialog.timing_label.text())
            self.assertTrue(dialog.wait_label.text())
            with patch("pawzura.art_ui.time.monotonic", return_value=166):
                dialog.set_progress("art_checking")
            self.assertEqual(dialog.progress_bar.maximum(), 0)
            self.assertEqual(dialog.wait_label.text(), "")
            stage = dialog.stage_label.text()
            dialog.worker = object()
            dialog.reject()
            self.assertEqual(dialog.stage_label.text(), stage)
            dialog.worker = None
            dialog.failed("art_output_blocked")
            self.assertFalse(dialog.progress_timer.isActive())
            self.assertEqual(dialog.progress_bar.format(), dialog.t["progress_stopped"])
            dialog.preview.timer.stop()
            dialog.deleteLater()

    def test_progress_event_accepts_bounded_progress_metadata(self):
        line = b'PAWZURA_PROGRESS {"stage":"art_review_models","completed":1,"total":2,"model_name":"Qwen2.5 1.5B","bytes_completed":750000000,"bytes_total":1117320736,"status_text":"downloading"}'
        event = art_client.progress_event(line)
        self.assertIsNotNone(event)
        self.assertEqual(event["stage"], "art_review_models")
        self.assertEqual(event["completed"], 1)
        self.assertEqual(event["total"], 2)
        self.assertEqual(event["model_name"], "Qwen2.5 1.5B")
        self.assertEqual(event["bytes_completed"], 750000000)
        self.assertEqual(event["bytes_total"], 1117320736)
        self.assertEqual(event["status_text"], "downloading")

    def test_dialog_progress_displays_model_names_and_bytes_in_both_languages(self):
        for lang, expected_unit in (("ko", "MB"), ("en", "MB")):
            dialog = ArtworkDialog(lang)
            dialog.started_at = dialog.stage_started_at = dialog.last_report_at = 100
            dialog.progress_timer.start()

            dialog.set_progress({
                "stage": "art_review_models",
                "completed": 0,
                "total": 2,
                "model_name": "Qwen2.5 1.5B",
                "bytes_completed": 750000000,
                "bytes_total": 1117320736,
                "status_text": "downloading",
            })
            self.assertIn("Qwen2.5 1.5B", dialog.stage_label.text())
            self.assertIn(expected_unit, dialog.stage_label.text())
            self.assertGreater(dialog.progress_bar.value(), 25)
            self.assertLess(dialog.progress_bar.value(), 40)
            self.assertEqual(dialog.progress_bar.maximum(), 100)

            dialog.set_progress({
                "stage": "art_downloading",
                "completed": 0,
                "total": 4,
                "item_name": "SD 1.5 (sd15)",
            })
            self.assertIn("SD 1.5 (sd15)", dialog.stage_label.text())
            self.assertEqual(dialog.progress_bar.value(), 0)
            self.assertEqual(dialog.progress_bar.maximum(), 4)

            dialog.preview.timer.stop()
            dialog.deleteLater()

    def test_pull_ollama_model_streams_events_and_falls_back(self):
        import io
        fake_stream = io.BytesIO(b'{"status":"pulling manifest"}\n'
                                 b'{"status":"downloading","total":100000000,"completed":50000000}\n'
                                 b'{"status":"success"}\n')
        events = []
        with patch("pawzura.art_client.build_opener") as opener:
            opener.return_value.open.return_value = fake_stream
            art_client._pull_ollama_model("qwen3-vl:2b", 1, 2, events.append)

        self.assertGreaterEqual(len(events), 2)
        model_names = [e.get("model_name") for e in events]
        self.assertTrue(all(name == "Qwen3-VL 2B" for name in model_names))
        self.assertEqual(events[-1]["completed"], 2)
        self.assertEqual(events[-1]["status_text"], "success")


if __name__ == "__main__":
    unittest.main()
