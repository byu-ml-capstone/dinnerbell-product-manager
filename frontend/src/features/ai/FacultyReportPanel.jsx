import { useState } from "react";
import { Download, ExternalLink } from "lucide-react";
import { analysesApi } from "../../api/analyses";
import { FormError } from "../../components/ErrorBanner";
import { MarkdownText } from "../../components/MarkdownText";
import { downloadBlob, downloadMarkdown, reportFilename } from "./reportDownloads";

export function FacultyReportPanel({ report, analysisId }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  if (!report) return null;

  async function downloadPresentation() {
    setError("");
    setBusy(true);
    try {
      const blob = await analysesApi.downloadSprintReport(analysisId);
      downloadBlob(blob, reportFilename("sprint-report", report.sprint, analysisId, "pptx"));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel faculty-report" aria-label="Faculty sprint report">
      <div className="section-heading">
        <div>
          <h3>Sprint Report</h3>
          <span className="muted">{report.team} · {report.sprint} · {report.date}</span>
        </div>
        <a href={report.template_url} target="_blank" rel="noreferrer">Faculty template <ExternalLink size={12} /></a>
      </div>
      <p className="report-notice">{report.notice}</p>
      <div className="faculty-report-grid">
        {report.sections.map((section, index) => (
          <section className="faculty-report-section" key={section.title}>
            <h4>{section.title}</h4>
            {index === 1 && (
              <div className="faculty-velocity-scroll">
                <table className="data-table">
                  <thead><tr><th>Sprint</th><th>Planned</th><th>Completed</th><th>Percentage</th></tr></thead>
                  <tbody>{report.velocity.map((row, i) => (
                    <tr key={i}><td>{row.sprint}</td><td>{row.planned ?? "N/A"}</td><td>{row.completed ?? "N/A"}</td><td>{row.percentage}</td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
            <MarkdownText text={section.content} />
          </section>
        ))}
      </div>
      <p className="muted">Generated with this analysis. PPTX follows the one-page faculty layout and condenses long text; Markdown includes the full draft. Add next goals and faculty feedback before running, or edit the downloaded presentation.</p>
      <div className="button-row">
        <button className="secondary-button" onClick={() => downloadMarkdown(report.markdown, reportFilename("sprint-report", report.sprint, analysisId))}>
          <Download size={16} /> Download .md
        </button>
        <button className="secondary-button" disabled={busy} onClick={downloadPresentation}>
          <Download size={16} /> {busy ? "Preparing PPTX…" : "Download .pptx"}
        </button>
      </div>
      <FormError message={error} />
    </section>
  );
}
