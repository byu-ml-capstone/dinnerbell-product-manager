import { useMemo, useState } from "react";
import dagre from "@dagrejs/dagre";
import { BaseEdge, Background, Controls, Handle, MarkerType, Position, ReactFlow, getSmoothStepPath } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Network } from "lucide-react";
import { dependenciesApi } from "../../api/dependencies";
import { useAsync } from "../../api/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { STATUSES, STATUS_LABELS } from "../../constants";
import { useWorkspace } from "../../workspace";
import { StoryDrawer } from "../stories/StoryDrawer";

const NODE_WIDTH = 220;
const NODE_HEIGHT = 74;

/** Left-to-right dagre layout. Nodes are sorted first so positions stay stable between changes. */
function layout(graph) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "LR", nodesep: 30, ranksep: 70 });
  g.setDefaultEdgeLabel(() => ({}));
  graph.nodes.forEach((node) => g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  graph.edges.forEach((edge) => g.setEdge(edge.source, edge.target));
  dagre.layout(g);
  return graph.nodes.map((node) => {
    const position = g.node(node.id);
    return {
      id: node.id,
      type: "story",
      position: { x: position.x - NODE_WIDTH / 2, y: position.y - NODE_HEIGHT / 2 },
      data: node,
      draggable: false,
      connectable: false,
    };
  });
}

function StoryNode({ data }) {
  return (
    <div className={`graph-node status-${data.status}${data.is_subtask ? " subtask-node" : ""}`} title={`${data.title} (${STATUS_LABELS[data.status]})`}>
      <Handle type="target" position={Position.Left} isConnectable={false} />
      <strong>{data.title}</strong>
      <small>
        {data.assignee_name || "Unassigned"} · {data.sprint_name || "Backlog"}
      </small>
      <Handle type="source" position={Position.Right} isConnectable={false} />
    </div>
  );
}

/** Shows the reason as a native hover tooltip (DEP-12). */
function ReasonEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, markerEnd, style, data }) {
  const [path] = getSmoothStepPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  return (
    <g>
      <title>{data?.reason || "No reason given"}</title>
      <BaseEdge id={id} path={path} markerEnd={markerEnd} style={style} />
    </g>
  );
}

const nodeTypes = { story: StoryNode };
const edgeTypes = { reason: ReasonEdge };

/** Read-only graph of blocking links; it fills in as dependencies are added (D-27, DEP-7). */
export function GraphView() {
  const { project, sprints, version, openStory } = useWorkspace();
  const [sprintFilter, setSprintFilter] = useState("all");
  const [hideDone, setHideDone] = useState(false);
  const graph = useAsync(
    () => dependenciesApi.graph(project.id, { sprintId: sprintFilter === "all" ? undefined : sprintFilter, includeDone: !hideDone }),
    [project.id, sprintFilter, hideDone, version],
  );

  const { nodes, edges } = useMemo(() => {
    if (!graph.data) return { nodes: [], edges: [] };
    return {
      nodes: layout(graph.data),
      edges: graph.data.edges.map((edge) => ({
        id: edge.id,
        source: edge.source,
        target: edge.target,
        type: "reason",
        data: { reason: edge.reason },
        markerEnd: { type: MarkerType.ArrowClosed, color: edge.order_warning ? "#c62828" : "#0a0a0a" },
        style: edge.order_warning ? { stroke: "#c62828", strokeDasharray: "6 4", strokeWidth: 2 } : { stroke: "#0a0a0a", strokeWidth: 1.5 },
      })),
    };
  }, [graph.data]);

  return (
    <>
      <section className="panel view-panel">
        <div className="section-heading">
          <PanelTitle icon={<Network size={16} />} title="Dependency graph" />
          <div className="button-row">
            <select value={sprintFilter} onChange={(event) => setSprintFilter(event.target.value)} aria-label="Filter by sprint">
              <option value="all">All sprints</option>
              <option value="backlog">Backlog</option>
              {sprints.map((sprint) => (
                <option key={sprint.id} value={sprint.id}>
                  {sprint.name}
                </option>
              ))}
            </select>
            <label className="checkbox-label">
              <input type="checkbox" checked={hideDone} onChange={(event) => setHideDone(event.target.checked)} /> Hide done
            </label>
          </div>
        </div>
        <div className="graph-legend">
          {STATUSES.map(([key, label]) => (
            <span key={key} className={`legend-item status-${key}`}>
              {label}
            </span>
          ))}
          <span className="legend-item warning-edge">Planned before its blocker</span>
          <span className="legend-item subtask-node">Subtask</span>
        </div>
        <FormError message={graph.error} />
        {graph.data && nodes.length === 0 ? (
          <EmptyState title="No dependencies yet" body="Add a blocker from a story to see it here." />
        ) : (
          <div className="graph-canvas">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onNodeClick={(_event, node) => openStory(node.id)}
              nodesDraggable={false}
              nodesConnectable={false}
              elementsSelectable={false}
              fitView
              fitViewOptions={{ padding: 0.2, maxZoom: 1 }}
              proOptions={{ hideAttribution: true }}
            >
              <Background gap={18} color="#e2e2e2" />
              <Controls showInteractive={false} />
            </ReactFlow>
          </div>
        )}
      </section>
      <StoryDrawer overlay />
    </>
  );
}
