import { defineConfig } from '@playwright/test'

/**
 * Kịch bản e2e chạy trên backend + frontend đang chạy với dữ liệu demo (`python -m app.seed --demo`).
 * Dùng `scripts/e2e.sh` ở gốc repo để dựng CSDL, chạy máy chủ và test. Kịch bản đổi dữ liệu thật nên chạy tuần tự.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_URL ?? 'http://localhost:5173',
    locale: 'vi-VN',
    timezoneId: 'Asia/Ho_Chi_Minh',
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
})
