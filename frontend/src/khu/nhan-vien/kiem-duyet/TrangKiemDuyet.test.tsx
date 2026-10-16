import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DG = { id: 1, san_pham_ten: 'Panadol', ten_khach: 'An', so_sao: 1, noi_dung: 'Tệ', anh: [], dang_hien: true, phan_hoi: null, created_at: '2026-10-16T03:00:00Z' }
const HD = { id: 2, san_pham_ten: 'Panadol', san_pham_slug: 'panadol', ten_khach: 'An', cau_hoi: 'Dùng cho trẻ được không?', tra_loi: null, tra_loi_luc: null, dang_hien: true, created_at: '2026-10-16T03:00:00Z' }

beforeEach(() => {
  GET.mockReset(); POST.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => {
    if (d.endsWith('/danh-gia')) return ok({ du_lieu: [DG], tong: 1, trang: 1, kich_thuoc: 20 })
    if (d.endsWith('/hoi-dap')) return ok({ du_lieu: [HD], tong: 1, trang: 1, kich_thuoc: 20 })
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
  PUT.mockResolvedValue(ok({}))
  POST.mockResolvedValue(ok({}))
})
const dung = () => renderTai('/nhan-vien/kiem-duyet', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'review.moderate': 'day_du', 'qa.answer': 'day_du' } as never })

describe('Kiểm duyệt (DS11)', () => {
  it('ẩn đánh giá', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Ẩn'))
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][1].body).toEqual({ dang_hien: false })
  })
  it('trả lời câu hỏi', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Hỏi đáp'))
    await u.click(await screen.findByText('Trả lời'))
    await u.type(await screen.findByLabelText('Nội dung trả lời'), 'Trẻ trên 6 tuổi')
    await u.click(screen.getByText('Gửi trả lời'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({ tra_loi: 'Trẻ trên 6 tuổi' })
  })
})
