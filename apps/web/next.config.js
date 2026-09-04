/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@samved/schemas", "@samved/config"],
};

module.exports = nextConfig;
