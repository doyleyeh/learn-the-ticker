# Delivery workflow

## Recover and select

Read the seven canonical documents and relevant design/migration mechanisms. Run git status --short; preserve unrelated work. Verify the current branch and recover any interrupted task from STATUS, including its actual test results and repair count. Select the highest-priority unblocked TASKS entry whose dependencies are satisfied. Record IN_PROGRESS, current task and next action before implementation.

## Implement and validate

State acceptance criteria, inspect existing implementation/tests, and reuse working behavior. Record significant deviations in DECISIONS and deliberately update SPEC/PLAN only for an authorized decision. Use affected behavioral tests while editing; run related suites after a component and the milestone gate after a coherent task/checkpoint. EVALS owns exact commands and prerequisites.

On failure: diagnose, repair, rerun the failed check and affected checks. After three failed repair attempts, write the observed failure, attempted repairs, diagnosis and required next action into dated evidence and STATUS. Mark the task BLOCKED if external input/environment is needed. Never count an omitted or unimplemented required check as passing. Independent unblocked tasks may proceed; dependent milestones may not.

## Review and checkpoint

Review git status, git diff and staged diff for secrets, raw provider/source payloads, generated junk, accidental fixtures, unrelated work and weakened tests. Generate contracts from their source and verify drift. Update TASKS and STATUS with exact evidence dates, commands, outcomes and limitations. Preserve historical verification; record new evidence under docs/verification.

Commit a verified coherent task/sub-milestone with a conventional message. Do not create meaningless or project-sized commits. Push, PR creation, merging and publication need separate authorization. If execution stops before verification, retain honest IN_PROGRESS/BLOCKED state and an actionable next step rather than marking DONE.

## Finish the project

All required milestones must pass their acceptance checks. Run full automated verification and the separate live-provider/clean-machine release matrix. Independently compare SPEC requirements to implementation and evidence, looking for forgotten, partial, untested, divergent or regressed behavior. Fix gaps and repeat affected/full release checks. Complete task lists alone never establish completion.
