import { useState } from "react";
import { Clock, Lock, Pencil, Plus, Trash2 } from "lucide-react";
import { sprintsApi } from "../../api/sprints";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { PanelTitle } from "../../components/PanelTitle";
import { useUndoDelete } from "../../components/useUndoDelete";
import { daysBetween, formatDay, isoDate, pluralize, sprintDates } from "../../format";
import { useWorkspace } from "../../workspace";
import { CloseSprintDialog } from "./CloseSprintDialog";
import { MoveUnfinishedDialog } from "./MoveUnfinishedDialog";
import { SprintBadge, SprintPicker } from "./SprintPicker";
import { SprintForm } from "./SprintForm";

function timing(sprint) {
  const today = isoDate(new Date());
  if (sprint.status === "closed") return `Closed ${formatDay(sprint.closed_at)}`;
  if (sprint.status === "planned") return `Starts in ${pluralize(daysBetween(today, sprint.start_date), "day")}`;
  if (sprint.is_overdue) return `Overdue by ${pluralize(daysBetween(sprint.end_date, today), "day")}`;
  return `${pluralize(daysBetween(today, sprint.end_date), "day")} left`;
}

export function SprintPanel({ unfinishedCount }) {
  const { selectedSprint: sprint, selectSprint, changed } = useWorkspace();
  const undoDelete = useUndoDelete();
  const [dialog, setDialog] = useState(null);

  return (
    <div className="panel">
      <PanelTitle icon={<Clock size={16} />} title="Sprint" />
      <SprintPicker />
      {sprint ? (
        <div className="sprint-header">
          <div className="sprint-header-line">
            <SprintBadge sprint={sprint} />
            <span>{sprintDates(sprint)}</span>
            <span className="muted">{timing(sprint)}</span>
          </div>
          <p className="muted">{sprint.goal || "No goal recorded."}</p>
          {sprint.capacity_warning && <p className="warning-line compact-warning">{sprint.capacity_warning}</p>}
          <div className="sprint-stats">
            <span>
              <strong>{sprint.planned_points}</strong> pts planned
            </span>
            <span>
              <strong>{sprint.completed_points}</strong> done
            </span>
            {sprint.status === "closed" && (
              <span>
                <strong>{sprint.velocity}</strong> velocity
              </span>
            )}
          </div>
          <div className="button-row">
            {sprint.status !== "closed" && (
              <>
                <button className="secondary-button compact" onClick={() => setDialog("edit")}>
                  <Pencil size={14} /> Edit
                </button>
                <button className="compact" onClick={() => setDialog("close")}>
                  <Lock size={14} /> Close
                </button>
              </>
            )}
            <button className="secondary-button compact" onClick={() => setDialog("delete")} title="Delete sprint">
              <Trash2 size={14} /> Delete
            </button>
          </div>
        </div>
      ) : (
        <p className="muted">No sprints yet.</p>
      )}
      <button className="secondary-button wide-button new-sprint" onClick={() => setDialog("new")}>
        <Plus size={16} /> New Sprint
      </button>

      {dialog === "new" && (
        <SprintForm
          onClose={() => setDialog(null)}
          onSaved={async (created) => {
            await changed();
            selectSprint(created.id);
          }}
        />
      )}
      {dialog === "edit" && <SprintForm sprint={sprint} onClose={() => setDialog(null)} onSaved={changed} />}
      {dialog === "close" && (
        <CloseSprintDialog
          sprint={sprint}
          unfinishedCount={unfinishedCount}
          onClose={() => setDialog(null)}
          onClosed={changed}
          onMoveUnfinished={() => setDialog("move")}
        />
      )}
      {dialog === "move" && <MoveUnfinishedDialog sprint={sprint} onClose={() => setDialog(null)} />}
      {dialog === "delete" && (
        <ConfirmDialog
          title={`Delete ${sprint.name}?`}
          body={
            <p>
              {sprint.story_count > 0 ? (
                <>
                  This will also delete <strong>{pluralize(sprint.story_count, "story")}</strong> in this sprint, with their subtasks,
                  comments and links.
                </>
              ) : (
                "This sprint has no stories."
              )}{" "}
              You can restore it from Trash.
            </p>
          }
          confirmLabel="Delete sprint"
          danger
          onCancel={() => setDialog(null)}
          onConfirm={async () => {
            const result = await sprintsApi.remove(sprint.id);
            setDialog(null);
            await changed();
            undoDelete(sprint.name, result, changed);
          }}
        />
      )}
    </div>
  );
}
