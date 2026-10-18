import { expect, test, type Page } from '@playwright/test'
import { dangNhapKhach, themVaoGio } from './dung_chung'

async function datHang(page: Page, cong: 'VNPay' | 'MoMo') {
  await dangNhapKhach(page)
  await themVaoGio(page, 'paracetamol-500mg')
  await page.goto('/thanh-toan')
  await page.getByText(cong, { exact: true }).click()
  await page.getByRole('button', { name: 'Đặt hàng' }).click()
  await expect(page).toHaveURL(/thanh-toan-gia\?giao_dich=/)
  await expect(page.getByText(/Môi trường mô phỏng/)).toBeVisible()
}

test('thanh toán VNPay (mô phỏng): thẻ thử nghiệm + OTP → IPN → đơn đã thanh toán', async ({ page }) => {
  await datHang(page, 'VNPay')
  await page.getByRole('button', { name: 'Tiếp tục' }).click()
  await page.getByLabel('Số thẻ').fill('9704198526191432198')
  await page.getByLabel('Tên chủ thẻ').fill('NGUYEN VAN A')
  await page.getByLabel('Ngày phát hành').fill('07/15')
  await page.getByRole('button', { name: 'Tiếp tục' }).click()
  await page.getByLabel('Mã OTP').fill('123456')
  await page.getByRole('button', { name: 'Xác nhận' }).click()
  await expect(page.getByText('Giao dịch thành công')).toBeVisible()
  await expect(page).toHaveURL(/thanh-toan\/ket-qua\?ma=/, { timeout: 10_000 })
  await expect(page.getByText('Thanh toán thành công')).toBeVisible()
})

test('thanh toán MoMo (mô phỏng): quét giả lập + PIN → đơn đã thanh toán', async ({ page }) => {
  await datHang(page, 'MoMo')
  await page.getByRole('button', { name: /Mô phỏng: mở ứng dụng MoMo/ }).click()
  await page.getByLabel('Mã PIN').fill('123456')
  await page.getByRole('button', { name: 'Xác nhận' }).click()
  await expect(page).toHaveURL(/thanh-toan\/ket-qua\?ma=/, { timeout: 10_000 })
  await expect(page.getByText('Thanh toán thành công')).toBeVisible()
})

test('thanh toán VNPay: thẻ không đủ số dư thì thất bại, đơn vẫn chờ thanh toán và thanh toán lại được', async ({ page }) => {
  await datHang(page, 'VNPay')
  await page.getByRole('button', { name: 'Tiếp tục' }).click()
  await page.getByLabel('Số thẻ').fill('9704195798459170488')
  await page.getByLabel('Tên chủ thẻ').fill('NGUYEN VAN A')
  await page.getByLabel('Ngày phát hành').fill('07/15')
  await page.getByRole('button', { name: 'Tiếp tục' }).click()
  await page.getByLabel('Mã OTP').fill('123456')
  await page.getByRole('button', { name: 'Xác nhận' }).click()
  await expect(page.getByText('Giao dịch không thành công')).toBeVisible()
  await expect(page).toHaveURL(/thanh-toan\/ket-qua\?ma=/, { timeout: 10_000 })
  await expect(page.getByRole('button', { name: 'Thanh toán lại' })).toBeVisible()
})
