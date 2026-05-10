import { apiRequest, setToken, clearToken } from "./client";

export interface LoginResponse {
  access_token: string;
  user?: {
    id: number;
    username: string;
    email: string;
  };
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });

  if (!response) {
    throw new Error("Network error - please try again");
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: "Login failed" }));
    throw new Error(errorData.error || "Login failed");
  }

  const data: LoginResponse = await response.json();
  setToken(data.access_token); // Token stored in memory only (matches backend)
  return data;
}

export function logout(): void {
  clearToken(); // Token gone immediately - no localStorage to cleanup
}

export async function register(
  username: string,
  email: string,
  password: string
): Promise<LoginResponse> {
  const response = await apiRequest("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });

  if (!response) {
    throw new Error("Network error - please try again");
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ error: "Registration failed" }));
    throw new Error(errorData.error || "Registration failed");
  }

  const data: LoginResponse = await response.json();
  setToken(data.access_token);
  return data;
}
