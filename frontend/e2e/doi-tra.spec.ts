import { expect, test } from '@playwright/test'
import { ADMIN, ADMIN_MAT_KHAU, ANH_PNG, API, DUOC_SI, KHACH, KHO, MAT_KHAU_MAU, dangNhapKhach, dangNhapNhanVien, taoDonDaGiao, tokenApi } from './dung_chung'

test('khách yêu cầu đổi trả → dược sĩ duyệt → kho nhận hàng → Admin xác nhận hoàn tiền', async ({ page, browser, request }) => {
  const ma = await taoDonDaGiao(request)
  await dangNhapKhach(page)
  await page.goto(`/tai-khoan/don-hang/${ma}`)
  await expect(page.getByText('Đã giao').first()).toBeVisible()
  await page.getByRole('button', { name: 'Yêu cầu đổi trả' }).click()
  const hop = page.getByRole('dialog')
  await hop.getByRole('spinbutton').fill('1')
  await hop.getByRole('combobox').click()
  await page.locator('.ant-select-item-option', { hasText: 'Giao sai sản phẩm' }).click()
  await hop.locator('input[type=file]').setInputFiles({ name: 'hu.png', mimeType: 'image/png', buffer: ANH_PNG })
  await hop.getByRole('button', { name: 'Gửi yêu cầu' }).click()
  await expect(hop).toBeHidden()

  const khach = await tokenApi(request, '/auth/dang-nhap', { ten_dang_nhap: KHACH, mat_khau: MAT_KHAU_MAU })
  const yc = (await (await request.get(`${API}/toi/doi-tra`, { headers: khach })).json())[0]

  // Dược sĩ duyệt, tạo vận đơn trả
  const ds = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(ds, DUOC_SI)
  await ds.goto('/nhan-vien/doi-tra')
  await ds.getByRole('row', { name: new RegExp(yc.ma_yeu_cau) }).getByRole('button', { name: 'Xử lý' }).click()
  await ds.getByRole('button', { name: 'Duyệt, tạo vận đơn trả' }).click()
  await expect(ds.getByRole('button', { name: 'Duyệt, tạo vận đơn trả' })).toHaveCount(0)

  // Kho nhận hàng trả về
  const kho = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(kho, KHO)
  await kho.goto('/nhan-vien/hang-tra-ve')
  await kho.getByRole('row', { name: new RegExp(yc.ma_yeu_cau) }).getByRole('button', { name: 'Nhận hàng' }).click()
  await kho.getByPlaceholder(/Kết quả kiểm hàng/).fill('Đúng mô tả, hàng nguyên niêm phong')
  await kho.getByRole('button', { name: 'Xác nhận đã nhận' }).click()
  await expect(kho.getByRole('button', { name: 'Xác nhận đã nhận' })).toHaveCount(0)

  // Dược sĩ tạo giao dịch hoàn tiền (khác người xác nhận hoàn)
  await ds.reload()
  await ds.getByRole('row', { name: new RegExp(yc.ma_yeu_cau) }).getByRole('button', { name: 'Xử lý' }).click()
  await ds.getByRole('button', { name: 'Tạo giao dịch hoàn tiền' }).click()
  await expect(ds.getByRole('button', { name: 'Tạo giao dịch hoàn tiền' })).toHaveCount(0)

  // Khách khai tài khoản nhận hoàn tiền khi đã có giao dịch hoàn (đơn COD không có giao dịch qua cổng để hoàn ngược)
  const tk = await request.put(`${API}/toi/doi-tra/${yc.ma_yeu_cau}/tai-khoan-nhan-hoan`, {
    headers: khach,
    data: { ngan_hang: 'Vietcombank', so_tai_khoan: '0123456789', chu_tai_khoan: 'LE MINH ANH' },
  })
  expect(tk.ok(), await tk.text()).toBeTruthy()

  // Admin xác nhận đã chuyển khoản hoàn tiền (kèm ảnh chứng từ)
  const admin = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(admin, ADMIN, ADMIN_MAT_KHAU)
  await admin.goto('/quan-tri/hoan-tien')
  const hang = admin.getByRole('row', { name: new RegExp(yc.ma_yeu_cau) })
  await hang.getByRole('button', { name: 'Xác nhận' }).click()
  await admin.getByRole('dialog').locator('input[type=file]').setInputFiles({ name: 'ck.png', mimeType: 'image/png', buffer: ANH_PNG })
  await admin.getByRole('button', { name: 'Đã chuyển khoản' }).click()
  await expect(hang).toHaveCount(0)

  // Khách thấy yêu cầu đổi trả đã hoàn tất
  const sau = await (await request.get(`${API}/toi/doi-tra/${yc.ma_yeu_cau}`, { headers: khach })).json()
  expect(sau.trang_thai).toBe('hoan_tat')
})
