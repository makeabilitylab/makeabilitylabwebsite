# Admin users, groups & permissions (#1125)

How editing access to the Django admin (`/admin`) is structured for the
Makeability Lab site, and the runbook for onboarding/offboarding people.

## Principle: Users = people, Groups = roles

Historically the site used a few shared, role-named *user* accounts
(`gradmin`, `ugradmin`, `collabmin`) as if they were groups — everyone in a
role shared one login. That cost us per-person attribution in the admin history,
clean offboarding (revoking one person meant rotating a shared password), and
least-privilege scoping.

Going forward: **each person gets their own account**, and **Groups carry the
permissions**. A person's access is determined by which group(s) they're in.

## The tiers

| Tier | Who | Account | How access is granted |
|---|---|---|---|
| **Superuser** | The maintainer (Jon) + one locked **break-glass** backup | personal | `is_superuser` flag (bypasses all permission checks) |
| **Editors** | PhD students & long-term staff who maintain the site | personal, one each | member of the `Editors` group |
| **Contributors** | Undergrads / interns | shared `contributor`, or personal if they become a regular maintainer | member of the `Contributors` group |

Why two superusers: never rely on exactly one. The break-glass account has a
strong, unique password and is used only to recover if the primary account is
locked out or broken.

Why account creation stays superuser-only: in Django's default admin, anyone who
can add/change `User` or `Group` objects can grant themselves permissions — an
escalation path. So neither group gets any `auth.*` permission; **only a
superuser creates accounts and assigns groups.**

## Permission sets

These are defined declaratively in
`website/management/commands/setup_admin_groups.py` and pinned by
`website/tests/test_setup_admin_groups.py`.

**`Editors`** — full `add`/`change`/`delete`/`view` on the public content models:
`banner, person, position, project, keyword, talk, publication, poster, news,
video, photo, projectumbrella, sponsor, projectrole`.

**`Contributors`** — submit-and-review, never destroy:
- `person`: `add`, `change`, `view` (edit bios)
- `publication`, `talk`, `poster`, `projectrole`: `add` + `view` (create their
  own work and review it; `view` is required so the admin changelist is
  reachable after an add)
- **no `delete` anywhere**

### Deliberately admin-only (neither group)

- **`Grant`** (Grants & Funding — funding data) and **`Award`** (curated external
  recognitions). Note: *paper* awards live on `Publication.award`, which Editors
  *can* edit via the publication; only the standalone `Award` model is withheld.
- `User`, `Group`, `Permission`, `LogEntry`, sessions — account/audit administration.

## How it's enforced

`setup_admin_groups` is **idempotent and the source of truth** for these two
groups' *permissions*: each run calls `Group.permissions.set(...)`, so a
permission added or removed by hand in the admin is reverted on the next run.

It runs automatically on every container start via `docker-entrypoint.sh`
(step 4.10) — this is the only push-deploy-compatible path because the test/prod
servers have no shell access. Edit the spec → redeploy to change a group's
permissions; don't hand-edit them in `/admin` (the change won't survive).

**Group *membership* is NOT managed by the command** — who belongs to a group is
set in `/admin → Users` and persists across deploys. Likewise users, the
superuser flag, and any other groups are untouched.

To preview without writing: `python manage.py setup_admin_groups --dry-run`.

## Runbook

**Onboard a PhD student / long-term editor**
1. `/admin → Users → Add`: create their account (they set their own password).
2. Set `is_staff = True`. Do **not** set `is_superuser`.
3. Add them to the `Editors` group. Save.

**Onboard an undergrad / intern**
- Either add them to the shared `contributor` account's owners, or (preferred for
  anyone staying a while) create a personal account in the `Contributors` group.
- Promote to `Editors` if they become a regular site maintainer.

**Offboard anyone**
- `/admin → Users`: set `is_active = False`. **Do not delete** the account —
  deleting it orphans their admin-history (`LogEntry`) attribution. Deactivating
  blocks login while preserving the record of what they changed.

**Rotate**
- The legacy shared accounts (`gradmin`/`ugradmin`/`collabmin`/old `makeadmin`)
  should be deactivated, and any retained superuser password reset, since their
  hashes exist in old DB dumps.
