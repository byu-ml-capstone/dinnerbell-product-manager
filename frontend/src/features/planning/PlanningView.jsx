import { useState } from "react";
import { DndContext, KeyboardSensor, PointerSensor, useDroppable, useSensor, useSensors } from "@dnd-kit/core";
import { CalendarRange, Plus } from "lucide-react";
import { projectsApi } from "../../api/projects";
import { storiesApi } from "../../api/stories";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { Spinner } from "../../components/Spinner";
import { useToast } from "../../components/Toast";
import { pluralize, sprintDates } from "../../format";
import { useWorkspace } from "../../workspace";
import { StoryCard } from "../board/StoryCard";
import { MoveUnfinishedDialog } from "../sprints/MoveUnfinishedDialog";
import { SprintBadge } from "../sprints/SprintPicker";
import { SprintForm } from "../sprints/SprintForm";
import { StoryDrawer } from "../stories/StoryDrawer";
import { StoryFormButton } from "../stories/StoryForm";

const BACKLOG = "backlog";

/** Backlog and every planned or active sprint side by side, with drag and drop (MOVE-5). */
export function PlanningView() {
  const { project, version, changed, openStory, members, sprints } = useWorkspace();
  const { show, warn } = useToast();
  const planning = useAsync(() => projectsApi.planning(project.id), [project.id, version]);
  const [selected, setSelected] = useState(new Set());
  const [target, setTarget] = useState(BACKLOG);
  const [error, setError] = useState("");
  const [dialog, setDialog] = useState(null);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 8 } }), useSensor(KeyboardSensor));
  const memberName = (id) => members.find((member) => member.id === id)?.name;

  const data = planning.data;
  const columns = data
    ? [{ id: BACKLOG, title: "Backlog", stories: data.backlog }, ...data.sprints.map((item) => ({ id: item.sprint.id, sprint: item.sprint, stories: item.stories, warning: item.capacity_warning }))]
    : [];
  const columnOf = (storyId) => columns.find((column) => column.stories.some((story) => story.id === storyId))?.id;

  async function move(storyIds, columnId) {
    setError("");
    try {
      const result = await storiesApi.move(project.id, storyIds, columnId === BACKLOG ? null : columnId);
      warn(result.warnings);
      setSelected(new Set());
      await changed();
    } catch (err) {
      setError(err.message);
    }
  }

  function handleDragEnd(event) {
    const storyId = event.active?.id;
    const columnId = event.over?.id;
    if (storyId && columnId && columnOf(storyId) !== columnId) move([storyId], columnId);
  }

  function toggle(storyId, checked) {
    const next = new Set(selected);
    if (checked) next.add(storyId);
    else next.delete(storyId);
    setSelected(next);
  }

  return (
    <>
      <section className="planning-view">
        <div className="section-heading">
          <PanelTitle icon={<CalendarRange size={18} />} title="Planning" />
          <div className="button-row">
            {selected.size > 0 && (
              <>
                <span className="muted">{pluralize(selected.size, "story")} selected</span>
                <select value={target} onChange={(event) => setTarget(event.target.value)} aria-label="Move selected to">
                  {columns.map((column) => (
                    <option key={column.id} value={column.id}>
                      {column.title || column.sprint.name}
                    </option>
                  ))}
                </select>
                <button onClick={() => move([...selected], target)}>Move selected</button>
              </>
            )}
            <StoryFormButton defaultSprintId="" />
          </div>
        </div>
        <FormError message={error || planning.error} />
        {data?.closed_with_unfinished.length > 0 && (
          <div className="closed-strip">
            <strong>Closed sprints with unfinished work:</strong>
            {data.closed_with_unfinished.map((item) => (
              <span key={item.sprint.id} className="closed-chip">
                {item.sprint.name} · {pluralize(item.unfinished_count, "unfinished story")}
                <button className="link-button" onClick={() => setDialog({ type: "move", sprint: item.sprint })}>
                  Move unfinished…
                </button>
              </span>
            ))}
          </div>
        )}
        {!data && planning.loading && <Spinner />}
        {data && (
          <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
            <div className="planning-columns">
              {columns.map((column) => (
                <PlanningColumn key={column.id} column={column}>
                  {column.stories.length === 0 && <p className="muted column-empty">Drop stories here.</p>}
                  {column.stories.map((story) => (
                    <StoryCard
                      key={story.id}
                      story={story}
                      memberName={memberName(story.assignee_id)}
                      onOpen={openStory}
                      selectable
                      selected={selected.has(story.id)}
                      onSelect={toggle}
                    />
                  ))}
                </PlanningColumn>
              ))}
              <button className="new-sprint-column secondary-button" onClick={() => setDialog({ type: "sprint" })}>
                <Plus size={16} /> New sprint
              </button>
            </div>
          </DndContext>
        )}
        {sprints.length === 0 && data && <p className="muted">Create a sprint to start planning. Give it a future start date to plan ahead.</p>}
      </section>
      <StoryDrawer overlay />
      {dialog?.type === "sprint" && (
        <SprintForm
          onClose={() => setDialog(null)}
          onSaved={async (created) => {
            show(`Created ${created.name}`);
            await changed();
          }}
        />
      )}
      {dialog?.type === "move" && <MoveUnfinishedDialog sprint={dialog.sprint} onClose={() => setDialog(null)} />}
    </>
  );
}

function PlanningColumn({ column, children }) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const sprint = column.sprint;
  return (
    <section ref={setNodeRef} className={isOver ? "column planning-column over" : "column planning-column"}>
      <header className="planning-header">
        <div>
          <h3>{sprint ? sprint.name : column.title}</h3>
          {sprint && <small className="muted">{sprintDates(sprint)}</small>}
        </div>
        {sprint && <SprintBadge sprint={sprint} />}
      </header>
      <p className="column-meta">
        {pluralize(column.stories.length, "story")}
        {sprint && ` · ${sprint.planned_points} pts planned`}
      </p>
      {column.warning && <p className="warning-line compact-warning">{column.warning}</p>}
      <div className="cards">{children}</div>
    </section>
  );
}
