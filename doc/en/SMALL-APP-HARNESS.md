[English](../en/SMALL-APP-HARNESS.md) | [한국어](../ko/SMALL-APP-HARNESS.md) · [Documentation](../README.md)

# A reusable workflow for building small apps

The deliverables are an active Pawzura `AGENTS.md` at the repository root and [reusable small-app rules](SMALL-APP-AGENTS.md) for another project. English is the default; Korean counterparts explain the same rules. No global Codex configuration, model, permission policy, extension or account is changed by these files.

## Start another app

1. Open the new project's folder in Codex. Copy the fenced rules from [the template](SMALL-APP-AGENTS.md) into its root `AGENTS.md`, merging existing guidance.
2. Fill in purpose, supported environments, code entry points and real run/check commands. Read only the relevant references when needed.
3. For a substantial task, put a brief under ignored `.cache/agent-work/BRIEF.md` and ask Codex to implement the result using that brief. If the project does not already ignore `.cache/`, add that exclusion. Keep private inputs elsewhere.
4. After a meaningful stage, inspect the app/output and `CHECKS.md`; resume from `STATE.md` when needed. Simple one-file edits do not need a separate task ledger.
5. Keep execution permissions in the host's supported controls. A rules file is guidance, not a new security/runtime engine. Start a new Codex session when checking automatic instruction discovery after installing or changing the file. [Official discovery rules](https://learn.chatgpt.com/docs/agent-configuration/agents-md).

Pawzura's root rules already name its actual modules, checks and invariants. Do not copy its Windows/Qt assumptions or executable names into an unrelated app. `AGENTS.ko.md` is a reference translation; default discovery does not automatically load that filename. The linked template is ordinary Markdown until its fenced content is installed as `AGENTS.md`.

## Task brief and inspectable evidence

These are suggested small notes, not mandatory schemas or Codex built-in commands. Do not record user profiles, secret values, private URLs or local diagnostic inventories.

```text
BRIEF.md
Goal: [one observable result]
Deliverables: [source/UI/artifact paths]
Scope / non-goals: [included and excluded work]
Acceptance: [criterion A; criterion B; relevant error/recovery behavior]
External actions authorized: [scope from the user; none if absent]

CHECKS.md
Criterion | Artifact/version/environment | Procedure | Result | Evidence
[criterion] | [tested target] | [actual command or manual steps] | [PASS/FAIL/NOT RUN/USER REPORTED] | [safe output reference]

STATE.md
Task / inputs: [current assignment and changes]
Outputs: [what exists and where]
Decisions: [confirmed choices and reasons]
Checks: [what passed/failed; what needs rechecking]
Open issues: [missing evidence or input]
Next action: [one concrete continuation step]
```

Resume prompt: “Read AGENTS.md and the current BRIEF.md, STATE.md and CHECKS.md under .cache/agent-work/. Compare them with my latest request and the current files. Preserve valid progress, recheck changed behavior, complete the remaining authorized work and update the notes.” Saving a checkpoint does not launch that prompt automatically.

## What the sources contribute

The OpenAI repository contains an executable agent harness, not simply a universal prompt. We inspected the following paths at commit [`a09812981de703f18f38015cd5d500ab373f616c`](https://github.com/openai/codex/tree/a09812981de703f18f38015cd5d500ab373f616c), checked 2026-11-02. This is a targeted source review, not an audit of the whole repository.

| Observed layer | OpenAI source | Adaptation here |
| --- | --- | --- |
| Model context and scoped project instructions | [Base guidance](https://github.com/openai/codex/blob/a09812981de703f18f38015cd5d500ab373f616c/codex-rs/protocol/src/prompts/base_instructions/default.md), [instruction fragment](https://github.com/openai/codex/blob/a09812981de703f18f38015cd5d500ab373f616c/codex-rs/core/src/context/user_instructions.rs) | Small root rules, task facts kept separately, current request wins over reference material |
| Actual approval/sandbox/retry orchestration | [Tool orchestrator](https://github.com/openai/codex/blob/a09812981de703f18f38015cd5d500ab373f616c/codex-rs/core/src/tools/orchestrator.rs), [core environment notes](https://github.com/openai/codex/blob/a09812981de703f18f38015cd5d500ab373f616c/codex-rs/core/README.md) | State boundaries honestly; do not pretend a Markdown deny rule constrains arbitrary shell code |
| Tool-result integration checks | [Tool harness tests](https://github.com/openai/codex/blob/a09812981de703f18f38015cd5d500ab373f616c/codex-rs/core/tests/suite/tool_harness.rs) | Inspect observable outcomes and target identity; a successful tool call alone is not feature completion |

OpenAI describes the runtime as the layer that carries context, invokes tools and handles configured boundaries; application rules belong above that runtime. This package uses Codex as already provided, rather than embedding its SDK or app-server in Pawzura. [Official harness overview](https://developers.openai.com/blog/codex-as-a-platform).

The user supplied the text of [Beam's long-task setup](https://x.com/beamnxw/status/2107522996046905797) after X returned 403 and desktop capture could not establish the browser URL. The supplied article discusses Claude Code. We read it as reference material, did not execute its snippets, and did not independently verify its Claude-specific model/command claims. Its prose/configuration is not reproduced here.

| Article layer | Small-app adaptation |
| --- | --- |
| Stable workspace facts | Short AGENTS.md with entry points and verified commands |
| Repeatable procedure | Brief → implementation slice → inspect result → checks → checkpoint |
| Access to source material | Exact primary links/commit references and task-relevant connectors only |
| Action rules at execution boundary | Respect host sandbox and connector controls; avoid ambiguous write retries |
| Evidence-producing review | Criterion/target/procedure/result/evidence table; independent reviewer only if requested |
| Reasoning effort | Keep the configured model/effort; compare actual outcomes before changing configuration |
| Completion and recovery | Openable/runnable output plus evidence and a next action; resume against changed inputs |

Claude-specific `CLAUDE.md`, `/goal`, `/rewind`, `$ARGUMENTS`, permission JSON and agent frontmatter are not installed as Codex features. No subagent, custom skill, automatic continuation, hard time/spending cap or token-savings claim is supplied. Those require supported tools/configuration and, where relevant, measured runs. This is our original MIT project guidance, informed by the sources above; no upstream runtime code is vendored.

## Review and improve the rules

Check three situations: a small wording change should take only relevant doc checks; a behavioral bug should produce a regression check and observed result; a resumed task should retain valid work and invalidate evidence affected by new requirements. Change one rule when a repeated failure exposes a concrete gap. Keep measured quality/cost/review effort separate from speculation about savings.

This initial rules package was checked for bilingual pairs, links and repository commands. It has not been benchmarked as an autonomous app-building runtime, and Markdown alone cannot guarantee adherence. The current task's local checkpoint is ignored rather than part of the release or repository history.
