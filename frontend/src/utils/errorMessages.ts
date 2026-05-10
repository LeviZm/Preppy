import { ApiRequestError } from "../api/client";

export type ErrorCategory =
  | "validation"   // 400 — user input was invalid; show server message
  | "conflict"     // 409 — user input conflicted with existing data
  | "not_found"    // 404 — resource does not exist
  | "upstream"     // 502, 503 — upstream dependency (AI service) failed
  | "server"       // 500+ — Preppy's own failure
  | "network"      // no response received (connection error)
  | "unknown";     // anything else

export interface ClassifiedError {
  category: ErrorCategory;
  /** Safe, user-facing message. Never contains internal details for 5xx. */
  userMessage: string;
  /** The original thrown value, for console logging only. */
  original: unknown;
}

/**
 * Classify any caught error and produce a user-facing message.
 *
 * This is the single place where status codes map to display strings.
 * Components call this and render the result — they do not contain
 * classification logic.
 *
 * Rule: the higher the status code, the less the server's message is trusted.
 *   400, 409 → show server message (written for the user)
 *   404      → show server message with a safe fallback
 *   500, 502 → substitute a safe generic message (may contain internals)
 *   network  → show a connectivity message (no server message exists)
 *
 * @param error    The caught value (may be ApiRequestError, Error, or unknown)
 * @param context  Short description of what was being attempted, used in
 *                 upstream messages. e.g. "recipe generation", "sign in"
 */
export function classifyError(error: unknown, context: string): ClassifiedError {
  if (error instanceof ApiRequestError) {
    const { status, data } = error;
    const serverMessage =
      typeof data["error"] === "string" ? data["error"] : null;

    if (status === 400) {
      return {
        category: "validation",
        userMessage: serverMessage ?? "Invalid input. Please check your entries.",
        original: error,
      };
    }

    if (status === 409) {
      return {
        category: "conflict",
        userMessage: serverMessage ?? "This conflicts with an existing entry.",
        original: error,
      };
    }

    if (status === 404) {
      return {
        category: "not_found",
        userMessage: serverMessage ?? "This item could not be found.",
        original: error,
      };
    }

    if (status === 429) {
      return {
        category: "upstream",
        userMessage: "You've made too many requests. Please wait a moment and try again.",
        original: error,
      };
    }

    if (status === 502 || status === 503) {
      return {
        category: "upstream",
        userMessage: `The ${context} service is temporarily unavailable. Please try again.`,
        original: error,
      };
    }

    if (status >= 500) {
      return {
        category: "server",
        userMessage: "Something went wrong on our end. Please try again.",
        original: error,
      };
    }

    return {
      category: "unknown",
      userMessage: "An unexpected error occurred. Please try again.",
      original: error,
    };
  }

  if (error instanceof Error) {
    if (error.message.toLowerCase().includes("failed to fetch") ||
        error.message.toLowerCase().includes("connection failed")) {
      return {
        category: "network",
        userMessage: "Could not connect. Check your internet connection.",
        original: error,
      };
    }
  }

  return {
    category: "unknown",
    userMessage: "An unexpected error occurred. Please try again.",
    original: error,
  };
}
