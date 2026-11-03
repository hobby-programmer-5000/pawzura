import io
import json
import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from PySide6.QtWidgets import QApplication

from pawzura import art_policy
from pawzura.art_ui import ArtworkDialog
from pawzura.characters import DETAIL_MODEL, GenerationError


def response(value):
    return io.BytesIO(json.dumps(value).encode())


class ArtReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_incomplete_response_is_not_repaired_or_allowed(self):
        for output in ({"response": '{"verdict":"allow"', "done_reason": "length"},
                       {"response": '{"verdict":"allow"}', "done": False}):
            with patch("pawzura.art_policy.build_opener") as opener:
                opener.return_value.open.return_value = response(output)
                with self.assertRaisesRegex(GenerationError, "art_review_prompt_incomplete"):
                    art_policy.review_art_prompt("An original brass astronomer")
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_installed_model_transport_and_backend_errors_are_distinct(self):
        cases = [(HTTPError("http://127.0.0.1", 404, "missing", {}, io.BytesIO()), "missing"),
                 (HTTPError("http://127.0.0.1", 500, "failed", {}, io.BytesIO(b"private input: out of memory")), "memory"),
                 (HTTPError("http://127.0.0.1", 400, "unsupported", {}, io.BytesIO(b"private backend data")), "service"),
                 (URLError(ConnectionRefusedError()), "unreachable"),
                 (URLError(TimeoutError()), "timeout"), (TimeoutError(), "timeout")]
        for error, reason in cases:
            with self.subTest(reason=reason), patch("pawzura.art_policy.build_opener") as opener:
                opener.return_value.open.side_effect = error
                with self.assertRaisesRegex(GenerationError, "art_review_prompt_" + reason) as caught:
                    art_policy.review_art_prompt("An original brass astronomer")
                self.assertNotIn("private", str(caught.exception))

    def test_approved_bounded_english_is_kept_exactly_without_translation(self):
        description = "An original turquoise turtle gardener with a copper shell and canvas apron."
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response({"response": '{"verdict":"allow"}', "done_reason": "stop"})
            self.assertEqual(art_policy.review_art_prompt(description), description)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_long_korean_is_classified_in_full_before_bounded_summary(self):
        description = ("독창적인 청록색 거북 정원사와 구리 등껍질. " * 100)[:2000]
        summary = "An original turquoise turtle gardener with a copper shell and canvas apron."
        progress = []
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.side_effect = [response({"response": '{"verdict":"allow"}'}),
                                                    response({"response": json.dumps({"prompt": summary})})]
            self.assertEqual(art_policy.review_art_prompt(description, progress.append), summary)
            calls = opener.return_value.open.call_args_list
            first, second = [json.loads(call.args[0].data) for call in calls]
            self.assertEqual(json.loads(first["prompt"])["description"], description.strip())
            self.assertEqual(first["options"]["num_ctx"], 8192)
            self.assertEqual(second["options"]["num_predict"], 1024)
            self.assertEqual(json.loads(second["prompt"])["color_translations"]["청록색"], "turquoise")
            self.assertEqual(progress, ["art_summarizing"])

    def test_rejected_or_invalid_verdict_never_calls_translator(self):
        for verdict in ("unsafe", "replica", "uncertain", "unknown"):
            with patch("pawzura.art_policy.build_opener") as opener:
                opener.return_value.open.return_value = response({"response": json.dumps({"verdict": verdict})})
                with self.assertRaises(GenerationError):
                    art_policy.review_art_prompt("독창적인 캐릭터 설명")
                self.assertEqual(opener.return_value.open.call_count, 1)

    def test_incomplete_or_unsafe_translation_never_becomes_a_prompt(self):
        for output in ({"response": '{"prompt":"original', "done_reason": "length"},
                       {"response": json.dumps({"prompt": "A named Pikachu character with yellow fur"})},
                       {"response": json.dumps({"prompt": "x" * 513})}):
            with patch("pawzura.art_policy.build_opener") as opener:
                opener.return_value.open.side_effect = [response({"response": '{"verdict":"allow"}'}), response(output)]
                with self.assertRaises(GenerationError):
                    art_policy.review_art_prompt("독창적인 캐릭터 설명")

    def test_image_invalid_coordinates_and_missing_model_name_are_actionable(self):
        from test_artwork import png
        output = {"message": {"content": json.dumps({"verdict": "allow", "identity": "none", "single_character": True, "mouth_x": 50, "mouth_y": .5})}}
        with patch("pawzura.art_policy.build_opener") as opener:
            opener.return_value.open.return_value = response(output)
            with self.assertRaisesRegex(GenerationError, "art_review_image_invalid"):
                art_policy.review_art_image(png())
        for language in ("en", "ko"):
            dialog = ArtworkDialog(language)
            dialog.failed("art_review_prompt_incomplete")
            self.assertIn(DETAIL_MODEL, dialog.status.text())
            self.assertNotIn("ollama pull", dialog.status.text())
            dialog.failed("art_review_image_missing")
            self.assertIn("ollama pull qwen3-vl:2b", dialog.status.text())
            dialog.preview.timer.stop()
            dialog.deleteLater()


if __name__ == "__main__":
    unittest.main()
