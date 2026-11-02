[English](../en/HARNESS-RECEIPTS.md) | [한국어](../ko/HARNESS-RECEIPTS.md) · [Workflow](SMALL-APP-HARNESS.md)

# Evidence, retry and recovery procedure

Use this procedure for substantial changes or multi-session work. A short wording edit needs its relevant checks and final report, not an audit service or mandatory JSON. These are workflow rules; no new runtime, CI gate or permission control is installed.

## Establish the checked snapshot

Record the base commit and existing dirty paths before changes. In the brief, map expected edit paths and preserved behavior to acceptance checks. Update the scope with a reason when another file is implicated. Use a separate worktree when concurrency, conflicts or an experiment justify it; preserve any original uncommitted work separately. Worktrees do not isolate host credentials/network. See [Git's description](https://git-scm.com/docs/git-worktree).

For each meaningful verification, identify the tested commit or working-tree diff/artifact checksum. A base commit alone does not identify uncommitted edits. Note changes to environment, inputs or generated artifacts that invalidate older checks. A fresh result applies only to its tested snapshot and scope.

## Evidence that supports a pass

- Capture the actual command's exit status and a safe output reference. In a command sequence, capture each relevant status; the last successful command must not conceal an earlier failure.
- Confirm that the intended tests ran against the intended target. No tests collected, all relevant tests skipped, stale logs or the wrong EXE version do not establish acceptance. A syntax/lint/type check also does not establish runtime behavior.
- For a regression, observe that the check covers the reported failure and passes after the fix. Record a before-fix failure when it can be reproduced safely; otherwise state the limitation.
- If a flaky/environmental failure is suspected, preserve its signature and reason for retry. Report the failure and the later result separately. An unexplained intermittent failure stays an open issue.
- Use PASS, FAIL, NOT RUN or USER REPORTED with procedure, environment and remaining gaps. UI/manual checks need observable steps/results as well as automated checks where relevant.

## Retry and improve the failure class

After two same-signature failures without new evidence, stop repeating that action. Distinguish implementation defects, missing context, wrong target/version, dependencies/environment, permission denial and external-service failure. Choose a new authorized hypothesis or checkpoint the exact missing input while continuing unaffected work. Do not bypass an explicit tool stop condition. Host-enforced deadlines, budgets or iteration limits require actual runner support.

Preserve the diff and relevant evidence. Do not automatically restore/reset/clean the whole checkout. If rollback is necessary, identify safely separable agent edits and the user's authorization first; do not delete user work to obtain green checks. A retained patch, targeted reversal or isolated experiment may be appropriate depending on the actual worktree state.

For a repeated confirmed failure, choose the smallest correction to the process: a regression check for behavior, a scoped guide for missing domain facts, or a purpose-built tool for a fragile repeated operation. Verify that it covers the failure before promoting it into standing guidance. One unconfirmed diagnosis is not a universal rule.

## Optional machine-readable receipt

Use a new ignored `.cache/agent-work/runs/<run-id>/receipt.json` for each checked snapshot, with sanitized evidence beside it. Preserve previous receipts; make a new correcting/superseding record rather than silently rewriting an accepted result. Update STATE.md to point at the latest applicable receipt. This retention convention is not cryptographic immutability or guaranteed crash recovery.

The following is an unexecuted example. `null` means unavailable/not measured, not zero. Populate revision/hash/command fields from observed results; omit irrelevant fields rather than fabricating usage, reviewer identity or a successful test count.

```json
{
  "schema_version": 1,
  "run_id": "EXAMPLE_ONLY",
  "base_commit": null,
  "tested_snapshot": {"kind": "working-tree-diff", "sha256": null},
  "changed_paths": ["path/to/file"],
  "checks": [
    {
      "criterion": "example acceptance condition",
      "command": null,
      "exit_code": null,
      "result": "NOT RUN",
      "tests_collected": null,
      "tests_skipped": null,
      "duration_seconds": null,
      "evidence": null
    }
  ],
  "review": {"kind": "self", "findings": []},
  "outcome": "NOT RUN",
  "unresolved": ["Illustrative example; no check was executed"],
  "final_commit": null,
  "artifact_sha256": null,
  "usage": {"model": null, "tokens": null, "cost_usd": null}
}
```

Keep private data, credentials, raw private diffs, machine paths and unsafe stdout out of receipts/evidence. Record only reviewed non-sensitive input/artifact hashes. Sanitized evidence must say what was omitted when omission limits verification. Record a final commit after it exists; do not pretend a receipt inside that same commit can contain its own final commit hash.

If independent review was requested and is available, supply the original acceptance contract, raw code diff and safe receipts. Require findings tied to specific code/evidence, their impact and a correction; recheck the corrected snapshot. Record self-review honestly when no separate reviewer exists. Do not prescribe a different model/effort or automatic delegation merely because a reference article used it.
