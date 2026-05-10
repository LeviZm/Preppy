import { ApiRequestError } from "../api/client";

/**
 * Retry an async operation with exponential backoff.
 *
 * Only retries on network errors and 5xx responses.
 * Does NOT retry 4xx (user errors) — retrying will not fix them.
 *
 * @param operation   The async function to attempt
 * @param maxRetries  Maximum number of total attempts (default: 3)
 * @param baseDelay   Initial delay in ms; doubles each attempt (default: 500)
 */
export async function withRetry<T>(
  operation: () => Promise<T>,
  maxRetries = 3,
  baseDelay = 500,
): Promise<T> {
  let lastError: unknown;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;

      if (error instanceof ApiRequestError && error.status < 500) {
        throw error;
      }

      if (attempt < maxRetries) {
        const delay = baseDelay * Math.pow(2, attempt - 1);
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}
