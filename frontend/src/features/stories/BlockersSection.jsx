import { useState } from "react";
import { Ban } from "lucide-react";
import { dependenciesApi } from "../../api/dependencies";
import { storiesApi } from "../../api/stories";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useToast } from "../../components/Toast";
import { useUndoDelete } from "../../components/useUndoDelete";
import { STATUS_LABELS } from "../../constants";
import { useWorkspace } from "../../workspace";

/** Blockers are added and removed only from story detail; the graph is read-only (DEP-7). */
export function BlockersSection({ story }) {
  const { project, version, changed, openStory } = useWorkspace();
  const { warn } = useToast();
  const undoDelete = useUndoDelete();
  const stories = useAsync(() => storiesApi.list(project.id), [project.id, version]);
  const [blockerId, setBlockerId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");

  const existing = new Set(story.blocked_by);
  const candidates = (stories.data || []).filter((item) => item.id !== story.id && !existing.has(item.id));

  async function add(event) {
    event.preventDefault();
    if (!blockerId) return;
    setError("");
    try {
      const result = await dependenciesApi.add(blockerId, story.id, reason.trim());
      warn(result.warnings);
      setBlockerId("");
      setReason("");
      await changed();
    } catch (err) {
      setError(err.message);
    }
  }

  async function remove(link) {
    setError("");
    try {
      const result = await dependenciesApi.remove(link.blocker_story_id, story.id);
      await changed();
      undoDelete(`link to ${link.blocker_title}`, result, changed);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="drawer-section">
      <PanelTitle icon={<Ban size={16} />} title="Blocked by" />
      {story.blocked_by_links.length === 0 && <p className="muted">Nothing blocks this story.</p>}
      {story.blocked_by_links.map((link) => (
        <div className="dependency" key={link.id}>
          <button className="link-button" onClick={() => openStory(link.blocker_story_id)}>
            {link.blocker_title}
          </button>
          <span className={`status-tag status-${link.blocker_status}`}>{STATUS_LABELS[link.blocker_status]}</span>
          <small>{link.reason || "No reason given"}</small>
          <button className="secondary-button compact" onClick={() => remove(link)}>
            Remove
          </button>
        </div>
      ))}
      {story.blocks.length > 0 && (
        <p className="muted blocks-line">
          Blocks:{" "}
          {story.blocks.map((link, index) => (
            <span key={link.id}>
              {index > 0 && ", "}
              <button className="link-button" onClick={() => openStory(link.blocked_story_id)}>
                {link.blocked_title}
              </button>
            </span>
          ))}
        </p>
      )}
      <form className="stack-form" onSubmit={add}>
        <select value={blockerId} onChange={(event) => setBlockerId(event.target.value)} aria-label="Add blocker">
          <option value="">Add blocker…</option>
          {candidates.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
        {blockerId && (
          <div className="inline-form">
            <input value={reason} onChange={(event) => setReason(event.target.value)} placeholder="Reason (optional)" />
            <button>Add</button>
          </div>
        )}
      </form>
      <FormError message={error} />
    </section>
  );
}
