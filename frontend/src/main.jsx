import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App.jsx";
// Platform / dist UI — same entry CSS as D:\Downloads\dist (Tailwind + phosphor).
import "./index.css";
// Legacy generation-layer UI only. Fully scoped under `.app` so it cannot
// override Platform sidebar/buttons the way unscoped `button {}` rules did.
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
