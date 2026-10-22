export function PanelTitle({ icon, title, children }) {
  return (
    <div className="panel-title">
      {icon}
      <span>{title}</span>
      {children}
    </div>
  );
}
