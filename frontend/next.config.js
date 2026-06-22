/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  experimental: { serverActions: { bodySizeLimit: "256mb" } },
};
module.exports = nextConfig;
