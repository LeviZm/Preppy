/**
 * API Client - Centralized HTTP client with JWT handling
 *
 * Security: Token stored in memory only (not localStorage) to prevent XSS theft.
 * On 401 response: clears token and triggers the registered onUnauthorized callback.
 *
 * Token injection policy: opt-out.
 * All paths receive the Authorization header by default.
 * Public paths (no token needed) are explicitly listed in PUBLIC_PATHS.
 * Do not add protected paths to PUBLIC_PATHS.
 */

// ---------------------------------------------------------------------------
// Environment
// ---------------------------------------------------------------------------

const _BASE_URL: string = (import.meta.env.VITE_API_BASE_URL as string) || "/api";

// ---------------------------------------------------------------------------
// Token storage — in-memory only, cleared on page refresh
// ---------------------------------------------------------------------------

let _token: string | null = null;
let _onUnauthorized: (() => void) | null = null;

/**
 * Register a callback to handle 401 unauthorized responses.
 * The AuthContext registers this to redirect to the login screen.
 */
export function setOnUnauthorized(callback: () => void): void {
  _onUnauthorized = callback;
}

/** Store the JWT after successful login. */
export function setToken(token: string): void {
  _token = token;
}

/** Clear the token (logout or 401 response). */
export function clearToken(): void {
  _token = null;
}

/** Read the current token. Prefer not calling this outside client.ts. */
export function getToken(): string | null {
  return _token;
}

// ---------------------------------------------------------------------------
// Token injection policy — opt-out
// ---------------------------------------------------------------------------

/**
 * Paths that never receive an Authorization header.
 *
 * Rules:
 *   - Exact matches only. "/auth/login" does not cover "/auth/login/refresh".
 *   - All methods for a listed path are treated as public.
 *   - Add new public paths here. Do NOT add protected paths.
 */
const PUBLIC_PATHS: ReadonlySet<string> = new Set([
  "/auth/login",
  "/auth/register",
]);

function isPublicPath(path: string): boolean {
  return PUBLIC_PATHS.has(path);
}

// ---------------------------------------------------------------------------
// Typed error class
// ---------------------------------------------------------------------------

/**
 * Thrown by apiRequest for every non-2xx response (except 401, which is
 * handled internally). Carries the HTTP status and the parsed response body
 * so callers can make decisions based on the failure type.
 */
export class ApiRequestError extends Error {
  public readonly status: number;
  public readonly data: Record<string, unknown>;

  constructor(message: string, status: number, data: Record<string, unknown>) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.data = data;
  }
}

// ---------------------------------------------------------------------------
// Core request function
// ---------------------------------------------------------------------------

/**
 * Central API request function.
 *
 * Responsibilities:
 *   - Attaches Authorization header for protected paths when token is present
 *   - Handles 401 by clearing the token and calling the registered callback
 *   - Throws ApiRequestError for all other non-2xx responses
 *   - Returns the raw Response for callers that need to inspect it
 */
export async function apiRequest(
  path: string,
  options: RequestInit = {}
): Promise<Response | undefined> {
  const shouldAttachToken = !isPublicPath(path) && _token !== null;

  const isMultipartBody = typeof FormData !== "undefined" && options.body instanceof FormData;

  const headers: Record<string, string> = {
    ...(isMultipartBody ? {} : { "Content-Type": "application/json" }),
    ...(shouldAttachToken ? { Authorization: `Bearer ${_token}` } : {}),
    ...((options.headers as Record<string, string> | undefined) ?? {}),
  };

  let response: Response;
  try {
    response = await fetch(`${_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Connection failed. Please check your internet and try again.");
  }

  if (response.status === 401) {
    clearToken();
    if (_onUnauthorized) _onUnauthorized();
    return undefined;
  }

  return response;
}

// ---------------------------------------------------------------------------
// Response helper
// ---------------------------------------------------------------------------

/**
 * Parse a Response from apiRequest, throwing ApiRequestError on failure.
 * Centralizes response handling so API modules don't duplicate this logic.
 */
export async function handleResponse<T>(res: Response | undefined): Promise<T> {
  if (!res) throw new Error("Connection failed. Please check your internet and try again.");

  if (!res.ok) {
    let data: Record<string, unknown> = {};
    try { data = await res.json(); } catch { /* non-JSON body — leave data empty */ }
    const message = typeof data["error"] === "string"
      ? data["error"]
      : `Request failed with status ${res.status}`;
    throw new ApiRequestError(message, res.status, data);
  }

  const contentType = res.headers.get("content-type");
  if (contentType?.includes("application/json")) {
    return res.json() as Promise<T>;
  }
  return undefined as unknown as T;
}