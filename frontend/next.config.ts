import createMDX from "@next/mdx";
import remarkGfm from "remark-gfm";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
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
    remarkPlugins: [remarkGfm],
    rehypePlugins: [],
  },
});

export default withMDX(nextConfig);
