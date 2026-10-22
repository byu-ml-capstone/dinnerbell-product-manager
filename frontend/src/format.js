const dateFormat = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });
const dateTimeFormat = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

/** "2026-11-02" -> "Nov 2". Plain dates are parsed as local dates, not UTC. */
export function formatDate(value) {
  if (!value) return "";
  const [year, month, day] = value.slice(0, 10).split("-").map(Number);
  return dateFormat.format(new Date(year, month - 1, day));
}

/** A timestamp shown as a local calendar day ("2026-10-21T03:38Z" -> "Oct 20" in Denver). */
export function formatDay(value) {
  return value ? dateFormat.format(new Date(value)) : "";
}

export function formatDateTime(value) {
  return value ? dateTimeFormat.format(new Date(value)) : "";
}

export function relativeTime(value) {
  if (!value) return "";
  const seconds = Math.round((Date.now() - new Date(value).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDate(value);
}

export function isoDate(date) {
  const pad = (number) => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function addDays(value, days) {
  const [year, month, day] = value.split("-").map(Number);
  return isoDate(new Date(year, month - 1, day + days));
}

export function daysBetween(start, end) {
  const toDate = (value) => {
    const [year, month, day] = value.split("-").map(Number);
    return Date.UTC(year, month - 1, day);
  };
  return Math.round((toDate(end) - toDate(start)) / 86400000);
}

export function sprintDates(sprint) {
  return `${formatDate(sprint.start_date)} – ${formatDate(sprint.end_date)}`;
}

export function pluralize(count, word) {
  if (count === 1) return `1 ${word}`;
  const plural = /[^aeiou]y$/.test(word) ? `${word.slice(0, -1)}ies` : `${word}s`;
  return `${count} ${plural}`;
}

/** {"stories": 4, "comments": 7} -> "4 stories, 7 comments" */
export function describeCounts(counts = {}) {
  const words = { stories: "story", sprints: "sprint", comments: "comment", dependencies: "link", messages: "message", projects: "project" };
  return Object.entries(counts)
    .filter(([, count]) => count)
    .map(([key, count]) => {
      const word = words[key] || key;
      return count === 1 ? `1 ${word}` : `${count} ${word === "story" ? "stories" : `${word}s`}`;
    })
    .join(", ");
}
