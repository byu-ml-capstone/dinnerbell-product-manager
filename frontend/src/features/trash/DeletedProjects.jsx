import { trashApi } from "../../api/trash";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { Modal } from "../../components/Modal";
import { Spinner } from "../../components/Spinner";
import { TrashRow } from "./TrashRow";

/** Deleted projects can't show their own Trash tab, so they're listed here (DEL-8). */
export function DeletedProjects({ onClose, onRestored }) {
  const deleted = useAsync(() => trashApi.deletedProjects(), []);
  return (
    <Modal title="Deleted projects" onClose={onClose} wide>
      <FormError message={deleted.error} />
      {deleted.loading && !deleted.data && <Spinner />}
      {deleted.data?.length === 0 && <p className="muted">No deleted projects.</p>}
      {deleted.data?.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Project</th>
              <th>Deleted by</th>
              <th>When</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {deleted.data.map((item) => (
              <TrashRow
                key={item.batch_id}
                item={item}
                onRestored={async (restored) => {
                  await onRestored(restored.root_id);
                  onClose();
                }}
              />
            ))}
          </tbody>
        </table>
      )}
    </Modal>
  );
}
