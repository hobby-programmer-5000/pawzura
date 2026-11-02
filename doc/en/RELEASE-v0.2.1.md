[English](../en/RELEASE-v0.2.1.md) | [한국어](../ko/RELEASE-v0.2.1.md) · [Documentation](../README.md)

# 0.2.1 — visible artwork progress

Creative artwork now has a persistent progress area with actual diffusion-step counts, stage names, total/stage elapsed time and the age of the last report. Loading and review remain indeterminate rather than displaying invented percentages. A notice appears after 60 seconds without a progress report; it does not claim that the backend has hung. Setup stages/model-group counts are also reported. Closing a busy dialog no longer hides the current stage behind the wait message. Final success/error stops the timer; the previous character is preserved on failure.

[Progress guide](CREATIVE-ART.md#follow-progress) · [Validation](VALIDATION.md). Model generation, licenses, content checks, private-data exclusion and guardian behavior remain unchanged. No cancellation or guaranteed ETA is added.
