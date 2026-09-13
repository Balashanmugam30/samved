const path = require("path");

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Output standalone directory for containerized deployments (Docker/Linux).
  // On Windows without Developer Mode, pnpm symlink tracing in .next/standalone triggers EPERM.
  ...(process.platform !== "win32" || process.env.BUILD_STANDALONE === "true" || process.env.DOCKER_BUILD === "true"
    ? {
        output: "standalone",
        experimental: {
          outputFileTracingRoot: path.join(__dirname, "../../"),
        },
      }
    : {}),
  reactStrictMode: true,
  transpilePackages: ["@samved/schemas", "@samved/config"],
};

module.exports = nextConfig;
