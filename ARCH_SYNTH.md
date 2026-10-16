# Team Architecture Synthesis

## 1. What We Learned from Individual Apps
Summarize the most important ideas, gaps, and lessons the team discovered by comparing individual apps.
Resurrecting sprints/stories, having chat/discussion features, graphs showing dependencies, velocity tracking.
Biggest gaps was in the UI. We were not prepared for good UI design.

## 2. Engineering Decisions
Identify the 3-5 most important decisions the team made while creating the unified app.

For each decision:
- describe the alternatives considered;
- explain what evidence or experience shaped the choice;
- explain why the choice was reasonable for the team.

1. Projects, sprints, and stories can be resurrected
   - We considered preventing deletion or having deletion simply be permanent.
   - We want to be able to delete tasks, but we do not want to risk losing things we might need in the future.
   - It is a simple solution for our needs.
2. Graphs to show story dependencies
   - An alternative was to not have a way to record dependencies, or simply record it but not show it.
   - We know that certain tasks will require others to be done first, and we do not want to find ourselves getting stuck in these scenarios.
   - Having a graph view will allow for us to visualize dependencies easily without having to make a mental model of our project structure.
3. Github Integration
   - The alternative is to manually keep track of which branches sprints and stories.
   - We felt that having these inherently connected will help us maintain our repository without confusing what branches are for.
   - This will reduce uncertainty when we have many branches and stories.
4. AI summary/analysis showing sprint progress
   - Originally we were thinking about having AI summaries only available once a sprint is completed.
   - We want more than just a percentage representing our work.
   - This will help guide us if we ever feel stuck mid-sprint about what is needed next.
5. Moving Stories Between Sprints
   - Alternatively, stories would be locked to a single sprint.
   - We understand that some stories may take longer than expected and need to be moved to future sprints. Stories also may end up being needed sooner than expected and need to be moved up,
   - This was the option that best suited the needs of our team.

## 3. Preserve / Replace / Simplify
Summarize what the team preserved from individual apps, what it replaced, and what it simplified.

## 4. Validation and Risk Lessons
Describe what the team learned about correctness, reliability, deployment, AI report behavior, integration, or other risks while comparing and combining the apps.

## 5. Engineering Growth
Explain how the team's engineering practice changed as you moved from individual development into team synthesis.
