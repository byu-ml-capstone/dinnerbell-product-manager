import { TrendingDown } from "lucide-react";
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { metricsApi } from "../../api/metrics";
import { useAsync } from "../../api/useAsync";
import { FormError } from "../../components/ErrorBanner";
import { PanelTitle } from "../../components/PanelTitle";
import { formatDate } from "../../format";
import { useWorkspace } from "../../workspace";

/** Remaining points per day against the ideal line, with scope changes marked (VEL-5). */
export function BurndownChart() {
  const { selectedSprint: sprint, version } = useWorkspace();
  const metrics = useAsync(
    () => (sprint ? metricsApi.sprint(sprint.id) : Promise.resolve(null)),
    [sprint?.id, version],
  );
  const data = metrics.data;
  const points = (data?.burndown || []).map((point) => ({ ...point, label: formatDate(point.date) }));

  return (
    <div className="panel">
      <PanelTitle icon={<TrendingDown size={16} />} title="Burndown" />
      <FormError message={metrics.error} />
      {!sprint && <p className="muted">Select a sprint to see its burndown.</p>}
      {sprint && data && (
        <>
          <div className="stat-row">
            <Stat label="Committed" value={data.committed_points ?? "—"} />
            <Stat label="Done" value={data.completed_points} />
            <Stat label="Remaining" value={data.remaining_points} />
            <Stat label="Complete" value={data.percent_complete == null ? "—" : `${data.percent_complete}%`} />
            <Stat label="Days left" value={data.days_remaining} />
            <Stat label="Estimate" value={data.estimated_completion_date ? formatDate(data.estimated_completion_date) : "not enough data"} />
          </div>
          {(data.scope_added_points > 0 || data.scope_removed_points > 0) && (
            <p className="muted">
              Scope: +{data.scope_added_points} / −{data.scope_removed_points} pts since the sprint started.
            </p>
          )}
          {data.unpointed_story_count > 0 && (
            <p className="warning-line">{data.unpointed_story_count} done stories have no points.</p>
          )}
          {points.length === 0 ? (
            <p className="muted">The burndown starts on {formatDate(sprint.start_date)}.</p>
          ) : (
            <div className="chart-box">
              <ResponsiveContainer width="100%" height={170}>
                <ComposedChart data={points} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e5e5" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend iconSize={10} wrapperStyle={{ fontSize: 12 }} />
                  <Bar isAnimationActive={false} dataKey="scope_change_points" name="Scope change" fill="#d97706" barSize={8} />
                  <Line isAnimationActive={false} type="linear" dataKey="ideal_points" name="Ideal" stroke="#9a9a9a" strokeDasharray="5 4" dot={false} />
                  <Line isAnimationActive={false} type="linear" dataKey="remaining_points" name="Remaining" stroke="#0a0a0a" strokeWidth={2} dot={{ r: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
