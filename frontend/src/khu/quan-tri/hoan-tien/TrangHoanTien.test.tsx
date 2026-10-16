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
const HOAN = {
  id: 4, ma_don: 'DHABC', ten_khach: 'An', so_tien: '50000.00', cong_thanh_toan: 'vnpay', trang_thai: 'khoi_tao', nguon: 'huy_don', ma_yeu_cau: null,
  tong_da_thanh_toan: '50000.00', tu_dong_qua_cong: true, thong_tin_nhan_hoan: null, thieu_tai_khoan: false, chung_tu: null, ghi_chu: null,
  created_at: '2026-10-16T03:00:00Z', xu_ly_luc: null,
}
let ds: unknown[] = []
const dung = () => renderTai('/quan-tri/hoan-tien', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'refund.confirm': 'day_du' } as never })

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  ds = [HOAN]
  GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/hoan-tien' ? ok(ds) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
  POST.mockResolvedValue(ok({}))
})

describe('Hoàn tiền (AD17)', () => {
  it('đơn VNPay: xác nhận gọi API hoàn không cần chứng từ', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Xác nhận'))
    expect(await screen.findByText(/Hệ thống gọi API hoàn tiền của VNPay/)).toBeInTheDocument()
    await u.click(screen.getByText('Hoàn qua VNPay'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/hoan-tien/{gd_id}/xac-nhan')
    expect(POST.mock.calls[0][1].params.path.gd_id).toBe(4)
  })

  it('chuyển khoản tay: cần chứng từ mới bấm được; thiếu tài khoản khách thì chưa xác nhận', async () => {
    ds = [{ ...HOAN, id: 5, cong_thanh_toan: 'cod', tu_dong_qua_cong: false, nguon: 'doi_tra', ma_yeu_cau: 'DT1', thong_tin_nhan_hoan: { ngan_hang: 'VCB', so_tai_khoan: '0123456789', chu_tai_khoan: 'AN' } }]
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Xác nhận'))
    expect(await screen.findByText('0123456789')).toBeInTheDocument()
    expect(screen.getByText('Đã chuyển khoản').closest('button')).toBeDisabled()
  })

  it('đổi trả chưa có tài khoản nhận hoàn hiện nhãn chờ khách', async () => {
    ds = [{ ...HOAN, cong_thanh_toan: 'cod', tu_dong_qua_cong: false, nguon: 'doi_tra', ma_yeu_cau: 'DT1', thieu_tai_khoan: true }]
    dung()
    expect(await screen.findByText('Chờ khách nhập tài khoản')).toBeInTheDocument()
    expect(screen.queryByText('Xác nhận')).not.toBeInTheDocument()
  })
})
