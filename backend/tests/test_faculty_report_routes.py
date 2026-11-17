"""Export endpoint checks with dependency overrides; never opens a database."""

import unittest
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pptx import Presentation

from app.database import get_db
from app.deps import get_current_user
from app.routers import analyses
from tests.test_faculty_report import snapshot


class FacultyReportRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(analyses.router)
        self.app.dependency_overrides[get_db] = lambda: object()
        self.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id="user-test")
        self.client = TestClient(self.app)
        self.analysis = SimpleNamespace(
            id="analysis-test", sprint_id="sprint-test", status="complete", input_snapshot=snapshot(),
            final_content=None, ai_content="## Blockers and Risks\nNeeds pilot validation.",
            created_at=datetime(2026, 11, 17, 12, tzinfo=timezone.utc), usage={},
        )

    def tearDown(self):
        self.client.close()

    def test_download_is_one_page_pptx_and_checks_membership(self):
        with patch.object(analyses, "get_or_404", return_value=self.analysis), patch.object(analyses, "get_sprint_for_member") as membership:
            response = self.client.get("/api/analyses/analysis-test/sprint-report.pptx")
        self.assertEqual(response.status_code, 200)
        membership.assert_called_once()
        self.assertEqual(response.headers["content-type"], "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        self.assertIn('filename="sprint-report-analysis-test.pptx"', response.headers["content-disposition"])
        self.assertEqual(len(Presentation(BytesIO(response.content)).slides), 1)

    def test_non_member_cannot_export(self):
        with patch.object(analyses, "get_or_404", return_value=self.analysis), patch.object(analyses, "get_sprint_for_member", side_effect=HTTPException(403, "Not a member")), patch.object(analyses, "render_pptx") as render:
            response = self.client.get("/api/analyses/analysis-test/sprint-report.pptx")
        self.assertEqual(response.status_code, 403)
        render.assert_not_called()

    def test_pending_running_and_failed_have_no_export(self):
        for status in ("pending", "running", "failed"):
            self.analysis.status = status
            with patch.object(analyses, "_analysis_for_member", return_value=self.analysis):
                response = self.client.get("/api/analyses/analysis-test/sprint-report.pptx")
            self.assertEqual(response.status_code, 400)

    def test_deleted_or_missing_analysis_cannot_export(self):
        with patch.object(analyses, "get_or_404", side_effect=HTTPException(404, "Analysis not found")):
            response = self.client.get("/api/analyses/analysis-test/sprint-report.pptx")
        self.assertEqual(response.status_code, 404)

    def test_saved_final_is_used_without_overwriting_ai_draft(self):
        self.analysis.final_content = "## Blockers and Risks\nHuman corrected blocker."
        report = analyses._faculty_report(self.analysis)
        self.assertIn("Human corrected blocker.", report["markdown"])
        self.assertEqual(self.analysis.ai_content, "## Blockers and Risks\nNeeds pilot validation.")


if __name__ == "__main__":
    unittest.main()
