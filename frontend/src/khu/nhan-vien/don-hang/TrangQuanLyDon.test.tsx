import { screen, waitFor, within } from '@testing-library/react'
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
const CT = (rieng: object = {}) => ({
  id: 9, ma_don: 'DHABCD2345', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', hinh_thuc_nhan: 'giao_tan_noi', kenh_ban: 'online',
  khach_hang_id: 3, tam_tinh: '20000.00', giam_gia: '0.00', phi_van_chuyen: '25000.00', tong_tien: '45000.00', han_thanh_toan: null, ma_giam_gia: null,
  ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678', dia_chi_giao: '12 Lê Lợi', ghi_chu: null, ly_do_huy: null, created_at: '2026-10-16T01:00:00Z',
  dong: [{ san_pham_id: 1, ten_san_pham: 'Paracetamol', ten_don_vi: 'viên', so_luong: 2, don_gia: '10000.00', giam_gia_phan_bo: '0.00', thanh_tien: '20000.00' }],
  lich_su: [{ tu_trang_thai: null, den_trang_thai: 'cho_xac_nhan', thoi_diem: '2026-10-16T01:00:00Z', ghi_chu: null, nguon: 'nguoi_dung', nguoi_thuc_hien: 'Nguyễn An' }],
  giao_dich: [], van_don: [], ...rieng,
})
const TOM_TAT = { id: 9, ma_don: 'DHABCD2345', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', tong_tien: '45000.00', so_san_pham: 1, created_at: '2026-10-16T01:00:00Z', kenh_ban: 'online', ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678' }
const DUOC_SI = { 'order.view': 'day_du', 'order.confirm': 'day_du', 'order.cancel': 'day_du' } as const

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/don-hang') return ok({ du_lieu: [TOM_TAT], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/don-hang/{don_id}') return ok(CT())
    return ok([])
  })
})

describe('quản lý đơn của dược sĩ (DS01–DS03)', () => {
  it('danh sách hiện đơn, dẫn tới chi tiết và gửi bộ lọc tìm kiếm lên máy chủ', async () => {
    renderTai('/nhan-vien/don-hang', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: DUOC_SI })
    expect(await screen.findByText('DHABCD2345')).toBeInTheDocument()
    const u = userEvent.setup()
    await u.type(screen.getByPlaceholderText(/Mã đơn, tên/), 'DHABC{enter}')
    await waitFor(() => {
      const cuoi = GET.mock.calls.filter((c) => c[0] === '/api/v1/noi-bo/don-hang').at(-1)!
      expect(cuoi[1].params.query).toMatchObject({ q: 'DHABC', trang: 1 })
    })
  })

  it('?trang_thai= trên địa chỉ đặt sẵn bộ lọc trạng thái, giá trị lạ bị bỏ', async () => {
    const dau = renderTai('/quan-tri/xem/don-hang?trang_thai=giao_that_bai', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'order.view': 'chi_xem' } })
    await waitFor(() => expect(GET.mock.calls.some((c) => c[0] === '/api/v1/noi-bo/don-hang')).toBe(true))
    expect(GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/don-hang')![1].params.query.trang_thai).toBe('giao_that_bai')
    dau.unmount()
    GET.mockClear()
    renderTai('/quan-tri/xem/don-hang?trang_thai=khong_co', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'order.view': 'chi_xem' } })
    await waitFor(() => expect(GET.mock.calls.some((c) => c[0] === '/api/v1/noi-bo/don-hang')).toBe(true))
    expect(GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/don-hang')![1].params.query.trang_thai).toBeUndefined()
  })

  it('chi tiết đơn chờ xác nhận: xác nhận gọi API xác nhận', async () => {
    POST.mockResolvedValue(ok(CT({ trang_thai: 'da_xac_nhan' })))
    renderTai('/nhan-vien/don-hang/9', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: DUOC_SI })
    const u = userEvent.setup()
    expect(await screen.findByText('Đơn DHABCD2345')).toBeInTheDocument()
    expect(screen.getByText('Dòng thời gian')).toBeInTheDocument()
    await u.click(screen.getByText('Xác nhận đơn'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/don-hang/{don_id}/xac-nhan')
  })

  it('hủy đơn bắt buộc nhập lý do (nút Hủy đơn trong hộp thoại bị khóa khi để trống)', async () => {
    POST.mockResolvedValue(ok(CT({ trang_thai: 'da_huy' })))
    renderTai('/nhan-vien/don-hang/9', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: DUOC_SI })
    const u = userEvent.setup()
    await screen.findByText('Đơn DHABCD2345')
    await u.click(screen.getByText('Hủy đơn'))
    const hop = await screen.findByRole('dialog')
    const nutHuy = within(hop).getByText('Hủy đơn', { selector: 'button span' }).closest('button')!
    expect(nutHuy).toBeDisabled()
    await u.type(within(hop).getByPlaceholderText(/Lý do hủy/), 'Hết hàng')
    await waitFor(() => expect(nutHuy).toBeEnabled())
    await u.click(nutHuy)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1]).toMatchObject({ params: { path: { don_id: 9 } }, body: { ly_do: 'Hết hàng' } })
  })

  it('người chỉ có quyền xem (kho, Admin) không thấy nút xác nhận và hủy', async () => {
    renderTai('/nhan-vien/don-hang/9', { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: { 'order.view': 'chi_xem' } })
    await screen.findByText('Đơn DHABCD2345')
    expect(screen.queryByText('Xác nhận đơn')).not.toBeInTheDocument()
    expect(screen.queryByText('Hủy đơn')).not.toBeInTheDocument()
  })

  it('đơn đang giao không còn nút hủy dù có quyền', async () => {
    GET.mockImplementation(async () => ok(CT({ trang_thai: 'dang_giao' })))
    renderTai('/nhan-vien/don-hang/9', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: DUOC_SI })
    await screen.findByText('Đơn DHABCD2345')
    expect(screen.queryByText('Hủy đơn')).not.toBeInTheDocument()
  })
})
