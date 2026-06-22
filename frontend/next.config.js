/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  eslint: { ignoreDuringBuilds: true },   // we lint via CI, not during the prod build
  typescript: { ignoreBuildErrors: false },
  experimental: { serverActions: { bodySizeLimit: "256mb" } },
};
module.exports = nextConfig;
