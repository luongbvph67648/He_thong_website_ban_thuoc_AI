import { expect, test } from '@playwright/test'
import { ANH_PNG, DUOC_SI, dangNhapKhach, dangNhapNhanVien } from './dung_chung'

test('khách gửi đơn thuốc → dược sĩ duyệt và tạo đơn → khách xác nhận', async ({ page, browser }) => {
  const ghiChu = `e2e-${Date.now()}`
  await dangNhapKhach(page)
  await page.goto('/gui-don-thuoc')
  await page.getByLabel('Họ tên người bệnh').fill('Lê Minh Anh')
  await page.getByLabel('Số điện thoại liên hệ').fill(`09${String(Date.now()).slice(-8)}`) // mỗi lần một SĐT liên hệ: máy chủ giới hạn 5 yêu cầu/SĐT/ngày
  await page.locator('input[type=file]').setInputFiles({ name: 'don.png', mimeType: 'image/png', buffer: ANH_PNG })
  await page.getByLabel('Ghi chú cho dược sĩ').fill(ghiChu)
  await page.getByRole('button', { name: 'Gửi đơn thuốc' }).click()
  await page.getByRole('link', { name: 'Xem đơn thuốc của tôi' }).click()
  const ma = (await page.locator('main').innerText()).match(/\bYC[A-F0-9]{8}\b/)?.[0]
  expect(ma, 'danh sách đơn thuốc của khách phải hiện mã yêu cầu').toBeTruthy()

  const ds = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(ds, DUOC_SI)
  await ds.goto('/nhan-vien/don-thuoc')
  await ds.getByRole('row', { name: new RegExp(ma!) }).getByRole('button', { name: 'Nhận xử lý' }).click()
  await expect(ds).toHaveURL(/\/nhan-vien\/don-thuoc\/\d+/)
  await ds.getByRole('button', { name: 'Thêm thuốc' }).click()
  await ds.getByLabel('Tên thuốc trên đơn').fill('Metformin')
  await ds.getByLabel('Hàm lượng').fill('500mg')
  await ds.getByLabel('Số lượng kê').fill('60 viên')
  await ds.getByRole('button', { name: 'Lưu danh sách thuốc' }).click()
  await ds.getByPlaceholder('Tìm theo tên thuốc hoặc hoạt chất').fill('Metformin')
  await ds.getByRole('button', { name: 'Thêm', exact: true }).first().click()
  for (const o of await ds.getByRole('checkbox').all()) await o.check()
  await ds.getByRole('button', { name: 'Tạo đơn gửi khách' }).click()
  await expect(ds.getByText(/đã tạo đơn|Đã gửi|chờ khách xác nhận/i).first()).toBeVisible()

  // Khách xác nhận đơn dược sĩ tạo (nhận tại nhà thuốc): đơn thuốc đã được duyệt nên vào thẳng trạng thái đã xác nhận
  await page.goto('/tai-khoan/don-hang')
  await page.locator('main a[href^="/tai-khoan/don-hang/"]').first().click()
  await expect(page.getByText('Chờ khách xác nhận').first()).toBeVisible()
  await page.getByLabel('Nhận tại nhà thuốc').check()
  await page.getByRole('button', { name: 'Xác nhận đơn' }).click()
  await expect(page.getByRole('button', { name: 'Xác nhận đơn' })).toHaveCount(0)
  await expect(page.getByText('Đã xác nhận').first()).toBeVisible()
})
