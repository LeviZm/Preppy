import { useState } from "react";
import { useAuth } from "../context/AuthContext";

export function LoginForm() {
  // Component state: form inputs, error message, loading spinner
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Auth context provides login function and session status
  const { login, sessionExpired, clearSessionExpired } = useAuth();

  // Handle form submission: validate, call API, handle errors
  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault(); // Prevent browser page reload
    setError(null);
    clearSessionExpired();

    if (!email.trim() || !password) {
      setError("Please enter both email and password");
      return;
    }

    setIsLoading(true);

    try {
      // Call login from AuthContext → calls API, stores token
      await login(email, password);
      setEmail("");
      setPassword("");
    } catch (err) {
      // API returned error - display it to user
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      // Always stop loading, success or failure
      setIsLoading(false);
    }
  }

  // Render form with conditional error/session messages
  return (
    <div className="login-container">
      {/* Show session expired message if redirected from 401 */}
      {sessionExpired && (
        <div className="alert alert-info">
          Your session has expired. Please log in again.
        </div>
      )}

      {/* Show API error messages (invalid credentials, etc) */}
      {error && (
        <div className="alert alert-error">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="login-form">
        <h2>Log In</h2>

        {/* Email input - controlled component: state binds to input, onChange updates state */}
        <div className="form-group">
          <label htmlFor="email">Email</label>
          <input
            type="email"
            id="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={isLoading}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="password">Password</label>
          <input
            type="password"
            id="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={isLoading}
            required
          />
        </div>

        <button type="submit" disabled={isLoading} className="btn btn-primary">
          {isLoading ? "Logging in..." : "Log In"}
        </button>
      </form>
    </div>
  );
}
