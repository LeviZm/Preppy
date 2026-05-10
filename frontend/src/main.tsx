import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider } from "./context/AuthContext";
import { LoginForm } from "./components/LoginForm";
import "./style.css";

// Create the root element for React to render into
const root = ReactDOM.createRoot(document.getElementById("root")!);

// Render the app wrapped with AuthProvider
root.render(
  <React.StrictMode>
    <AuthProvider>
      <div className="app">
        <h1>Preppy</h1>
        <LoginForm />
      </div>
    </AuthProvider>
  </React.StrictMode>
);
