# Evaluation record, 2026-10-11

An isolated reviewer tested four pressure scenarios before reading the skill: protected-folder scanning, source-derived counts, a mismatched comparison with an approved side, and an older local snapshot after owner cloud edits. The baseline already handled those correctly. No baseline failure is invented and no claim that the skill alone caused an improvement is made.

Independent static review of the first implementation found source/output tree overlap, unsafe state-file symlink resolution, lost updates between concurrent writers, generation-first resume ordering, stale source prompts, stale page records, no authorized retry reopening and failure to preserve existing image assignments. Regression tests demonstrated five actual failures. These were corrected before publication. Retry reopening received its own failing test before implementation.

The final local test run exercises 18 tests: 17 pass; one actual file-symlink creation test is skipped on this Windows host because it lacks the privilege to create symlinks. The directory-junction test runs on Windows and demonstrated a second overwrite defect before its correction. A Linux GitHub Actions job exercises the file-symlink path where symlinks are available. Do not present an unrun/skipped test as a verified pass.

Actual Darwin extraction verified 26 read-only source pages, 315 ordinary placeholders, 78 pairs and 471 image sides, equivalent to 393 logical slots. All original source SHA-256 values matched after preparation. Production state has zero generated images and no owner-approved outputs. This delivery prepares the next agent; it does not claim the future image batch is finished.

Remaining limits are deliberate and documented: no Vercel/online manual export reconciliation, no image pixel QA in this preparation task, no paid API/hosted agent runtime, no automatic inference of approval/job evidence, and no arbitrary source-markup support. Directory protection and approval records depend on using the supplied workflow; direct external filesystem changes cannot be prevented by a skill.
