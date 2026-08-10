/**
 * Service for billing API operations
 */

import { apiClient } from "@/lib/api/client";
import type {
  SubscriptionPlan,
  SubscriptionPlanCreate,
  SubscriptionPlanUpdate,
  OrganizationSubscriptionWithPlan,
  CreditEvent,
  CreditProduct,
  BillingHistory,
  OrganizationBillingSummary,
  CreditBalance,
  CreditUsageResponse,
  CreditConsumptionRequest,
  CreditConsumptionResponse,
  CreditPurchaseResponse,
  OrgEntitlements,
  PlanMigrationResponse,
  CustomerPlanVersion,
  FreePlanActivationResponse,
  SubscriptionActivationStatus,
  VersionedSubscriptionCheckoutRequest,
  VersionedSubscriptionCheckoutResponse,
  PlanChangePreview,
  PlanChangeConfirmationResponse,
} from "@/types/billing";

class BillingService {
  private baseUrl = "/api/v1/billing";

  // Subscription Plans
  /**
   * Fetches the legacy flat subscription catalog.
   *
   * @deprecated Customer-facing plan selection must use
   * `getAvailablePlanVersions`, which resolves platform plan products and
   * immutable versions. This method remains for compatibility with legacy
   * records and webhook fallback handling.
   */
  async getSubscriptionPlans(
    activeOnly: boolean = true,
  ): Promise<SubscriptionPlan[]> {
    const params = new URLSearchParams();
    if (activeOnly) params.append("active_only", "true");

    const response = await apiClient.get<SubscriptionPlan[]>(
      `${this.baseUrl}/plans?${params}`,
    );
    return response.data;
  }

  async createSubscriptionPlan(
    planData: SubscriptionPlanCreate,
  ): Promise<SubscriptionPlan> {
    const response = await apiClient.post<SubscriptionPlan>(
      `${this.baseUrl}/plans`,
      planData,
    );
    return response.data;
  }

  async getSubscriptionPlan(planId: string): Promise<SubscriptionPlan> {
    const response = await apiClient.get<SubscriptionPlan>(
      `${this.baseUrl}/plans/${planId}`,
    );
    return response.data;
  }

  /**
   * Fetches published plan versions that are available to new organizations.
   *
   * @returns Promise resolving to customer-safe plan catalog entries.
   */
  async getAvailablePlanVersions(): Promise<CustomerPlanVersion[]> {
    const response = await apiClient.get<CustomerPlanVersion[]>(
      `${this.baseUrl}/plans/available`,
    );
    return response.data;
  }

  /**
   * Activates a free plan version without invoking Stripe.
   *
   * @param organizationId Organization being enrolled
   * @param planVersionId Published free plan version selected by the founder
   */
  async activateFreePlan(
    organizationId: string,
    planVersionId: string,
  ): Promise<FreePlanActivationResponse> {
    const response = await apiClient.post<FreePlanActivationResponse>(
      `${this.baseUrl}/subscription/free`,
      { organization_id: organizationId, plan_version_id: planVersionId },
    );
    return response.data;
  }

  /**
   * Starts Stripe Checkout for a published paid plan version.
   *
   * @param request Organization, immutable plan version, and return URLs
   */
  async createVersionedSubscriptionCheckout(
    request: VersionedSubscriptionCheckoutRequest,
  ): Promise<VersionedSubscriptionCheckoutResponse> {
    const response =
      await apiClient.post<VersionedSubscriptionCheckoutResponse>(
        `${this.baseUrl}/checkout/versioned-subscription`,
        request,
      );
    return response.data;
  }

  /**
   * Previews an active subscription transition without mutating billing state.
   *
   * @param organizationId Organization whose subscription is changing
   * @param targetPlanVersionId Published internal target version
   */
  async previewPlanChange(
    organizationId: string,
    targetPlanVersionId: string,
  ): Promise<PlanChangePreview> {
    const response = await apiClient.post<PlanChangePreview>(
      `${this.baseUrl}/subscription/plan-change/preview`,
      {
        organization_id: organizationId,
        target_plan_version_id: targetPlanVersionId,
      },
    );
    return response.data;
  }

  /**
   * Confirms a previewed plan transition after the user reviews its effects.
   */
  async confirmPlanChange(request: {
    organization_id: string;
    transition_id: string;
    target_plan_version_id: string;
    success_url?: string;
    cancel_url?: string;
  }): Promise<PlanChangeConfirmationResponse> {
    const response = await apiClient.post<PlanChangeConfirmationResponse>(
      `${this.baseUrl}/subscription/plan-change/confirm`,
      request,
    );
    return response.data;
  }

  /**
   * Gets the activation state used while waiting for Stripe webhooks.
   *
   * @param organizationId Organization whose activation is being checked
   */
  async getSubscriptionActivationStatus(
    organizationId: string,
  ): Promise<SubscriptionActivationStatus> {
    const response = await apiClient.get<SubscriptionActivationStatus>(
      `${this.baseUrl}/subscription/status/${organizationId}`,
    );
    return response.data;
  }

  async updateSubscriptionPlan(
    planId: string,
    planData: SubscriptionPlanUpdate,
  ): Promise<SubscriptionPlan> {
    const response = await apiClient.put<SubscriptionPlan>(
      `${this.baseUrl}/plans/${planId}`,
      planData,
    );
    return response.data;
  }

  // Organization Subscriptions
  async getOrganizationSubscription(
    organizationId: string,
  ): Promise<OrganizationSubscriptionWithPlan> {
    const response = await apiClient.get<OrganizationSubscriptionWithPlan>(
      `${this.baseUrl}/subscription/${organizationId}`,
    );
    return response.data;
  }

  /**
   * Fetches resolved plan-version entitlements including migration/grace info.
   */
  async getOrganizationEntitlements(
    organizationId: string,
  ): Promise<OrgEntitlements> {
    const response = await apiClient.get<OrgEntitlements>(
      `${this.baseUrl}/entitlements/${organizationId}`,
    );
    return response.data;
  }

  /**
   * Self-service migrate to a newer plan version before grace period ends.
   */
  async migrateSubscriptionPlan(
    organizationId: string,
  ): Promise<PlanMigrationResponse> {
    const response = await apiClient.post<PlanMigrationResponse>(
      `${this.baseUrl}/subscription/migrate`,
      { organization_id: organizationId },
    );
    return response.data;
  }

  async createCustomerPortal(
    organizationId: string,
    returnUrl: string,
  ): Promise<{ portal_url: string }> {
    console.log("Creating customer portal for organization:", organizationId);
    console.log("Return URL:", returnUrl);

    try {
      const response = await apiClient.post<{ portal_url: string }>(
        `${this.baseUrl}/subscription/portal`,
        {
          organization_id: organizationId,
          return_url: returnUrl,
        },
      );
      console.log("Customer portal response:", response);
      return response.data;
    } catch (error) {
      console.error("Customer portal creation failed:", error);
      throw error;
    }
  }

  // Credits
  async getCreditBalance(organizationId: string): Promise<CreditBalance> {
    const response = await apiClient.get<CreditBalance>(
      `${this.baseUrl}/credits/${organizationId}`,
    );
    return response.data;
  }

  /**
   * Fetches the organization's current credit pools, period usage, category
   * breakdown, and recent ledger entries for the reporting dashboard.
   *
   * @param organizationId Organization whose credit usage is requested
   * @returns Promise resolving to the dashboard-ready credit usage payload
   */
  async getCreditUsage(organizationId: string): Promise<CreditUsageResponse> {
    const response = await apiClient.get<CreditUsageResponse>(
      `${this.baseUrl}/credits/${organizationId}/usage`,
    );
    return response.data;
  }

  async consumeCredits(
    consumptionRequest: CreditConsumptionRequest,
  ): Promise<CreditConsumptionResponse> {
    const response = await apiClient.post<CreditConsumptionResponse>(
      `${this.baseUrl}/credits/consume`,
      consumptionRequest,
    );
    return response.data;
  }

  async getCreditEvents(activeOnly: boolean = true): Promise<CreditEvent[]> {
    const params = new URLSearchParams();
    if (activeOnly) params.append("active_only", "true");

    const response = await apiClient.get<CreditEvent[]>(
      `${this.baseUrl}/credit-events?${params}`,
    );
    return response.data;
  }

  async getCreditProducts(
    activeOnly: boolean = true,
  ): Promise<CreditProduct[]> {
    const params = new URLSearchParams();
    if (activeOnly) params.append("active_only", "true");

    const response = await apiClient.get<CreditProduct[]>(
      `${this.baseUrl}/credit-products?${params}`,
    );
    return response.data;
  }

  async createCreditPurchaseCheckout(
    organizationId: string,
    productId: string,
    successUrl: string,
    cancelUrl: string,
  ): Promise<CreditPurchaseResponse> {
    const response = await apiClient.post<CreditPurchaseResponse>(
      `${this.baseUrl}/credit-products/checkout`,
      {
        organization_id: organizationId,
        product_id: productId,
        success_url: successUrl,
        cancel_url: cancelUrl,
      },
    );
    return response.data;
  }

  // Billing History
  async getBillingHistory(
    organizationId: string,
    limit: number = 10,
  ): Promise<BillingHistory[]> {
    const params = new URLSearchParams();
    params.append("limit", limit.toString());

    const response = await apiClient.get<BillingHistory[]>(
      `${this.baseUrl}/history/${organizationId}?${params}`,
    );
    return response.data;
  }

  // Billing Summary
  async getBillingSummary(
    organizationId: string,
  ): Promise<OrganizationBillingSummary> {
    const response = await apiClient.get<OrganizationBillingSummary>(
      `${this.baseUrl}/summary/${organizationId}`,
    );
    return response.data;
  }

  // Helper methods for frontend use
  async initializeSubscription(
    organizationId: string,
    planId: string,
  ): Promise<string> {
    const checkoutResponse = await this.createSubscriptionCheckout(
      planId,
      organizationId,
    );

    // Redirect to Stripe checkout
    window.location.href = checkoutResponse.session_url;
    return checkoutResponse.session_id;
  }

  async purchaseCredits(
    organizationId: string,
    productId: string,
  ): Promise<string> {
    const currentUrl = window.location.origin;
    const successUrl = `${currentUrl}/dashboard/billing/success?session_id={CHECKOUT_SESSION_ID}`;
    const cancelUrl = `${currentUrl}/dashboard/billing/cancel`;

    const checkoutResponse = await this.createCreditPurchaseCheckout(
      organizationId,
      productId,
      successUrl,
      cancelUrl,
    );

    // Redirect to Stripe checkout
    window.location.href = checkoutResponse.checkout_url;
    return checkoutResponse.session_id;
  }

  async openCustomerPortal(organizationId: string): Promise<void> {
    const returnUrl = `${window.location.origin}/dashboard/billing`;

    const portalResponse = await this.createCustomerPortal(
      organizationId,
      returnUrl,
    );

    // Redirect to Stripe customer portal
    window.location.href = portalResponse.portal_url;
  }

  // Utility methods
  formatCurrency(amount: number, currency: string = "USD"): string {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  }

  formatCredits(credits: number): string {
    return new Intl.NumberFormat("en-US").format(credits);
  }

  formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }

  formatDateTime(dateString: string): string {
    return new Date(dateString).toLocaleString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  calculateAnnualSavings(monthlyPrice: number, annualPrice: number): number {
    const monthlyTotal = monthlyPrice * 12;
    return monthlyTotal - annualPrice;
  }

  calculateSavingsPercentage(
    monthlyPrice: number,
    annualPrice: number,
  ): number {
    const monthlyTotal = monthlyPrice * 12;
    const savings = monthlyTotal - annualPrice;
    return Math.round((savings / monthlyTotal) * 100);
  }

  getDaysUntilExpiry(expiryDate: string): number {
    const expiry = new Date(expiryDate);
    const now = new Date();
    const diffTime = expiry.getTime() - now.getTime();
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  }

  isTrialExpiringSoon(trialEnd: string | null, days: number = 3): boolean {
    if (!trialEnd) return false;
    const daysUntilExpiry = this.getDaysUntilExpiry(trialEnd);
    return daysUntilExpiry <= days && daysUntilExpiry > 0;
  }

  isSubscriptionActive(
    subscription: OrganizationSubscriptionWithPlan | null,
  ): boolean {
    return (
      subscription?.status === "active" || subscription?.status === "trial"
    );
  }

  getUsagePercentage(used: number, limit: number): number {
    if (limit === 0 || limit === null) return 0;
    return Math.min((used / limit) * 100, 100);
  }

  isUsageNearLimit(
    used: number,
    limit: number,
    threshold: number = 80,
  ): boolean {
    const percentage = this.getUsagePercentage(used, limit);
    return percentage >= threshold;
  }

  // Checkout and payment methods
  /**
   * Starts the legacy flat-plan checkout flow.
   *
   * @deprecated Use `createVersionedSubscriptionCheckout` so the backend
   * resolves the Stripe Price from the selected internal plan version.
   */
  async createSubscriptionCheckout(
    planId: string,
    organizationId: string,
  ): Promise<{ session_url: string; session_id: string }> {
    const response = await apiClient.post<{
      session_url: string;
      session_id: string;
    }>(`${this.baseUrl}/checkout/subscription`, {
      plan_id: planId,
      organization_id: organizationId,
    });
    return response.data;
  }

  async createCreditsCheckout(
    productId: string,
    organizationId: string,
  ): Promise<{ session_url: string; session_id: string }> {
    const response = await apiClient.post<{
      session_url: string;
      session_id: string;
    }>(`${this.baseUrl}/checkout/credits`, {
      product_id: productId,
      organization_id: organizationId,
    });
    return response.data;
  }

  async cancelSubscription(
    organizationId: string,
  ): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(
      `${this.baseUrl}/subscription/cancel`,
      {
        organization_id: organizationId,
      },
    );
    return response.data;
  }

  async reactivateSubscription(
    organizationId: string,
  ): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(
      `${this.baseUrl}/subscription/reactivate`,
      {
        organization_id: organizationId,
      },
    );
    return response.data;
  }
}

export const billingService = new BillingService();
