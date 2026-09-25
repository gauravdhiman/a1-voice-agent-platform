/**
 * Role-aware product-tour definitions and browser persistence helpers.
 *
 * The tour is intentionally described as ordered data instead of being
 * assembled inside the rendering component. Adding a step at the beginning,
 * end, or between existing steps should only require editing the relevant
 * ordered list below.
 */

export const PRODUCT_TOUR_VERSION = "v1";

export type ProductTourRole = "member" | "org_admin" | "platform_admin";

export type ProductTourBranch =
  | "agents"
  | "calls"
  | "skills"
  | "agent-details";

export type ProductTourStorageScope = "main" | ProductTourBranch;

export type ProductTourStatus = "skipped" | "completed";

export interface ProductTourStep {
  /** Stable identifier used by tests, analytics, and future step migrations. */
  id: string;
  /** CSS selector for the persistent element the tour should spotlight. */
  target: string;
  /** Short heading shown in the tour popover. */
  title: string;
  /** Plain-language explanation of the feature or action. */
  content: string;
  /** Preferred popover placement relative to the target. */
  placement?: "top" | "bottom" | "left" | "right" | "auto";
  /** Optional branch the user can open from this overview step. */
  branch?: ProductTourBranch;
  /** Roles that can see this step; omitted means every role. */
  roles?: readonly ProductTourRole[];
}

type ProductTourStorageReader = Pick<Storage, "getItem">;
type ProductTourStorageWriter = Pick<Storage, "setItem">;
type ProductTourStorageRemover = Pick<Storage, "removeItem">;

const WORKSPACE_STEPS: readonly ProductTourStep[] = [
  {
    id: "welcome",
    target: '[data-tour="brand"]',
    title: "Welcome to 24x7 AI",
    content:
      "This quick tour shows you where to manage your AI workspace, voice agents, calls, and account settings.",
    placement: "right",
  },
  {
    id: "organization-switcher",
    target: '[data-tour="organization-switcher"]',
    title: "Choose your workspace",
    content:
      "Use the organization switcher to move between workspaces or create a new organization when you need one.",
    placement: "right",
  },
  {
    id: "agents",
    target: '[data-tour="nav-agents"]',
    title: "Build voice agents",
    content:
      "Create, configure, and test the AI agents that answer calls for your organization.",
    placement: "right",
    branch: "agents",
  },
  {
    id: "phone-numbers",
    target: '[data-tour="nav-phone-numbers"]',
    title: "Connect phone numbers",
    content:
      "Buy or import phone numbers, then assign them to the agents that should answer incoming calls.",
    placement: "right",
  },
  {
    id: "skills",
    target: '[data-tour="nav-skills"]',
    title: "Extend agent skills",
    content:
      "Browse and manage reusable skills that give your agents richer workflows and capabilities.",
    placement: "right",
    branch: "skills",
  },
  {
    id: "calls",
    target: '[data-tour="nav-calls"]',
    title: "Review call activity",
    content:
      "Open Calls to review call history and the activity your agents handled for the organization.",
    placement: "right",
    branch: "calls",
  },
];

const AGENTS_BRANCH_STEPS: readonly ProductTourStep[] = [
  {
    id: "agents-overview",
    target: '[data-tour="agents-page"]',
    title: "Your agent workspace",
    content:
      "This is the workspace for viewing agents across the organizations you can access. Use the controls here to find the agent you want to work with.",
    placement: "bottom",
  },
  {
    id: "agents-create",
    target: '[data-tour="agents-create"]',
    title: "Create an agent",
    content:
      "Organization and platform admins can start a new voice agent here. The setup flow guides you through its identity, behavior, voice, and call settings.",
    placement: "left",
    roles: ["org_admin", "platform_admin"],
  },
  {
    id: "agents-view-toggle",
    target: '[data-tour="agents-view-toggle"]',
    title: "Choose a view",
    content:
      "Switch between a compact list and a visual grid depending on how you prefer to scan your agents.",
    placement: "bottom",
  },
  {
    id: "agents-filters",
    target: '[data-tour="agents-filters"]',
    title: "Find the right agent",
    content:
      "Filter by organization or search by agent name and phone number to quickly locate a specific configuration.",
    placement: "bottom",
  },
  {
    id: "agents-results",
    target: '[data-tour="agents-results"]',
    title: "Open an agent to configure it",
    content:
      "Select an agent to work through its configuration. Depending on your permissions, you can manage its instructions, voice, phone number, skills, tools, and testing settings.",
    placement: "top",
  },
];

const CALLS_BRANCH_STEPS: readonly ProductTourStep[] = [
  {
    id: "calls-overview",
    target: '[data-tour="calls-page"]',
    title: "Understand call activity",
    content:
      "The Call Log is the place to review how your agents are handling incoming calls for the selected organization.",
    placement: "bottom",
  },
  {
    id: "calls-filters",
    target: '[data-tour="calls-filters"]',
    title: "Filter call history",
    content:
      "Narrow the log by agent, call status, or date range when you need to investigate a specific slice of activity.",
    placement: "bottom",
  },
  {
    id: "calls-results",
    target: '[data-tour="calls-results"]',
    title: "Review the call log",
    content:
      "Scan caller details, agent, status, duration, and timestamps. Open an individual row when you need more context.",
    placement: "top",
  },
  {
    id: "calls-refresh",
    target: '[data-tour="calls-refresh"]',
    title: "Refresh for the latest activity",
    content:
      "Refresh the log after a live call or while you are monitoring activity so the newest results are available.",
    placement: "left",
  },
];

const SKILLS_BRANCH_STEPS: readonly ProductTourStep[] = [
  {
    id: "skills-overview",
    target: '[data-tour="skills-page"]',
    title: "Build reusable skills",
    content:
      "Skills package repeatable instructions and supporting files that agents can use for richer, more consistent workflows.",
    placement: "bottom",
  },
  {
    id: "skills-add",
    target: '[data-tour="skills-add"]',
    title: "Add a skill",
    content:
      "Admins can create a custom skill, import one from a URL, or bring one in from the platform library.",
    placement: "bottom",
    roles: ["org_admin", "platform_admin"],
  },
  {
    id: "skills-filter",
    target: '[data-tour="skills-filter"]',
    title: "Find a skill",
    content:
      "Filter the skill library by name, slug, or description to get to the workflow you need.",
    placement: "bottom",
  },
  {
    id: "skills-library",
    target: '[data-tour="skills-library"]',
    title: "Explore the skill library",
    content:
      "Select a skill to expand its file tree and inspect the entry file or supporting references.",
    placement: "right",
  },
  {
    id: "skills-editor",
    target: '[data-tour="skills-editor"]',
    title: "Edit the skill workspace",
    content:
      "The editor shows the selected skill's content and actions. Admins can update instructions, add files, and manage visibility or platform updates.",
    placement: "left",
  },
];

const AGENT_DETAILS_BRANCH_STEPS: readonly ProductTourStep[] = [
  {
    id: "agent-details-overview",
    target: '[data-tour="agent-detail-page"]',
    title: "Configure this agent",
    content:
      "This is the agent workspace. Use the tabs below to move between core properties, skills, and tools without leaving the agent.",
    placement: "bottom",
  },
  {
    id: "agent-details-test",
    target: '[data-tour="agent-detail-test"]',
    title: "Test the agent",
    content:
      "When the agent is ready, use Test Agent to place a test call and verify how it responds before putting it into service.",
    placement: "left",
    roles: ["org_admin", "platform_admin"],
  },
  {
    id: "agent-details-tabs",
    target: '[data-tour="agent-detail-tabs"]',
    title: "Explore configuration areas",
    content:
      "Persona defines identity and behavior, Skills add reusable workflows, Tools connect external capabilities, and Settings control availability and voice.",
    placement: "bottom",
  },
  {
    id: "agent-details-persona",
    target: '[data-tour="agent-detail-persona"]',
    title: "Start with the essentials",
    content:
      "The Persona tab is where you set the agent name and instructions. Use Settings for the phone number, availability, publishing, call recording, voice profile, and call credits.",
    placement: "top",
  },
];

const PRODUCT_TOUR_BRANCH_ROUTES: Readonly<
  Record<ProductTourBranch, string>
> = {
  agents: "/agents",
  calls: "/calls",
  skills: "/skills",
  "agent-details": "/agents",
};

const ORGANIZATION_ADMIN_STEPS: readonly ProductTourStep[] = [
  {
    id: "members",
    target: '[data-tour="nav-members"]',
    title: "Manage your team",
    content:
      "Invite teammates, review membership, and manage the roles that control access to your organization.",
    placement: "right",
  },
  {
    id: "billing",
    target: '[data-tour="nav-billing"]',
    title: "Manage billing",
    content:
      "Review your organization plan, usage, and billing actions from the Billing area.",
    placement: "right",
  },
  {
    id: "organization",
    target: '[data-tour="nav-organization"]',
    title: "Configure the organization",
    content:
      "Update organization details and credentials that power your workspace and agents.",
    placement: "right",
  },
];

const PLATFORM_ADMIN_STEPS: readonly ProductTourStep[] = [
  {
    id: "organizations",
    target: '[data-tour="nav-organizations"]',
    title: "Oversee organizations",
    content:
      "Review and manage organizations across the 24x7 AI platform from this platform-only area.",
    placement: "right",
  },
  {
    id: "all-users",
    target: '[data-tour="nav-all-users"]',
    title: "Manage all users",
    content:
      "Find platform users and review access across organizations from a central administration view.",
    placement: "right",
  },
  {
    id: "platform-skills",
    target: '[data-tour="nav-platform-skills"]',
    title: "Curate platform skills",
    content:
      "Create and maintain the reusable skill templates available to organizations on the platform.",
    placement: "right",
  },
  {
    id: "platform-tools",
    target: '[data-tour="nav-platform-tools"]',
    title: "Manage platform tools",
    content:
      "Configure the tools and integrations that can be made available to organization agents.",
    placement: "right",
  },
  {
    id: "voice-presets",
    target: '[data-tour="nav-voice-presets"]',
    title: "Tune voice presets",
    content:
      "Maintain the voice and pipeline presets used when organizations configure their agents.",
    placement: "right",
  },
  {
    id: "platform-settings",
    target: '[data-tour="nav-platform-settings"]',
    title: "Manage platform settings",
    content:
      "Configure platform notification delivery and phone-number lifecycle policies in one place.",
    placement: "right",
  },
  {
    id: "plan-catalog",
    target: '[data-tour="nav-plan-catalog"]',
    title: "Manage the plan catalog",
    content:
      "Maintain the plans and entitlements available to organizations across the platform.",
    placement: "right",
  },
];

const USER_MENU_STEP: ProductTourStep = {
  id: "user-menu",
  target: '[data-tour="user-menu"]',
  title: "Your account menu",
  content:
    "Open this menu any time to reach Settings, switch the theme, or sign out. Use the help icon in the header whenever you want to replay the walkthrough.",
  placement: "bottom",
};

/**
 * Returns the ordered walkthrough for a user's effective role.
 *
 * Platform admins inherit organization-admin capabilities, so their tour
 * includes workspace, organization, and platform administration steps.
 *
 * @param role Effective role for the current organization context
 * @returns A fresh ordered array of tour steps
 */
export function getProductTourSteps(
  role: ProductTourRole,
): ProductTourStep[] {
  const roleSteps =
    role === "platform_admin"
      ? [...ORGANIZATION_ADMIN_STEPS, ...PLATFORM_ADMIN_STEPS]
      : role === "org_admin"
        ? [...ORGANIZATION_ADMIN_STEPS]
        : [];

  return [...WORKSPACE_STEPS, ...roleSteps, USER_MENU_STEP];
}

/**
 * Returns the ordered in-context walkthrough for a feature branch.
 *
 * Branch tours deliberately stay focused on the view the user opened. They
 * are optional extensions of the overview tour, so a user can skip one and
 * return to the overview without changing the overview's persisted outcome.
 *
 * @param branch Feature area to explain inside its route
 * @param role Effective role for the current organization context
 * @returns A fresh role-filtered array of branch steps
 */
export function getProductTourBranchSteps(
  branch: ProductTourBranch,
  role: ProductTourRole,
): ProductTourStep[] {
  const definitions =
    branch === "agents"
      ? AGENTS_BRANCH_STEPS
      : branch === "calls"
        ? CALLS_BRANCH_STEPS
        : branch === "skills"
          ? SKILLS_BRANCH_STEPS
          : AGENT_DETAILS_BRANCH_STEPS;

  return definitions
    .filter((step) => !step.roles || step.roles.includes(role))
    .map((step) => ({ ...step }));
}

/**
 * Resolves the dashboard route that hosts a feature branch tour.
 *
 * @param branch Feature area to open
 * @returns Route used to render the branch's in-context targets
 */
export function getProductTourBranchRoute(branch: ProductTourBranch): string {
  return PRODUCT_TOUR_BRANCH_ROUTES[branch];
}

/**
 * Resolves the contextual walkthrough for a dashboard pathname.
 *
 * The agent creation flow is intentionally excluded because its existing
 * widget already guides the user through creation. Agent detail routes get a
 * short orientation tour, while the list-level branches explain the broader
 * workspace actions.
 *
 * @param pathname Current dashboard pathname without query parameters
 * @returns Matching contextual branch, or null for pages without one
 */
export function getProductTourBranchForPath(
  pathname: string,
): ProductTourBranch | null {
  if (pathname === "/agents") return "agents";
  if (pathname === "/calls") return "calls";
  if (pathname === "/skills") return "skills";
  if (pathname === "/agents/create") return null;
  if (/^\/agents\/[^/]+$/.test(pathname)) return "agent-details";
  return null;
}

/**
 * Maps permission-derived role flags to the tour's internal role key.
 *
 * @param flags Role flags resolved from the authenticated user and current org
 * @returns Platform admin, org admin, or regular member role
 */
export function getProductTourRole(flags: {
  isPlatformAdmin: boolean;
  isOrgAdmin: boolean;
}): ProductTourRole {
  if (flags.isPlatformAdmin) return "platform_admin";
  if (flags.isOrgAdmin) return "org_admin";
  return "member";
}

/**
 * Builds the versioned local-storage key for one user's tour state.
 *
 * @param userId Authenticated user's stable ID
 * @param role Effective tour role; defaults to the regular-user experience
 * @returns Namespaced storage key
 */
export function getProductTourStorageKey(
  userId: string,
  role: ProductTourRole = "member",
  scope: ProductTourStorageScope = "main",
): string {
  const baseKey = `24x7-ai.product-tour.${PRODUCT_TOUR_VERSION}.${role}.${userId}`;
  return scope === "main" ? baseKey : `${baseKey}.${scope}`;
}

/**
 * Reads a valid persisted tour outcome.
 *
 * @param storage Storage-like reader, injected to keep the helper testable
 * @param userId Authenticated user's stable ID
 * @param role Effective tour role
 * @returns Completed/skipped state, or null when absent/invalid
 */
export function readProductTourStatus(
  storage: ProductTourStorageReader,
  userId: string,
  role: ProductTourRole = "member",
  scope: ProductTourStorageScope = "main",
): ProductTourStatus | null {
  const value = storage.getItem(getProductTourStorageKey(userId, role, scope));
  return value === "skipped" || value === "completed" ? value : null;
}

/**
 * Persists a tour outcome for the current user and tour version.
 *
 * @param storage Storage-like writer, injected to keep the helper testable
 * @param userId Authenticated user's stable ID
 * @param status Outcome to persist
 * @param role Effective tour role
 */
export function writeProductTourStatus(
  storage: ProductTourStorageWriter,
  userId: string,
  status: ProductTourStatus,
  role: ProductTourRole = "member",
  scope: ProductTourStorageScope = "main",
): void {
  storage.setItem(getProductTourStorageKey(userId, role, scope), status);
}

/**
 * Clears the stored outcome so the tour can be started from step one again.
 *
 * @param storage Storage-like remover, injected to keep the helper testable
 * @param userId Authenticated user's stable ID
 * @param role Effective tour role
 */
export function clearProductTourStatus(
  storage: ProductTourStorageRemover,
  userId: string,
  role: ProductTourRole = "member",
  scope: ProductTourStorageScope = "main",
): void {
  storage.removeItem(getProductTourStorageKey(userId, role, scope));
}

// TODO: [Persistence] Move tour status to a backend user preference before
// multi-device onboarding state is required; localStorage is intentionally a
// low-friction first iteration for this client-only walkthrough.
