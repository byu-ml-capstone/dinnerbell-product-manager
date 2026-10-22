import { LoaderCircle } from "lucide-react";

export function Spinner({ label = "Loading…", size = 16 }) {
  return (
    <span className="spinner" role="status">
      <LoaderCircle size={size} className="spin" />
      {label && <span>{label}</span>}
    </span>
  );
}
