import { Trash2 } from "lucide-react";
import { trashApi } from "../../api/trash";
import { useAsync } from "../../api/useAsync";
import { EmptyState } from "../../components/EmptyState";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { Spinner } from "../../components/Spinner";
import { useToast } from "../../components/Toast";
import { useWorkspace } from "../../workspace";
import { TrashRow } from "./TrashRow";

export function TrashView() {
  const { project, version, changed } = useWorkspace();
  const { show } = useToast();
  const trash = useAsync(() => trashApi.project(project.id), [project.id, version]);

  return (
    <section className="panel view-panel">
      <PanelTitle icon={<Trash2 size={16} />} title="Trash" />
      <p className="muted">Nothing is ever deleted for good. Restoring an item brings back everything that was deleted with it.</p>
      <FormError message={trash.error} />
      {trash.loading && !trash.data && <Spinner />}
      {trash.data?.length === 0 && <EmptyState title="Trash is empty" body="Deleted sprints, stories, links and messages show up here." />}
      {trash.data?.length > 0 && (
        <table className="data-table">
          <thead>
            <tr>
              <th>Type</th>
              <th>Item</th>
              <th>Deleted by</th>
              <th>When</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {trash.data.map((item) => (
              <TrashRow
                key={item.batch_id}
                item={item}
                onRestored={async (restored) => {
                  show(`Restored ${restored.root_label}`);
                  await changed();
                }}
              />
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
