import { BarChart3 } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Legend, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { metricsApi } from "../../api/metrics";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { useWorkspace } from "../../workspace";

/** Committed vs completed points for the last 6 closed sprints, with the 3-sprint average (VEL-5). */
export function VelocityChart() {
  const { project, version } = useWorkspace();
  const velocity = useAsync(() => metricsApi.velocity(project.id), [project.id, version]);
  const sprints = velocity.data?.sprints || [];
  const average = velocity.data?.average_velocity_3;

  return (
    <div className="panel">
      <PanelTitle icon={<BarChart3 size={16} />} title="Velocity">
        {average != null && <span className="panel-note">avg {average} pts</span>}
      </PanelTitle>
      <FormError message={velocity.error} />
      {sprints.length === 0 ? (
        <p className="muted">Velocity appears after closing a sprint.</p>
      ) : (
        <div className="chart-box">
          <ResponsiveContainer width="100%" height={190}>
            <BarChart data={sprints} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
              <Bar isAnimationActive={false} dataKey="committed_points" name="Committed" fill="#c8c8c8" radius={[3, 3, 0, 0]} />
              <Bar isAnimationActive={false} dataKey="velocity" name="Completed" fill="#0a0a0a" radius={[3, 3, 0, 0]} />
              {average != null && <ReferenceLine y={average} stroke="#707070" strokeDasharray="5 4" />}
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
