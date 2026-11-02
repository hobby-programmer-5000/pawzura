[English](../en/RELEASE-v0.2.2.md) | [한국어](../ko/RELEASE-v0.2.2.md) · [Documentation](../README.md)

# 0.2.2 — fix incomplete local review responses

Long Korean descriptions could exhaust the old combined review's 600-token output budget, leaving unfinished JSON and the vague “local review failed” error. Description safety/originality verdicts and bounded English summaries now run separately. Approved short ASCII descriptions are kept exactly. Incomplete, malformed, missing-model, connection, timeout, memory and service failures identify the review stage/model and the relevant next action. No partial JSON is repaired or accepted, and no failed review is bypassed.

The larger text context and explicit response bounds improve long-input handling, but small-model summaries can still miss details. Existing model licenses, progress reporting and image/guardian protections remain in place. No new model or library is required. Restart using the new extracted EXE; installed models/runtime are reused.

[Review troubleshooting](CREATIVE-ART.md#when-something-fails) · [Validation](VALIDATION.md).
