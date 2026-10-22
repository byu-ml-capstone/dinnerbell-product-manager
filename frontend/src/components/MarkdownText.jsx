/**
 * Renders the small subset of Markdown the AI writes (headings, bullet lists, **bold**, `code`) as React
 * elements. No HTML is injected, so AI output can't run scripts.
 */
export function MarkdownText({ text }) {
  const blocks = [];
  let list = null;
  (text || "").split("\n").forEach((line, index) => {
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (bullet) {
      if (!list) {
        list = [];
        blocks.push({ type: "list", items: list, key: index });
      }
      list.push(bullet[1]);
      return;
    }
    list = null;
    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) blocks.push({ type: "heading", text: heading[2], key: index });
    else if (line.trim()) blocks.push({ type: "paragraph", text: line, key: index });
  });

  return (
    <div className="markdown">
      {blocks.map((block) => {
        if (block.type === "heading") return <h4 key={block.key}>{inline(block.text)}</h4>;
        if (block.type === "list")
          return (
            <ul key={block.key}>
              {block.items.map((item, index) => (
                <li key={index}>{inline(item)}</li>
              ))}
            </ul>
          );
        return <p key={block.key}>{inline(block.text)}</p>;
      })}
    </div>
  );
}

function inline(text) {
  return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) return <strong key={index}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`")) return <code key={index}>{part.slice(1, -1)}</code>;
    return part;
  });
}
