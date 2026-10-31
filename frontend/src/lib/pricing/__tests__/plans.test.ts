import { describe, expect, it } from "vitest";
import {
  PLANS,
  PLAN_ORDER,
  formatMonthlyPrice,
  formatMonthlyPriceCompact,
  formatPriceUSD,
  getCompactPricingCopy,
  getLowestPaidPlanPrice,
  getPlanById,
  getStandardPricingCopy,
} from "@/lib/pricing/plans";

describe("public plan catalog", () => {
  it("locks the GTM Priority 1 amounts and names", () => {
    expect(PLANS.FREE).toMatchObject({
      id: "free",
      displayName: "Free",
      monthlyUSD: 0,
      monthlyCents: 0,
    });
    expect(PLANS.STARTER).toMatchObject({
      id: "starter",
      displayName: "Starter",
      monthlyUSD: 79,
      monthlyCents: 7900,
      annualUSD: 790,
      annualCents: 79000,
      creditsPerMonth: 2500,
      approximateMinutes: 250,
    });
    expect(PLANS.PRO).toMatchObject({
      id: "pro",
      displayName: "Pro",
      monthlyUSD: 149,
      monthlyCents: 14900,
    });
    expect(PLANS.SCALE).toMatchObject({
      id: "scale",
      displayName: "Scale",
      monthlyUSD: 299,
      monthlyCents: 29900,
    });
    expect(PLAN_ORDER).toEqual(["free", "starter", "pro", "scale"]);
  });

  it("formats marketing copy from the shared Starter amount", () => {
    expect(formatPriceUSD(PLANS.STARTER.monthlyUSD)).toBe("$79");
    expect(formatMonthlyPrice(PLANS.STARTER.monthlyUSD)).toBe("$79/month");
    expect(formatMonthlyPriceCompact(PLANS.STARTER.monthlyUSD)).toBe("$79/mo");
    expect(getLowestPaidPlanPrice()).toBe(79);
    expect(getStandardPricingCopy()).toBe(
      "Plans from $79/month, including up to 250 call minutes",
    );
    expect(getCompactPricingCopy()).toBe("Plans from $79/mo");
    expect(getPlanById("starter")).toEqual(PLANS.STARTER);
  });
});
