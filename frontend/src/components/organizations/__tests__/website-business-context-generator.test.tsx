import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  isValidWebsiteUrl,
  WebsiteBusinessContextGenerator,
} from "@/components/organizations/website-business-context-generator";
import { organizationService } from "@/services/organization-service";

describe("WebsiteBusinessContextGenerator", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("accepts public sites and rejects private or reserved IP addresses", () => {
    expect(isValidWebsiteUrl("https://example.com/about")).toBe(true);
    expect(isValidWebsiteUrl("http://100.64.1.2")).toBe(false);
    expect(isValidWebsiteUrl("http://192.0.2.4")).toBe(false);
  });

  it("does not show an action for an invalid website and never runs automatically", () => {
    const generate = vi.spyOn(
      organizationService,
      "generateWebsiteBusinessContext",
    );

    const { rerender } = render(
      <WebsiteBusinessContextGenerator
        organizationId="org-1"
        website="not a website"
        businessContext=""
        onBusinessContextChange={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("generate-business-context")).toBeNull();
    expect(generate).not.toHaveBeenCalled();

    rerender(
      <WebsiteBusinessContextGenerator
        organizationId="org-1"
        website="https://example.com"
        businessContext=""
        onBusinessContextChange={vi.fn()}
      />,
    );

    expect(screen.getByTestId("generate-business-context")).toBeTruthy();
    expect(generate).not.toHaveBeenCalled();
  });

  it("asks before replacing existing context and makes no request on cancel", async () => {
    const generate = vi.spyOn(
      organizationService,
      "generateWebsiteBusinessContext",
    );

    render(
      <WebsiteBusinessContextGenerator
        organizationId="org-1"
        website="https://example.com"
        businessContext="Keep this current context"
        onBusinessContextChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("generate-business-context"));
    expect(screen.getByRole("dialog").textContent).toContain(
      "Replace the current business context?",
    );
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog")).toBeNull();
    });
    expect(generate).not.toHaveBeenCalled();
  });

  it("replaces the editable form value only after confirmation", async () => {
    const generate = vi
      .spyOn(organizationService, "generateWebsiteBusinessContext")
      .mockResolvedValue({
        business_details: "Draft with verified service details",
        pages_analyzed: 4,
        page_limit_reached: false,
      });
    const onBusinessContextChange = vi.fn();

    render(
      <WebsiteBusinessContextGenerator
        organizationId="org-1"
        website="https://example.com"
        businessContext="Existing context"
        onBusinessContextChange={onBusinessContextChange}
      />,
    );

    fireEvent.click(screen.getByTestId("generate-business-context"));
    fireEvent.click(
      screen.getByRole("button", { name: "Generate new draft" }),
    );

    await waitFor(() => {
      expect(generate).toHaveBeenCalledWith("org-1", "https://example.com");
      expect(onBusinessContextChange).toHaveBeenCalledWith(
        "Draft with verified service details",
      );
    });
    expect(screen.getByRole("status").textContent).toContain(
      "Drafted from 4 public pages",
    );
  });

  it("reports when the site has more pages than the scan limit", async () => {
    vi.spyOn(organizationService, "generateWebsiteBusinessContext").mockResolvedValue({
      business_details: "Draft",
      pages_analyzed: 50,
      page_limit_reached: true,
    });

    render(
      <WebsiteBusinessContextGenerator
        organizationId="org-1"
        website="https://example.com"
        businessContext=""
        onBusinessContextChange={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByTestId("generate-business-context"));
    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toContain(
        "more pages than the 50-page scan limit",
      );
    });
  });
});
