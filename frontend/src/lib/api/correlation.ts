/** Create content-free W3C context for one API attempt; never attach auth or URLs. */
export function createTraceparent(): string | undefined {
  if (typeof crypto === "undefined" || !crypto.getRandomValues)
    return undefined;
  const bytes = crypto.getRandomValues(new Uint8Array(24));
  const hex = Array.from(bytes, (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("");
  return `00-${hex.slice(0, 32)}-${hex.slice(32)}-01`;
}

/** Accept only server-generated UUID request IDs for support diagnostics. */
export function readRequestId(headers: Headers): string | undefined {
  const id = headers.get("x-request-id");
  return id &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)
    ? id
    : undefined;
}
