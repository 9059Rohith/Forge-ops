import { defineConfig, devices } from "@playwright/test";

const e2eDatabaseUrl = `sqlite+aiosqlite:///./e2e-${process.pid}.db`;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 2 : 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "alembic upgrade head && python -m uvicorn app.main:app --host 127.0.0.1 --port 8765",
      cwd: "../backend",
      url: "http://127.0.0.1:8765/api/health",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        DEMO_MODE: "true",
        DATABASE_URL: e2eDatabaseUrl,
        ALLOWED_ORIGINS: "http://127.0.0.1:3000",
      },
    },
    {
      command: "npm run dev",
      cwd: ".",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { BACKEND_URL: "http://127.0.0.1:8765" },
    },
  ],
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } },
    { name: "mobile-chromium", use: { ...devices["Pixel 7"] } },
  ],
});
