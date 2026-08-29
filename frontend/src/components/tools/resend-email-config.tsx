import * as React from "react";
import { Plus, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export const RESEND_EMAIL_TOOL_NAME = "Resend_email";

export interface ResendEmailRouteConfig {
  route_id: string;
  label: string;
  recipients: string[];
}

export interface ResendEmailConfigEditorProps {
  routes: ResendEmailRouteConfig[];
  fromEmail: string;
  fromName: string;
  onFromEmailChange: (value: string) => void;
  onFromNameChange: (value: string) => void;
  onChange: (routes: ResendEmailRouteConfig[]) => void;
  canEdit: boolean;
}

const ROUTE_ID_PATTERN = /^[a-z0-9][a-z0-9_-]{0,63}$/;
const EMAIL_PATTERN =
  /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$/;
const MAX_EMAIL_LENGTH = 254;
const MAX_FROM_EMAIL_LENGTH = 254;
const MAX_FROM_NAME_LENGTH = 100;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Convert persisted JSONB into the editor's safe, controlled shape.
 *
 * The backend remains the source of truth; this helper only protects the UI
 * from malformed or legacy configuration values while an administrator edits
 * the attachment.
 */
export function parseResendEmailRoutes(value: unknown): ResendEmailRouteConfig[] {
  if (!Array.isArray(value)) return [];

  return value.reduce<ResendEmailRouteConfig[]>((routes, item) => {
    if (!isRecord(item)) return routes;

    const recipients = Array.isArray(item.recipients)
      ? item.recipients.filter((recipient): recipient is string =>
          typeof recipient === "string",
        )
      : [];
    routes.push({
      route_id: typeof item.route_id === "string" ? item.route_id : "",
      label: typeof item.label === "string" ? item.label : "",
      recipients,
    });
    return routes;
  }, []);
}

/**
 * Return the first actionable configuration error, or null when valid.
 *
 * This is a UX check only. The backend validates the same invariants before
 * saving so direct API clients cannot bypass route validation.
 */
export function getResendEmailRoutesError(
  routes: ResendEmailRouteConfig[],
): string | null {
  // An empty route map is valid: it keeps the tool attached but unavailable
  // until an administrator configures a destination, and lets an administrator
  // clear routes without being forced to delete the tool attachment.
  if (routes.length === 0) return null;
  if (routes.length > 50) return "You can configure at most 50 email routes.";

  const routeIds = new Set<string>();
  for (const [index, route] of routes.entries()) {
    const routeNumber = index + 1;
    const routeId = route.route_id.trim();
    if (!ROUTE_ID_PATTERN.test(routeId)) {
      return `Route ${routeNumber} needs a lowercase route ID using letters, numbers, hyphens, or underscores.`;
    }
    if (routeIds.has(routeId)) {
      return `Route ID '${routeId}' is duplicated.`;
    }
    routeIds.add(routeId);

    if (!route.label.trim()) return `Route ${routeNumber} needs a label.`;
    if (route.label.trim().length > 100) {
      return `Route ${routeNumber} label must be 100 characters or fewer.`;
    }
    if (route.recipients.length === 0 || route.recipients.length > 10) {
      return `Route ${routeNumber} needs between 1 and 10 recipient addresses.`;
    }

    const recipients = new Set<string>();
    for (const recipient of route.recipients) {
      const normalizedRecipient = recipient.trim().toLowerCase();
      if (!normalizedRecipient) {
        return `Route ${routeNumber} has an empty recipient. Finish entering the email address after each comma.`;
      }
      if (normalizedRecipient.length > MAX_EMAIL_LENGTH) {
        return `Route ${routeNumber} contains an email address longer than ${MAX_EMAIL_LENGTH} characters.`;
      }
      if (!EMAIL_PATTERN.test(normalizedRecipient)) {
        return `Route ${routeNumber} contains an invalid recipient address.`;
      }
      if (recipients.has(normalizedRecipient)) {
        return `Route ${routeNumber} contains a duplicated recipient address.`;
      }
      recipients.add(normalizedRecipient);
    }
  }
  return null;
}

/**
 * Validate the sender identity that Resend will use for this attachment.
 *
 * Resend requires the address's domain to be verified in the organization's
 * Resend account. The backend repeats this validation before saving.
 */
export function getResendEmailSenderError(
  fromEmail: string,
  fromName: string,
): string | null {
  const normalizedEmail = fromEmail.trim().toLowerCase();
  if (!normalizedEmail) return "A verified sender email address is required.";
  if (normalizedEmail.length > MAX_FROM_EMAIL_LENGTH) {
    return `The sender email must be ${MAX_FROM_EMAIL_LENGTH} characters or fewer.`;
  }
  if (!EMAIL_PATTERN.test(normalizedEmail)) {
    return "Enter a valid sender email address from a Resend-verified domain.";
  }
  if (fromName.includes("\r") || fromName.includes("\n")) {
    return "The sender name must be a single line.";
  }
  if (fromName.trim().length > MAX_FROM_NAME_LENGTH) {
    return `The sender name must be ${MAX_FROM_NAME_LENGTH} characters or fewer.`;
  }
  return null;
}

/**
 * Validate all persisted Resend attachment configuration before save.
 */
export function getResendEmailConfigError(
  fromEmail: string,
  fromName: string,
  routes: ResendEmailRouteConfig[],
): string | null {
  return getResendEmailSenderError(fromEmail, fromName) ??
    getResendEmailRoutesError(routes);
}

/**
 * Determine whether an attached Resend tool can actually send an email.
 *
 * The organization credential status is deliberately required to be exactly
 * true. An absent status means the organization read model has not confirmed
 * that the encrypted credential exists, so the UI must not present a green
 * connected state by default.
 */
export function isResendEmailConfigurationReady(
  config: unknown,
  organizationCredentialConfigured: boolean | undefined,
): boolean {
  if (organizationCredentialConfigured !== true || !isRecord(config)) {
    return false;
  }

  const fromEmail =
    typeof config.from_email === "string" ? config.from_email : "";
  const fromName = typeof config.from_name === "string" ? config.from_name : "";
  const routes = parseResendEmailRoutes(config.routes);

  return (
    routes.length > 0 &&
    getResendEmailConfigError(fromEmail, fromName, routes) === null
  );
}

/**
 * Convert the editable comma-separated recipient text into persisted values.
 * Empty segments are retained so a trailing/doubled comma is visible to the
 * validation layer instead of being silently discarded.
 */
export function parseResendRecipientInput(value: string): string[] {
  if (!value.trim()) return [];
  return value.split(",").map((recipient) => recipient.trim());
}

function serializeRoutes(routes: ResendEmailRouteConfig[]): string {
  return JSON.stringify(routes);
}

function createRouteId(routes: ResendEmailRouteConfig[]): string {
  const existingIds = new Set(routes.map((route) => route.route_id));
  let suffix = routes.length + 1;
  let routeId = `route_${suffix}`;
  while (existingIds.has(routeId)) {
    suffix += 1;
    routeId = `route_${suffix}`;
  }
  return routeId;
}

/**
 * Edit the logical destinations available to the Resend voice tool.
 *
 * The editor deliberately shows recipient addresses only to the authorized
 * administrator configuring the agent. The model receives route IDs and
 * labels through the tool, never these addresses.
 */
export function ResendEmailConfigEditor({
  routes,
  fromEmail,
  fromName,
  onFromEmailChange,
  onFromNameChange,
  onChange,
  canEdit,
}: ResendEmailConfigEditorProps) {
  const validationError = getResendEmailConfigError(
    fromEmail,
    fromName,
    routes,
  );
  const [recipientInputValues, setRecipientInputValues] = React.useState(() =>
    routes.map((route) => route.recipients.join(", ")),
  );
  const lastEmittedRoutesRef = React.useRef<string | null>(null);

  // Keep local text (including a trailing comma or space) during editing, but
  // accept external resets/reloads from the parent as the source of truth.
  React.useEffect(() => {
    const incomingSignature = serializeRoutes(routes);
    if (lastEmittedRoutesRef.current === incomingSignature) {
      lastEmittedRoutesRef.current = null;
      return;
    }
    setRecipientInputValues(
      routes.map((route) => route.recipients.join(", ")),
    );
  }, [routes]);

  const emitRoutes = (nextRoutes: ResendEmailRouteConfig[]) => {
    lastEmittedRoutesRef.current = serializeRoutes(nextRoutes);
    onChange(nextRoutes);
  };

  const updateRoute = (
    index: number,
    field: "route_id" | "label",
    value: string,
  ) => {
    const normalizedValue =
      field === "route_id"
        ? value.toLowerCase().replace(/\s+/g, "_")
        : value;
    emitRoutes(
      routes.map((route, routeIndex) =>
        routeIndex === index ? { ...route, [field]: normalizedValue } : route,
      ),
    );
  };

  const updateRecipients = (index: number, value: string) => {
    setRecipientInputValues((current) => {
      const next = [...current];
      next[index] = value;
      return next;
    });
    emitRoutes(
      routes.map((route, routeIndex) =>
        routeIndex === index
          ? { ...route, recipients: parseResendRecipientInput(value) }
          : route,
      ),
    );
  };

  const addRoute = () => {
    const nextRoutes = [
      ...routes,
      {
        route_id: createRouteId(routes),
        label: "New route",
        recipients: [],
      },
    ];
    setRecipientInputValues((current) => [...current, ""]);
    emitRoutes(nextRoutes);
  };

  const removeRoute = (index: number) => {
    setRecipientInputValues((current) =>
      current.filter((_, routeIndex) => routeIndex !== index),
    );
    emitRoutes(routes.filter((_, routeIndex) => routeIndex !== index));
  };

  return (
    <div className="space-y-4">
      <div className="space-y-3 rounded-lg border p-3">
        <div className="space-y-1">
          <p className="text-sm font-medium">Sender identity</p>
          <p className="text-xs leading-5 text-muted-foreground">
            Use an address from a domain verified in the organization&apos;s
            Resend account. The organization&apos;s Resend API key is configured
            separately under Organization → Credentials.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="resend-from-email" className="text-xs">
              From email address
            </Label>
            <Input
              id="resend-from-email"
              type="email"
              value={fromEmail}
              onChange={(event) => onFromEmailChange(event.target.value)}
              placeholder="noreply@your-verified-domain.com"
              disabled={!canEdit}
              aria-invalid={Boolean(getResendEmailSenderError(fromEmail, fromName))}
              className="h-9 text-sm"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="resend-from-name" className="text-xs">
              From name (optional)
            </Label>
            <Input
              id="resend-from-name"
              value={fromName}
              onChange={(event) => onFromNameChange(event.target.value)}
              placeholder="Your business name"
              disabled={!canEdit}
              aria-invalid={Boolean(getResendEmailSenderError(fromEmail, fromName))}
              className="h-9 text-sm"
            />
          </div>
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">Email routes</span>
            <Badge variant="secondary" className="h-5 text-[10px]">
              {routes.length}
            </Badge>
          </div>
          <p className="text-xs leading-5 text-muted-foreground">
            Choose a route in the conversation; Resend sends to its configured
            business recipients. Addresses are never supplied by the caller.
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={addRoute}
          disabled={!canEdit || routes.length >= 50}
          aria-label="Add email route"
        >
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          Add route
        </Button>
      </div>

      {routes.length === 0 && (
        <div className="rounded-lg border border-dashed border-muted-foreground/30 bg-muted/20 px-4 py-5 text-center">
          <p className="text-sm font-medium">No routes configured</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Add a route such as customer_support or front_desk.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {routes.map((route, index) => {
          const routeIdInput = `resend-route-id-${index}`;
          const labelInput = `resend-route-label-${index}`;
          const recipientsInput = `resend-route-recipients-${index}`;
          return (
            <div
              // The route ID is edited in this card. It must not be part of
              // the React key or the input will remount and lose focus.
              key={index}
              className="space-y-3 rounded-lg border p-3"
            >
              <div className="flex items-start justify-between gap-3">
                <p className="text-xs font-medium text-muted-foreground">
                  Route {index + 1}
                </p>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  onClick={() => removeRoute(index)}
                  disabled={!canEdit}
                  aria-label={`Remove route ${index + 1}`}
                  className="h-7 w-7 text-muted-foreground hover:text-destructive"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor={routeIdInput} className="text-xs">
                    Route ID
                  </Label>
                  <Input
                    id={routeIdInput}
                    value={route.route_id}
                    onChange={(event) =>
                      updateRoute(index, "route_id", event.target.value)
                    }
                    placeholder="customer_support"
                    disabled={!canEdit}
                    className="h-9 text-sm"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor={labelInput} className="text-xs">
                    Label
                  </Label>
                  <Input
                    id={labelInput}
                    value={route.label}
                    onChange={(event) =>
                      updateRoute(index, "label", event.target.value)
                    }
                    placeholder="Customer Support"
                    disabled={!canEdit}
                    className="h-9 text-sm"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor={recipientsInput} className="text-xs">
                  Recipient email addresses
                </Label>
                <Input
                  id={recipientsInput}
                  type="text"
                  inputMode="email"
                  autoComplete="off"
                  spellCheck={false}
                  value={recipientInputValues[index] ?? ""}
                  onChange={(event) =>
                    updateRecipients(index, event.target.value)
                  }
                  placeholder="support@example.com, manager@example.com"
                  disabled={!canEdit}
                  aria-describedby={`${recipientsInput}-help`}
                  className="h-9 text-sm"
                />
                <p
                  id={`${recipientsInput}-help`}
                  className="text-[11px] leading-4 text-muted-foreground"
                >
                  Separate multiple addresses with commas. Maximum 10 per route.
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {validationError && (
        <p
          className="text-xs text-destructive"
          role="alert"
          aria-live="polite"
        >
          {validationError}
        </p>
      )}
    </div>
  );
}
