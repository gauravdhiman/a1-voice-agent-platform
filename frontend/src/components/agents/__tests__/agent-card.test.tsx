/**
 * Tests for <AgentCard> row-action permission gates.
 *
 * Contract (mirrors the N1 permission-aware-UI follow-up; see
 * `docs/tw-drafts/navigation-redesign.md` Section 6.5 + the user
 * feedback that "actions like deleting a skill ... should respect
 * the permissions of the user's role"):
 *
 *   - When `canDelete` is false (e.g. a regular org member), the
 *     per-card trash icon (in both list and grid views) MUST NOT
 *     be rendered. The page-level onDelete click is harmless, but
 *     surfacing the icon promises a destructive action that the
 *     page would deny.
 *   - When `canEdit` is false, the "Edit" / pencil button is hidden
 *     in BOTH the list view (text-labeled "Edit" button) and the
 *     grid view (icon-only top-right button). The same goes for
 *     the "Tools" / "Configure Tools" button gated on
 *     `canConfigure` in the list view; the grid-view "Configure
 *     Tools" footer button is the only one on the grid card and
 *     is gated on `canConfigure` too.
 *   - When all three flags are true (e.g. an org admin), every
 *     button renders.
 *   - When the flags are NOT passed at all (existing call sites
 *     pre-N1), the buttons still render — the prop is optional
 *     and the default is "show everything", so this is a
 *     backward-compatible change. The page is the right place to
 *     make the gate strict; the card just respects the prop.
 */
import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
  }),
  useSearchParams: () => ({ get: vi.fn().mockReturnValue(null) }),
  useParams: () => ({}),
  usePathname: () => "/agents",
}));

import { AgentCard } from "../agent-card";
import type { VoiceAgent } from "@/types/agent";

const FIXTURE_AGENT: VoiceAgent = {
  id: "agent-1",
  organization_id: "org-1",
  name: "Fixture Agent",
  is_active: true,
  phone_number: "+15555550100",
  system_prompt: "You are a fixture.",
  // Fields below are not all required by the type but the card may
  // read them. Cast to `VoiceAgent` to keep the fixture minimal.
} as unknown as VoiceAgent;

function makeWrapper(queryClient: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
}

/**
 * The trash icon inside AgentCard is rendered as a lucide-react
 * <Trash2 /> SVG. lucide-react sets `class="lucide lucide-trash2"`.
 * There is no aria-label; the test pins the icon by its class name
 * (stable across lucide-react versions) inside the relevant card
 * scope. If lucide ever changes the class, the test will need an
 * update; the alternative (a data-testid on the icon) is owned by
 * the component, not the test.
 */
function queryTrashIcons() {
  return Array.from(document.querySelectorAll("svg.lucide-trash2"));
}

describe("AgentCard - row-action permission gates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("list view", () => {
    it("hides the trash icon when canDelete=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
          canDelete={false}
          canEdit
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(
        queryTrashIcons().length,
        "list view must not render the trash icon when canDelete is false",
      ).toBe(0);
    });

    it("renders the trash icon when canDelete=true", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
          canDelete
          canEdit
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(queryTrashIcons().length).toBeGreaterThan(0);
    });

    it("hides the Edit button when canEdit=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
          canDelete
          canEdit={false}
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      // List view has a text-labeled "Edit" button. The grid view
      // also has a top-right icon button, but this test renders the
      // list view only, so the only "Edit" should be the labeled one.
      expect(
        screen.queryByRole("button", { name: /^edit$/i }),
        "list view must not render the Edit button when canEdit is false",
      ).not.toBeInTheDocument();
    });

    it("hides the Tools button when canConfigure=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
          canDelete
          canEdit
          canConfigure={false}
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      // List view has a text-labeled "Tools" button.
      expect(
        screen.queryByRole("button", { name: /^tools$/i }),
        "list view must not render the Tools button when canConfigure is false",
      ).not.toBeInTheDocument();
    });

    it("renders all three actions when canDelete+canEdit+canConfigure are true", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
          canDelete
          canEdit
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(screen.getByRole("button", { name: /^edit$/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^tools$/i })).toBeInTheDocument();
      expect(queryTrashIcons().length).toBeGreaterThan(0);
    });
  });

  describe("grid view", () => {
    it("hides the trash icon when canDelete=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="grid"
          canDelete={false}
          canEdit
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(
        queryTrashIcons().length,
        "grid view must not render the trash icon when canDelete is false",
      ).toBe(0);
    });

    it("hides the Edit icon button when canEdit=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="grid"
          canDelete
          canEdit={false}
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      // Grid view has an icon-only Edit3 button + a trash button +
      // a footer "Configure Tools" button. When canEdit=false, the
      // icon-only Edit button must not render. We can't name-by-text
      // (it's icon-only), so we count ghost-variant icon buttons
      // in the card's top-right cluster.
      const edit3Icons = document.querySelectorAll("svg.lucide-edit-3");
      // 0 because the only edit button in the grid view is the
      // top-right icon button (gated on canEdit). The right side
      // trash icon would still appear if canDelete were true.
      expect(
        edit3Icons.length,
        "grid view must not render the Edit icon button when canEdit is false",
      ).toBe(0);
    });

    it("hides the Configure Tools footer button when canConfigure=false", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="grid"
          canDelete
          canEdit
          canConfigure={false}
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(
        screen.queryByRole("button", { name: /configure tools/i }),
        "grid view must not render the Configure Tools footer button when canConfigure is false",
      ).not.toBeInTheDocument();
    });

    it("renders the trash icon when canDelete=true", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="grid"
          canDelete
          canEdit
          canConfigure
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(queryTrashIcons().length).toBeGreaterThan(0);
    });
  });

  describe("backward compatibility", () => {
    it("renders all actions when the permission flags are NOT passed (legacy call sites)", () => {
      // Pre-N1 call sites (e.g. test fixtures) don't pass the flags.
      // The card must continue to render every action in that case
      // so existing usage does not silently lose functionality. The
      // page-level wire-up is the strict gate; the card is permissive
      // by default.
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="list"
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(screen.getByRole("button", { name: /^edit$/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /^tools$/i })).toBeInTheDocument();
      expect(queryTrashIcons().length).toBeGreaterThan(0);
    });

    it("renders the trash icon in the grid view when the permission flags are NOT passed", () => {
      const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
      });

      render(
        <AgentCard
          agent={FIXTURE_AGENT}
          organizationName="Acme"
          onDelete={vi.fn()}
          view="grid"
        />,
        { wrapper: makeWrapper(queryClient) },
      );

      expect(queryTrashIcons().length).toBeGreaterThan(0);
    });
  });
});
