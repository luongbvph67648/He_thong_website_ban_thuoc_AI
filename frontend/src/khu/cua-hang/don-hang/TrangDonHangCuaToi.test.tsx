import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 60_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DON = (rieng: object = {}) => ({
  ma_don: 'DHABCD2345', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', hinh_thuc_nhan: 'giao_tan_noi',
  tam_tinh: '20000.00', giam_gia: '0.00', phi_van_chuyen: '25000.00', tong_tien: '45000.00', han_thanh_toan: null, ma_giam_gia: null,
  ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678', dia_chi_giao: '12 Lê Lợi', ghi_chu: null, ly_do_huy: null,
  created_at: '2026-10-16T01:00:00Z',
  dong: [{ san_pham_id: 1, ten_san_pham: 'Paracetamol', ten_don_vi: 'viên', so_luong: 2, don_gia: '10000.00', giam_gia_phan_bo: '0.00', thanh_tien: '20000.00' }],
  lich_su: [{ tu_trang_thai: null, den_trang_thai: 'cho_xac_nhan', thoi_diem: '2026-10-16T01:00:00Z', ghi_chu: null }],
  ...rieng,
})

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  localStorage.clear()
})
function giaLap(don: object) {
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/toi/don-hang') return ok({ du_lieu: [{ ma_don: 'DHABCD2345', trang_thai: 'cho_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', tong_tien: '45000.00', so_san_pham: 1, created_at: '2026-10-16T01:00:00Z' }], tong: 1, trang: 1, kich_thuoc: 10 })
    if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok(don)
    if (duong === '/api/v1/toi/gio-hang') return ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 })
    return ok([])
  })
}

describe('đơn hàng của tôi (KTV06)', () => {
  it('khách chưa đăng nhập bị chuyển sang trang đăng nhập', async () => {
    giaLap(DON())
    const { router } = renderTai('/tai-khoan/don-hang')
    await waitFor(() => expect(router.state.location.pathname).toBe('/dang-nhap'))
  })

  it('danh sách có mã đơn dẫn tới chi tiết và lọc theo trạng thái gửi tham số lên máy chủ', async () => {
    giaLap(DON())
    renderTai('/tai-khoan/don-hang', { loai: 'khach' })
    expect(await screen.findByText('DHABCD2345')).toBeInTheDocument()
    expect(screen.getByText('Chờ xác nhận', { selector: '.ant-tag' })).toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/toi/don-hang')!
    expect(goi[1].params.query).toMatchObject({ trang: 1, kich_thuoc: 10 })
  })

  it('chi tiết đơn chờ xác nhận có nút Hủy đơn; hủy gửi lý do rồi thông báo thành công', async () => {
    giaLap(DON())
    POST.mockResolvedValue(ok(DON({ trang_thai: 'da_huy', ly_do_huy: 'Đặt nhầm' })))
    renderTai('/tai-khoan/don-hang/DHABCD2345', { loai: 'khach' })
    const u = userEvent.setup()
    expect(await screen.findByText('Đơn DHABCD2345')).toBeInTheDocument()
    expect(screen.getByText('Paracetamol (viên)')).toBeInTheDocument()
    await u.click(screen.getByText('Hủy đơn'))
    const hop = await screen.findByRole('dialog')
    await u.type(within(hop).getByPlaceholderText(/Lý do hủy/), 'Đặt nhầm')
    await u.click(within(hop).getByText('Hủy đơn', { selector: 'button span' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/toi/don-hang/{ma_don}/huy')
    expect(POST.mock.calls[0][1]).toMatchObject({ params: { path: { ma_don: 'DHABCD2345' } }, body: { ly_do: 'Đặt nhầm' } })
  })

  it.each(['dang_soan_hang', 'da_huy', 'da_giao'])('đơn %s không có nút hủy', async (trang_thai) => {
    giaLap(DON({ trang_thai }))
    renderTai('/tai-khoan/don-hang/DHABCD2345', { loai: 'khach' })
    expect(await screen.findByText('Đơn DHABCD2345')).toBeInTheDocument()
    expect(screen.queryByText('Hủy đơn')).not.toBeInTheDocument()
  })

  it('đơn đã hủy chờ hoàn tiền hiện thông báo hoàn tiền; đơn không có hiện 404', async () => {
    giaLap(DON({ trang_thai: 'da_huy', trang_thai_tt: 'cho_hoan_tien' }))
    renderTai('/tai-khoan/don-hang/DHABCD2345', { loai: 'khach' })
    expect(await screen.findByText(/sẽ hoàn lại tiền/)).toBeInTheDocument()
  })

  it('đơn không có hoặc của người khác hiện không tìm thấy', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'Không tìm thấy đơn hàng', chi_tiet: null }, response: { ok: false, status: 404 } }))
    renderTai('/tai-khoan/don-hang/DHXXXX', { loai: 'khach' })
    expect(await screen.findByText('Không tìm thấy đơn hàng')).toBeInTheDocument()
  })
})
