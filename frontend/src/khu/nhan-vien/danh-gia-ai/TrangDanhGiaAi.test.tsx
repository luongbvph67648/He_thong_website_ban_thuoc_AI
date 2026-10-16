import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn(), PUT: (...a: unknown[]) => PUT(...a), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const dung = (muc: 'day_du' | 'chi_xem' = 'day_du') =>
  renderTai('/nhan-vien/danh-gia-ai', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'ai_answer.review': muc } as never })
const TOM = { id: 7, created_at: '2026-10-16T01:00:00Z', loai: 'ai', trang_thai: 'dang_mo', bi_gan_co: true, ly_do_gan_co: 'dau_hieu_nguy_hiem', so_tin_nhan: 2, so_khach_bao_sai: 1, so_duoc_si_danh_gia: 0, cau_hoi_dau: 'Liều Paracetamol cho [tên]?', tong_token: 10, chi_phi: '0.001' }
const TIN = (rieng: object = {}) => ({ ...TOM, tin_nhan: [
  { id: 1, vai_tro: 'khach', noi_dung: 'Liều Paracetamol cho [tên]?', y_dinh: 'cach_dung', dau_hieu_nguy_hiem: false, created_at: TOM.created_at, danh_gia: [] },
  { id: 2, vai_tro: 'ai', noi_dung: 'Uống 10 viên mỗi ngày', y_dinh: null, dau_hieu_nguy_hiem: false, created_at: TOM.created_at, danh_gia: [{ nguon: 'khach', ket_qua: 'khong_huu_ich', ghi_chu: null, cua_toi: false }] },
], ...rieng })

beforeEach(() => {
  GET.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => {
    if (d === '/api/v1/noi-bo/danh-gia-ai') return ok({ du_lieu: [TOM], tong: 1, trang: 1, kich_thuoc: 20 })
    if (d === '/api/v1/noi-bo/danh-gia-ai/{hoi_thoai_id}') return ok(TIN())
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
})

describe('Đánh giá câu trả lời AI (DS12)', () => {
  it('liệt kê hội thoại gắn cờ (mặc định chỉ chưa đánh giá) kèm lý do', async () => {
    dung()
    expect(await screen.findByText('Liều Paracetamol cho [tên]?')).toBeInTheDocument()
    expect(screen.getByText('Dấu hiệu nguy hiểm')).toBeInTheDocument()
    expect(screen.getByText('Khách báo sai: 1')).toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/danh-gia-ai')!
    expect(goi[1].params.query).toMatchObject({ trang: 1, chua_danh_gia: true })
  })

  it('mở hội thoại, đánh dấu đúng cho câu trả lời của AI', async () => {
    PUT.mockResolvedValue(ok(TIN()))
    dung()
    const u = userEvent.setup()
    await u.click((await screen.findByText('Xem')).closest('button')!)
    expect(await screen.findByText('Uống 10 viên mỗi ngày')).toBeInTheDocument()
    expect(screen.getByText('Khách: không hữu ích')).toBeInTheDocument()
    await u.click(screen.getByText('Đúng').closest('button')!)
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][0]).toBe('/api/v1/noi-bo/danh-gia-ai/{hoi_thoai_id}/tin-nhan/{tin_nhan_id}')
    expect(PUT.mock.calls[0][1]).toMatchObject({ params: { path: { hoi_thoai_id: 7, tin_nhan_id: 2 } }, body: { ket_qua: 'dung', ghi_chu: null } })
  })

  it('đánh dấu sai phải ghi nội dung đúng: bấm Sai lần đầu mở ô ghi chú, lần hai gửi', async () => {
    PUT.mockResolvedValue(ok(TIN()))
    dung()
    const u = userEvent.setup()
    await u.click((await screen.findByText('Xem')).closest('button')!)
    await screen.findByText('Uống 10 viên mỗi ngày')
    await u.click(screen.getByText('Sai').closest('button')!)
    expect(PUT).not.toHaveBeenCalled()
    await u.type(screen.getByLabelText('Nội dung đúng'), 'Tối đa 4 g mỗi ngày')
    await u.click(screen.getByText('Sai').closest('button')!)
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][1].body).toEqual({ ket_qua: 'sai', ghi_chu: 'Tối đa 4 g mỗi ngày' })
  })

  it('lỗi từ máy chủ hiện thông điệp; chỉ xem thì không có nút đánh giá', async () => {
    PUT.mockResolvedValue({ error: { ma_loi: 'DU_LIEU_KHONG_HOP_LE', thong_diep: 'Câu trả lời sai cần ghi nội dung đúng', chi_tiet: null }, response: { ok: false, status: 400 } })
    dung()
    const u = userEvent.setup()
    await u.click((await screen.findByText('Xem')).closest('button')!)
    await screen.findByText('Uống 10 viên mỗi ngày')
    await u.click(screen.getByText('Đúng').closest('button')!)
    expect(await screen.findByText('Câu trả lời sai cần ghi nội dung đúng')).toBeInTheDocument()
  })

  it('Admin chỉ xem: mở được hội thoại nhưng không có nút Đúng/Sai', async () => {
    dung('chi_xem')
    const u = userEvent.setup()
    await u.click((await screen.findByText('Xem')).closest('button')!)
    await screen.findByText('Uống 10 viên mỗi ngày')
    expect(screen.queryByText('Đúng')).not.toBeInTheDocument()
  })
})
