# Sprint Planner Decisions

The decisions we have to make as a team before building the sprint planner. We go through this list together and answer each item in a line or two. An AI assistant then uses our answers, `ARCH_SYNTH.md` and the code to fill in `SPRINT_PLANNER_SPEC.md`, and we review what it writes.

- Check an item once the whole team agrees.
- `Spec:` lists the questions in `SPRINT_PLANNER_SPEC.md` that the answer settles, so the AI knows where it goes.
- If we can't settle something in the meeting, write "open" and who's following up. If an item is left blank, the AI proposes an answer and we have to review it later.

## 1. Already agreed: confirm

These came up while planning. Check each one if everyone agrees, or edit it if not.

- [ ] **A-1** This repo is the base for the shared sprint planner, which we'll use for our main project over the next two semesters.
- [ ] **A-2** There are four of us, and we have about 10 days to build it.
- [ ] **A-3** We act as engineers and architects, and LLMs write most of the code. A person reviews everything before it's merged.
- [ ] **A-4** Git workflow: everyone branches off `staging` for their own work and opens a PR. PRs are reviewed before they're merged into `staging`. When `staging` is stable, it's merged into `main` (the repo's default branch is `main`, not `master`).
- [ ] **A-5** Working on separate branches is practice for our main project, but we won't split the work so finely that people have to wait on each other.
- [ ] **A-6** Projects, sprints and stories can be deleted and restored later. (`ARCH_SYNTH.md` decision 1)
- [ ] **A-7** Story dependencies are shown as a graph. (`ARCH_SYNTH.md` decision 2)
- [ ] **A-8** "GitHub integration" means a place to add a link to the GitHub branch or issue for a sprint or story. There's no syncing, no webhooks and no automatic status changes. (`ARCH_SYNTH.md` decision 3)
- [ ] **A-9** AI analysis of sprint progress is available during a sprint, not only after it closes. (`ARCH_SYNTH.md` decision 4)
- [ ] **A-10** The AI uses the GitHub links to read the actual code and compare it with what the sprint says has been done.
- [ ] **A-11** Stories can be moved to earlier or later sprints. (`ARCH_SYNTH.md` decision 5)
- [ ] **A-12** We also want discussion features and velocity tracking. (`ARCH_SYNTH.md` §1)
- [ ] **A-13** UI was the biggest gap in our individual apps, so it needs real attention here.
- [ ] **A-14** We answer this file together, AI fills in the spec from it, and we review the spec before building.

## 2. To check before the meeting

Facts rather than decisions. Anyone can look these up.

- [ ] **C-1** Is our repo private? If so, the backend needs a GitHub token to read the code.
  - Answer:
- [ ] **C-2** Can the deployed backend make outbound requests to `api.github.com` and the AI provider? (Spec: OPS-2)
  - Answer:
- [ ] **C-3** Does someone on the team have admin rights on the repo, so we can set up branch protection?
  - Answer:
- [ ] **C-4** Does the class allow sending our source code to an outside AI provider? Is there an AI budget or a provided API key? (Spec: AI-7, AI-8)
  - Answer:

## 3. To decide

### Team and process

- [ ] **D-1** What has to work before we start using the planner for our main project? What gets cut first if we run out of time? (Spec: SCOPE-1, §3)
  - Answer:
- [ ] **D-2** Who owns what? Suggested in planning: four areas. Platform (foundation, login, delete/restore) · Sprint flow (workflow, moving stories, velocity) · AI (GitHub links, analysis, code review) · Graph and discussion. (Spec: §16)
  - Answer:
- [ ] **D-3** Do we do a short shared foundation step before splitting up (break `main.py` and `main.jsx` into smaller files, add migrations, add shared helpers)? Who does it, and how long do we give it? (Spec: PLAN-1, PLAN-2)
  - Answer:

### Git, PRs and review

- [ ] **D-4** Branch protection on `staging` and `main`: how many approvals, and which CI checks have to pass? (Spec: TEST-5)
  - Answer:
- [ ] **D-5** How do PRs get merged into `staging`: squash, merge commit or rebase?
  - Answer:
- [ ] **D-6** What's our branch naming convention (e.g. `<area>/<short-description>` or `story/SP-42-short-title`)? (Spec: GH-6)
  - Answer:
- [ ] **D-7** How big can a PR be, and how quickly do we review them?
  - Answer:
- [ ] **D-8** Who reviews what: a rotation, or a CODEOWNERS file that maps folders to owners?
  - Answer:
- [ ] **D-9** When does `staging` get merged into `main`, and who decides it's stable?
  - Answer:
- [ ] **D-10** Do we keep a shared instructions file for our LLMs (`CLAUDE.md` or `AGENTS.md`)? Which rules go in it (folder layout, required tests, don't edit other people's areas, don't reformat untouched code)?
  - Answer:
- [ ] **D-11** What's our rule when two PRs both add a database migration? (Spec: MIG-4)
  - Answer:

### Technical foundations

- [ ] **D-12** Which migration tool do we use, and what happens to the existing staging and production data? (Spec: MIG-1, MIG-3)
  - Answer:
- [ ] **D-13** How do people log in, and how are accounts created? (Spec: AUTH-1, AUTH-2)
  - Answer:
- [ ] **D-14** Which roles do we need, and who can delete, restore, close sprints and run AI reviews? (Spec: PERM-1, PERM-2)
  - Answer:
- [ ] **D-15** Frontend stack: routing, data fetching, component library, and TypeScript or not? (Spec: UI-2 to UI-5)
  - Answer:
- [ ] **D-16** Which pages do we need? (Spec: UI-1)
  - Answer:
- [ ] **D-17** Do we sketch screens before building them, and who signs off on the UI? (Spec: UI-6)
  - Answer:
- [ ] **D-18** Which tests does every PR need? Do CI tests run against Postgres? (Spec: TEST-1 to TEST-3)
  - Answer:
- [ ] **D-19** Do we rename the app or the repo? Renaming the repo changes the deployed URL. (Spec: OPS-1)
  - Answer:

### How we work in the planner

- [ ] **D-20** Which board columns do we use? Is "blocked" set by a person, or worked out from unfinished blockers? (Spec: CORE-1, CORE-2, DEP-1)
  - Answer:
- [ ] **D-21** Which point scale do we use, and can unpointed stories go into a sprint? (Spec: CORE-5)
  - Answer:
- [ ] **D-22** Do stories get short keys like `SP-42`? (Spec: CORE-6)
  - Answer:
- [ ] **D-23** How long are sprints, and is only one sprint active at a time? (Spec: CORE-7, CORE-8)
  - Answer:
- [ ] **D-24** Are subtasks full stories with a parent, or a simple checklist? (Spec: CORE-4)
  - Answer:
- [ ] **D-25** What's our definition of done? (Spec: CORE-9)
  - Answer:

### Features

- [ ] **D-26** Delete and restore: what can be deleted, what happens to a deleted sprint's stories, and is anything ever deleted permanently? (Spec: DEL-1, DEL-2, DEL-7)
  - Answer:
- [ ] **D-27** Dependency graph: what does it show by default, and can links be drawn on it? (Spec: DEP-4, DEP-7)
  - Answer:
- [ ] **D-28** When a sprint closes, what happens to its unfinished stories? (Spec: MOVE-1)
  - Answer:
- [ ] **D-29** Can several future sprints be planned at once, and what does the planning view look like? (Spec: MOVE-4, MOVE-5)
  - Answer:
- [ ] **D-30** Is velocity measured in points or in stories, and which charts do we want? (Spec: VEL-1, VEL-5)
  - Answer:
- [ ] **D-31** Where can discussion happen (stories, sprints, the whole project)? Do we want @mentions and notifications? (Spec: CHAT-1, CHAT-4)
  - Answer:
- [ ] **D-32** GitHub links: which kinds (branch, PR, issue), how many per story, and do sprints get links too? Branches are usually deleted after merging, which breaks branch links. (Spec: GH-1 to GH-3, GH-5)
  - Answer:

### AI analysis and code review

- [ ] **D-33** Which kinds of AI analysis do we want, and when can they run? (Spec: AI-1, AI-2)
  - Answer:
- [ ] **D-34** What should the code review check? For example: done stories match the code, acceptance criteria have evidence, merged work isn't linked to any story, changes have tests. (Spec: REPO-1)
  - Answer:
- [ ] **D-35** How much code does the AI see: only the linked PRs' diffs, or can it explore the repo with read-only tools? (Spec: REPO-2)
  - Answer:
- [ ] **D-36** Is the AI's verdict only advice, or can it flag or change stories? (Spec: AI-6, REPO-11)
  - Answer:
- [ ] **D-37** Which AI provider and model, whose API key, and what budget? (Spec: AI-7, REPO-15)
  - Answer:
- [ ] **D-38** How does the backend read the repo (e.g. a read-only token), and who creates and stores the credential? (Spec: REPO-4, OPS-3)
  - Answer:
- [ ] **D-39** Do stories need acceptance criteria before the AI can review them? (Spec: REPO-13)
  - Answer:
