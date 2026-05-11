/**
 * AuthContext - React state management for authentication
 *
 * Think of this like a global variable that any component can read/update,
 * but React automatically re-renders components when it changes.
 */

import { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { setOnUnauthorized } from "../api/client";
import { login as apiLogin, logout as apiLogout, register as apiRegister, type LoginResponse } from "../api/auth";

// TypeScript: describe what the context contains
interface AuthContextType {
  user: LoginResponse["user"] | Record<string, never> | null;  // null = not logged in
  sessionExpired: boolean;              // true if 401 triggered redirect
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string) => Promise<void>;
  clearSessionExpired: () => void;
}

// Create the context (like a global variable container)
const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * AuthProvider - Wraps your app and provides auth state to all children
 *
 * Usage: Wrap your <App /> in main.tsx with <AuthProvider>
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  // React state: when these change, React re-renders components using them
  const [user, setUser] = useState<LoginResponse["user"] | Record<string, never> | null>(null);
  const [sessionExpired, setSessionExpired] = useState(false);

  /**
   * useEffect: Runs once when component mounts
   * Registers the 401 handler with our API client
   */
  useEffect(() => {
    // When API gets 401, this callback runs
    setOnUnauthorized(() => {
      setUser(null);           // Clear user state (logged out)
      setSessionExpired(true); // Show "session expired" message on login page
    });
  }, []); // Empty array = run once on mount

  // Login function: calls API, updates state
  async function login(email: string, password: string): Promise<void> {
    const data = await apiLogin(email, password);
    setUser(data.user || {});
    setSessionExpired(false);
  }

  // Logout function: clears API token + state
  function logout(): void {
    apiLogout();
    setUser(null);
  }

  // Register function: same as login (API returns token)
  async function register(username: string, email: string, password: string): Promise<void> {
    const data = await apiRegister(username, email, password);
    setUser(data.user || {});
    setSessionExpired(false);
  }

  function clearSessionExpired(): void {
    setSessionExpired(false);
  }

  // Provide the context value to all children
  return (
    <AuthContext.Provider
      value={{ user, sessionExpired, login, logout, register, clearSessionExpired }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/**
 * useAuth - Hook to access auth context from any component
 *
 * Usage in a component:
 *   const { user, login } = useAuth();
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
