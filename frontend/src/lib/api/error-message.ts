/**
 * Safe extraction of user-facing API error messages.
 *
 * Never surfaces raw validation payloads or sensitive request fields such as
 * passwords, tokens, or secrets.
 */

const SENSITIVE_FIELD_PATTERN =
  /"(password|password_confirm|current_password|new_password|new_password_confirm|token|refresh_token|access_token|secret|api_key)"\s*:/i;

type ValidationIssue = {
  msg?: string;
  loc?: Array<string | number>;
};

function stripValueErrorPrefix(message: string): string {
  return message.replace(/^Value error,\s*/i, "").trim();
}

function messageFromValidationIssues(issues: ValidationIssue[]): string | null {
  const messages = issues
    .map((issue) => issue.msg?.trim())
    .filter((message): message is string => Boolean(message))
    .map(stripValueErrorPrefix);

  if (messages.length === 0) {
    return null;
  }

  return messages.join(" ");
}

function messageFromDetailObject(detail: Record<string, unknown>): string | null {
  if (typeof detail.message === "string" && detail.message.trim()) {
    return detail.message.trim();
  }
  return null;
}

function containsSensitiveContent(message: string): boolean {
  return SENSITIVE_FIELD_PATTERN.test(message);
}

/**
 * Build a safe, human-readable message from an API error payload.
 */
export function getSafeApiErrorMessage(
  data: unknown,
  fallback = "Something went wrong. Please try again.",
): string {
  if (!data || typeof data !== "object") {
    return fallback;
  }

  const payload = data as Record<string, unknown>;

  if (typeof payload.message === "string" && payload.message.trim()) {
    const message = payload.message.trim();
    return containsSensitiveContent(message) ? fallback : message;
  }

  if (typeof payload.error === "string" && payload.error.trim()) {
    const message = payload.error.trim();
    return containsSensitiveContent(message) ? fallback : message;
  }

  const detail = payload.detail;
  if (typeof detail === "string" && detail.trim()) {
    const message = detail.trim();
    return containsSensitiveContent(message) ? fallback : message;
  }

  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const objectMessage = messageFromDetailObject(detail as Record<string, unknown>);
    if (objectMessage) {
      return objectMessage;
    }
  }

  if (Array.isArray(detail)) {
    const validationMessage = messageFromValidationIssues(
      detail as ValidationIssue[],
    );
    if (validationMessage) {
      return validationMessage;
    }
  }

  return fallback;
}

/**
 * Redact sensitive JSON-like substrings before logging errors in the browser.
 */
export function redactSensitiveLogMessage(message: string): string {
  return message.replace(
    SENSITIVE_FIELD_PATTERN,
    (_match, fieldName: string) => `"${fieldName}":"[REDACTED]":`,
  );
}
