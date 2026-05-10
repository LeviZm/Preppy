import { useState } from "react";
import { useAuth } from "../../context/AuthContext";
import { Input } from "../ui/Input";
import { Button } from "../ui/Button";

type Status = "idle" | "submitting" | "error";

const EMPTY_LOGIN = { email: "", password: "" };
const EMPTY_REGISTER = { username: "", email: "", password: "" };

export function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fields, setFields] = useState({ username: "", email: "", password: "" });
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { login, register, sessionExpired, clearSessionExpired } = useAuth();

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const { name, value } = e.target;
    setFields(prev => ({ ...prev, [name]: value }));
  }

  function switchMode(next: "login" | "register") {
    setMode(next);
    setStatus("idle");
    setErrorMessage(null);
    setFields({ ...EMPTY_REGISTER, ...EMPTY_LOGIN });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (status === "submitting") return;

    clearSessionExpired();

    if (mode === "login" && !fields.email.trim()) {
      setStatus("error");
      setErrorMessage("Email is required.");
      return;
    }
    if (!fields.password) {
      setStatus("error");
      setErrorMessage("Password is required.");
      return;
    }

    setStatus("submitting");
    setErrorMessage(null);
    try {
      if (mode === "login") {
        await login(fields.email, fields.password);
      } else {
        await register(fields.username, fields.email, fields.password);
      }
    } catch (err) {
      setStatus("error");
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    }
  }

  const isSubmitting = status === "submitting";

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-stone-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="font-display text-4xl font-bold text-sage-800 mb-1">Preppy</h1>
          <p className="text-stone-500 text-sm">Your AI-powered meal planning kitchen</p>
        </div>

        <div className="bg-white rounded-2xl border border-stone-200 shadow-sm p-6">
          <div className="flex rounded-xl bg-stone-100 p-1 mb-6">
            <button
              onClick={() => switchMode("login")}
              className={`flex-1 py-1.5 text-sm font-medium rounded-lg transition-colors ${mode === "login" ? "bg-white text-stone-800 shadow-sm" : "text-stone-500 hover:text-stone-700"}`}
            >
              Log in
            </button>
            <button
              onClick={() => switchMode("register")}
              className={`flex-1 py-1.5 text-sm font-medium rounded-lg transition-colors ${mode === "register" ? "bg-white text-stone-800 shadow-sm" : "text-stone-500 hover:text-stone-700"}`}
            >
              Create account
            </button>
          </div>

          {sessionExpired && (
            <div role="alert" className="mb-4 p-3 bg-clay-400/10 border border-clay-400/30 text-clay-600 rounded-xl text-sm">
              Your session expired. Please log in again.
            </div>
          )}
          {status === "error" && errorMessage && (
            <p role="alert" id="auth-error" className="mb-4 p-3 bg-clay-400/10 border border-clay-400/30 text-clay-600 rounded-xl text-sm">
              {errorMessage}
            </p>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <Input
                id="username"
                name="username"
                label="Username"
                value={fields.username}
                onChange={handleChange}
                placeholder="yourname"
                disabled={isSubmitting}
                required
              />
            )}
            <Input
              id="email"
              name="email"
              label="Email"
              type="email"
              value={fields.email}
              onChange={handleChange}
              placeholder="you@example.com"
              disabled={isSubmitting}
              aria-describedby={status === "error" ? "auth-error" : undefined}
              required
            />
            <Input
              id="password"
              name="password"
              label="Password"
              type="password"
              value={fields.password}
              onChange={handleChange}
              placeholder="••••••••"
              disabled={isSubmitting}
              required
            />
            <Button type="submit" loading={isSubmitting} className="w-full justify-center mt-2">
              {isSubmitting
                ? mode === "login" ? "Logging in…" : "Creating account…"
                : mode === "login" ? "Log in" : "Create account"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
