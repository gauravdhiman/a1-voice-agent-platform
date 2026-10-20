import createMDX from "@next/mdx";
import type { NextConfig } from "next";
import { applicationSecurityHeaders } from "./src/lib/security-headers";

const nextConfig: NextConfig = {
  output: "standalone",
  async headers() {
    return applicationSecurityHeaders(process.env.NODE_ENV === "production");
  },
  async redirects() {
    return [
      {
        source: "/dental",
        destination: "/dental-appointment-booking",
        permanent: true,
      },
      {
        source: "/hvac",
        destination: "/hvac-service-call-answering",
        permanent: true,
      },
      {
        source: "/restaurants",
        destination: "/restaurant-order-taking",
        permanent: true,
      },
      {
        source: "/plumbing",
        destination: "/plumbing-service-requests",
        permanent: true,
      },
      {
        source: "/auto-repair",
        destination: "/auto-repair-service-booking",
        permanent: true,
      },
      {
        source: "/veterinary",
        destination: "/veterinary-appointment-booking",
        permanent: true,
      },
      {
        source: "/salons",
        destination: "/salon-appointment-booking",
        permanent: true,
      },
      {
        source: "/real-estate",
        destination: "/real-estate-lead-capture",
        permanent: true,
      },
    ];
  },
};

const withMDX = createMDX({
  options: {
    remarkPlugins: [],
    rehypePlugins: [],
  },
});

export default withMDX(nextConfig);
