export function EmptyState({ title, body, children }) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      {body && <p>{body}</p>}
      {children}
    </div>
  );
}
