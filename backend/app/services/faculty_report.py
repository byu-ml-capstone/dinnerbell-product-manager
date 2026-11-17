"""Faculty's six-section sprint report, derived from a saved analysis snapshot.

No additional provider call and no live project reads: historical reports retain
the facts supplied to their analysis. Missing evidence stays explicitly missing.
"""

import re
import unicodedata
from io import BytesIO

TEMPLATE_URL = "https://docs.google.com/presentation/d/1dW5kYP1oPO6Z1FRyHY5LItOXbVs0H3Q95fvm9S6qAtA/edit"
REVIEW_NOTICE = "Draft for team review. Check all claims and evidence before using this report in the faculty template."


def _section(markdown: str, title: str) -> str:
    match = re.search(r"^## " + re.escape(title) + r"\s*\n(.*?)(?=^## |\Z)", markdown or "", re.M | re.S)
    return match[1].strip() if match else ""


def _velocity(name: str, planned, completed) -> dict:
    # Integer half-up rounding matches the faculty example (5/8 = 63%).
    percentage = f"{(200 * completed + planned) // (2 * planned)}%" if planned and completed is not None else "N/A"
    return {"sprint": name, "planned": planned, "completed": completed, "percentage": percentage}


def build_faculty_report(snapshot: dict, content: str, created_on: str) -> dict:
    sprint = snapshot.get("sprint") or {}
    metrics = snapshot.get("metrics") or {}
    history = list(reversed(snapshot.get("velocity_history") or []))[:2]
    velocity = [_velocity(sprint.get("name", "Current sprint"), metrics.get("committed_points"), metrics.get("completed_points"))]
    velocity.extend(_velocity(row["sprint"], row.get("committed_points"), row.get("completed_points")) for row in history)
    while len(velocity) < 3:
        velocity.append(_velocity("No prior sprint recorded", None, None))
    velocity_note = "Story points; planned means committed at sprint start. N/A means no baseline or zero planned points."
    if not history:
        velocity_note += " No prior velocity is recorded; a trend cannot yet be established."
    if sprint.get("status") != "closed":
        velocity_note += " Current sprint is open; completed points are provisional."

    review = snapshot.get("sprint_review") or {}
    verdicts = {row["story"]: row for row in review.get("verdicts", [])}
    deliveries = []
    for story in snapshot.get("stories", []):
        if story.get("status") != "done":
            continue
        entry = verdicts.get(story["title"])
        text = f"{story['title']}: recorded as done."
        if entry:
            text += f" Code review: {entry.get('verdict', 'unknown')}. {entry.get('summary', '')}"
            for evidence in entry.get("evidence") or []:
                location = evidence.get("path") or evidence.get("commit") or "Evidence note"
                if evidence.get("lines"):
                    location += ":" + str(evidence["lines"])
                text += f" Evidence: {location}"
                if entry.get("head_sha"):
                    text += f" at {entry['head_sha']}"
                if evidence.get("note"):
                    text += f" ({evidence['note']})"
                text += "."
            text += " Code review does not establish deployed or user validation."
        else:
            text += " No validation evidence recorded in this analysis snapshot; team verification needed."
        deliveries.append(text)
    delivery_text = "\n".join(f"- {item}" for item in deliveries) or "No completed deliveries are recorded in this snapshot; validation is not yet available."

    decisions = _section(content, "Blockers and Risks") or "No decisions, blockers, risks or tradeoffs recorded in this report; team confirmation needed."
    if sprint.get("closing_notes"):
        decisions += "\n\nRecorded closing notes: " + sprint["closing_notes"]
    next_goals = (snapshot.get("report_context") or {}).get("next_sprint_goals", "").strip()
    if not next_goals:
        next_goals = "\n".join(f"- {row['name']}: {row['goal']}" for row in snapshot.get("next_sprints", []))
    if not next_goals:
        advice = _section(content, "Suggested Next Steps")
        next_goals = "No agreed next sprint goals recorded."
        if advice:
            next_goals += " Proposed steps for team review (not agreed goals):\n" + advice
        else:
            next_goals += " For the final sprint, record Semester 2 priorities."
    faculty = (snapshot.get("report_context") or {}).get("faculty_feedback", "").strip()
    faculty = faculty or "No faculty feedback or requests recorded in this snapshot. The team must add any feedback or requests from the review."
    sections = [
        {"title": "Sprint Goal", "content": sprint.get("goal") or "No sprint goal recorded; the team must supply it."},
        {"title": "Velocity Trend (last 3 sprints)", "content": velocity_note},
        {"title": "Sprint Deliveries & Validation", "content": delivery_text},
        {"title": "Key Decisions / Blockers", "content": decisions},
        {"title": "Next Sprint Goals", "content": next_goals},
        {"title": "Faculty Feedback / Requests", "content": faculty},
    ]
    warnings = snapshot.get("report_warnings") or []
    notice = REVIEW_NOTICE + (" Unresolved analysis checks: " + "; ".join(warnings) if warnings else "")
    report = {
        "team": snapshot.get("project_name") or "Team name not recorded",
        "sprint": sprint.get("name") or "Sprint",
        "date": sprint.get("closed_on") or created_on,
        "is_closed": sprint.get("status") == "closed",
        "notice": notice,
        "template_url": TEMPLATE_URL,
        "velocity": velocity,
        "sections": sections,
    }
    report["markdown"] = report_markdown(report)
    return report


def report_markdown(report: dict) -> str:
    lines = [f"# {report['team']} Sprint Report: {report['date']}", f"Sprint: {report['sprint']}", f"> {report['notice']}"]
    for index, section in enumerate(report["sections"]):
        lines.extend([f"## {section['title']}", section["content"]])
        if index == 1:
            table = ["| Sprint | Planned | Completed | Percentage |", "| --- | --- | --- | --- |"]
            for row in report["velocity"]:
                name = row["sprint"].replace("|", "\\|").replace("\n", " ")
                planned = row["planned"] if row["planned"] is not None else "N/A"
                completed = row["completed"] if row["completed"] is not None else "N/A"
                table.append(f"| {name} | {planned} | {completed} | {row['percentage']} |")
            lines.append("\n".join(table))
    lines.append(f"Template: {TEMPLATE_URL}")
    return "\n\n".join(lines) + "\n"


def render_pptx(report: dict) -> bytes:
    """Generate the faculty's one-page layout without redistributing course files."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_ANCHOR
    from pptx.oxml.xmlchemy import OxmlElement
    from pptx.util import Inches, Pt

    deck = Presentation()
    deck.slide_width, deck.slide_height = Inches(10), Inches(5.625)
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    title = slide.shapes.add_textbox(Inches(0.5), Inches(0.15), Inches(9.19), Inches(0.808))
    title.text = "Sprint Report:"
    body_shape = slide.shapes.add_table(3, 2, Inches(0.6217), Inches(1.1458), Inches(8.8783), Inches(3.62))
    velocity_shape = slide.shapes.add_table(4, 4, Inches(5.2001), Inches(1.4684), Inches(4.1781), Inches(1.08))

    def cell_style(cell, fill, border):
        cell.fill.solid()
        cell.fill.fore_color.rgb = RGBColor.from_string(fill)
        cell.margin_left = cell.margin_right = Inches(0.10)
        cell.margin_top = cell.margin_bottom = Inches(0.0375)
        properties = cell._tc.get_or_add_tcPr()
        for edge in ("lnL", "lnR", "lnT", "lnB"):
            line = OxmlElement(f"a:{edge}")
            line.set("w", "12700")
            solid = OxmlElement("a:solidFill")
            color = OxmlElement("a:srgbClr")
            color.set("val", border)
            solid.append(color)
            line.append(solid)
            properties.append(line)

    for row in body_shape.table.rows:
        for cell in row.cells:
            cell_style(cell, "FFFFFF", "000000")
    for index, row in enumerate(velocity_shape.table.rows):
        for cell in row.cells:
            cell_style(cell, "4285F4" if index == 0 else "D0D8E8" if index % 2 else "E8ECF4", "FFFFFF")
    for col, (label, width) in enumerate(zip(("Sprint", "Planned", "Completed", "Percentage"), (0.8448, 1.0230, 1.1379, 1.1724))):
        velocity_shape.table.columns[col].width = Inches(width)
        cell = velocity_shape.table.cell(0, col)
        cell.text = label
        font = cell.text_frame.paragraphs[0].runs[0].font
        font.name, font.size, font.bold = "Calibri", Pt(11), True
        font.color.rgb = RGBColor(255, 255, 255)
    condensed = False

    def fit_text(text: str, limit: int) -> str:
        nonlocal condensed
        text = re.sub(r"\s+", " ", re.sub(r"[*`#]", "", text)).strip()
        def width(char):
            return 2 if unicodedata.east_asian_width(char) in ("W", "F") or char in "WM@" else 1
        if sum(width(char) for char in text) <= limit:
            return text
        condensed = True
        marker = "… [full details in Markdown]"
        budget = max(0, limit - len(marker))
        end = 0
        for char in text:
            budget -= width(char)
            if budget < 0:
                break
            end += 1
        return text[:end].rstrip() + marker

    title = next(shape for shape in slide.shapes if shape.has_text_frame and "Sprint Report:" in shape.text)
    title.text_frame.clear()
    title.text_frame.paragraphs[0].text = f"{fit_text(report['team'], 38)} Sprint Report: {report['date']}"
    title.text_frame.paragraphs[0].font.size = Pt(20)
    title.text_frame.paragraphs[0].font.name = "Arial"
    table_shapes = [shape for shape in slide.shapes if shape.has_table]
    tables = [shape.table for shape in table_shapes]
    body = next(table for table in tables if len(table.columns) == 2)
    velocity = next(table for table in tables if len(table.columns) == 4)
    # Match the geometry observed in the supplied faculty-template preview.
    for row, height in zip(body.rows, (1.47, 1.10, 1.05)):
        row.height = Inches(height)
    for row, height in zip(velocity.rows, (0.30, 0.26, 0.26, 0.26)):
        row.height = Inches(height)
    for shape in table_shapes:
        shape.width = sum(column.width for column in shape.table.columns)
        shape.height = sum(row.height for row in shape.table.rows)
    for index, section in enumerate(report["sections"]):
        row, col = divmod(index, 2)
        # Velocity's original cell contains the overlaid table; keep that cell's heading only.
        cell = body.cell(row, col)
        cell.vertical_anchor = MSO_ANCHOR.TOP
        cell.text_frame.word_wrap = True
        cell.text_frame.clear()
        paragraph = cell.text_frame.paragraphs[0]
        paragraph.text = section["title"]
        paragraph.font.bold = True
        paragraph.font.size = Pt(12)
        if index != 1:
            paragraph = cell.text_frame.add_paragraph()
            paragraph.text = fit_text(section["content"], 400 if index == 0 else 230)
            paragraph.font.size = Pt(10)
            paragraph.space_after = Pt(0)
        # Explicit run formatting also keeps importers from inheriting a white
        # table-text theme when the original Google table has no style id.
        for paragraph in cell.text_frame.paragraphs:
            for run in paragraph.runs:
                run.font.name = "Calibri"
                run.font.size = paragraph.font.size
                run.font.bold = bool(paragraph.font.bold)
                run.font.color.rgb = RGBColor(0, 0, 0)
    for index, entry in enumerate(report["velocity"], 1):
        values = [("N", "N – 1", "N – 2")[index - 1], entry["planned"], entry["completed"], entry["percentage"]]
        for col, value in enumerate(values):
            cell = velocity.cell(index, col)
            cell.text = str(value) if value is not None else "N/A"
            font = cell.text_frame.paragraphs[0].runs[0].font
            font.name, font.size = "Calibri", Pt(10)
            font.color.rgb = RGBColor(0, 0, 0)
    footer = slide.shapes.add_textbox(Inches(0.6), Inches(5.1), Inches(8.9), Inches(0.45))
    note = f"{fit_text(report['sprint'], 70)} · Draft: team review required. Points; N/A = no/zero baseline."
    if report["velocity"][1]["completed"] is None:
        note += " No prior velocity recorded."
    if not report.get("is_closed"):
        note += " Open sprint: provisional."
    if condensed:
        note += " Condensed; see Markdown."
    if "Unresolved analysis checks" in report["notice"]:
        note += " Unresolved checks; see Markdown."
    footer.text_frame.paragraphs[0].text = note
    footer.text_frame.paragraphs[0].font.size = Pt(8)
    stream = BytesIO()
    deck.save(stream)
    return stream.getvalue()
