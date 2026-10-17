import { expect, test } from '@playwright/test'
import { API, DUOC_SI, KHO, dangNhapKhach, dangNhapNhanVien, themVaoGio } from './dung_chung'

test('khách đặt COD → dược sĩ xác nhận → kho soạn và đóng gói → giao thành công', async ({ page, browser, request }) => {
  // 1. Khách đặt hàng COD, nhận tại địa chỉ có sẵn
  await dangNhapKhach(page)
  await themVaoGio(page, 'paracetamol-500mg')
  await page.goto('/gio-hang')
  await page.getByRole('link', { name: 'Tiến hành thanh toán' }).click()
  await page.getByRole('button', { name: 'Đặt hàng' }).click()
  await expect(page).toHaveURL(/thanh-toan\/ket-qua\?ma=/)
  const ma = new URL(page.url()).searchParams.get('ma')!

  // 2. Dược sĩ xác nhận
  const dsPage = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(dsPage, DUOC_SI)
  await dsPage.goto('/nhan-vien/don-hang')
  await dsPage.getByRole('link', { name: ma }).click()
  await dsPage.getByRole('button', { name: 'Xác nhận đơn' }).click()
  await expect(dsPage.getByRole('button', { name: 'Xác nhận đơn' })).toHaveCount(0)

  // 3. Kho bắt đầu soạn, xác nhận từng dòng, đóng gói và tạo vận đơn
  const khoPage = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(khoPage, KHO)
  await khoPage.goto('/nhan-vien/soan-hang')
  await khoPage.getByRole('link', { name: ma }).click()
  await khoPage.getByRole('button', { name: 'Bắt đầu soạn hàng' }).click()
  const xacNhanTay = khoPage.getByRole('button', { name: 'Xác nhận tay' })
  await expect(xacNhanTay.first()).toBeVisible()
  while (await xacNhanTay.count()) {
    const truoc = await xacNhanTay.count()
    await xacNhanTay.first().click()
    await expect(xacNhanTay).toHaveCount(truoc - 1)
  }
  await khoPage.getByRole('button', { name: /Đóng gói/ }).click()
  await expect(khoPage.getByRole('button', { name: /Đóng gói/ })).toHaveCount(0)

  // 4. Đối tác vận chuyển (giả) báo lấy hàng rồi giao thành công; COD được ghi nhận
  await page.goto(`/tai-khoan/don-hang/${ma}`)
  await expect(page.getByText('Mã vận đơn')).toBeVisible()
  const maVanDon = (await page.locator('body').innerText()).match(/\bGIA[A-Z0-9-]+/)?.[0]
  expect(maVanDon, 'trang đơn của khách phải hiện mã vận đơn').toBeTruthy()
  for (const trangThai of ['picked', 'delivered']) {
    const r = await request.post(`${API}/webhook/gia-van-chuyen`, {
      data: { ma_van_don: maVanDon, trang_thai_doi_tac: trangThai },
    })
    expect(r.ok()).toBeTruthy()
  }
  await page.reload()
  await expect(page.getByText('Đã giao').first()).toBeVisible()
})
