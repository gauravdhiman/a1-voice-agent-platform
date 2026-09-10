/**
 * Dialog component for creating new organizations
 */
"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { PlanCard, toPlanCardData } from "@/components/billing/plan-card";
import { billingService } from "@/services/billing-service";
import { organizationService } from "@/services/organization-service";
import { Loader2, Building2 } from "lucide-react";
import type { CustomerPlanVersion } from "@/types/billing";

const organizationSchema = z.object({
  name: z
    .string()
    .min(2, "Organization name must be at least 2 characters")
    .max(100, "Organization name must be less than 100 characters"),
  description: z
    .string()
    .max(500, "Description must be less than 500 characters")
    .optional(),
  slug: z
    .string()
    .min(2, "Slug must be at least 2 characters")
    .max(50, "Slug must be less than 50 characters")
    .regex(
      /^[a-z0-9-]+$/,
      "Slug can only contain lowercase letters, numbers, and hyphens",
    ),
  website: z
    .string()
    .url("Please enter a valid URL")
    .optional()
    .or(z.literal("")),
  is_active: z.boolean(),
});

type OrganizationFormData = z.infer<typeof organizationSchema>;

import type { Organization } from "@/types/organization";

interface OrganizationCreateDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: (organization: Organization) => void;
}

export function OrganizationCreateDialog({
  open,
  onOpenChange,
  onSuccess,
}: OrganizationCreateDialogProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [plans, setPlans] = useState<CustomerPlanVersion[]>([]);
  const [plansLoading, setPlansLoading] = useState(false);
  const [plansError, setPlansError] = useState<string | null>(null);
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);

  const form = useForm<OrganizationFormData>({
    resolver: zodResolver(organizationSchema),
    defaultValues: {
      name: "",
      description: "",
      slug: "",
      is_active: true,
    },
  });

  useEffect(() => {
    if (!open) return;

    let cancelled = false;
    setPlansLoading(true);
    setPlansError(null);
    setSelectedPlanId(null);

    void billingService
      .getAvailablePlanVersions()
      .then((availablePlans) => {
        if (!cancelled) setPlans(availablePlans);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setPlansError(
          requestError instanceof Error
            ? requestError.message
            : "We could not load the available plans.",
        );
      })
      .finally(() => {
        if (!cancelled) setPlansLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open]);

  const sortedPlans = useMemo(
    () =>
      [...plans].sort((left, right) => {
        if (left.tier_rank !== right.tier_rank) {
          return left.tier_rank - right.tier_rank;
        }
        if (left.product_slug !== right.product_slug) {
          return left.product_slug.localeCompare(right.product_slug);
        }
        return left.billing_interval.localeCompare(right.billing_interval);
      }),
    [plans],
  );

  // Auto-generate slug from name
  const watchName = form.watch("name");
  React.useEffect(() => {
    if (watchName && !form.getValues("slug")) {
      const slug = watchName
        .toLowerCase()
        .replace(/[^a-z0-9\s-]/g, "")
        .replace(/\s+/g, "-")
        .replace(/-+/g, "-")
        .trim();
      form.setValue("slug", slug);
    }
  }, [watchName, form]);

  const onSubmit = async (data: OrganizationFormData) => {
    try {
      setLoading(true);
      setError(null);

      if (!selectedPlanId) {
        setError("Choose an initial plan before creating the organization.");
        return;
      }

      const newOrganization = await organizationService.createOrganization({
        name: data.name,
        description: data.description || "",
        slug: data.slug,
        website: data.website || "",
        is_active: data.is_active,
        plan_version_id: selectedPlanId,
      });

      onSuccess(newOrganization);
      form.reset();
      setSelectedPlanId(null);
    } catch (err: unknown) {
      const error = err as Error;
      console.error("Error creating organization:", err);
      setError(error.message || "Failed to create organization");
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!loading) {
      onOpenChange(newOpen);
      if (!newOpen) {
        form.reset();
        setError(null);
        setSelectedPlanId(null);
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Create Organization
          </DialogTitle>
          <DialogDescription>
            Create the organization and choose its initial plan. Paid plans are
            assigned by the platform administrator during the controlled launch.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {error && (
              <div className="p-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md">
                {error}
              </div>
            )}

            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Organization Name *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., Acme Corporation"
                      {...field}
                      disabled={loading}
                    />
                  </FormControl>
                  <FormDescription>
                    The display name for your organization
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="slug"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Slug *</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="e.g., acme-corporation"
                      {...field}
                      disabled={loading}
                    />
                  </FormControl>
                  <FormDescription>
                    URL-friendly identifier (lowercase, numbers, hyphens only)
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Brief description of your organization..."
                      rows={3}
                      {...field}
                      disabled={loading}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional description of your organization
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="website"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Website</FormLabel>
                  <FormControl>
                    <Input
                      type="url"
                      placeholder="https://www.example.com"
                      {...field}
                      disabled={loading}
                    />
                  </FormControl>
                  <FormDescription>
                    Your organization&apos;s official website URL
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                  <FormControl>
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={field.onChange}
                      disabled={loading}
                    />
                  </FormControl>
                  <div className="space-y-1 leading-none">
                    <FormLabel>Active Organization</FormLabel>
                    <FormDescription>
                      Active organizations can be used immediately
                    </FormDescription>
                  </div>
                </FormItem>
              )}
            />

            <div className="space-y-3 border-t pt-4">
              <div>
                <h3 className="text-sm font-semibold">Initial plan *</h3>
                <p className="text-sm text-muted-foreground">
                  Choose from every currently published plan. The selected plan
                  is active as soon as the organization is created.
                </p>
              </div>

              {plansLoading ? (
                <div className="flex items-center justify-center rounded-lg border py-8 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading available plans...
                </div>
              ) : plansError ? (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  {plansError}
                </div>
              ) : sortedPlans.length === 0 ? (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                  No plans are available. Publish a plan before creating an
                  organization.
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {sortedPlans.map((plan) => {
                    const selected = selectedPlanId === plan.id;
                    return (
                      <PlanCard
                        key={plan.id}
                        plan={toPlanCardData(plan)}
                        badge={
                          plan.billing_mode === "free" ? (
                            <Badge variant="secondary">Free</Badge>
                          ) : (
                            <Badge variant="outline">Admin assigned</Badge>
                          )
                        }
                        className={
                          selected
                            ? "border-primary ring-2 ring-primary"
                            : undefined
                        }
                        testId={`organization-plan-card-${plan.id}`}
                        footer={
                          <Button
                            type="button"
                            variant={selected ? "default" : "outline"}
                            className="w-full"
                            onClick={() => setSelectedPlanId(plan.id)}
                            disabled={loading}
                            data-testid={`organization-plan-select-${plan.id}`}
                          >
                            {selected ? "Selected" : "Select this plan"}
                          </Button>
                        }
                      />
                    );
                  })}
                </div>
              )}
            </div>

            <div className="flex gap-3 pt-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={loading}
                className="flex-1"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={
                  loading || plansLoading || sortedPlans.length === 0 || !selectedPlanId
                }
                className="flex-1"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Creating and assigning...
                  </>
                ) : (
                  "Create & assign plan"
                )}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
