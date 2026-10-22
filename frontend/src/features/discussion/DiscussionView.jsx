import { useCallback, useRef, useState } from "react";
import { MessageSquare, Pencil, Reply, Trash2 } from "lucide-react";
import { messagesApi } from "../../api/messages";
import { useAsync } from "../../api/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useUndoDelete } from "../../components/useUndoDelete";
import { formatDateTime, relativeTime } from "../../format";
import { useWorkspace } from "../../workspace";
import { usePolling } from "../ai/usePolling";
import { SprintPicker } from "../sprints/SprintPicker";

const POLL_MS = 15000;

/** A discussion board per sprint (D-31): posts with one level of replies (CHAT-2). */
export function DiscussionView() {
  const { selectedSprint: sprint, sprints } = useWorkspace();
  if (!sprints.length) {
    return <EmptyState title="No sprints yet" body="Each sprint has its own discussion board. Create a sprint first." />;
  }
  return (
    <section className="panel view-panel discussion">
      <div className="section-heading">
        <PanelTitle icon={<MessageSquare size={16} />} title={sprint ? `${sprint.name} discussion` : "Discussion"} />
        <div className="discussion-picker">
          <SprintPicker label="Sprint" />
        </div>
      </div>
      {sprint && <Board key={sprint.id} sprintId={sprint.id} />}
    </section>
  );
}

function Board({ sprintId }) {
  const { version } = useWorkspace();
  const undoDelete = useUndoDelete();
  const messages = useAsync(() => messagesApi.list(sprintId), [sprintId, version]);
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const lastSeen = useRef(null);

  const posts = messages.data || [];
  const allTimes = posts.flatMap((post) => [post, ...post.replies]).flatMap((item) => [item.created_at, item.edited_at]).filter(Boolean);
  lastSeen.current = allTimes.sort().at(-1) || lastSeen.current;

  // Polls with ?since= and reloads the board only when something changed (CHAT-5).
  const reload = messages.reload;
  const poll = useCallback(async () => {
    if (!lastSeen.current) return reload();
    const changed = await messagesApi.list(sprintId, lastSeen.current).catch(() => []);
    if (changed.length) await reload();
  }, [sprintId, reload]);
  usePolling(true, poll, POLL_MS);

  async function submit(event) {
    event.preventDefault();
    if (!text.trim()) return;
    setError("");
    try {
      await messagesApi.create(sprintId, text);
      setText("");
      await reload();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <>
      <form className="comment-box new-post" onSubmit={submit}>
        <textarea value={text} onChange={(event) => setText(event.target.value)} placeholder="Start a topic for this sprint" aria-label="New post" />
        <button>Post</button>
      </form>
      <FormError message={error || messages.error} />
      {messages.data && posts.length === 0 && <p className="muted">No discussion for this sprint yet.</p>}
      <div className="posts">
        {posts.map((post) => (
          <Message
            key={post.id}
            message={post}
            sprintId={sprintId}
            onChanged={reload}
            onDeleted={(result) => undoDelete("post", result, reload)}
          >
            {post.replies.map((reply) => (
              <Message key={reply.id} message={reply} sprintId={sprintId} onChanged={reload} onDeleted={(result) => undoDelete("reply", result, reload)} />
            ))}
          </Message>
        ))}
      </div>
    </>
  );
}

function Message({ message, sprintId, onChanged, onDeleted, children }) {
  const { user } = useWorkspace();
  const [mode, setMode] = useState(null);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const isPost = !message.parent_message_id;
  const mine = message.author_id === user.id;

  async function act(action) {
    setError("");
    try {
      await action();
      setMode(null);
      setDraft("");
      await onChanged();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <article className={isPost ? "message post" : "message reply"}>
      <header>
        <strong>{message.author_name}</strong>
        <span className="muted" title={formatDateTime(message.created_at)}>
          {relativeTime(message.created_at)}
        </span>
        {message.edited_at && (
          <span className="muted" title={formatDateTime(message.edited_at)}>
            (edited)
          </span>
        )}
        <span className="message-actions">
          {isPost && (
            <button className="ghost-button compact" onClick={() => setMode(mode === "reply" ? null : "reply")}>
              <Reply size={13} /> Reply
            </button>
          )}
          {mine && (
            <>
              <button
                className="ghost-button compact"
                onClick={() => {
                  setDraft(message.text);
                  setMode(mode === "edit" ? null : "edit");
                }}
              >
                <Pencil size={13} /> Edit
              </button>
              <button
                className="ghost-button compact"
                onClick={async () => {
                  try {
                    const result = await messagesApi.remove(message.id);
                    await onChanged();
                    onDeleted(result);
                  } catch (err) {
                    setError(err.message);
                  }
                }}
              >
                <Trash2 size={13} /> Delete
              </button>
            </>
          )}
        </span>
      </header>
      {mode === "edit" ? (
        <form className="comment-box" onSubmit={(event) => (event.preventDefault(), act(() => messagesApi.update(message.id, draft)))}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} aria-label="Edit message" />
          <div className="button-row">
            <button type="button" className="secondary-button" onClick={() => setMode(null)}>
              Cancel
            </button>
            <button disabled={!draft.trim()}>Save</button>
          </div>
        </form>
      ) : (
        <RichText text={message.text} />
      )}
      <FormError message={error} />
      {children && <div className="replies">{children}</div>}
      {mode === "reply" && (
        <form className="comment-box reply-box" onSubmit={(event) => (event.preventDefault(), act(() => messagesApi.create(sprintId, draft, message.id)))}>
          <textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Write a reply" aria-label="Reply" autoFocus />
          <button disabled={!draft.trim()}>Reply</button>
        </form>
      )}
    </article>
  );
}

/** Plain text with line breaks kept, URLs linked and `code` in monospace (CHAT-6). */
function RichText({ text }) {
  const parts = text.split(/(`[^`\n]+`|https?:\/\/[^\s]+)/g);
  return (
    <p className="pre-wrap message-text">
      {parts.map((part, index) => {
        if (part.startsWith("`") && part.endsWith("`") && part.length > 2) return <code key={index}>{part.slice(1, -1)}</code>;
        if (/^https?:\/\//.test(part))
          return (
            <a key={index} href={part} target="_blank" rel="noreferrer">
              {part}
            </a>
          );
        return part;
      })}
    </p>
  );
}
