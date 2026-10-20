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

- [x] **C-1** Is our repo private? If so, the backend needs a GitHub token to read the code.
  - Answer: yes it is private
- [x] **C-2** Can the deployed backend make outbound requests to `api.github.com` and the AI provider? (Spec: OPS-2)
  - Answer: yes
- [x] **C-3** Does someone on the team have admin rights on the repo, so we can set up branch protection?
  - Answer: yes, we all have admin rights
- [x] **C-4** Does the class allow sending our source code to an outside AI provider? Is there an AI budget or a provided API key? (Spec: AI-7, AI-8)
  - Answer: there is a class provided api keys that we will use

## 3 To decide

### Team and process

- [x] **D-1** What has to work before we start using the planner for our main project? What gets cut first if we run out of time? (Spec: SCOPE-1, §3)
  - Answer: the base functionality that is in the base app is most important. the graph and discussion area would be the first thing to go, next would be the ai code reviews. we can implement those in the future if needed.
- [x] **D-2** Who owns what? Suggested in planning: four areas. Platform (foundation, login, delete/restore) · Sprint flow (workflow, moving stories, velocity) · AI (GitHub links, analysis, code review) · Graph and discussion. (Spec: §16)
  - Answer: Johnny, Bella, Eason, and Taft respectively.
- [x] **D-3** Do we do a short shared foundation step before splitting up (break `main.py` and `main.jsx` into smaller files, add migrations, add shared helpers)? Who does it, and how long do we give it? (Spec: PLAN-1, PLAN-2)
  - Answer: yes. we want an ai to build everything, then we will split up to refine our individual parts.

### Git, PRs and review

- [x] **D-4** Branch protection on `staging` and `main`: how many approvals, and which CI checks have to pass? (Spec: TEST-5)
  - Answer: one approval per branch. ci can just be our test suite
- [x] **D-5** How do PRs get merged into `staging`: squash, merge commit or rebase?
  - Answer: merge commit
- [x] **D-6** What's our branch naming convention (e.g. `<area>/<short-description>` or `story/SP-42-short-title`)? (Spec: GH-6)
  - Answer: name of developer combined with task
- [x] **D-7** How big can a PR be, and how quickly do we review them?
  - Answer: arbitrarily big for now
- [ ] **D-8** Who reviews what: a rotation, or a CODEOWNERS file that maps folders to owners?
  - Answer: ---
- [x] **D-9** When does `staging` get merged into `main`, and who decides it's stable?
  - Answer: we'll decide this as a group
- [x] **D-10** Do we keep a shared instructions file for our LLMs (`CLAUDE.md` or `AGENTS.md`)? Which rules go in it (folder layout, required tests, don't edit other people's areas, don't reformat untouched code)?
  - Answer: yes, lets have an initial one
- [x] **D-11** What's our rule when two PRs both add a database migration? (Spec: MIG-4)
  - Answer: if conflicts arise, we will address them as they come

### Technical foundations

- [ ] **D-12** Which migration tool do we use, and what happens to the existing staging and production data? (Spec: MIG-1, MIG-3)
  - Answer: we're not familiar with any, recommend some.
- [x] **D-13** How do people log in, and how are accounts created? (Spec: AUTH-1, AUTH-2)
  - Answer: simple username password
- [x] **D-14** Which roles do we need, and who can delete, restore, close sprints and run AI reviews? (Spec: PERM-1, PERM-2)
  - Answer: just one user role, all users can do everything
- [x] **D-15** Frontend stack: routing, data fetching, component library, and TypeScript or not? (Spec: UI-2 to UI-5)
  - Answer: keep as is, change if needed
- [x] **D-16** Which pages do we need? (Spec: UI-1)
  - Answer: keep as is, add more when needed such as graph view and discussion board
- [x] **D-17** Do we sketch screens before building them, and who signs off on the UI? (Spec: UI-6)
  - Answer: Build first, redesign later
- [ ] **D-18** Which tests does every PR need? Do CI tests run against Postgres? (Spec: TEST-1 to TEST-3)
  - Answer: what are the current ci tests checking?
- [x] **D-19** Do we rename the app or the repo? Renaming the repo changes the deployed URL. (Spec: OPS-1)
  - Answer: leave the repo as is for now, rename the app

### How we work in the planner

- [x] **D-20** Which board columns do we use? Is "blocked" set by a person, or worked out from unfinished blockers? (Spec: CORE-1, CORE-2, DEP-1)
  - Answer: manually set blocks 
- [x] **D-21** Which point scale do we use, and can unpointed stories go into a sprint? (Spec: CORE-5)
  - Answer: whatever point scale you'd recommend and yes
- [x] **D-22** Do stories get short keys like `SP-42`? (Spec: CORE-6)
  - Answer: just have the user set name be required unique
- [x] **D-23** How long are sprints, and is only one sprint active at a time? (Spec: CORE-7, CORE-8)
  - Answer: multiple sprints can be active at the same time, users set the time range
- [x] **D-24** Are subtasks full stories with a parent, or a simple checklist? (Spec: CORE-4)
  - Answer: full stories with a parent story
- [x] **D-25** What's our definition of done? (Spec: CORE-9)
  - Answer: user marks it done at every level

### Features

- [x] **D-26** Delete and restore: what can be deleted, what happens to a deleted sprint's stories, and is anything ever deleted permanently? (Spec: DEL-1, DEL-2, DEL-7)
  - Answer: children should be deleted with a parent and restored with parents as well. no deletion is permanent
- [x] **D-27** Dependency graph: what does it show by default, and can links be drawn on it? (Spec: DEP-4, DEP-7)
  - Answer: blank by default, automatically populate when dependencies are added
- [x] **D-28** When a sprint closes, what happens to its unfinished stories? (Spec: MOVE-1)
  - Answer: they remain in the sprint unless a user moves them out. this should be reflected in the report
- [x] **D-29** Can several future sprints be planned at once, and what does the planning view look like? (Spec: MOVE-4, MOVE-5)
  - Answer: yes. the creation should look the same for all sprints, but planning ones is simply setting the start date as a future date
- [x] **D-30** Is velocity measured in points or in stories, and which charts do we want? (Spec: VEL-1, VEL-5)
  - Answer: points. which charts are good? 
- [x] **D-31** Where can discussion happen (stories, sprints, the whole project)? Do we want @mentions and notifications? (Spec: CHAT-1, CHAT-4)
  - Answer: discussion board per sprint, not on stories or the whole project. @mentions and notifications would be nice but not essential
- [x] **D-32** GitHub links: which kinds (branch, PR, issue), how many per story, and do sprints get links too? Branches are usually deleted after merging, which breaks branch links. (Spec: GH-1 to GH-3, GH-5)
  - Answer: one link to the main page of the repo on the project, and links in each story for the related branch. not all stories need a link ie substories/subtasks might not have their own branch

### AI analysis and code review

- [x] **D-33** Which kinds of AI analysis do we want, and when can they run? (Spec: AI-1, AI-2)
  - Answer: analysis on the sprints. runs on request and on sprint completion. analysis should have velocity, progress, estimated completion date, what has been accomplished
- [x] **D-34** What should the code review check? For example: done stories match the code, acceptance criteria have evidence, merged work isn't linked to any story, changes have tests. (Spec: REPO-1)
  - Answer: yeah the examples look good
- [x] **D-35** How much code does the AI see: only the linked PRs' diffs, or can it explore the repo with read-only tools? (Spec: REPO-2)
  - Answer: explore the repo with read only
- [x] **D-36** Is the AI's verdict only advice, or can it flag or change stories? (Spec: AI-6, REPO-11)
  - Answer: verdict is advice only
- [x] **D-37** Which AI provider and model, whose API key, and what budget? (Spec: AI-7, REPO-15)
  - Answer: codex, we have an api key, lite usage, no strict budget
- [x] **D-38** How does the backend read the repo (e.g. a read-only token), and who creates and stores the credential? (Spec: REPO-4, OPS-3)
  - Answer: read only token
- [x] **D-39** Do stories need acceptance criteria before the AI can review them? (Spec: REPO-13)
  - Answer: reviews should sprint level so all stories belonging to the sprint are up for review 
