"""Deterministic facts and checks for sprint-analysis drafts (AI-4, AI-5, AI-9)"""

import copy
import re
from datetime import date

STATUSES = ("backlog", "selected", "in_progress", "blocked", "done")
HEADINGS = ("Summary", "Progress", "Velocity", "Estimated Completion", "Accomplished",
            "Remaining Work", "Blockers and Risks", "Suggested Next Steps")
PRIORITY = re.compile(r"\b(urgent|high|medium|low)\s+priority\b|\bpriority\s*(?:is|:|=)\s*(urgent|high|medium|low)\b", re.I)
DEPENDENCY = re.compile(r"\b(?:depend\w*\s+on|blocked\s+by|wait\w*\s+(?:for|on)|once|after|until)\b", re.I)
BLOCKER = re.compile(
    r"^\s*(?:currently\s+)?blocked\b|^\s*waiting (?:for|on)\b"
    r"|\b(?:(?:this|the) (?:task|story|work)|it|we|i)\s+(?:is|are|am|remains?)\s+(?:currently\s+)?blocked\b"
    r"|\bservers? (?:are |is )?down\b|\b(?:we|i) (?:cannot|can't) start\b", re.I,
)
DESTRUCTIVE = re.compile(
    r"\b(?:delete|drop|wipe|truncate|erase|purge|destroy)\b[^\n.!?]{0,80}\b(?:database|schema|tables?|all data)\b"
    r"|\b(?:database|db)\s+(?:deletion|delete)\b", re.I,
)
CAUTION = re.compile(r"\b(?:risk\w*|destruct\w*|unsafe|approval|backup|clarif\w*|avoid|never|do not|don't|human review|manual review)\b", re.I)
WORDS = {word: i for i, word in enumerate(
    ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
     "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")
)}
NUMBER = r"(?:\d+|" + "|".join(WORDS) + r")"


class GroundingError(ValueError):
    pass


def _normal(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.casefold()))


def _negated(text: str) -> bool:
    return bool(re.search(r"\b(?:not|isn't|never|no longer|do not|don't|cannot|can't|no basis|avoid|unknown whether|no evidence)\b[^.!?\n]{0,60}$", text, re.I))


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text or "") if part.strip()]


def _observations(stories: list[dict]) -> list[dict]:
    notes = []

    def add(kind, story, source, evidence, message):
        note = {"kind": kind, "story": story["title"], "source": source, "evidence": evidence, "message": message}
        if note not in notes:
            notes.append(note)

    for story in stories:
        if story["status"] == "blocked" and not story.get("blocked_by"):
            add("recorded_blocker", story, "status", "blocked",
                "Status is blocked without a dependency link; confirm the reason from the text or with the team.")
        for blocker in story.get("blocked_by", []):
            add("formal_dependency", story, "blocked_by", blocker, f"Recorded dependency on {blocker}.")
        sources = [(key, story.get(key) or "") for key in ("description", "acceptance_criteria")]
        comment = story.get("latest_comment") or {}
        if comment.get("text"):
            sources.append(("latest_comment", comment["text"]))
        for source, text in sources:
            for sentence in _sentences(text):
                for match in PRIORITY.finditer(sentence):
                    mentioned = match[1] or match[2]
                    if mentioned.lower() != story.get("priority") and not _negated(sentence[:match.start()]):
                        add("priority_conflict", story, source, sentence,
                            f"Priority conflict: field is {story.get('priority')}, text says {mentioned.lower()}. Confirm with the team.")
                dependency = DEPENDENCY.search(sentence)
                related = []
                if dependency and not _negated(sentence[:dependency.start()]):
                    related = [other["title"] for other in stories if other["title"] != story["title"]
                               and re.search(r"(?<!\w)" + re.escape(other["title"]) + r"(?!\w)", sentence, re.I)]
                    for title in related:
                        if title not in story.get("blocked_by", []):
                            add("text_dependency", story, source, sentence,
                                f"Text suggests a dependency involving {title}, not a recorded link. Confirm its direction.")
                blocker = BLOCKER.search(sentence)
                if blocker and not related and not _negated(sentence[:blocker.start()]):
                    add("text_blocker", story, source, sentence,
                        f"Text reports a blocker; recorded status is {story['status']}. Confirm with the team.")
                if story.get("points") is None and re.search(r"\b(?:worth|more|higher|greater|fewer|less)\b.*\bpoints?\b", sentence, re.I):
                    add("unestimated_point_claim", story, source, sentence,
                        "Points are unassigned; the text's point claim needs a team estimate.")
                if DESTRUCTIVE.search(sentence):
                    add("destructive_request", story, source, sentence,
                        "Destructive-operation risk: clarify scope, require explicit team approval and a recovery plan. This is not an approved requirement or unblocker.")
    return notes


def prepare_snapshot(snapshot: dict) -> dict:
    """Enrich AI inputs without changing the shared metrics API or the original snapshot"""
    result = copy.deepcopy(snapshot)
    stories = result.get("stories", [])
    top = [story for story in stories if story.get("parent_story") is None]

    def counts(rows):
        return {
            "total": len(rows),
            "by_status": {status: sum(story["status"] == status for story in rows) for status in STATUSES},
            "in_progress_or_blocked": sum(story["status"] in ("in_progress", "blocked") for story in rows),
            "unpointed": sum(story.get("points") is None for story in rows),
            "unpointed_titles": [story["title"] for story in rows if story.get("points") is None],
        }

    result["grounding"] = {
        "version": 1,
        "story_counts": {"all_rows": counts(stories), "top_level": counts(top)},
        "metric_definitions": {
            "unpointed_story_count": "Done top-level stories without points, not all unpointed stories.",
            "points": "Metrics count top-level story points only; subtask points are not added again. Closed-sprint metrics are frozen at close.",
            "story_counts": "Current rows in this input snapshot. all_rows includes subtasks; top_level excludes them. These counts are not frozen point totals.",
            "progress_baseline": "No agreed planned-progress baseline is supplied. An estimated completion date is a forecast, not a planned-progress baseline.",
        },
        "progress_baseline": None,
        "required_observations": _observations(stories),
    }
    return result


def _markdown(text) -> str:
    return re.sub(r"([\\`*_\[\]<>#])", r"\\\1", str(text).replace("\n", " "))


def _progress(snapshot: dict) -> str:
    metrics = snapshot["metrics"]
    counts = snapshot["grounding"]["story_counts"]
    rows, top = counts["all_rows"], counts["top_level"]
    lines = [f"- {label}: {metrics.get(key, 'unknown')}" for key, label in (
        ("committed_points", "Committed points"), ("completed_points", "Completed points (top-level)"),
        ("remaining_points", "Remaining points (top-level)"), ("percent_complete", "Percent complete"),
        ("days_elapsed", "Days elapsed"), ("days_remaining", "Days remaining"),
    )]
    lines += [
        f"- All story rows, including subtasks: {rows['total']} total; {rows['by_status']['done']} done; {rows['in_progress_or_blocked']} in progress or blocked.",
        f"- Top-level stories: {top['total']} total; {top['by_status']['done']} done.",
        f"- Unpointed stories, including subtasks: {rows['unpointed']}" + (" — " + ", ".join(_markdown(title) for title in rows['unpointed_titles']) if rows['unpointed_titles'] else "") + ".",
        f"- Done top-level stories without points: {metrics.get('unpointed_story_count', 'unknown')} (the legacy unpointed_story_count metric; not the total unpointed count).",
    ]
    return "\n".join(lines)


def _estimated_completion(snapshot: dict) -> str:
    sprint = snapshot["sprint"]
    if sprint["status"] == "closed":
        return "The sprint is closed" + (f" (actual closing date: {sprint['closed_on']})" if sprint.get("closed_on") else "; actual closing date is unknown") + ". No completion forecast applies."
    estimate = snapshot["metrics"].get("estimated_completion_date")
    try:
        forecast = date.fromisoformat(estimate)
    except (TypeError, ValueError):
        return "Estimated completion: not enough data."
    lines = [f"Estimated completion: {forecast.isoformat()} (an estimate, not a guarantee)."]
    for key, label in (("today", "the snapshot date"), ("end_date", "the planned end date")):
        reference = date.fromisoformat(sprint[key])
        days = (forecast - reference).days
        comparison = f"{abs(days)} calendar days {'after' if days >= 0 else 'before'}"
        lines.append(f"- {comparison} {label} ({reference.isoformat()}).")
    return "\n".join(lines)


def _number(value: str) -> int:
    return int(value) if value.isdigit() else WORDS[value]


def _recorded_checks(notes: list[dict]) -> str:
    # Quote each source sentence once even when it contains several conflicts
    grouped = {}
    labels = {"blocked_by": "recorded dependency", "acceptance_criteria": "acceptance criteria",
              "latest_comment": "latest comment"}
    for note in notes:
        key = (note["story"], note["source"], note["evidence"])
        grouped.setdefault(key, []).append(note["message"])
    return "\n".join(
        f"- **{_markdown(story)}** ({labels.get(source, source)}): "
        + _markdown(" ".join(messages)) + f" Source: “{_markdown(evidence)}”"
        for (story, source, evidence), messages in grouped.items()
    )


def _count_issues(text: str, snapshot: dict) -> list[str]:
    text = re.sub(r"[*_`]+", " ", text.casefold())
    text = re.sub(r"\s+", " ", text)
    counts = snapshot["grounding"]["story_counts"]
    issues = []
    patterns = (
        (rf"\b(?P<n>{NUMBER})\s+(?P<scope>top-level\s+)?(?:unpointed|unestimated)\s+(?:stories|tasks)\b", "unpointed"),
        (rf"\b(?P<n>{NUMBER})\s+(?P<scope>top-level\s+)?(?:stories|tasks)\s+(?:are\s+|remain\s+)?(?:in progress\s*(?:or|/)\s*blocked)\b", "in_progress_or_blocked"),
    )
    for pattern, key in patterns:
        for match in re.finditer(pattern, text):
            if _negated(text[max(0, match.start() - 60):match.start()]):
                continue
            scope = "top_level" if match["scope"] else "all_rows"
            if _number(match["n"]) != counts[scope][key]:
                issues.append(f"Incorrect {key} count; use grounding.story_counts.{scope}.{key}.")
    ratio = rf"\b(?P<done>{NUMBER})\s*(?:of|out of|/)\s*(?P<total>{NUMBER})\s+(?:stories|tasks)\s+(?:are\s+)?(?:marked\s+)?(?:done|complete)\b"
    allowed = {(value["by_status"]["done"], value["total"]) for value in counts.values()}
    for match in re.finditer(ratio, text):
        if _negated(text[max(0, match.start() - 60):match.start()]):
            continue
        if (_number(match["done"]), _number(match["total"])) not in allowed:
            issues.append("Done/total ratio mixes top-level stories and subtasks; use one consistent scope.")
    return issues


def ground_report(text: str, snapshot: dict) -> str:
    """Check model commentary, render trusted counts, and include source-backed observations"""
    closed = snapshot["sprint"]["status"] == "closed"
    expected = list(HEADINGS)
    if closed:
        expected[5] = "Unfinished Work Left in Sprint"
    matches = list(re.finditer(r"(?m)^##\s+([^\n]+?)\s*$", text))
    if [match[1] for match in matches] != expected:
        raise GroundingError("Return the eight required section headings exactly once, in order.")
    sections = {match[1]: text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
                for i, match in enumerate(matches)}
    commentary = "\n".join(body for heading, body in sections.items() if heading != "Progress")
    issues = _count_issues(commentary, snapshot)
    remaining = _normal(sections[expected[5]])
    missing = [story["title"] for story in snapshot.get("stories", [])
               if story["status"] != "done" and _normal(story["title"]) not in remaining]
    if missing:
        issues.append("List every unfinished story, including unfinished subtasks, under the remaining-work heading: " + ", ".join(missing))
    notes = snapshot["grounding"]["required_observations"]
    if notes and re.search(r"\bno (?:blockers|risks|dependencies)(?: or (?:blockers|risks))?\b", sections["Blockers and Risks"], re.I):
        issues.append("Do not claim there are no blockers/risks when required_observations contains recorded checks.")
    unsupported = re.compile(r"fall(?:ing|s)? short of (?:the )?planned progress|(?:behind|ahead of) (?:the )?(?:plan|planned progress)\b", re.I)
    for match in unsupported.finditer(commentary):
        if snapshot["grounding"]["progress_baseline"] is None and not _negated(commentary[max(0, match.start() - 60):match.start()]):
            issues.append("No planned-progress baseline is supplied; describe the recorded forecast and dates instead.")
    for line in commentary.splitlines():
        normalized = _normal(line)
        for story in snapshot.get("stories", []):
            comment = story.get("latest_comment") or {}
            quoted = _normal(comment.get("text") or "")
            if quoted and quoted in normalized:
                for date in re.findall(r"\((?:[^()\n]*,\s*)?(\d{4}-\d{2}-\d{2})\)", line):
                    if date != comment.get("posted_on") and date not in comment["text"]:
                        issues.append(f"Do not invent the posting date of the quoted comment on {story['title']}; use its posted_on if supplied, otherwise omit the date.")
            if story.get("assignee") == "Unassigned":
                action = re.search(r"\bunassign\s+(?:(?:the\s+)?story\s+)?" + re.escape(_normal(story["title"])) + r"\b", normalized)
                if action and not _negated(normalized[:action.start()]):
                    issues.append(f"{story['title']} is already Unassigned. Do not recommend unassigning it; use the recorded assignee when advising on ownership.")
        scope = re.search(r"scope (?:ambiguity|is (?:ambiguous|unclear))", line, re.I)
        if scope and not _negated(line[:scope.start()]):
            supported = any(_normal(story["title"]) in _normal(line) and (
                not story.get("description") and not story.get("acceptance_criteria")
                or re.search(r"\b(?:unclear|ambiguous|tbd)\b", (story.get("description") or "") + " " + (story.get("acceptance_criteria") or ""), re.I)
            ) for story in snapshot.get("stories", []))
            if not supported:
                issues.append("Do not invent scope ambiguity for a described story; identify a specific missing requirement.")
        if DESTRUCTIVE.search(line) and not CAUTION.search(line):
            issues.append("A destructive data operation must be described as a risk requiring clarification and explicit approval, not a normal prerequisite.")
    if closed:
        estimate = sections["Estimated Completion"]
        if re.search(r"\b(?:will|should|expected to|estimated to)\s+(?:be\s+)?(?:complete|finish)", estimate, re.I):
            issues.append("A closed sprint has no future completion forecast; say it is closed.")
        for date in re.findall(r"\b\d{4}-\d{2}-\d{2}\b", estimate):
            if date != snapshot["sprint"].get("closed_on") or "closed" not in estimate.casefold():
                issues.append("Do not include a completion date estimate for a closed sprint.")
        for match in re.finditer(r"\bclosed\s+(?:on|at)\s+(\d{4}-\d{2}-\d{2})", commentary, re.I):
            if match[1] != snapshot["sprint"].get("closed_on"):
                issues.append("Use sprint.closed_on for the actual closing date; never substitute end_date. If unknown, omit the date.")
    if issues:
        raise GroundingError("\n".join(dict.fromkeys(issues)))
    sections["Progress"] = _progress(snapshot)
    sections["Estimated Completion"] = _estimated_completion(snapshot)
    if notes:
        sections["Blockers and Risks"] = "Recorded checks (text claims are not workflow changes):\n" + _recorded_checks(notes) + "\n\n" + sections["Blockers and Risks"]
    return "\n\n".join(f"## {heading}\n{sections[heading]}" for heading in expected)
