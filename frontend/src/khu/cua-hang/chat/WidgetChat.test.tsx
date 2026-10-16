import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { WsGia } from '../../../test/wsGia'

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

  describe('gặp dược sĩ (KTV12)', () => {
    const chatAi = () => ({ data: luong('event: van_ban\ndata: {"noi_dung":"Bạn ho bao lâu?"}\n\nevent: ket_thuc\ndata: {"tin_nhan_id":9}\n\n'), response: { ok: true, status: 200 } })
    beforeEach(() => { WsGia.tatCa = []; vi.stubGlobal('WebSocket', WsGia) })
    afterEach(() => vi.unstubAllGlobals())

    it('trong giờ: chuyển dược sĩ rồi chat trực tiếp qua WebSocket', async () => {
      POST.mockImplementation(async (d: string) => (d === '/api/v1/tu-van/chat' ? chatAi() : ok({ trang_thai: 'cho_duoc_si', trong_gio: true, thong_diep: 'Đang kết nối bạn với dược sĩ' })))
      renderTai('/dang-nhap')
      const u = userEvent.setup()
      await u.click(await screen.findByLabelText('Mở chat tư vấn'))
      expect(screen.queryByText('Gặp dược sĩ')).not.toBeInTheDocument() // chưa hỏi gì
      await u.type(screen.getByLabelText('Tin nhắn'), 'Tôi bị ho{Enter}')
      await u.click(await screen.findByText('Gặp dược sĩ'))
      expect(await screen.findByText('Đang kết nối bạn với dược sĩ')).toBeInTheDocument()
      expect(POST.mock.calls.find((c) => c[0] === '/api/v1/tu-van/gap-duoc-si')![1].body).toMatchObject({ ma_phien: expect.any(String) })
      await waitFor(() => expect(WsGia.tatCa).toHaveLength(1))
      WsGia.cuoi().mo()
      expect(WsGia.cuoi().gui[0]).toEqual({ loai: 'xac_thuc', vai_tro: 'khach' })
      WsGia.cuoi().nhan({ loai: 'he_thong', su_kien: 'da_ket_noi' })
      await u.type(screen.getByLabelText('Tin nhắn'), 'Có ai không?{Enter}')
      expect(WsGia.cuoi().gui.at(-1)).toEqual({ loai: 'tin_nhan', noi_dung: 'Có ai không?' })
      WsGia.cuoi().nhan({ loai: 'tin_nhan', id: 20, vai_tro: 'duoc_si', noi_dung: 'Dược sĩ đây' })
      expect(await screen.findByText('Dược sĩ đây')).toBeInTheDocument()
    })

    it('ngoài giờ: hỏi số điện thoại rồi gửi lại, không mở WebSocket', async () => {
      let lan = 0
      POST.mockImplementation(async (d: string) => {
        if (d === '/api/v1/tu-van/chat') return chatAi()
        return ++lan === 1
          ? { error: { ma_loi: 'DU_LIEU_KHONG_HOP_LE', thong_diep: 'Dữ liệu không hợp lệ', chi_tiet: [{ truong: 'so_dien_thoai', loi: 'x' }] }, response: { ok: false, status: 400 } }
          : ok({ trang_thai: 'cho_goi_lai', trong_gio: false, thong_diep: 'Dược sĩ sẽ gọi lại bạn' })
      })
      renderTai('/dang-nhap')
      const u = userEvent.setup()
      await u.click(await screen.findByLabelText('Mở chat tư vấn'))
      await u.type(screen.getByLabelText('Tin nhắn'), 'Tôi bị ho{Enter}')
      await u.click(await screen.findByText('Gặp dược sĩ'))
      await u.type(await screen.findByLabelText('Số điện thoại để dược sĩ gọi lại'), '0912345678')
      await u.click(screen.getByText('Gửi', { selector: 'button span' }))
      expect(await screen.findByText('Dược sĩ sẽ gọi lại bạn')).toBeInTheDocument()
      const goiCuoi = POST.mock.calls.filter((c) => c[0] === '/api/v1/tu-van/gap-duoc-si').at(-1)!
      expect(goiCuoi[1].body).toMatchObject({ so_dien_thoai: '0912345678' })
      expect(WsGia.tatCa).toHaveLength(0)
    })
  })
})
