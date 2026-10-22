from pydantic import BaseModel


class GraphNode(BaseModel):
    id: str
    title: str
    status: str
    priority: str
    story_points: int | None
    assignee_name: str | None
    sprint_id: str | None
    sprint_name: str | None
    is_subtask: bool


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    reason: str
    order_warning: bool


class DependencyGraph(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
