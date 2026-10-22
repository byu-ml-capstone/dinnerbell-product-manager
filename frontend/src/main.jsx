import { createRoot } from "react-dom/client";
import { App } from "./App";
// Imported in this order so the cascade matches the original single stylesheet.
import "./styles/base.css";
import "./styles/board.css";
import "./styles/components.css";
import "./styles/panels.css";
import "./styles/ai.css";
import "./styles/views.css";

createRoot(document.getElementById("root")).render(<App />);
