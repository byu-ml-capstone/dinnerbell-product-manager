import { Settings, Users } from "lucide-react";
import { PanelTitle } from "../../components/PanelTitle";
import { STATUSES } from "../../constants";
import { BurndownChart } from "../metrics/BurndownChart";
import { VelocityChart } from "../metrics/VelocityChart";
import { SprintPanel } from "../sprints/SprintPanel";
import { useWorkspace } from "../../workspace";

export function Dashboard({ summary, unfinishedCount }) {
  const { members } = useWorkspace();
  const counts = summary?.counts || {};
  return (
    <section className="dashboard">
      <div className="metric-strip">
        {STATUSES.map(([status, label]) => (
          <div className="metric" key={status}>
            <span>{label}</span>
            <strong>{counts[status] || 0}</strong>
          </div>
        ))}
      </div>
      <div className="dashboard-row">
        <SprintPanel unfinishedCount={unfinishedCount} />
        <BurndownChart />
        <VelocityChart />
        <div className="panel team-panel">
          <PanelTitle icon={<Users size={16} />} title="Team" />
          <div className="team-list">
            {members.map((member) => (
              <span key={member.id}>{member.name}</span>
            ))}
          </div>
          <p className="muted team-hint">
            <Settings size={12} /> Add or remove members in Settings.
          </p>
        </div>
      </div>
    </section>
  );
}
