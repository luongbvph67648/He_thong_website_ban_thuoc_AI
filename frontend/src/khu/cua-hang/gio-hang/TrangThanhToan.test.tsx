import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { useGioCucBo } from './gioHang'

vi.setConfig({ testTimeout: 60_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (ma_loi: string, thong_diep: string, chi_tiet: unknown = null, status = 409) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })
const DV = { id: 5, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00' }
const GIO = {
  dong: [{ dong_id: 11, san_pham: { id: 1, ten: 'Paracetamol', slug: 'paracetamol', anh_chinh_url: null, can_tu_van: false }, don_vi: DV, don_vi_co_the_chon: [DV], so_luong: 2, thanh_tien: '2000.00', toi_da_don_vi: null, ton_kha_dung_don_vi: 50, mua_duoc: true, ly_do: null }],
  tam_tinh: '2000.00',
  tong_so_luong: 2,
}
const DIA_CHI = [{ id: 7, ten_nguoi_nhan: 'Nguyễn An', so_dien_thoai: '0912345678', dia_chi_chi_tiet: '12 Lê Lợi', ma_tinh: '01', ten_tinh: 'Hà Nội', ma_phuong_xa: '0001', ten_phuong_xa: 'Phường A', la_mac_dinh: true }]
const TONG = { tam_tinh: '2000.00', giam_gia: '0.00', phi_van_chuyen: '25000.00', tong_tien: '27000.00', ma_giam_gia: null }
const DON = { ma_don: 'DHABCD2345', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', hinh_thuc_nhan: 'giao_tan_noi', ...TONG, han_thanh_toan: null, ma_giam_gia: null, ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678', dia_chi_giao: '12 Lê Lợi, Phường A, Hà Nội', ghi_chu: null, created_at: '2026-10-16T00:00:00Z', dong: [{ san_pham_id: 1, ten_san_pham: 'Paracetamol', ten_don_vi: 'viên', so_luong: 2, don_gia: '1000.00', giam_gia_phan_bo: '0.00', thanh_tien: '2000.00' }] }

beforeEach(() => {
  for (const m of [GET, POST]) m.mockReset()
  localStorage.clear()
  useGioCucBo.setState({ dong: [] })
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/gio-hang') return ok(GIO)
    if (duong === '/api/v1/toi/dia-chi') return ok(DIA_CHI)
    if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok(DON)
    throw new Error(`Chưa giả lập ${duong}`)
  })
  POST.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/toi/don-hang/xem-truoc') return ok(TONG)
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('TrangThanhToan (KTV02)', () => {
  it('khách vãng lai bị đưa về đăng nhập', async () => {
    renderTai('/thanh-toan')
    expect((await screen.findAllByText(/Đăng nhập/i)).length).toBeGreaterThan(0)
    expect(screen.queryByRole('button', { name: /Đặt hàng/ })).not.toBeInTheDocument()
  })

  it('hiện địa chỉ mặc định, phí ship và tổng tiền từ máy chủ', async () => {
    renderTai('/thanh-toan', { loai: 'khach' })
    expect(await screen.findByText('Tổng cộng')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText(/27\.000/)).toBeInTheDocument())
    expect(screen.getByText(/25\.000/)).toBeInTheDocument()
    const lanDau = POST.mock.calls.find((c) => c[0] === '/api/v1/toi/don-hang/xem-truoc')!
    expect(lanDau[1].body).toEqual({ hinh_thuc_nhan: 'giao_tan_noi', phuong_thuc_tt: 'cod', dia_chi_id: 7 })
  })

  it('đặt hàng gửi Idempotency-Key và tổng kỳ vọng rồi chuyển sang trang kết quả đọc từ máy chủ', async () => {
    POST.mockImplementation(async (duong: string) => (duong === '/api/v1/toi/don-hang' ? ok(DON) : ok(TONG)))
    renderTai('/thanh-toan', { loai: 'khach' })
    const u = userEvent.setup()
    const nut = await screen.findByRole('button', { name: /Đặt hàng/ })
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    await waitFor(() => expect(POST.mock.calls.some((c) => c[0] === '/api/v1/toi/don-hang')).toBe(true))
    const goiDat = POST.mock.calls.find((c) => c[0] === '/api/v1/toi/don-hang')!
    expect(goiDat[1].body).toMatchObject({ phuong_thuc_tt: 'cod', dia_chi_id: 7, tong_tien_ky_vong: '27000.00' })
    expect(goiDat[1].params.header['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
    expect(await screen.findByText('Đặt hàng thành công')).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/toi/don-hang/{ma_don}', { params: { path: { ma_don: 'DHABCD2345' } } })
    expect(screen.getByText('Đơn DHABCD2345')).toBeInTheDocument()
  })

  it('GIA_DA_THAY_DOI: hiện tổng mới, không chuyển trang, đặt lại dùng tổng mới', async () => {
    const MOI = { tam_tinh: '2000.00', giam_gia: '0.00', phi_van_chuyen: '30000.00', tong_tien: '32000.00', dong: [] }
    let lan = 0
    POST.mockImplementation(async (duong: string) => {
      if (duong !== '/api/v1/toi/don-hang') return ok(TONG)
      return ++lan === 1 ? loi('GIA_DA_THAY_DOI', 'Giá đã đổi', MOI) : ok(DON)
    })
    renderTai('/thanh-toan', { loai: 'khach' })
    const u = userEvent.setup()
    const nut = await screen.findByRole('button', { name: /Đặt hàng/ })
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    await waitFor(() => expect(screen.getByText(/32\.000/)).toBeInTheDocument())
    expect(screen.queryByText('Đặt hàng thành công')).not.toBeInTheDocument()
    await u.click(screen.getByRole('button', { name: /Đặt hàng/ }))
    await waitFor(() => expect(lan).toBe(2))
    const lanHai = POST.mock.calls.filter((c) => c[0] === '/api/v1/toi/don-hang')[1]
    expect(lanHai[1].body.tong_tien_ky_vong).toBe('32000.00')
    expect(await screen.findByText('Đặt hàng thành công')).toBeInTheDocument()
  })

  it('hết hàng: báo lỗi của máy chủ, ở lại trang', async () => {
    POST.mockImplementation(async (duong: string) => (duong === '/api/v1/toi/don-hang' ? loi('HET_HANG', 'Sản phẩm Paracetamol chỉ còn 1') : ok(TONG)))
    renderTai('/thanh-toan', { loai: 'khach' })
    const u = userEvent.setup()
    const nut = await screen.findByRole('button', { name: /Đặt hàng/ })
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    expect(await screen.findByText('Sản phẩm Paracetamol chỉ còn 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Đặt hàng/ })).toBeInTheDocument()
  })

  it('chưa có địa chỉ: gợi ý thêm địa chỉ, khóa nút đặt hàng; nhận tại nhà thuốc đặt được', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/dia-chi') return ok([])
      if (duong === '/api/v1/toi/gio-hang') return ok(GIO)
      return ok([])
    })
    renderTai('/thanh-toan', { loai: 'khach' })
    expect(await screen.findByText('Bạn chưa có địa chỉ giao hàng')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Đặt hàng/ })).toBeDisabled()
    await userEvent.setup().click(screen.getByLabelText('Nhận tại nhà thuốc'))
    await waitFor(() => expect(screen.getByRole('button', { name: /Đặt hàng/ })).toBeEnabled())
  })

  it('giỏ có sản phẩm không mua được: cảnh báo và khóa đặt hàng', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/gio-hang') return ok({ ...GIO, dong: [{ ...GIO.dong[0], mua_duoc: false, ly_do: 'khong_hien_thi' }] })
      if (duong === '/api/v1/toi/dia-chi') return ok(DIA_CHI)
      return ok([])
    })
    renderTai('/thanh-toan', { loai: 'khach' })
    expect(await screen.findByText(/không còn mua được/)).toBeInTheDocument()
    expect(within(document.body).getByRole('button', { name: /Đặt hàng/ })).toBeDisabled()
  })
})

describe('TrangKetQuaDatHang', () => {
  it('đơn online chờ thanh toán hiện hạn thanh toán', async () => {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/gio-hang') return ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 })
      if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok({ ...DON, trang_thai: 'cho_thanh_toan', phuong_thuc_tt: 'vnpay', han_thanh_toan: '2026-10-16T08:15:00Z' })
      return ok([])
    })
    renderTai('/thanh-toan/ket-qua?ma=DHABCD2345', { loai: 'khach' })
    expect(await screen.findByText('Đơn hàng đang chờ thanh toán')).toBeInTheDocument()
    expect(screen.getByText('VNPay')).toBeInTheDocument()
  })

  it('không có đơn thì báo không tìm thấy', async () => {
    GET.mockImplementation(async (duong: string) =>
      duong === '/api/v1/toi/gio-hang'
        ? ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 })
        : { error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 404 } },
    )
    renderTai('/thanh-toan/ket-qua?ma=SAI', { loai: 'khach' })
    expect(await screen.findByText('Không tìm thấy đơn hàng')).toBeInTheDocument()
  })
})
