import { useState } from "react";
import { Bot, ScanSearch } from "lucide-react";
import { PanelTitle } from "../../components/PanelTitle";
import { useWorkspace } from "../../workspace";
import { SprintBadge } from "../sprints/SprintPicker";
import { AnalysisPanel } from "./AnalysisPanel";
import { SprintReviewPanel } from "./SprintReviewPanel";

/** Replaces the base app's report panel (§10.3 UI changes). */
export function AiPanel() {
  const { selectedSprint: sprint } = useWorkspace();
  const [tab, setTab] = useState("analysis");
  return (
    <section className="report-panel">
      <div className="section-heading">
        <PanelTitle icon={<Bot size={18} />} title={sprint ? `AI for ${sprint.name}` : "AI"} />
        {sprint && <SprintBadge sprint={sprint} />}
      </div>
      <nav className="sub-tabs">
        <button className={tab === "analysis" ? "tab active" : "tab"} onClick={() => setTab("analysis")}>
          <Bot size={14} /> Analysis
        </button>
        <button className={tab === "review" ? "tab active" : "tab"} onClick={() => setTab("review")}>
          <ScanSearch size={14} /> Sprint review
        </button>
      </nav>
      {!sprint ? (
        <p className="muted">Create or select a sprint to use the AI tools.</p>
      ) : tab === "analysis" ? (
        <AnalysisPanel sprint={sprint} />
      ) : (
        <SprintReviewPanel sprint={sprint} />
      )}
    </section>
  );
}
