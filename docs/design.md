# Approved design, 2026-10-11

Owner response: "all approved". Covers specification, plan and autonomous execution choices. No further design approval loop is needed.

## Outcome

A portable Codex skill and local CLI turn source HTML into a per-page image datasheet, prompt queue, resumable checkpoint, provenance ledger and human-readable page asset folders. Images are the main deliverable. HTML integration is optional and lowest priority. The implementation does not call paid agent APIs, generate a batch without context checks, or access Vercel.

## Architecture

Use one local agent with deterministic CLI checks rather than a hosted multi-agent application. Preserve the current Codex execution environment. The OpenAI Agents skill informs durable state, explicit results and bounded retries; an API session is not needed for this handover.

The skill is discoverable in `.agents/skills/cleaning-image-production` and installable in the user's Codex skill directory. The CLI parses actual placeholders and comparison layers, records exact selectors and source hashes, and refuses output inside the source directory. Saved owner approvals remain tied to the exact asset hash. Read-only source and protected-directory checks happen before scanning or writing.

## Data flow

Source HTML -> slot inventory -> task-specific prompt and equipment selection -> built-in image tool -> local asset registration -> technical/visual review -> explicit owner approval -> optional copied-HTML integration.

Per-slot state separates pending, generated, reviewed and owner-approved. Approved assets cannot be overwritten. A failed comparison revises only the necessary unapproved side. The queue starts with heroes and works one page at a time. Sources define image counts, not an assumed 5/10/15 quota.

Each slot records page/category/section/selector, role, pair membership, literal source context, source hash, suggested filename, Google inspiration query, provenance, asset hash, review evidence and approval evidence. Reference images stay local. Public publication contains reusable code, tests and generic documentation only.

## Project requirements

- Sydney archive: three category folders, 26 page folders, originals and corresponding local images. Label the snapshot accurately; later manual online changes are not locally verified.
- Darwin: source is read-only, business is Shining Services cleaning, 26 pages with 471 image sides. Keep supplied source claims separate from verified company facts.
- Source count and pair positions must survive parsing. No website copy, section-order or CSS redesign.
- Equipment references and actual task suitability are mandatory before generation/edit when applicable. No forced machine in AFTER scenes.
- Prompt realism, visible cleaning target, clear result and page/environment diversity are explicit review criteria. Synthetic imagery remains illustrative.
- Never inspect or enumerate the protected recovered-images directory. Never access Vercel. Never publish owner images, private HTML, tokens or customer details.
- Skill cannot override system instructions or guarantee perfect adherence. CLI guards enforce supported operations; direct filesystem edits outside it remain outside its control.

## Verification and delivery

Test extraction, source immutability, blocked output paths, resumability, source drift, locked assets, proof-required reviews/approvals and retry limits. Independently evaluate the skill with realistic pressure scenarios. Run the parser on the actual 26 Darwin source files. Package local data separately from the public workflow repository. Verify GitHub content and SHA after publication, without touching deployments.
