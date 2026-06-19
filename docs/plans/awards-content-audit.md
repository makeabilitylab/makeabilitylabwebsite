# Awards page — content audit & redesign plan (#issue TBD)

Source data: prod snapshot `~/Downloads/makeability-prod-2026-06-14.sql.gz`, loaded into a
scratch DB (`award_scan`) and queried read-only. As of the snapshot there are **21**
`Award` rows and **298** news items; **54** news posts hit award keywords.

Two distinct buckets matter here:

- **`Award` model** → people / project / faculty *distinctions* (this page's top sections).
- **`Publication.award`** → **paper awards** (Best Paper, Honorable Mention). These render in
  the page's "Best Paper Awards" / "Other Paper Awards" sections and must be set on the
  *publication*, **not** entered as `Award` rows. Many news items below are paper awards — they
  need a publication audit, not an Award entry.

Legend: `[ ]` = candidate to add · `STU` Student Award · `PHD` PhD Fellowship · `FAC` Faculty
Honor · `PROJ` Project Award · `PAPER` → goes on `Publication.award` · ⚠ needs a decision.

---

## A. Faculty Honors — missing from the 21

- [ ] **2017 · NSF CAREER Award** (FAC) — Jon. News: `/news/nsf-career-award/` (2017-02-14). *On your CV; not in DB.*
- [ ] **2017 · Google Faculty Research Award — GlassEar** (FAC) — Jon, Leah Findlater. News: `/news/google-faculty-award-on-glassear/`. *CV ✓.*
- [ ] **2018 · 10-Year Impact Award — UbiFit** (FAC, test-of-time) — Jon. News: `/news/10-year-impact-award-for-ubifit/`. *Not on the CV list you sent — worth adding.*
- [ ] **2024 · Society-Centered AI Google Research Award** (FAC) — Jon, Jacob Wobbrock, Dhruv Jain, Arnavi Chheda-Kothary. News: `/news/society-centered-ai-google-research-award/`.
- [ ] **2012 · Google Faculty Research Award** — street-level accessibility (FAC) — Jon. *CV only; no news post found.*
- [ ] **2013 · "Inventors in our Midst", 1st DC-area Maker Faire** (FAC ⚠ or PROJ) — Jon. *CV only.*

## B. Student Awards & Fellowships — missing from the 21

- [ ] **2026 · NSF GRFP** (PHD) — Michael Duan **and** Ritesh Kanchi (alums). News: `/news/two-alums-receive-nsf-grfp/`. ⚠ one entry honoring both, or two? (recommend one).
- [ ] **2024 · CRA Outstanding Undergraduate Researcher — Honorable Mention** (STU) — Ritesh Kanchi. News: `/news/ritesh-earns-honorable-mention-for-cra-outstanding-undergraduate-researcher/`.
- [ ] **2024 · ACM Student Research Competition (Tapia)** (STU) — Daniel Campos Zamora. News: `/news/daniel-wins-acm-student-research-competition-at-the-tapia-conference/`.
- [ ] **2024 · American Junior Academy of Science — selected** (STU) — Aditya Sengupta. News: `/news/...selected-to-attend-american-junior-academy-of-science/`. ⚠ Possibly the same recognition as existing award #20 (Aditya, WA State delegate, 2024) — verify before adding.
- [ ] **2022 · CRA Outstanding Undergraduate Researcher** (STU) — Michael Duan. News: `/news/congrats-michael-duan-for-cra-undergrad-award/`.
- [ ] **2021 · Google-CMD-IT LEAP Alliance Fellowship** (PHD) — Dhruv Jain. News: `/news/dhruv-jain-selected-for-google-cmd-it-leap-alliance-fellowship/`.
- [ ] **2021 · Bob Bandes Memorial Teaching Award — Honorable Mention** (STU, teaching) — Liang He. News: `/news/liang-he-receives-bob-bandes-memorial-honorable-mention-teaching-award/`.
- [ ] **2019 · National SWE Scholarship** (STU) — Aileen Zeng. News: `/news/aileen-awarded-national-swe-scholarship/`.
- [ ] **2019 · Mary Gates Research Scholarship** (STU) — Aileen Zeng. News: `/news/aileen-zeng-awarded-mary-gates-research-scholarship/`.
- [ ] **2019 · Google Lime Scholarship** (STU) — Venkatesh Potluri. News: `/news/venkatesh-receives-google-lime-scholarship/`.
- [ ] **2017 · All-S.T.A.R. Fellow** (PHD/STU) — Matt Mauriello. News: `/news/matt-mauriello-selected-as-all-star-fellow/`.
- [ ] **2016 · ACM-W Scholarship (CHI 2016)** (STU) — Manaswi Saha. News: `/news/acm-w-scholarship-to-attend-chi-2016/`.
- [ ] **2012 · Graduate School Distinguished Dissertation Award, UW** (STU) — Jon. *CV only.*
- [ ] **2012 · CGS/ProQuest Distinguished Dissertation Award — Honorable Mention** (STU) — Jon. *CV only.*
- [ ] **2009 · Precourt Center Fellow, BECC** (PHD/STU) — Jon. *CV only.*

Low-priority / ⚠ judgment calls (probably skip or batch):
- [ ] 2016 · Matt Mauriello "Future Faculty Program" — *selected*, not an award. (skip?)
- [ ] 2023 · Ritesh — Google Product Inclusion & Equity Summit — *attended*, not an award. (skip?)
- [ ] 2018 · Dhruv — Tapia travel award / AccessComputing travel award — minor travel grants. (skip?)

## C. Project Awards — missing from the 21

- [ ] **2024 · Smart City Hub Switzerland Award (ZüriACT)** (PROJ) — Project Sidewalk. News: `/news/zuriact-with-project-sidewalk-win-smart-city-hub-switzerland-award-2024/`.
- [ ] **2024 · People's Choice Award — AltGeoViz** (PROJ ⚠) — Chu Li / AltGeoViz. News: `/news/altgeoviz-receives-people-choice-award/`. ⚠ could be a demo/poster award.
- [ ] **2020 · Best Artifact Award, ASSETS — SoundWatch** (PROJ ⚠) — Dhruv Jain, Leah Findlater. News: `/news/soundwatch-wins-best-artifact-award-at-assets/`. ⚠ artifact award — PROJ vs PAPER.
- [ ] **2019 · People's Choice Award — HomeSound** (PROJ) — Dhruv Jain. News: `/news/homesound-wins-peoples-choice-award/`.
- [ ] **2018 · People's Choice Award, Allen School Research Day — AR Captioning** (PROJ) — Dhruv Jain. News: `/news/ar-captioning-wins-the-peoples-choice-award.../`. *CV "2018 People's Choice [C.44]" ✓.*
- [ ] **2016 · Facilitators' Choice Award, NSF Video Showcase — BodyVis** (PROJ) — "13 of 156 (8.3%)". *CV ✓; missing from DB.*
- [ ] **2019 · Madrona Innovation Prize — HomeSound [C.58]** (PROJ ⚠ or PAPER) — *CV; verify whether to attach to the HomeSound paper instead.*

## D. Paper awards found in news → set on `Publication.award` (NOT Award rows)

These should be entered on the **publication's** Award field so they appear in the page's
Best/Other Paper sections. Needs a separate publication audit.

- [ ] 2026 · Best Paper, GAZE'26 workshop — "Causal Egocentric Gaze Estimation"
- [ ] 2026 · Best Paper, CHI'26 — GeoVisA11y
- [ ] 2024 · Best Paper, ASSETS'24 — ArtInsight ("Engaging with Children's Artwork…")
- [ ] 2024 · Best Paper (Belonging & Inclusion), UIST'24 — CookAR
- [ ] 2024 · Best Paper, IDEATExR'24 — ARSports / ARTennis
- [ ] 2024 · Best Paper **Nomination**, ASSETS'24 — ArtInsight (nomination only)
- [ ] 2021 · Honorable Mention + D&I Award, CSCW'21 — Small Group Captioning
- [ ] 2019 · Best Student Paper, ASSETS'19 — Deep Learning for Sidewalk Assessment
- [ ] 2019 · two Best Paper noms, ASSETS'19 (nominations only)
- [ ] 2019 · two Best Paper Awards, CHI'19 — Project Sidewalk / Anchored Audio Sampling
- [ ] 2017 · Best Paper, CHI'17 — MakerWear
- [ ] 2024 · **Best Academic Research, The Game Accessibility Conference** — "Playing on Hard Mode" [C.69]. *CV ✓.*

## E. Excluded (matched keywords but not awards)

Grants: Mapillary Camera Grant (2025), $1.2m NSF Grant (2018), GPSS Travel Grant (2020).
Other: "Project Sidewalk used in award-winning APA paper" (someone else's award); Distinguished
Lecture @ UMN (invited talk); CS Distinguished Lecture: Bjoern Hartmann (external speaker);
Liang's CHI'19 t-shirt design contest.

## F. Data fixes to existing rows

- [ ] **Award #18 — Facilitators' Choice (NSF Video Showcase)**: dated **2020-05-20**, description
  "21 of 242 (8.7%)". That stat + news #113 indicate this is the **2019 PrototypAR** award.
  Fix the date to 2019 and attach the **PrototypAR** project (recipient Seokbin Kang).
- [ ] Confirm William Chan #9 (Jon, 2012) vs #10 (Dhruv, 2023) — both correct, leave as-is.

## G. CV items already represented (no action)

SIGCHI Societal Impact 2026, PacTrans 2022, COE Outstanding Faculty 2021, Sloan 2017,
Madrona Prize 2009, Best Clean-Tech / UW Business Plan 2009, 1st Place UW Env. Innovation
Challenge 2009, MSR Graduate Fellowship 2008, COE Student Innovator 2010, William Chan 2012,
Project Sidewalk / Scistarter 2023.

---

### Open question for Jon
Once you've triaged A–D, do you want these entered **by hand in the admin**, or shipped as an
**idempotent `import_awards` management command** (wired into `docker-entrypoint.sh`, the
established pattern) so they land on test/prod via deploy? ~25 new rows makes the command worth it.
