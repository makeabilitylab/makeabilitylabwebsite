# Makeability Lab public REST API

A **public, read-only** JSON API over the lab's already-public content
(publications, projects, grants, people, and project leadership). It lets
external sites treat this website as the source of truth instead of duplicating
content. Introduced in #1268.

- **Base URL:** `https://makeabilitylab.cs.washington.edu/api/v1/`
  (test server: `https://makeabilitylab-test.cs.washington.edu/api/v1/`)
- **Format:** JSON. Read-only — only `GET`/`HEAD`/`OPTIONS`.
- **Auth:** none. All data is already public on the site.
- **Cross-origin:** enabled (`Access-Control-Allow-Origin: *`) on `/api/` only,
  so browser-side JavaScript can fetch it directly.
- **Versioned:** everything lives under `/api/v1/`. See *Stability contract*.

Built on Django REST Framework. In local dev (`DEBUG=True`) the endpoints also
render a **browsable HTML API** — just open them in a browser.

## Pagination

List endpoints are paginated (page-number style):

```json
{ "count": 157, "next": "...?page=2", "previous": null, "results": [ ... ] }
```

- `?page=<n>` — page number.
- `?page_size=<n>` — items per page (default **25**, max **100**).

A "top 5 most recent" list is just `?page_size=5` on an endpoint whose default
order is newest-first.

## Endpoints

### Publications — `GET /api/v1/publications/`

Default order: **newest first** (`-date`). Optional, combinable filters:

| Param       | Example                | Meaning                               |
|-------------|------------------------|---------------------------------------|
| `project`   | `?project=sidewalk`    | Publications attached to a project (by `short_name`). |
| `author`    | `?author=jonfroehlich` | Publications by a person (by `url_name`). |
| `year`      | `?year=2024`           | Publications in a calendar year.      |
| `type`      | `?type=Conference`     | By venue type (`Conference`, `Journal`, `Poster`, …). |
| `ordering`  | `?ordering=title`      | One of `date`, `-date`, `title`, `-title`. |

`GET /api/v1/publications/<id>/` adds a formatted `citation_html` and raw
`bibtex`, plus `book_title`, `publisher`, `isbn`, `num_pages`, `peer_reviewed`.

**Example — a "Recent Publications" widget** (client-side, e.g. on an academic
page):

```js
const r = await fetch(
  "https://makeabilitylab.cs.washington.edu/api/v1/publications/" +
  "?author=jonfroehlich&page_size=5"
);
const { results } = await r.json();
results.forEach(p => {
  // p.title, p.year, p.forum_name, p.authors[].name, p.pdf_url, p.official_url
});
```

### Projects — `GET /api/v1/projects/`

Only **publicly visible** projects (`is_visible=True`). Detail and
sub-resources are keyed by `short_name`:

- `GET /api/v1/projects/<short_name>/` — summary, about, website, dates,
  keywords, umbrellas, thumbnail.
- `GET /api/v1/projects/<short_name>/publications/` — the project's pubs.
- `GET /api/v1/projects/<short_name>/grants/` — grants funding the project.
- `GET /api/v1/projects/<short_name>/people/` — everyone with a role on the
  project, each as a `{ person, role, lead_project_role, start_date, end_date,
  is_active }` record (a person may appear more than once for multiple roles).
- `GET /api/v1/projects/<short_name>/leadership/` — **all** leadership across
  all time (current *and* past), grouped:
  `{ pis, co_pis, student_leads, postdoc_leads, research_scientist_leads }`,
  each a list of role records ordered newest-start first. A person appears once
  per lead role they've held (so a past student lead who later became PI shows
  up in both). Each record's `is_active` flag lets you separate current from
  past leadership.

### Grants — `GET /api/v1/grants/`

Filters: `?project=<short_name>`, `?sponsor=<sponsor short_name>`. Each grant
includes its `sponsor`, `grant_id`, `grant_url`, and the `projects` it funds.
Funding amounts are intentionally **not** exposed by the API.

### People — `GET /api/v1/people/`

Actual lab members (people with at least one Position); external co-authors are
not listed here even though they appear as publication `authors`. Detail by
`url_name`: `GET /api/v1/people/<url_name>/` — name, current title, bio,
thumbnail, and public social/web links (ORCID, Google Scholar, GitHub, etc.).

> **Note:** `email` is intentionally **not** exposed by the API to avoid making
> it an email-harvesting surface, even where it appears on a member page.

## Stability contract

- **`v1` fields are additive-only.** New fields may be added; existing field
  names and meanings will not change or be removed within `v1`. Breaking changes
  ship as `/api/v2/`.
- Don't hardcode pagination page sizes as a proxy for "all" — page through
  `next`, or set `page_size` explicitly (≤100).
- URLs in responses (PDFs, thumbnails, page links) are absolute and safe to use
  directly.

## Implementation notes (for maintainers)

Code lives in `website/api/` (`serializers.py`, `views.py`, `urls.py`,
`middleware.py`), mounted at `/api/` by the root URLconf
(`makeabilitylab/urls.py`). Config is the `REST_FRAMEWORK` block in
`settings.py`. CORS is a tiny in-repo middleware
(`website.api.middleware.ApiCorsMiddleware`), scoped to `/api/`, rather than a
third-party package. Tests: `website/tests/test_api.py`.

**Deliberately deferred** (add on the same pattern when needed): write
endpoints, auth / API keys, request throttling, and Talks/Posters/Videos
resources.
