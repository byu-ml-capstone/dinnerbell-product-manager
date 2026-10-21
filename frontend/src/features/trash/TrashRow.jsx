import { useState } from "react";
import { FolderKanban, Link2, MessageSquare, RotateCcw, SquareKanban, StickyNote } from "lucide-react";
import { trashApi } from "../../api/trash";
import { describeCounts, formatDateTime } from "../../format";

const ICONS = { project: FolderKanban, sprint: SquareKanban, story: StickyNote, dependency: Link2, message: MessageSquare };
const TYPE_LABELS = { project: "Project", sprint: "Sprint", story: "Story", dependency: "Link", message: "Message" };

export function TrashRow({ item, onRestored }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const Icon = ICONS[item.root_type] || StickyNote;
  const extra = describeCounts(item.counts);

  async function restore() {
    setBusy(true);
    setError("");
    try {
      await trashApi.restore(item.batch_id);
      await onRestored(item);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <tr>
      <td>
        <span className="trash-type">
          <Icon size={15} /> {TYPE_LABELS[item.root_type] || item.root_type}
        </span>
      </td>
      <td>
        <strong>{item.root_label}</strong>
        {extra && <div className="muted">with {extra}</div>}
        {error && <div className="inline-error">{error}</div>}
      </td>
      <td>{item.deleted_by || "Unknown"}</td>
      <td>{formatDateTime(item.deleted_at)}</td>
      <td className="actions-cell">
        <button className="secondary-button compact" onClick={restore} disabled={busy}>
          <RotateCcw size={14} /> Restore
        </button>
      </td>
    </tr>
  );
}
