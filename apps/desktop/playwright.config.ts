import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../..", import.meta.url));
const python = process.platform === "win32" ? ".venv\\Scripts\\python.exe" : ".venv/bin/python";
export default defineConfig({
  testDir: "./browser",
  outputDir: "../../output/playwright/automated",
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 10_000 },
  use: { baseURL: "http://127.0.0.1:1420", viewport: { width: 1280, height: 900 }, trace: "off", screenshot: "only-on-failure" },
  webServer: [
    { command: `${python} -m tests.desktop.preview_server --financials-demo --source-review-demo --parity-demo --conversations-demo --comparisons-demo --reports-demo`, cwd: root,
      url: "http://127.0.0.1:18764/api/health", reuseExistingServer: false, timeout: 30_000 },
    { command: "npm run start", cwd: root, url: "http://127.0.0.1:1420", reuseExistingServer: false, timeout: 30_000 },
  ],
});
