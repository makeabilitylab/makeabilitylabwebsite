# Issue #649 — Link old talks / papers / videos to projects

> Retroactively populate the `projects` M2M on existing artifacts that currently
> have none. Source of truth for scoping: `~/Downloads/makeability-prod-2026-06-14.sql.gz`
> (prod snapshot, 2026-06-14).

## Status (2026-06-22)

**Shipped:** a read-only Data Health check, `UnlinkedArtifactsCheck`
(`website/admin/data_health/checks/unlinked_artifacts.py`), surfacing unlinked
artifacts at `/admin/data-health/` — **pre-2012 work excluded** (pre-Makeability-
Lab — cutoff is `settings.DATE_MAKEABILITYLAB_FORMED`), parent-publication
propagation flagged, deep-links to each edit page, CSV export, regression-tested
(`website/tests/test_unlinked_artifacts_check.py`).
Issue #649 updated with the scope table + decision.

**Shipped (Tier-1 propagation):** `propagate_publication_projects` management
command (`website/management/commands/`) copies a publication's projects onto any
childless `talk`/`video`/`poster` — additive-only, idempotent — wired into
`docker-entrypoint.sh` so it self-heals on every container start. Clears the
"parent publication is linked — inherit its projects" rows automatically. Tested
in `website/tests/test_propagate_publication_projects.py`.

**Deferred:** the Tier-2 semi-automated suggestion/apply pipeline below (for
artifacts with *no* parent publication to inherit from). Not built — held unless
the manual route through the health check proves too slow. Kept for reference.

---

## Scope (measured from the prod dump)

| Type        | Total | Linked (≥1 project) | **Unlinked** |
|-------------|------:|--------------------:|-------------:|
| Publication |   227 |                 164 |       **63** |
| Talk        |   187 |                  98 |       **89** |
| Poster      |     9 |                   8 |        **1** |
| Video       |    74 |                  30 |       **44** |
| **Total**   |       |                     |      **197** |

85 projects exist to link against.

### Key data-model facts
- `Artifact` is **abstract**; each concrete type has its own through table:
  `website_publication_projects`, `website_talk_projects`,
  `website_poster_projects`, `website_video_projects`.
- A `Publication` carries `talk_id`, `video_id`, `poster_id` FKs to its own
  child artifacts.
- Publications & talks have authors (`*_authors`) and keywords (`*_keywords`).
  **Videos have neither** (only title/caption/date) and posters have authors.
- `ProjectRole(person_id, project_id, lead_project_role, start/end_date)` maps
  people to projects over time.

### Why naive matching fails
Author overlap **alone is useless for disambiguation**: all 63 unlinked pubs and
all 89 unlinked talks each map to *more than one* candidate project (frequent
authors sit on many projects). Matching must **combine signals and rank**.

## Approach — two tiers

### Tier 1 — Propagation (high confidence, can auto-apply)
A child artifact inherits the projects of its parent publication.
From the dump this safely links **23 videos + 2 talks** (their parent pub is
already linked; child is not). Near-zero risk — the publication is the same
scholarly artifact.

### Tier 2 — Ranked suggestions (human-reviewed)
For the remaining ~172 artifacts, score every (artifact, project) pair with a
weighted blend and emit the top candidates for review:

- **Author ∈ project members** (via `ProjectRole`); weight ↑ for lead role,
  weight ↑ for role-window overlapping the artifact date.
- **Keyword overlap** — artifact keywords ∩ project keywords / umbrella keywords.
- **Title ↔ project** — token/substring match of artifact title against project
  `name` + `short_name`.
- **Date proximity** — artifact date within the project's active window.

Videos (no authors/keywords) lean on Tier-1 propagation first, then
title/caption ↔ project-name matching only.

## Deliverables

1. **`suggest_artifact_projects` management command**
   `website/management/commands/suggest_artifact_projects.py`
   - Reads the live DB (so it runs in any environment), computes Tier-1 +
     Tier-2, writes a reviewable **CSV**: one row per artifact with its top-3
     ranked project candidates, each with score + human-readable reason, plus an
     `approved_project_ids` column for the reviewer to fill/edit.
   - `--tier1-only` flag to emit just the high-confidence propagation set.
   - Read-only; writes nothing to the DB.

2. **`apply_artifact_projects` management command**
   `website/management/commands/apply_artifact_projects.py`
   - Consumes the reviewed CSV and adds the approved links (idempotent — never
     removes existing links, skips rows already linked).
   - `--dry-run` prints what it *would* do.

3. **Tests** (`website/tests/test_link_artifacts.py`, `DatabaseTestCase`)
   - Tier-1 propagation correctness (child gets parent's projects).
   - Scorer ranking on a small fixture (right project ranks first).
   - `apply` idempotency + dry-run does nothing.

## Workflow for Jon
1. Load the prod snapshot into a local scratch DB (so suggestions reflect prod).
2. `manage.py suggest_artifact_projects --out suggestions.csv`
3. Review/edit the CSV (approve/correct the `approved_project_ids` column).
4. `manage.py apply_artifact_projects suggestions.csv --dry-run`, then for real.
5. **Apply to prod** via the established entrypoint one-shot pattern: ship the
   reviewed CSV + an `apply` invocation through `docker-entrypoint.sh`, verify in
   logs. (No direct prod DB access — per repo constraints.)

## Open questions
- Auto-apply Tier-1 (the 25 propagations) without per-row review, or fold them
  into the same review CSV?
- CSV format OK, or prefer reviewing inside Django admin instead?
