// LoopsView - SVG node-graph of the control topology.

import { api } from "../api";
import usePolling from "../hooks/usePolling";
import LoopGraph from "../operating/LoopGraph";

export default function LoopsView() {
  const { data: topology, error } = usePolling(
    () => api.operating.loops(), 30000);

  return (
    <div className="view loops-view">
      <h2>Loop Graph</h2>
      <p className="view-subtitle">
        The control topology. Every cycle must terminate at an anchor (🔒) or a human decision.
      </p>

      {error && <div className="error-msg">Error loading topology: {error}</div>}
      <LoopGraph topology={topology} />
    </div>
  );
}
