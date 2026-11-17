"""Pure report/export regressions; also runnable with unittest without a database."""

import copy
import unittest
from io import BytesIO

from pptx import Presentation

from app.services.faculty_report import build_faculty_report, render_pptx


def snapshot():
    return {
        "project_name": "DinnerBell",
        "sprint": {"name": "Sprint 3", "goal": "Validate grocery matching", "status": "active"},
        "metrics": {"committed_points": 12, "completed_points": 9},
        "velocity_history": [
            {"sprint": "Sprint 1", "committed_points": 8, "completed_points": 5},
            {"sprint": "Sprint 2", "committed_points": 10, "completed_points": 7},
        ],
        "stories": [{"title": "Product matching", "status": "done"}, {"title": "Pilot", "status": "selected"}],
    }


class FacultyReportTests(unittest.TestCase):
    def report(self, data=None, content=""):
        return build_faculty_report(data if data is not None else snapshot(), content, "2026-11-17")

    def test_six_sections_and_three_sprint_velocity_with_correct_denominator(self):
        report = self.report()
        self.assertEqual(len(report["sections"]), 6)
        self.assertEqual([row["percentage"] for row in report["velocity"]], ["75%", "70%", "63%"])
        self.assertEqual([row["sprint"] for row in report["velocity"]], ["Sprint 3", "Sprint 2", "Sprint 1"])
        self.assertIn("provisional", report["sections"][1]["content"])
        self.assertNotIn("Pilot: recorded as done", report["markdown"])

    def test_first_sprint_and_zero_or_unknown_baseline(self):
        data = snapshot()
        data["velocity_history"] = []
        for planned in (0, None):
            data["metrics"]["committed_points"] = planned
            report = self.report(data)
            self.assertEqual(len(report["velocity"]), 3)
            self.assertEqual(report["velocity"][0]["percentage"], "N/A")
            self.assertIn("No prior velocity", report["markdown"])

    def test_done_status_does_not_invent_validation(self):
        report = self.report()
        self.assertIn("No validation evidence recorded", report["sections"][2]["content"])

    def test_code_review_cites_evidence_and_does_not_claim_deployed_validation(self):
        data = snapshot()
        data["sprint_review"] = {"verdicts": [{
            "story": "Product matching", "verdict": "matches", "summary": "Matching endpoint found.",
            "head_sha": "abc123", "evidence": [{"path": "app/match.py", "lines": "10-20", "note": "Endpoint"}],
        }]}
        text = self.report(data)["sections"][2]["content"]
        self.assertIn("app/match.py:10-20 at abc123", text)
        self.assertIn("does not establish deployed or user validation", text)

    def test_inputs_upcoming_goals_and_final_semester_fallback(self):
        data = snapshot()
        data["report_context"] = {"next_sprint_goals": "Semester 2: validate pilot", "faculty_feedback": "Please review our evaluation plan."}
        report = self.report(data)
        self.assertEqual(report["sections"][4]["content"], "Semester 2: validate pilot")
        self.assertEqual(report["sections"][5]["content"], "Please review our evaluation plan.")
        data.pop("report_context")
        data["next_sprints"] = [{"name": "Sprint 4", "goal": "Run pilot"}]
        self.assertIn("Sprint 4: Run pilot", self.report(data)["sections"][4]["content"])
        data.pop("next_sprints")
        self.assertIn("Semester 2 priorities", self.report(data)["sections"][4]["content"])

    def test_missing_sections_explain_missing_data_and_suggestions_stay_proposals(self):
        report = self.report({}, "## Suggested Next Steps\n- Test the pilot")
        self.assertTrue(all(section["content"].strip() for section in report["sections"]))
        self.assertIn("not agreed goals", report["sections"][4]["content"])
        self.assertIn("No faculty feedback or requests recorded", report["markdown"])

    def test_markdown_table_has_contiguous_rows_and_escaped_names(self):
        data = snapshot()
        data["sprint"]["name"] = "Sprint | Three"
        text = self.report(data)["markdown"]
        self.assertIn("| Sprint | Planned | Completed | Percentage |\n| ---", text)
        self.assertIn("Sprint \\| Three", text)
        self.assertNotIn("|\n\n|", text)

    def test_snapshot_unchanged_and_actual_close_date_used(self):
        data = snapshot()
        data["sprint"].update(status="closed", closed_on="2026-11-16", end_date="2026-11-20")
        before = copy.deepcopy(data)
        report = self.report(data)
        self.assertEqual(data, before)
        self.assertEqual(report["date"], "2026-11-16")
        self.assertNotIn("provisional", report["markdown"])

    def test_unresolved_checks_are_included_in_download(self):
        data = snapshot()
        data["report_warnings"] = ["Completion claim needs review"]
        self.assertIn("Unresolved analysis checks: Completion claim needs review", self.report(data)["markdown"])

    def test_pptx_is_one_page_faculty_layout_without_sample_content(self):
        report = self.report()
        deck = Presentation(BytesIO(render_pptx(report)))
        self.assertEqual(len(deck.slides), 1)
        self.assertEqual(deck.slide_width, 9144000)
        self.assertEqual(deck.slide_height, 5143500)
        tables = [shape for shape in deck.slides[0].shapes if shape.has_table]
        self.assertEqual(len(tables), 2)
        text = "\n".join(shape.text if shape.has_text_frame else "\n".join(cell.text for row in shape.table.rows for cell in row.cells) if shape.has_table else "" for shape in deck.slides[0].shapes)
        self.assertIn("DinnerBell Sprint Report", text)
        self.assertIn("No validation evidence", text)
        self.assertIn("75%", text)
        self.assertNotIn("Quinnovators", text)
        self.assertNotIn("<team name>", text)
        for shape in tables:
            self.assertLessEqual(shape.left + shape.width, deck.slide_width)
            self.assertLessEqual(shape.top + shape.height, deck.slide_height)

    def test_long_content_condenses_pptx_but_full_markdown_survives(self):
        data = snapshot()
        data["sprint"]["goal"] = "Full goal content. " * 100
        report = self.report(data)
        self.assertIn(data["sprint"]["goal"], report["markdown"])
        deck = Presentation(BytesIO(render_pptx(report)))
        body = next(shape.table for shape in deck.slides[0].shapes if shape.has_table and len(shape.table.columns) == 2)
        self.assertIn("full details in Markdown", body.cell(0, 0).text)
        self.assertLess(len(body.cell(0, 0).text), 450)

    def test_multiline_chinese_feedback_is_compacted_for_one_page(self):
        data = snapshot()
        data["report_context"] = {"faculty_feedback": "请检查试点结果。\n" * 100}
        report = self.report(data)
        self.assertIn(data["report_context"]["faculty_feedback"].strip(), report["markdown"])
        deck = Presentation(BytesIO(render_pptx(report)))
        body = next(shape.table for shape in deck.slides[0].shapes if shape.has_table and len(shape.table.columns) == 2)
        text = body.cell(2, 1).text
        self.assertEqual(len(text.splitlines()), 2)  # heading and a wrapped body paragraph
        self.assertIn("full details in Markdown", text)
        self.assertLess(len(text), 170)


if __name__ == "__main__":
    unittest.main()
