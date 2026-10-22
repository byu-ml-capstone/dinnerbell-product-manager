"""Dependency rules shared by the graph view, dependency endpoints and moves (DEP-4, DEP-8, BUG-6)."""

from sqlalchemy.orm import Session, selectinload

from ..models import Dependency, Story
from ..schemas.graph import DependencyGraph, GraphEdge, GraphNode


def project_links(db: Session, project_id: str) -> list[Dependency]:
    return (
        db.query(Dependency)
        .join(Story, Story.id == Dependency.blocked_story_id)
        .filter(Story.project_id == project_id)
        .all()
    )


def find_cycle(db: Session, project_id: str, blocker_id: str, blocked_id: str) -> list[str] | None:
    """Story ids [blocker, blocked, ..., blocker] if adding blocker -> blocked would close a loop."""
    adjacency: dict[str, list[str]] = {}
    for link in project_links(db, project_id):
        adjacency.setdefault(link.blocker_story_id, []).append(link.blocked_story_id)
    stack = [(blocked_id, [blocked_id])]
    seen = set()
    while stack:
        node, path = stack.pop()
        if node == blocker_id:
            return [blocker_id, *path]
        if node in seen:
            continue
        seen.add(node)
        for nxt in adjacency.get(node, []):
            stack.append((nxt, [*path, nxt]))
    return None


def order_warning(blocker: Story, blocked: Story) -> bool:
    """The blocked story is planned before an unfinished blocker (DEP-8)."""
    if blocked.sprint is None or blocker.status == "done":
        return False
    if blocker.sprint is None:
        return True
    return blocker.sprint.start_date > blocked.sprint.start_date


def order_warning_message(blocker: Story, blocked: Story) -> str:
    if blocker.sprint is None:
        return f"'{blocked.title}' is blocked by '{blocker.title}', which is in the backlog"
    return f"'{blocked.title}' is blocked by '{blocker.title}', which is planned for a later sprint ({blocker.sprint.name})"


def warnings_for(stories: list[Story]) -> list[str]:
    messages: list[str] = []
    for story in stories:
        for link in story.blocked_by_links:
            if order_warning(link.blocker, story):
                messages.append(order_warning_message(link.blocker, story))
        for link in story.blocks:
            if order_warning(story, link.blocked):
                messages.append(order_warning_message(story, link.blocked))
    return list(dict.fromkeys(messages))


def build_graph(db: Session, project_id: str, sprint_filter: str | None, include_done: bool) -> DependencyGraph:
    links = (
        db.query(Dependency)
        .options(
            selectinload(Dependency.blocker).selectinload(Story.sprint),
            selectinload(Dependency.blocker).selectinload(Story.assignee),
            selectinload(Dependency.blocked).selectinload(Story.sprint),
            selectinload(Dependency.blocked).selectinload(Story.assignee),
        )
        .join(Story, Story.id == Dependency.blocked_story_id)
        .filter(Story.project_id == project_id)
        .all()
    )
    links = [link for link in links if link.blocker is not None and link.blocked is not None]

    def in_filter(story: Story) -> bool:
        if sprint_filter is None or sprint_filter == "all":
            return True
        if sprint_filter == "backlog":
            return story.sprint_id is None
        return story.sprint_id == sprint_filter

    if sprint_filter not in (None, "all"):
        # Stories in the chosen sprint plus their direct blockers and dependents (DEP-11).
        links = [link for link in links if in_filter(link.blocker) or in_filter(link.blocked)]
    if not include_done:
        links = [link for link in links if link.blocker.status != "done" and link.blocked.status != "done"]

    nodes: dict[str, Story] = {}
    for link in links:
        nodes[link.blocker.id] = link.blocker
        nodes[link.blocked.id] = link.blocked

    return DependencyGraph(
        nodes=[
            GraphNode(
                id=story.id,
                title=story.title,
                status=story.status,
                priority=story.priority,
                story_points=story.story_points,
                assignee_name=story.assignee.name if story.assignee else None,
                sprint_id=story.sprint_id,
                sprint_name=story.sprint.name if story.sprint else None,
                is_subtask=story.parent_story_id is not None,
            )
            for story in sorted(nodes.values(), key=lambda item: item.id)
        ],
        edges=[
            GraphEdge(
                id=link.id,
                source=link.blocker_story_id,
                target=link.blocked_story_id,
                reason=link.reason,
                order_warning=order_warning(link.blocker, link.blocked),
            )
            for link in sorted(links, key=lambda item: item.id)
        ],
    )
