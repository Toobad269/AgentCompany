import type { NextConfig } from "next";
import { config } from "dotenv";

config({ path: "../../.env", quiet: true });

const nextConfig: NextConfig = {
  poweredByHeader: false,
  reactStrictMode: true,
  transpilePackages: ["@agentcompany/db", "@agentcompany/shared"],
  async headers() {
    const productionHeaders = [
      {
        key: "Strict-Transport-Security",
        value: "max-age=31536000; includeSubDomains"
      }
    ];

    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "X-Content-Type-Options",
            value: "nosniff"
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin"
          },
          {
            key: "X-Frame-Options",
            value: "DENY"
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()"
          },
          ...(process.env.APP_ENV === "production" ? productionHeaders : [])
        ]
      }
    ];
  }
};

export default nextConfig;
