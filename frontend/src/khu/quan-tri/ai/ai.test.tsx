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
const CH = { ai_module: { tim_kiem: true, chat: true, tra_anh: true, doc_don_thuoc: true, goi_y: true, du_bao: true }, ai_dau_hieu_nguy_hiem: ['đau ngực'], ai_nguong_chuyen_duoc_si: 0.6, ai_loi_nhac_bo_sung: '', phien_ban: 'abc' }
const TK = { tong_doan: 10, theo_nguon: { san_pham: 8, bai_viet: 2 }, mo_hinh_hien_tai: 'gia-lap', mo_hinh_trong_kho: ['gia-lap'], cap_nhat_gan_nhat: '2026-10-16T03:00:00Z', can_dong_bo_lai_vector: false }
const admin = (quyen: object) => ({ loai: 'noi_bo' as const, vaiTro: 'ADMIN', quyen: quyen as never })

beforeEach(() => {
  GET.mockReset(); POST.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/cau-hinh-ai' ? ok(CH) : d === '/api/v1/noi-bo/tri-thuc' ? ok(TK) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
  PUT.mockResolvedValue(ok({ ...CH, phien_ban: 'def' }))
  POST.mockResolvedValue(ok({ them: 3, sua: 2, xoa: 1, bo_qua: 4, tong_doan: 10, mo_hinh: 'gia-lap' }))
})

describe('Quản trị AI', () => {
  it('AD09: tắt module chatbot rồi lưu kèm phien_ban', async () => {
    renderTai('/quan-tri/cau-hinh-ai', admin({ 'ai.config': 'day_du' }))
    const u = userEvent.setup()
    const chat = (await screen.findAllByRole('switch'))[1]
    await u.click(chat)
    await u.click(screen.getByText('Lưu'))
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    const body = PUT.mock.calls[0][1].body
    expect(body.phien_ban).toBe('abc')
    expect(body.ai_module.chat).toBe(false)
    expect(body.ai_nguong_chuyen_duoc_si).toBe(0.6)
  })
  it('AD10: đồng bộ hiện số thêm/sửa/xóa', async () => {
    renderTai('/quan-tri/tri-thuc-ai', admin({ 'ai.knowledge.sync': 'day_du' }))
    const u = userEvent.setup()
    await u.click(await screen.findByText('Đồng bộ ngay'))
    expect(await screen.findByText('Bỏ qua (không đổi)')).toBeInTheDocument()
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/tri-thuc/dong-bo')
  })
  it('chỉ xem: không có nút đồng bộ', async () => {
    renderTai('/quan-tri/tri-thuc-ai', admin({ 'ai.knowledge.sync': 'chi_xem' }))
    expect(await screen.findByText('Tổng số đoạn')).toBeInTheDocument()
    expect(screen.queryByText('Đồng bộ ngay')).not.toBeInTheDocument()
  })
})
