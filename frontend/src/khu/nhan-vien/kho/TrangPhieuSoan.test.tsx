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
const KHO = { 'order.pick': 'day_du', 'shipment.create': 'day_du', 'order.view': 'chi_xem' } as const
const PB = { id: 5, lo_id: 11, so_lo: 'L0001', han_su_dung: '2027-10-16', so_luong_co_so: 2, trang_thai: 'dang_giu', ly_do_doi_lo: null }
const DONG = { ct_don_hang_id: 1, san_pham_id: 1, ten_san_pham: 'Paracetamol', ten_don_vi: 'viên', he_so: 1, so_luong: 2, ma_vach: '893001', phan_bo: [PB], goi_y: [
  { lo_id: 11, so_lo: 'L0001', han_su_dung: '2027-10-16', kha_dung: 50 },
  { lo_id: 12, so_lo: 'L0002', han_su_dung: '2028-01-01', kha_dung: 80 },
] }
const PHIEU = (rieng: object = {}) => ({
  id: 9, ma_don: 'DHABCD2345', trang_thai: 'da_xac_nhan', hinh_thuc_nhan: 'giao_tan_noi', ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678',
  dia_chi_giao: '12 Lê Lợi', ghi_chu: null, created_at: '2026-10-16T01:00:00Z', dong: [DONG], van_don: [], che_do_van_chuyen_gia: true, ...rieng,
})

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/soan-hang/{don_id}') return ok(PHIEU())
    if (duong === '/api/v1/noi-bo/don-hang') return ok({ du_lieu: [{ id: 9, ma_don: 'DHABCD2345', trang_thai: 'da_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'cod', tong_tien: '45000.00', so_san_pham: 1, created_at: '2026-10-16T01:00:00Z', kenh_ban: 'online', ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678' }], tong: 1, trang: 1, kich_thuoc: 20 })
    return ok([])
  })
})
const dung = (duong: string, quyen: object = KHO) => renderTai(duong, { loai: 'noi_bo', vaiTro: 'WAREHOUSE', quyen: quyen as never })

describe('soạn hàng của kho (KHO03, KHO04)', () => {
  it('hàng đợi lọc theo trạng thái và dẫn tới phiếu', async () => {
    dung('/nhan-vien/soan-hang')
    expect(await screen.findByText('DHABCD2345')).toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/don-hang')!
    expect(goi[1].params.query).toMatchObject({ trang_thai: 'da_xac_nhan' })
  })

  it('đơn đã xác nhận: bắt đầu soạn gọi API chốt lô', async () => {
    POST.mockResolvedValue(ok(PHIEU({ trang_thai: 'dang_soan_hang' })))
    dung('/nhan-vien/soan-hang/9')
    const u = userEvent.setup()
    expect(await screen.findByText('Phiếu soạn hàng DHABCD2345')).toBeInTheDocument()
    expect(screen.getByText(/L0001 · HSD/)).toBeInTheDocument()
    expect(screen.queryByText('Đóng gói & tạo vận đơn')).not.toBeInTheDocument()
    await u.click(screen.getByText('Bắt đầu soạn hàng'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/soan-hang/{don_id}/bat-dau')
  })

  it('đổi lô cần chọn lô khác và lý do rồi gửi lên máy chủ', async () => {
    POST.mockResolvedValue(ok(PHIEU()))
    dung('/nhan-vien/soan-hang/9')
    const u = userEvent.setup()
    await screen.findByText('Phiếu soạn hàng DHABCD2345')
    await u.click(screen.getByText('Đổi lô'))
    const hop = await screen.findByRole('dialog')
    const nut = within(hop).getByText('Đổi lô', { selector: 'button span' }).closest('button')!
    expect(nut).toBeDisabled()
    await u.click(within(hop).getByRole('combobox'))
    await u.click(await screen.findByText(/L0002 · HSD/))
    await u.type(within(hop).getByPlaceholderText(/Lý do đổi lô/), 'Khách muốn hạn dài')
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({ phan_bo_lo_id: 5, lo_id: 12, ly_do: 'Khách muốn hạn dài' })
  })

  it('đang soạn: phải quét đủ mã mới đóng gói được; mã lạ bị báo lỗi', async () => {
    GET.mockImplementation(async () => ok(PHIEU({ trang_thai: 'dang_soan_hang', dong: [{ ...DONG, goi_y: [], phan_bo: [{ ...PB, trang_thai: 'da_xuat' }] }] })))
    POST.mockResolvedValue(ok(PHIEU({ trang_thai: 'cho_lay_hang' })))
    dung('/nhan-vien/soan-hang/9')
    const u = userEvent.setup()
    const o = await screen.findByPlaceholderText(/Quét mã vạch/)
    const nut = screen.getByText('Đóng gói & tạo vận đơn').closest('button')!
    expect(nut).toBeDisabled()
    await u.type(o, '999{enter}')
    expect(await screen.findByText(/không thuộc đơn này/)).toBeInTheDocument()
    expect(nut).toBeDisabled()
    await u.type(o, '893001{enter}893001{enter}')
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/soan-hang/{don_id}/dong-goi')
  })

  it('có vận đơn và chế độ giả: hiện mã vận đơn và nút giả lập gửi sự kiện đúng mã', async () => {
    GET.mockImplementation(async () => ok(PHIEU({ trang_thai: 'cho_lay_hang', van_don: [{ ma_van_don: 'GIA9123456', don_vi_van_chuyen: 'GIA', created_at: '2026-10-16T02:00:00Z' }] })))
    POST.mockResolvedValue(ok({ trang_thai: 'ok' }))
    dung('/nhan-vien/soan-hang/9')
    const u = userEvent.setup()
    expect(await screen.findByText('GIA GIA9123456')).toBeInTheDocument()
    await u.click(screen.getByText('Đã lấy hàng'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0]).toEqual(['/api/v1/webhook/gia-van-chuyen', { body: { ma_van_don: 'GIA9123456', trang_thai_doi_tac: 'picked' } }])
  })

  it('chỉ có quyền xem thì không có nút thao tác', async () => {
    dung('/nhan-vien/soan-hang/9', { 'order.pick': 'chi_xem' })
    await screen.findByText('Phiếu soạn hàng DHABCD2345')
    expect(screen.queryByText('Bắt đầu soạn hàng')).not.toBeInTheDocument()
    expect(screen.queryByText('Đổi lô')).not.toBeInTheDocument()
  })
})
