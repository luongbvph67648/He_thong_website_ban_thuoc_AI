import { expect, test } from '@playwright/test'
import { ADMIN, ADMIN_MAT_KHAU, API, DUOC_SI, dangNhapNhanVien, tokenApi } from './dung_chung'

test.beforeAll(async ({ request }) => {
  // Dược sĩ trực cả ngày để kịch bản không phụ thuộc giờ chạy
  const admin = await tokenApi(request, '/noi-bo/auth/dang-nhap', { email: ADMIN, mat_khau: ADMIN_MAT_KHAU })
  const ds = await (await request.get(`${API}/noi-bo/cau-hinh`, { headers: admin })).json()
  const muc = (Array.isArray(ds) ? ds : (ds.du_lieu ?? ds.items)).flatMap((n: { muc?: unknown[] }) => n.muc ?? n).find(
    (m: { khoa: string }) => m.khoa === 'gio_lam_viec_duoc_si',
  )
  const r = await request.put(`${API}/noi-bo/cau-hinh/gio_lam_viec_duoc_si`, {
    headers: admin,
    data: { gia_tri: { bat_dau: '00:00', ket_thuc: '23:59', ngay_trong_tuan: [1, 2, 3, 4, 5, 6, 7] }, phien_ban: muc.phien_ban },
  })
  expect(r.ok(), await r.text()).toBeTruthy()
})

test('khách hỏi chatbot AI → chuyển dược sĩ → dược sĩ nhận và trả lời trực tiếp', async ({ page, browser }) => {
  const cauHoi = `Tôi bị đau đầu nhẹ, nên làm gì? ${Date.now()}`
  await page.goto('/')
  await page.getByRole('button', { name: 'Mở chat tư vấn' }).click()
  const chat = page.getByRole('region', { name: 'Chat tư vấn' })
  await chat.getByLabel('Tin nhắn').fill(cauHoi)
  await chat.getByLabel('Tin nhắn').press('Enter')
  await expect(chat.getByText(cauHoi)).toBeVisible()
  await expect(chat.getByLabel('Tin nhắn')).toBeEnabled({ timeout: 30_000 }) // AI trả lời xong
  await chat.getByRole('button', { name: 'Gặp dược sĩ' }).click()
  await expect(chat.getByText(/dược sĩ/i).last()).toBeVisible()

  const ds = await (await browser.newContext()).newPage()
  await dangNhapNhanVien(ds, DUOC_SI)
  await ds.goto('/nhan-vien/tu-van')
  await ds.getByRole('button', { name: 'Nhận tư vấn' }).first().click()
  const loiDs = `Chào bạn, mình là dược sĩ ${Date.now()}`
  await ds.getByLabel('Tin nhắn cho khách').fill(loiDs)
  await ds.getByRole('button', { name: 'Gửi', exact: true }).click()
  await expect(chat.getByText(loiDs)).toBeVisible()

  await chat.getByLabel('Tin nhắn').fill('Cảm ơn dược sĩ')
  await chat.getByLabel('Tin nhắn').press('Enter')
  await expect(ds.getByRole('log', { name: 'Nội dung trò chuyện' }).getByText('Cảm ơn dược sĩ')).toBeVisible()
  await ds.getByRole('button', { name: 'Kết thúc tư vấn' }).click()
})
