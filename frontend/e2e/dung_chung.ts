import { expect, type APIRequestContext, type Page } from '@playwright/test'

export const MAT_KHAU_MAU = 'Mau@12345'
export const KHACH = '0900000001'
export const DUOC_SI = 'duocsi@example.com'
export const KHO = 'kho@example.com'
export const ADMIN = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com'
export const ADMIN_MAT_KHAU = process.env.E2E_ADMIN_MAT_KHAU ?? 'Admin@12345678'

// PNG 1×1 hợp lệ: đủ cho kiểm tra kiểu tệp, không cần đơn thuốc thật (AI đọc ảnh chạy bằng bản giả ở dev)
export const ANH_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

export const API = process.env.E2E_API ?? 'http://localhost:8000/api/v1'

export async function dangNhapKhach(page: Page, sdt = KHACH) {
  await page.goto('/dang-nhap')
  await page.getByLabel('Số điện thoại hoặc email').fill(sdt)
  await page.getByLabel('Mật khẩu').fill(MAT_KHAU_MAU)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page).toHaveURL('/')
}

export async function dangNhapNhanVien(page: Page, email: string, matKhau = MAT_KHAU_MAU) {
  await page.goto('/nhan-vien/dang-nhap')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Mật khẩu').fill(matKhau)
  await page.getByRole('button', { name: 'Đăng nhập', exact: true }).click()
  await expect(page).not.toHaveURL(/dang-nhap/)
}

/** Thêm một sản phẩm vào giỏ từ trang chi tiết (đơn vị mặc định, số lượng 1). */
export async function themVaoGio(page: Page, slug: string) {
  await page.goto(`/san-pham/${slug}`)
  await page.getByRole('button', { name: 'Thêm vào giỏ' }).click()
  await expect(page.getByText(/đã thêm|thêm vào giỏ hàng/i).first()).toBeVisible()
}

/** Đăng nhập qua API, trả header Authorization (dựng đơn nhanh cho kịch bản không cần đi lại cả luồng bằng giao diện). */
const boNhoToken = new Map<string, { Authorization: string; luc: number }>()

export async function tokenApi(request: APIRequestContext, duong: string, than: object) {
  // Giữ token 10 phút (hạn 15 phút): máy chủ giới hạn 20 lần đăng nhập/10 phút/IP
  const khoa = `${duong}${JSON.stringify(than)}`
  const co = boNhoToken.get(khoa)
  if (co && Date.now() - co.luc < 600_000) return { Authorization: co.Authorization }
  const r = await request.post(`${API}${duong}`, { data: than })
  expect(r.ok(), `đăng nhập ${duong}`).toBeTruthy()
  const Authorization = `Bearer ${(await r.json()).access_token}`
  boNhoToken.set(khoa, { Authorization, luc: Date.now() })
  return { Authorization }
}

/** Tạo đơn COD của khách mẫu rồi đưa tới `da_giao` bằng đúng các API thật; trả mã đơn. */
export async function taoDonDaGiao(request: APIRequestContext, slug = 'paracetamol-500mg'): Promise<string> {
  const khach = await tokenApi(request, '/auth/dang-nhap', { ten_dang_nhap: KHACH, mat_khau: MAT_KHAU_MAU })
  const ds = await tokenApi(request, '/noi-bo/auth/dang-nhap', { email: DUOC_SI, mat_khau: MAT_KHAU_MAU })
  const kho = await tokenApi(request, '/noi-bo/auth/dang-nhap', { email: KHO, mat_khau: MAT_KHAU_MAU })
  const sp = await (await request.get(`${API}/san-pham/${slug}`)).json()
  const donVi = sp.don_vi.find((d: { con_hang: boolean }) => d.con_hang) ?? sp.don_vi[0]
  const diaChi = (await (await request.get(`${API}/toi/dia-chi`, { headers: khach })).json())[0]
  await request.delete(`${API}/toi/gio-hang`, { headers: khach })
  const them = await request.post(`${API}/toi/gio-hang/dong`, {
    headers: khach,
    data: { san_pham_id: sp.id, don_vi_id: donVi.id, so_luong: 1 },
  })
  expect(them.ok()).toBeTruthy()
  const dat = await request.post(`${API}/toi/don-hang`, {
    headers: { ...khach, 'Idempotency-Key': crypto.randomUUID() },
    data: { hinh_thuc_nhan: 'giao_tan_noi', dia_chi_id: diaChi.id, phuong_thuc_tt: 'cod' },
  })
  expect(dat.status(), await dat.text()).toBe(201)
  const { ma_don: ma } = await dat.json()
  const ds_ = await (await request.get(`${API}/noi-bo/don-hang`, { headers: ds, params: { q: ma } })).json()
  const id = ds_.du_lieu[0].id
  expect((await request.post(`${API}/noi-bo/don-hang/${id}/xac-nhan`, { headers: ds })).ok()).toBeTruthy()
  expect((await request.post(`${API}/noi-bo/soan-hang/${id}/bat-dau`, { headers: kho })).ok()).toBeTruthy()
  expect((await request.post(`${API}/noi-bo/soan-hang/${id}/dong-goi`, { headers: kho })).ok()).toBeTruthy()
  const don = await (await request.get(`${API}/toi/don-hang/${ma}`, { headers: khach })).json()
  for (const trangThai of ['picked', 'delivered']) {
    const r = await request.post(`${API}/webhook/gia-van-chuyen`, {
      data: { ma_van_don: don.van_don[0].ma_van_don, trang_thai_doi_tac: trangThai },
    })
    expect(r.ok()).toBeTruthy()
  }
  return ma
}
