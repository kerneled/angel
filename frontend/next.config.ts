import type { NextConfig } from "next";
import withPWA from "@ducanh2912/next-pwa";

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  turbopack: {},
  allowedDevOrigins: ["192.168.50.130", "dogsense.eac-bt.com"],
};

export default withPWA({
  dest: "public",
  register: true,
  cacheOnFrontEndNav: true,
  fallbacks: {
    document: "/offline",
  },
  workboxOptions: {
    skipWaiting: true,
    clientsClaim: true,
  },
})(nextConfig);
