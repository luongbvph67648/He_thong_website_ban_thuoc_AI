import { screen, waitFor } from '@testing-library/react'
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
  id: 7, ma_don: 'DHABCD2345', ten_nguoi_nhan: 'Trần Bình', sdt_nguoi_nhan: '0987654321', tong_tien: '45000.00', phuong_thuc_tt: 'cod',
  trang_thai_tt: 'chua_thanh_toan', dong: [{ ten_san_pham: 'Paracetamol', ten_don_vi: 'viên', so_luong: 2 }], ...rieng,
})
const QUAY = '/api/v1/noi-bo/giao-tai-quay'
const tra = (ds: unknown[]) => GET.mockImplementation(async (duong: string) => (duong === QUAY ? ok(ds) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
const dung = () => renderTai('/nhan-vien/giao-tai-quay', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'order.pickup_handover': 'day_du' } as never })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
})

describe('giao đơn tại quầy (DS15)', () => {
  it('đơn chưa trả tiền: phải chọn cách thu rồi mới giao được', async () => {
    tra([DON()])
    POST.mockResolvedValue(ok(DON()))
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('Mã đơn hoặc SĐT của khách'), '0987654321{Enter}')
    expect(await screen.findByText('Đơn DHABCD2345')).toBeInTheDocument()
    expect(GET.mock.calls.find((c) => c[0] === QUAY)![1].params.query).toEqual({ q: '0987654321' })
    const nut = screen.getByRole('button', { name: 'Đã thu tiền, giao hàng' })
    expect(nut).toBeDisabled()
    await u.click(screen.getByLabelText('Tiền mặt'))
    await u.click(nut)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1]).toMatchObject({ params: { path: { don_id: 7 } }, body: { phuong_thuc_thu: 'tien_mat' } })
    await waitFor(() => expect(screen.queryByText('Đơn DHABCD2345')).not.toBeInTheDocument())
  })

  it('đơn đã thanh toán: giao luôn, không thu thêm', async () => {
    tra([DON({ trang_thai_tt: 'da_thanh_toan', phuong_thuc_tt: 'vnpay' })])
    POST.mockResolvedValue(ok(DON()))
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('Mã đơn hoặc SĐT của khách'), 'DHABCD2345{Enter}')
    await u.click(await screen.findByRole('button', { name: 'Giao hàng' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({ phuong_thuc_thu: null })
    expect(screen.queryByLabelText('Tiền mặt')).not.toBeInTheDocument()
  })

  it('không có đơn khớp thì báo trống', async () => {
    tra([])
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText('Mã đơn hoặc SĐT của khách'), 'xyz{Enter}')
    expect(await screen.findByText(/Không có đơn nhận tại nhà thuốc/)).toBeInTheDocument()
  })
})
