import { useDraggable } from "@dnd-kit/core";
import { Ban, GitBranch } from "lucide-react";
import { STATUSES } from "../../constants";

export function StoryCard({ story, memberName, onStatus, onOpen, readOnly = false, selectable = false, selected = false, onSelect }) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: story.id, disabled: readOnly });
  const style = transform ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` } : undefined;

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={`story-card status-${story.status}${isDragging ? " dragging" : ""}`}
      {...listeners}
      {...attributes}
    >
      <div className="card-top">
        {selectable && (
          <input
            type="checkbox"
            className="card-check"
            checked={selected}
            aria-label={`Select ${story.title}`}
            onChange={(event) => onSelect(story.id, event.target.checked)}
            onPointerDown={(event) => event.stopPropagation()}
          />
        )}
        <span className={`priority ${story.priority}`}>{story.priority}</span>
        {story.parent_story_id && <span className="tag">Subtask</span>}
        {story.carryover_count > 0 && (
          <span className="tag" title={`Carried over ${story.carryover_count}×`}>
            ↻{story.carryover_count}
          </span>
        )}
        {story.github_branch && (
          <span className="tag icon-tag" title={story.github_branch}>
            <GitBranch size={12} />
          </span>
        )}
      </div>
      <button className="story-main" onClick={() => onOpen(story.id)} onPointerDown={(event) => event.stopPropagation()}>
        <strong>{story.title}</strong>
        <small>
          {memberName || "Unassigned"}
          {story.story_points ? ` · ${story.story_points} pts` : ""}
          {story.subtask_count ? ` · ${story.subtask_count} subtask${story.subtask_count === 1 ? "" : "s"}` : ""}
        </small>
      </button>
      {(story.blocked_by.length > 0 || onStatus) && (
        <div className="card-actions">
          {story.blocked_by.length > 0 && (
            <span className="blocked-pill" title={`Blocked by: ${story.blocked_by_titles.join(", ")}`}>
              <Ban size={13} /> {story.all_blockers_done ? "blockers done" : `blocked by ${story.blocked_by.length}`}
            </span>
          )}
          {onStatus && (
            <select
              value={story.status}
              disabled={readOnly}
              aria-label={`Status of ${story.title}`}
              onChange={(event) => onStatus(story, event.target.value)}
              onPointerDown={(event) => event.stopPropagation()}
              onKeyDown={(event) => event.stopPropagation()}
            >
              {STATUSES.map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          )}
        </div>
      )}
    </article>
  );
}
