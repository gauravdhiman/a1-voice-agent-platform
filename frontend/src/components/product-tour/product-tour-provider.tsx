"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  ACTIONS,
  STATUS,
  type EventHandler,
  type Step,
  type TooltipRenderProps,
  useJoyride,
} from "react-joyride";
import { useAuth } from "@/contexts/auth-context";
import { useUserPermissions } from "@/hooks/use-user-permissions";
import {
  clearProductTourStatus,
  getProductTourBranchForPath,
  getProductTourBranchRoute,
  getProductTourBranchSteps,
  getProductTourRole,
  getProductTourSteps,
  readProductTourStatus,
  writeProductTourStatus,
  type ProductTourBranch,
  type ProductTourRole,
} from "@/lib/product-tour";

type ProductTourName = "main" | ProductTourBranch;

interface ProductTourContextValue {
  /** Replays the walkthrough for the current page or the overview. */
  openProductTour: () => void;
  /** Clears the overview outcome and starts the overview at its first step. */
  restartProductTour: () => void;
}

interface ProductTourProviderProps {
  /** Dashboard content that should remain available while the tour is open. */
  children: React.ReactNode;
}

interface PendingTourStart {
  /** Route whose in-context target must be rendered before Joyride runs. */
  route: string | null;
  /** First target used as the readiness signal for the route. */
  target: string;
}

interface ProductTourStepData {
  /** Active level in the overview/branch tour tree. */
  tour: ProductTourName;
  /** Optional branch that can be opened from an overview step. */
  branch?: ProductTourBranch;
  /** Human-readable label used by the branch action. */
  branchLabel?: string;
  /** Opens the branch from an overview step. */
  onExplore?: () => void;
  /** Returns from a branch to the overview. */
  onBack?: () => void;
}

const ProductTourContext = createContext<ProductTourContextValue | undefined>(
  undefined,
);

const BRANCH_LABELS: Record<ProductTourBranch, string> = {
  agents: "Agents",
  calls: "Calls",
  skills: "Skills",
  "agent-details": "Agent settings",
};

function getBrowserStorage(): Storage | null {
  if (typeof window === "undefined") return null;

  try {
    return window.localStorage ?? null;
  } catch {
    // Storage can be unavailable in privacy-restricted browser contexts. The
    // tour remains usable for the current session in that case.
    return null;
  }
}

/**
 * Renders the product tour popover with explicit overview and branch actions.
 *
 * The custom tooltip keeps branch navigation visible without adding a second
 * persistent control to the dashboard. The main tour can open an in-context
 * branch, and every branch exposes a direct route back to the overview.
 *
 * @param props Joyride's current tooltip state and button handlers
 * @returns Branded, keyboard-accessible product tour tooltip
 */
export function ProductTourTooltip({
  backProps,
  continuous,
  index,
  isLastStep,
  primaryProps,
  skipProps,
  step,
  tooltipProps,
  size,
}: TooltipRenderProps): React.JSX.Element {
  const data = (step.data ?? {}) as ProductTourStepData;
  const isBranch = data.tour !== "main";

  return (
    <div
      {...tooltipProps}
      className="w-[min(380px,calc(100vw-2rem))] overflow-hidden rounded-2xl border border-border bg-popover text-popover-foreground shadow-2xl shadow-foreground/10"
    >
      <div className="h-1 bg-primary" />
      <div className="space-y-4 p-5">
        <div className="flex items-center justify-between gap-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-primary/80">
          <span>
            {isBranch
              ? `${BRANCH_LABELS[data.tour as ProductTourBranch]} deep dive`
              : "Guided walkthrough"}
          </span>
          <span className="tabular-nums text-muted-foreground">
            {index + 1} / {size}
          </span>
        </div>

        <div className="space-y-2">
          <h3 className="text-base font-semibold tracking-tight text-foreground">
            {step.title}
          </h3>
          <p className="text-sm leading-6 text-muted-foreground">{step.content}</p>
        </div>

        {(data.onExplore || data.onBack) && (
          <div className="flex flex-wrap gap-2 border-t border-border pt-3">
            {data.onExplore && data.branch && (
              <button
                type="button"
                className="inline-flex items-center rounded-lg border border-primary/40 bg-primary/10 px-3 py-2 text-xs font-semibold text-primary transition-colors hover:bg-primary/20 focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  data.onExplore?.();
                }}
              >
                Explore {BRANCH_LABELS[data.branch]}
              </button>
            )}
            {data.onBack && (
              <button
                type="button"
                className="inline-flex items-center rounded-lg border border-border px-3 py-2 text-xs font-semibold text-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  data.onBack?.();
                }}
              >
                Back to overview
              </button>
            )}
          </div>
        )}

        <div className="flex items-center justify-between gap-2 border-t border-border pt-3">
          <div className="flex items-center gap-1">
            {index > 0 && (
              <button
                {...backProps}
                className="rounded-lg px-2.5 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring"
              >
                Back
              </button>
            )}
            <button
              {...skipProps}
              className="rounded-lg px-2.5 py-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground focus:outline-none focus:ring-2 focus:ring-ring"
            >
              Skip tour
            </button>
          </div>
          {continuous && (
            <button
              {...primaryProps}
              className="rounded-lg bg-primary px-3.5 py-2 text-xs font-bold text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
            >
              {isLastStep ? "Finish" : "Next"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

/**
 * Provides the role-aware product walkthrough and its restart action.
 *
 * The provider owns a small navigation tree: the overview tour starts
 * automatically for a new user, and optional Agents, Calls, and Skills
 * branches navigate to their real routes before starting in-context steps.
 * Branches opened from the overview can return to it; contextual tours opened
 * from a page stay on that page after completion or skipping.
 *
 * @param children Dashboard shell and page content
 * @returns Dashboard content plus the Joyride tour portal
 */
export function ProductTourProvider({
  children,
}: ProductTourProviderProps): React.JSX.Element {
  const { user, loading: authLoading } = useAuth();
  const { isPlatformAdmin, isOrgAdmin, isLoading: permissionsLoading } =
    useUserPermissions();
  const router = useRouter();
  const pathname = usePathname();
  const [activeTour, setActiveTour] = useState<ProductTourName>("main");
  const [run, setRun] = useState(false);
  const [startIndex, setStartIndex] = useState(0);
  const [pendingStart, setPendingStart] = useState<PendingTourStart | null>(
    null,
  );
  const initializedTourKey = useRef<string | null>(null);
  const autoStartedContextKey = useRef<string | null>(null);
  const mainResumeIndex = useRef(0);
  const branchReturnsToOverview = useRef(false);

  const role: ProductTourRole = getProductTourRole({
    isPlatformAdmin,
    isOrgAdmin,
  });
  const userId = user?.id ?? null;

  const queueTourStart = useCallback(
    (
      tour: ProductTourName,
      index: number,
      route: string | null,
      target: string,
    ) => {
      setRun(false);
      setActiveTour(tour);
      setStartIndex(index);
      setPendingStart({ route, target });
      if (route && pathname !== route) router.push(route);
    },
    [pathname, router],
  );

  const returnToOverview = useCallback(
    (resumeIndex: number) => {
      queueTourStart(
        "main",
        resumeIndex,
        "/dashboard",
        '[data-tour="brand"]',
      );
    },
    [queueTourStart],
  );

  const startBranch = useCallback(
    (branch: ProductTourBranch, overviewStepIndex: number) => {
      const overviewSteps = getProductTourSteps(role);
      mainResumeIndex.current = Math.min(
        overviewStepIndex + 1,
        Math.max(overviewSteps.length - 1, 0),
      );
      branchReturnsToOverview.current = true;
      queueTourStart(
        branch,
        0,
        getProductTourBranchRoute(branch),
        getProductTourBranchSteps(branch, role)[0]?.target ?? "body",
      );
    },
    [queueTourStart, role],
  );

  const startContextualBranch = useCallback(
    (branch: ProductTourBranch) => {
      branchReturnsToOverview.current = false;
      const route = branch === "agent-details"
        ? pathname
        : getProductTourBranchRoute(branch);
      queueTourStart(
        branch,
        0,
        route,
        getProductTourBranchSteps(branch, role)[0]?.target ?? "body",
      );
    },
    [pathname, queueTourStart, role],
  );

  const steps = useMemo<Step[]>(() => {
    const definitions =
      activeTour === "main"
        ? getProductTourSteps(role)
        : getProductTourBranchSteps(activeTour, role);

    return definitions.map((step, index) => ({
      id: step.id,
      target: step.target,
      title: step.title,
      content: step.content,
      placement: step.placement,
      // The walkthrough is a guided surface, not a notification that users
      // must discover by clicking a beacon.
      skipBeacon: true,
      data: {
        tour: activeTour,
        branch: step.branch,
        branchLabel: step.branch ? BRANCH_LABELS[step.branch] : undefined,
        onExplore:
          activeTour === "main" && step.branch
            ? () => startBranch(step.branch as ProductTourBranch, index)
            : undefined,
        onBack:
          activeTour !== "main" && branchReturnsToOverview.current
            ? () => returnToOverview(mainResumeIndex.current)
            : undefined,
      } satisfies ProductTourStepData,
    }));
  }, [activeTour, returnToOverview, role, startBranch]);

  const handleEvent = useCallback<EventHandler>(
    (data) => {
      const isExitEvent =
        data.status === STATUS.SKIPPED ||
        data.status === STATUS.FINISHED ||
        data.action === ACTIONS.SKIP ||
        data.action === ACTIONS.COMPLETE;

      if (!isExitEvent) return;

      if (activeTour !== "main") {
        if (userId) {
          const storage = getBrowserStorage();
          if (storage) {
            writeProductTourStatus(
              storage,
              userId,
              data.status === STATUS.SKIPPED || data.action === ACTIONS.SKIP
                ? "skipped"
                : "completed",
              role,
              activeTour,
            );
          }
        }
        if (branchReturnsToOverview.current) {
          branchReturnsToOverview.current = false;
          returnToOverview(mainResumeIndex.current);
        } else {
          setRun(false);
        }
        return;
      }

      if (!userId) {
        setRun(false);
        return;
      }

      const storage = getBrowserStorage();
      if (storage) {
        if (data.status === STATUS.SKIPPED || data.action === ACTIONS.SKIP) {
          writeProductTourStatus(storage, userId, "skipped", role);
        } else {
          writeProductTourStatus(storage, userId, "completed", role);
        }
      }
      setRun(false);
    },
    [activeTour, role, returnToOverview, userId],
  );

  const { Tour } = useJoyride({
    steps,
    run,
    initialStepIndex: startIndex,
    continuous: true,
    scrollToFirstStep: true,
    onEvent: handleEvent,
    options: {
      buttons: ["back", "skip", "primary"],
      closeButtonAction: "skip",
      skipBeacon: true,
      overlayClickAction: false,
      primaryColor: "var(--primary)",
      backgroundColor: "var(--popover)",
      textColor: "var(--popover-foreground)",
      overlayColor: "rgba(8, 18, 38, 0.58)",
      spotlightRadius: 12,
      zIndex: 1000,
    },
    tooltipComponent: ProductTourTooltip,
    locale: {
      back: "Back",
      next: "Next",
      nextWithProgress: "Next ({current} of {total})",
      last: "Finish",
      skip: "Skip tour",
    },
  });

  useEffect(() => {
    if (authLoading || permissionsLoading || !userId) {
      setRun(false);
      return;
    }

    const tourKey = `${userId}:${role}`;
    if (initializedTourKey.current === tourKey) return;
    initializedTourKey.current = tourKey;
    autoStartedContextKey.current = null;

    const storage = getBrowserStorage();
    const status = storage ? readProductTourStatus(storage, userId, role) : null;
    if (status === null) {
      setActiveTour("main");
      setStartIndex(0);
      setPendingStart({
        route: null,
        target: '[data-tour="brand"]',
      });
    } else {
      setRun(false);
    }
  }, [authLoading, permissionsLoading, role, userId]);

  useEffect(() => {
    if (authLoading || permissionsLoading || !userId) return;

    const storage = getBrowserStorage();
    const overviewStatus = storage
      ? readProductTourStatus(storage, userId, role)
      : null;
    if (overviewStatus === null) return;

    const branch = getProductTourBranchForPath(pathname);
    if (!branch) return;

    const contextKey = `${userId}:${role}:${branch}`;
    if (autoStartedContextKey.current === contextKey) return;

    const branchStatus = storage
      ? readProductTourStatus(storage, userId, role, branch)
      : null;
    if (branchStatus !== null) return;

    autoStartedContextKey.current = contextKey;
    startContextualBranch(branch);
  }, [
    authLoading,
    pathname,
    permissionsLoading,
    role,
    run,
    startContextualBranch,
    userId,
  ]);

  useEffect(() => {
    if (!pendingStart || authLoading || permissionsLoading || !userId) return;
    if (pendingStart.route === null) {
      setPendingStart(null);
      setRun(true);
      return;
    }
    if (pathname !== pendingStart.route) return;

    let attempts = 0;
    let timeoutId: number | undefined;
    const waitForTarget = () => {
      if (document.querySelector(pendingStart.target)) {
        setPendingStart(null);
        setRun(true);
        return;
      }

      attempts += 1;
      if (attempts >= 60) {
        // Let Joyride surface its normal target-not-found handling rather than
        // leaving the user with a tour that never starts after a slow route.
        setPendingStart(null);
        setRun(true);
        return;
      }
      timeoutId = window.setTimeout(waitForTarget, 50);
    };

    waitForTarget();
    return () => {
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [authLoading, pathname, pendingStart, permissionsLoading, userId]);

  const restartProductTour = useCallback(() => {
    if (!userId) return;

    const storage = getBrowserStorage();
    if (storage) clearProductTourStatus(storage, userId, role);
    mainResumeIndex.current = 0;
    branchReturnsToOverview.current = false;
    queueTourStart("main", 0, "/dashboard", '[data-tour="brand"]');
  }, [queueTourStart, role, userId]);

  const openProductTour = useCallback(() => {
    if (!userId) return;

    const branch = getProductTourBranchForPath(pathname);
    if (branch) {
      startContextualBranch(branch);
      return;
    }

    branchReturnsToOverview.current = false;
    queueTourStart("main", 0, "/dashboard", '[data-tour="brand"]');
  }, [pathname, queueTourStart, startContextualBranch, userId]);

  const contextValue = useMemo<ProductTourContextValue>(
    () => ({ openProductTour, restartProductTour }),
    [openProductTour, restartProductTour],
  );

  return (
    <ProductTourContext.Provider value={contextValue}>
      {children}
      {Tour}
    </ProductTourContext.Provider>
  );
}

/**
 * Accesses the product-tour controls from dashboard descendants.
 *
 * @returns Product-tour actions
 * @throws Error when rendered outside ProductTourProvider
 */
export function useProductTour(): ProductTourContextValue {
  const context = useContext(ProductTourContext);
  if (!context) {
    throw new Error("useProductTour must be used within ProductTourProvider");
  }
  return context;
}
