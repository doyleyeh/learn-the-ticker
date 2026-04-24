# Model Selection

## Repo Defaults

The current repo control docs and harness scripts default the local agent loop to:

- model: `gpt-5.4`
- reasoning effort: `high`

This is reflected in `SPEC.md`, `EVALS.md`, `scripts/activate_agent_env.sh`, `scripts/agent_loop.sh`, `scripts/agent_loop.ps1`, and `scripts/run_task_cycle.sh`.

## Spark Usage Rule

Use `gpt-5.3-codex-spark` only when there is a reliable signal that Spark capacity is still healthy for the run.

Operational rule for this skill:

- If `LTT_CODEX_SPARK_REMAINING_PERCENT` is set and is at least `30`, use `gpt-5.3-codex-spark`.
- If `LTT_CODEX_SPARK_REMAINING_PERCENT` is set and is below `30`, use `gpt-5.4`.
- If only `LTT_CODEX_SPARK_USED_PERCENT` is set, use Spark only when the value is `70` or lower.
- If neither signal is available, use `gpt-5.4` unless the operator explicitly opts into Spark.

## Why the Skill Falls Back

OpenAI's current help and product docs make two points that matter here:

- GPT-5.3-Codex-Spark has separate research-preview rate limits.
- Codex usage in local environments is not available through the Compliance API.

Because a local repo agent cannot reliably discover Spark usage on its own, this skill treats missing usage telemetry as a fallback-to-`gpt-5.4` case instead of guessing.

## Helper Environment Variables

The helper script in this skill reads these variables:

- `LTT_FORCE_TASK_CYCLE_MODEL`
- `LTT_CODEX_SPARK_REMAINING_PERCENT`
- `LTT_CODEX_SPARK_USED_PERCENT`
- `LTT_ENABLE_SPARK_WITHOUT_USAGE_SIGNAL`

`LTT_FORCE_TASK_CYCLE_MODEL` wins over every other rule and is the escape hatch when a human intentionally wants a different model.
