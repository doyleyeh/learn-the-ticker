/** @type {import('next').NextConfig} */
const configuredApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.trim() ||
  process.env.API_BASE_URL?.trim() ||
  (process.env.NODE_ENV === "production" ? "" : "http://127.0.0.1:8000");

const apiBaseUrl = configuredApiBaseUrl.replace(/\/+$/, "");

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    if (!apiBaseUrl) {
      return [];
    }

    return [
      {
        source: "/api/:path*",
        destination: `${apiBaseUrl}/api/:path*`
      }
    ];
  }
};

export default nextConfig;
