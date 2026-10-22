import { useState } from "react";
import { DndContext, KeyboardSensor, PointerSensor, useSensor, useSensors } from "@dnd-kit/core";
import { Columns3, Lock } from "lucide-react";
import { projectsApi } from "../../api/projects";
import { sprintsApi } from "../../api/sprints";
import { storiesApi } from "../../api/stories";
import { useAsync } from "../../api/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useToast } from "../../components/Toast";
import { STATUSES } from "../../constants";
import { useWorkspace } from "../../workspace";
import { AiPanel } from "../ai/AiPanel";
import { MoveUnfinishedDialog } from "../sprints/MoveUnfinishedDialog";
import { StoryDrawer } from "../stories/StoryDrawer";
import { StoryFormButton } from "../stories/StoryForm";
import { BoardColumn } from "./BoardColumn";
import { Dashboard } from "./Dashboard";

export function BoardView() {
  const { project, selectedSprint: sprint, version, changed, openStory, members } = useWorkspace();
  const { warn } = useToast();
  const summary = useAsync(() => projectsApi.summary(project.id), [project.id, version]);
  const board = useAsync(() => (sprint ? sprintsApi.board(sprint.id) : Promise.resolve(null)), [sprint?.id, version]);
  const [error, setError] = useState("");
  const [moving, setMoving] = useState(false);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }), useSensor(KeyboardSensor));

  // Ignore a board that belongs to the previously selected sprint while the new one loads.
  const columns = board.data && sprint && board.data.sprint_id === sprint.id ? board.data.columns : null;
  const readOnly = Boolean(board.data?.read_only);
  const allStories = columns ? Object.values(columns).flat() : [];
  const unfinishedCount = allStories.filter((story) => story.sprint_id && !story.parent_story_id && story.status !== "done").length;
  const memberName = (id) => members.find((member) => member.id === id)?.name;

  async function moveStory(story, status) {
    if (!sprint || readOnly) return;
    setError("");
    const payload = { status };
    // Dropping a backlog story into a status column puts it in this sprint; the Backlog column takes it out.
    if (status === "backlog" && story.sprint_id) payload.sprint_id = null;
    if (status !== "backlog" && !story.sprint_id) payload.sprint_id = sprint.id;
    if (!("sprint_id" in payload) && story.status === status) return;
    try {
      const result = await storiesApi.update(story.id, payload);
      warn(result.warnings);
      await changed();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleDragEnd(event) {
    const story = allStories.find((item) => item.id === event.active?.id);
    const status = event.over?.id;
    if (story && STATUSES.some(([key]) => key === status)) moveStory(story, status);
  }

  return (
    <>
      <Dashboard summary={summary.data} unfinishedCount={unfinishedCount} />
      <section className="main-grid">
        <div className="board-panel">
          <div className="section-heading">
            <PanelTitle icon={<Columns3 size={18} />} title={sprint ? `${sprint.name} board` : "Sprint Board"} />
            <div className="button-row">
              {readOnly && unfinishedCount > 0 && (
                <button className="secondary-button" onClick={() => setMoving(true)}>
                  Move unfinished stories…
                </button>
              )}
              <StoryFormButton />
            </div>
          </div>
          {readOnly && (
            <p className="note-line">
              <Lock size={14} /> This sprint is closed. Its board is read-only; unfinished stories can be moved out.
            </p>
          )}
          <FormError message={error || board.error} />
          {sprint ? (
            <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
              <div className="board">
                {STATUSES.map(([status, label]) => (
                  <BoardColumn
                    key={status}
                    id={status}
                    label={label}
                    stories={columns?.[status] || []}
                    memberName={memberName}
                    onStatus={moveStory}
                    onOpen={openStory}
                    readOnly={readOnly}
                  />
                ))}
              </div>
            </DndContext>
          ) : (
            <EmptyState title="No sprint yet" body="Create a sprint to start planning the board." />
          )}
        </div>
        <StoryDrawer />
      </section>
      <AiPanel />
      {moving && sprint && <MoveUnfinishedDialog sprint={sprint} onClose={() => setMoving(false)} />}
    </>
  );
}
