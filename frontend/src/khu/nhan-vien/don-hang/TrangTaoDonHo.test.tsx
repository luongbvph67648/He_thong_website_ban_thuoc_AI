import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (ma_loi: string, thong_diep: string) => ({ error: { ma_loi, thong_diep, chi_tiet: null }, response: { ok: false, status: 404 } })
const SP = { id: 1, ten: 'Paracetamol 500mg', slug: 'para', loai_san_pham: 'thuoc_khong_ke_don', can_tu_van: false, thuong_hieu: null, quy_cach: null, anh_chinh_url: null, gia: '1000.00', ten_don_vi_gia: 'viên', con_hang: true }
const KE_DON = { ...SP, id: 2, ten: 'Amoxicillin kê đơn', slug: 'amox', loai_san_pham: 'thuoc_ke_don' }
const CHI_TIET = { id: 1, ten: 'Paracetamol 500mg', loai_san_pham: 'thuoc_khong_ke_don', don_vi: [{ id: 10, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00', la_mac_dinh: true, con_hang: true }] }
const QUYEN = { 'order.create_phone': 'day_du' } as const
const RA = (rieng: object = {}) => ({ don: { ma_don: 'DHABCD2345', tong_tien: '2000.00' }, lien_ket_thanh_toan: null, ...rieng })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string, tuy?: { params?: { query?: { sdt?: string } } }) => {
    if (duong === '/api/v1/noi-bo/don-ho/khach') {
      return tuy?.params?.query?.sdt === '0912345678' ? ok({ ho_ten: 'Lê Hoa', so_dien_thoai: '0912345678', dia_chi: [] }) : loi('KHONG_TIM_THAY', 'Không tìm thấy khách hàng')
    }
    if (duong === '/api/v1/tim-kiem') return ok({ du_lieu: [SP, KE_DON], tong: 2, trang: 1, kich_thuoc: 10 })
    if (duong === '/api/v1/san-pham/{slug}') return ok(CHI_TIET)
    return ok([])
  })
})
const dung = () => renderTai('/nhan-vien/don-hang/tao', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN as never })

async function themSanPham(u: ReturnType<typeof userEvent.setup>, ten: string) {
  await u.type(screen.getAllByRole('combobox')[0], 'para')
  await u.click(await screen.findByText(ten))
}

describe('tạo đơn hộ khách (DS07)', () => {
  it('tìm khách, thêm sản phẩm, lập đơn COD nhận tại nhà thuốc', async () => {
    POST.mockResolvedValue(ok(RA()))
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('SĐT khách (nếu đã có tài khoản)'), '0912345678')
    await u.click(screen.getByRole('button', { name: /Tìm khách/ }))
    expect(await screen.findByText(/Khách có tài khoản: Lê Hoa/)).toBeInTheDocument()
    await u.click(screen.getByLabelText('Nhận tại nhà thuốc'))
    await themSanPham(u, 'Paracetamol 500mg')
    await u.click(await screen.findByRole('button', { name: 'Thêm vào đơn' }))
    expect(await screen.findByText('Paracetamol 500mg (viên)')).toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: 'Lập đơn' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    const [duong, tuy] = POST.mock.calls[0]
    expect(duong).toBe('/api/v1/noi-bo/don-ho')
    expect(tuy.body).toMatchObject({ sdt_khach: '0912345678', hinh_thuc_nhan: 'nhan_tai_nha_thuoc', phuong_thuc_tt: 'cod', dia_chi: null, dong: [{ san_pham_id: 1, don_vi_id: 10, so_luong: 1 }] })
    expect(tuy.headers['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
    expect(await screen.findByText('Đã lập đơn DHABCD2345')).toBeInTheDocument()
  })

  it('khách chưa có tài khoản: chỉ COD, không chọn được VNPay/MoMo', async () => {
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('SĐT khách (nếu đã có tài khoản)'), '0900000000')
    await u.click(screen.getByRole('button', { name: /Tìm khách/ }))
    expect(await screen.findByText(/Chưa có tài khoản với số này/)).toBeInTheDocument()
    expect(screen.getByLabelText('VNPay')).toBeDisabled()
    expect(screen.getByLabelText('MoMo')).toBeDisabled()
  })

  it('thuốc kê đơn không thêm được vào đơn', async () => {
    dung()
    const u = userEvent.setup()
    await themSanPham(u, 'Amoxicillin kê đơn')
    expect(await screen.findByText(/Thuốc kê đơn không bán qua điện thoại/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Thêm vào đơn' })).not.toBeInTheDocument()
    expect(GET).not.toHaveBeenCalledWith('/api/v1/san-pham/{slug}', expect.anything())
  })

  it('đơn online hiện link thanh toán để gửi khách', async () => {
    POST.mockResolvedValue(ok(RA({ lien_ket_thanh_toan: '/thanh-toan/ket-qua?ma=DHABCD2345' })))
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('SĐT khách (nếu đã có tài khoản)'), '0912345678')
    await u.click(screen.getByRole('button', { name: /Tìm khách/ }))
    await screen.findByText(/Khách có tài khoản/)
    await u.click(screen.getByLabelText('Nhận tại nhà thuốc'))
    await u.click(screen.getByLabelText('VNPay'))
    await themSanPham(u, 'Paracetamol 500mg')
    await u.click(await screen.findByRole('button', { name: 'Thêm vào đơn' }))
    await u.click(screen.getByRole('button', { name: 'Lập đơn' }))
    const o = await screen.findByDisplayValue(/\/thanh-toan\/ket-qua\?ma=DHABCD2345$/)
    expect(o).toHaveAttribute('readonly')
    expect(POST.mock.calls[0][1].body).toMatchObject({ phuong_thuc_tt: 'vnpay', sdt_khach: '0912345678' })
  })
})
