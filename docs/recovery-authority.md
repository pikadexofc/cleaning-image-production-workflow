# Evidence-first recovery rules

Latest scoped owner instruction takes precedence. Source HTML determines slot context, not image approval or customer-job verification. Approved selections are locked. Missing evidence stays missing.

| Rule | Source evidence | Acceptance test | Verification boundary |
|---|---|---|---|
| R01 No humans in heroes, including partial bodies/reflections/shadows | Latest owner hero correction | test_hero_no_humans; test_unknown_human_status_blocks | Actual image observation required |
| R02 Cropped head means present worker in active process imagery, forest-green polo, practical dark trousers | Master prompt section 2; historical photography note | test_cropped_head_still_needs_worker | Applies to active work, hero exception overrides |
| R03 Rug BEFORE has active worker, professional tools and clearly visible rug | Owner rug annotations | test_rug_before_requires_action | Not universal BEFORE rule |
| R04 Exact visible hardware and physical colours; no inferred brands/specs or promotional ribbons | Owner equipment instructions | test_equipment_mismatch_blocks; test_ai_registration_requires_preflight | Reference inspection and attachments required; geometry is attested |
| R05 Same identifiable item/environment; visibly different plausible viewpoint; visible believable cleaning result | Approved historical photography correction and latest pair feedback | test_pair_identity_and_result_are_required; test_identical_pair_bytes_block; test_opposite_pair_missing_blocks | Six-image contact sheet QA when authorized |
| R06 Natural documentary lighting, neutral-warm balance, restrained contrast, microtextures; no CGI/HDR/stock posing/blur/logos/text | Master prompt sections 1, 5, 6, 7 | test_every_common_observation_required | Visual observation, not automated style detection |
| R07 No synthetic customer-job proof | Owner recovery plan and master provenance boundaries | test_synthetic_job_evidence_rejected; test_context_not_job_evidence | Export selection is not job verification |
| R08 Preserve exact owner selection; general approval never means image approval | Owner manual-assignment instructions | test_approval_requires_review_and_exact_asset_hash_and_locks_it; test_real_review_and_exact_approval | Approval record authenticity requires direct owner evidence |
| R09 No ambiguous guessed mappings | Owner database instruction | test_ambiguous_and_missing_mapping_block | Owner export page/selector/token map retained |
| R10 Source read-only; preserve layout, three horizontal comparisons and provided templates | Owner source/template comments | test_exact_roles_context_and_source_unchanged; test_output_under_source_rejected_before_write | No HTML integration performed; horizontal rendered layout untested |
| R11 Protected folder excluded before access, including resolved links | Project AGENTS | test_protected_source_rejected; test_state_symlink_into_protected_folder_rejected_before_read | Windows file-symlink test may skip; junction test separate |
| R12 Resume partial work; source hashes and concurrent checkpoints | Owner recovery plan | test_resume_reviews_existing_batch_first; test_stale_save_cannot_erase_newer_progress | Source drift blocks queue |
| R13 Bounded attempts and explicit blockers | Owner recovery plan; existing retry cycle | test_retry_limit; test_retry_reopens_only_with_explicit_evidence_and_keeps_versions; test_blocked_state_visible_and_progress_preserved | Three total attempts per authorized cycle, equivalent to initial plus two corrections |
| R14 Real decoding, correct file extension; honest separate technical/visual layers | Owner verify requests | test_real_decoding_and_extension; test_legacy_review_cannot_be_approved_by_gateway | No visual claims from bytes alone |
| R15 Saved review evidence required and hash-bound | No fabricated proof instruction | test_missing_and_changed_review_evidence_block | File existence cannot establish authenticity; no claim otherwise |
| R16 No Vercel/deployment changes; correct Darwin business and claims | Current owner boundaries and supplied local export | Configuration and repository review | Access prohibition by instruction, not a network sandbox |

## Supersession and limitations

The no-human hero rule supersedes active-worker defaults only for heroes. Active process images still show a correctly cropped worker. Finished AFTER scenes do not force machinery. BEFORE may be condition-only except the explicit rug rule. Equipment is appropriate to task, not automatically industrial for domestic/clinical/delicate services.

The owner supplied a standalone Sydney export as assignment authority. No live Vercel equality is inferred. Historic variants are excluded from the Sydney delivery image set. Old access-denied reports are historical, not current status.

Full raw conversation exports, every rejection and an older referenced 4565-line specification have not been established as available. Source-indexed local evidence is included privately in the ZIP. This system is not claimed definitive or a vector database. JSON/CSV records are structured memory, not computed embeddings.

## Supported production entrypoint

Use `scripts/recovery.py`; `workflow.py` is the low-level checkpoint library retained for compatibility and tested independently. Calling the library directly bypasses new policy gates. No script can prevent an agent from intentionally bypassing instructions or lying in an observation. The supported path rejects absent/failed observations, legacy reviews, missing pair assets, identical pair hashes, corrupt bytes and changed evidence.

Run status/next first. Review existing generated work before further generation. Heroes contain no people. Never regenerate an approved record. Scope generation to the current page and relevant references. Import an exact owner assignment before considering generation. No website redesign or deployment is part of this handover.
