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
function luong(...phan: string[]): ReadableStream<Uint8Array> {
  const enc = new TextEncoder()
  return new ReadableStream({ start(c) { phan.forEach((p) => c.enqueue(enc.encode(p))); c.close() } })
}
const THE = { id: 1, ten: 'Panadol Extra', slug: 'panadol-extra', loai_san_pham: 'thuoc_khong_ke_don', can_tu_van: false, thuong_hieu: null, quy_cach: null, anh_chinh_url: null, gia: '25000.00', ten_don_vi_gia: 'hộp', con_hang: true }

beforeEach(() => {
  GET.mockReset(); POST.mockReset(); sessionStorage.clear()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/toi/gio-hang' ? ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 }) : ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 })))
})

describe('Widget chat AI (KVL05)', () => {
  it('gửi câu hỏi, hiện câu trả lời stream, thẻ sản phẩm và gửi báo sai', async () => {
    POST.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/tu-van/chat') {
        return { data: luong('event: van_ban\ndata: {"noi_dung":"Panadol giúp "}\n\nevent: van_ban\ndata: {"noi_dung":"hạ sốt."}\n\n', `event: the_san_pham\ndata: ${JSON.stringify({ san_pham: [THE] })}\n\nevent: ket_thuc\ndata: {"tin_nhan_id":9}\n\n`), response: { ok: true, status: 200 } }
      }
      return ok({})
    })
    renderTai('/dang-nhap')
    const u = userEvent.setup()
    await u.click(await screen.findByLabelText('Mở chat tư vấn'))
    await u.type(screen.getByLabelText('Tin nhắn'), 'Hạ sốt dùng gì?{Enter}')
    expect(await screen.findByText('Panadol giúp hạ sốt.')).toBeInTheDocument()
    expect(await screen.findByText('Panadol Extra')).toBeInTheDocument()
    expect(screen.getByText(/Từ 25.000/)).toBeInTheDocument()
    const goi = POST.mock.calls[0][1]
    expect(goi.body.noi_dung).toBe('Hạ sốt dùng gì?')
    expect(goi.body.ma_phien).toMatch(/^[0-9a-f-]{36}$/)
    await u.click(await screen.findByText('Báo sai'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][1].body).toEqual({ ma_phien: goi.body.ma_phien, tin_nhan_id: 9, ket_qua: 'khong_huu_ich' })
  })

  it('quá giới hạn lượt hiện thông báo và bỏ tin chờ', async () => {
    POST.mockResolvedValue({ error: { ma_loi: 'QUA_GIOI_HAN' }, response: { ok: false, status: 429 } })
    renderTai('/dang-nhap')
    const u = userEvent.setup()
    await u.click(await screen.findByLabelText('Mở chat tư vấn'))
    await u.type(screen.getByLabelText('Tin nhắn'), 'xin chào{Enter}')
    expect(await screen.findByText(/hỏi quá nhanh/)).toBeInTheDocument()
  })
})
