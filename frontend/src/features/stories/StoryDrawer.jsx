import { useEffect, useState } from "react";
import { AlertTriangle, Check, CircleDot, History, Lock, MessageSquare, Pencil, Trash2, X } from "lucide-react";
import { storiesApi } from "../../api/stories";
import { useAsync } from "../../api/useAsync";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { Spinner } from "../../components/Spinner";
import { useUndoDelete } from "../../components/useUndoDelete";
import { POINTS, STATUS_LABELS } from "../../constants";
import { describeCounts, formatDate, relativeTime } from "../../format";
import { useWorkspace } from "../../workspace";
import { BlockersSection } from "./BlockersSection";
import { BranchSection } from "./BranchSection";
import { MoveOutForm, StoryEditForm } from "./StoryEditForm";

/** Story detail lives in a side drawer (UI-7). `overlay` floats it over views that have no drawer column. */
export function StoryDrawer({ overlay = false }) {
  const { storyId, closeStory } = useWorkspace();
  if (!storyId) {
    if (overlay) return null;
    return (
      <aside className="drawer placeholder">
        <CircleDot size={20} /> Select a story to inspect details.
      </aside>
    );
  }
  return (
    <aside className={overlay ? "drawer drawer-overlay" : "drawer"}>
      <button className="drawer-close ghost-button compact" onClick={closeStory} aria-label="Close story">
        <X size={16} /> Close
      </button>
      <StoryDetail key={storyId} storyId={storyId} />
    </aside>
  );
}

function StoryDetail({ storyId }) {
  const { version, changed, closeStory, openStory, members } = useWorkspace();
  const undoDelete = useUndoDelete();
  const story = useAsync(() => storiesApi.get(storyId), [storyId, version]);
  const [mode, setMode] = useState("view");
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (story.error && /not found/i.test(story.error)) closeStory();
  }, [story.error, closeStory]);

  if (!story.data) return story.error ? <FormError message={story.error} /> : <Spinner />;
  const data = story.data;
  const memberName = (id) => members.find((member) => member.id === id)?.name;
  const readOnly = data.sprint_closed;

  return (
    <>
      <div className="drawer-tags">
        <span className={`priority ${data.priority}`}>{data.priority}</span>
        <span className={`status-tag status-${data.status}`}>{STATUS_LABELS[data.status]}</span>
        {data.parent_story_id && (
          <button className="link-button" onClick={() => openStory(data.parent_story_id)}>
            Subtask of {data.parent_title}
          </button>
        )}
      </div>
      <h3>{data.title}</h3>

      {readOnly && (
        <p className="note-line">
          <Lock size={14} /> In a closed sprint ({data.sprint_name}).{" "}
          {data.status === "done" ? "Done stories stay where they were finished." : "It can only be moved out."}
        </p>
      )}
      {data.warnings.map((warning) => (
        <p key={warning} className="warning-line">
          <AlertTriangle size={14} /> {warning}
        </p>
      ))}
      {data.status === "blocked" && data.all_blockers_done && !readOnly && (
        <p className="hint-line">
          All blockers done.{" "}
          <button
            className="link-button"
            onClick={async () => {
              await storiesApi.update(data.id, { status: "selected" });
              await changed();
            }}
          >
            Unblock?
          </button>
        </p>
      )}

      {mode === "edit" && <StoryEditForm story={data} onDone={() => setMode("view")} />}
      {mode === "move" && <MoveOutForm story={data} onDone={() => setMode("view")} />}
      {mode === "view" && (
        <>
          <div className="button-row drawer-actions">
            {!readOnly && (
              <button className="secondary-button compact" onClick={() => setMode("edit")}>
                <Pencil size={14} /> Edit
              </button>
            )}
            {readOnly && data.status !== "done" && (
              <button className="secondary-button compact" onClick={() => setMode("move")}>
                Move out…
              </button>
            )}
            {!readOnly && (
              <button className="secondary-button compact" onClick={() => setConfirmDelete(true)}>
                <Trash2 size={14} /> Delete
              </button>
            )}
          </div>
          <p className="description">{data.description || <span className="muted">No description.</span>}</p>
          <dl className="details">
            <div>
              <dt>Assignee</dt>
              <dd>{memberName(data.assignee_id) || "Unassigned"}</dd>
            </div>
            <div>
              <dt>Points</dt>
              <dd>{data.story_points || "None"}</dd>
            </div>
            <div>
              <dt>Sprint</dt>
              <dd>{data.sprint_name || "Backlog"}</dd>
            </div>
            <div>
              <dt>Due</dt>
              <dd>{data.due_date ? formatDate(data.due_date) : "No date"}</dd>
            </div>
          </dl>
          {data.acceptance_criteria && (
            <div className="note">
              <strong>Acceptance criteria</strong>
              <p className="pre-wrap">{data.acceptance_criteria}</p>
            </div>
          )}
          {data.sprint_history.length > 0 && (
            <p className="history-line">
              <History size={14} /> {data.sprint_history.map((entry) => entry.sprint_name).join(" → ")}
              {data.carryover_count > 0 && ` (carried over ${data.carryover_count}×)`}
            </p>
          )}
        </>
      )}

      <BranchSection story={data} readOnly={readOnly} />
      <BlockersSection story={data} />
      <SubtasksSection story={data} readOnly={readOnly || Boolean(data.parent_story_id)} />
      <CommentsSection story={data} />

      {confirmDelete && (
        <ConfirmDialog
          title={`Delete “${data.title}”?`}
          body={
            <p>
              {describeCounts({ stories: data.subtasks.length, comments: data.comments.length }) ? (
                <>This also deletes {describeCounts({ stories: data.subtasks.length, comments: data.comments.length })}. </>
              ) : null}
              You can restore it from Trash.
            </p>
          }
          confirmLabel="Delete story"
          danger
          onCancel={() => setConfirmDelete(false)}
          onConfirm={async () => {
            const result = await storiesApi.remove(data.id);
            setConfirmDelete(false);
            closeStory();
            await changed();
            undoDelete(`“${data.title}”`, result, changed);
          }}
        />
      )}
    </>
  );
}

function SubtasksSection({ story, readOnly }) {
  const { changed, openStory } = useWorkspace();
  const [title, setTitle] = useState("");
  const [points, setPoints] = useState("");
  const [error, setError] = useState("");

  async function add(event) {
    event.preventDefault();
    if (!title.trim()) return;
    setError("");
    try {
      await storiesApi.createSubtask(story.id, { title, story_points: points ? Number(points) : null });
      setTitle("");
      setPoints("");
      await changed();
    } catch (err) {
      setError(err.message);
    }
  }

  if (story.parent_story_id) return null;
  return (
    <section className="drawer-section">
      <PanelTitle icon={<Check size={16} />} title="Subtasks" />
      {story.subtasks.length === 0 && <p className="muted">No subtasks.</p>}
      {story.subtasks.map((subtask) => (
        <button key={subtask.id} className="subtask" onClick={() => openStory(subtask.id)}>
          <span className="subtask-title">{subtask.title}</span>
          <span className={`status-tag status-${subtask.status}`}>{STATUS_LABELS[subtask.status]}</span>
          {subtask.sprint_id !== story.sprint_id && <small className="muted">in another sprint</small>}
        </button>
      ))}
      {!readOnly && (
        <form className="inline-form" onSubmit={add}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="New subtask" aria-label="New subtask" />
          <select value={points} onChange={(event) => setPoints(event.target.value)} aria-label="Subtask points" className="points-select">
            <option value="">Pts</option>
            {POINTS.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
          <button>Add</button>
        </form>
      )}
      <FormError message={error} />
    </section>
  );
}

function CommentsSection({ story }) {
  const { changed } = useWorkspace();
  const [text, setText] = useState("");
  const [error, setError] = useState("");

  return (
    <section className="drawer-section">
      <PanelTitle icon={<MessageSquare size={16} />} title="Comments" />
      {story.comments.map((comment) => (
        <div className="comment" key={comment.id}>
          <strong>{comment.author_name}</strong> <span className="muted">{relativeTime(comment.created_at)}</span>
          <p className="pre-wrap">{comment.text}</p>
        </div>
      ))}
      <form
        className="comment-box"
        onSubmit={async (event) => {
          event.preventDefault();
          if (!text.trim()) return;
          setError("");
          try {
            await storiesApi.addComment(story.id, text);
            setText("");
            await changed();
          } catch (err) {
            setError(err.message);
          }
        }}
      >
        <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Add progress, context, or blocker notes" />
        <button>Comment</button>
      </form>
      <FormError message={error} />
    </section>
  );
}
