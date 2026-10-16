import { screen, waitFor, within } from '@testing-library/react'
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
const dung = (quyen: object) => renderTai('/nhan-vien/tu-van', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: quyen as never })
const TOM = (rieng: object = {}) => ({ id: 3, ma_phien: '11111111-1111-4111-8111-111111111111', trang_thai: 'cho_duoc_si', tom_tat: 'Khách ho kéo dài.', ten_khach: 'Nguyễn An', so_dien_thoai_goi_lai: null, bi_gan_co: false, duoc_si_cua_toi: false, created_at: '2026-10-16T01:00:00Z', ...rieng })
const CT = (rieng: object = {}) => ({ ...TOM(), tin_nhan: [{ id: 1, vai_tro: 'khach', noi_dung: 'Mình bị ho', dau_hieu_nguy_hiem: false, created_at: '2026-10-16T01:00:00Z' }], ho_so_suc_khoe: null, ...rieng })

beforeEach(() => {
  GET.mockReset(); POST.mockReset(); WsGia.tatCa = []
  vi.stubGlobal('WebSocket', WsGia)
  GET.mockImplementation(async (d: string) => {
    if (d === '/api/v1/noi-bo/tu-van') return ok([TOM()])
    if (d === '/api/v1/noi-bo/tu-van/{hoi_thoai_id}') return ok(CT())
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
})
afterEach(() => vi.unstubAllGlobals())

describe('Tư vấn khách (DS06)', () => {
  it('hiện hàng chờ với tóm tắt AI; nhận tư vấn gọi API, mở chat WebSocket và gửi tin', async () => {
    POST.mockResolvedValue(ok(CT({ trang_thai: 'duoc_si_dang_xu_ly', duoc_si_cua_toi: true, ho_so_suc_khoe: { nam_sinh: 1985, dang_mang_thai: false, dang_cho_con_bu: false, di_ung: ['Penicillin'] } })))
    dung({ 'chat.handle': 'day_du' })
    const u = userEvent.setup()
    expect(await screen.findByText('Khách ho kéo dài.')).toBeInTheDocument()
    await u.click(screen.getByText('Nhận tư vấn'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/tu-van/{hoi_thoai_id}/nhan')
    expect(await screen.findByText(/Dị ứng: Penicillin/)).toBeInTheDocument()
    await waitFor(() => expect(WsGia.tatCa).toHaveLength(1))
    expect(WsGia.cuoi().url).toContain('ma_phien=11111111-1111-4111-8111-111111111111')
    WsGia.cuoi().mo()
    expect(WsGia.cuoi().gui[0]).toEqual({ loai: 'xac_thuc', vai_tro: 'duoc_si', token: 'token-thu' })
    WsGia.cuoi().nhan({ loai: 'he_thong', su_kien: 'da_ket_noi' })
    const o = await screen.findByLabelText('Tin nhắn cho khách')
    await waitFor(() => expect(o).toBeEnabled())
    await u.type(o, 'Chào bạn{Enter}')
    expect(WsGia.cuoi().gui.at(-1)).toEqual({ loai: 'tin_nhan', noi_dung: 'Chào bạn' })
    WsGia.cuoi().nhan({ loai: 'tin_nhan', id: 9, vai_tro: 'khach', noi_dung: 'Cảm ơn dược sĩ' })
    expect(await screen.findByText('Cảm ơn dược sĩ')).toBeInTheDocument()
  })

  it('đã có người nhận: báo lỗi 409 từ máy chủ', async () => {
    POST.mockResolvedValue({ error: { ma_loi: 'CHUYEN_TRANG_THAI_KHONG_HOP_LE', thong_diep: 'Phiên này không còn ở hàng chờ', chi_tiet: null }, response: { ok: false, status: 409 } })
    dung({ 'chat.handle': 'day_du' })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Nhận tư vấn'))
    expect(await screen.findByText('Phiên này không còn ở hàng chờ')).toBeInTheDocument()
    expect(WsGia.tatCa).toHaveLength(0)
  })

  it('chỉ xem: không có nút nhận; phiên chờ gọi lại hiện số điện thoại và nút đóng', async () => {
    GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/tu-van' ? ok([TOM({ trang_thai: 'cho_goi_lai', so_dien_thoai_goi_lai: '0912345678' })]) : ok(CT({ trang_thai: 'cho_goi_lai', so_dien_thoai_goi_lai: '0912345678' }))))
    dung({ 'chat.handle': 'chi_xem' })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Xem'))
    const nhat = await screen.findByRole('log', { name: 'Nội dung trò chuyện' })
    expect(within(nhat).getByText('Mình bị ho')).toBeInTheDocument()
    expect(screen.getByText('0912345678', { selector: 'td, span' })).toBeInTheDocument()
    expect(screen.queryByText('Nhận tư vấn')).not.toBeInTheDocument()
    expect(WsGia.tatCa).toHaveLength(0)
  })

  it('kết thúc tư vấn gọi API đóng phiên', async () => {
    GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/tu-van' ? ok([TOM({ trang_thai: 'duoc_si_dang_xu_ly', duoc_si_cua_toi: true })]) : ok(CT({ trang_thai: 'duoc_si_dang_xu_ly', duoc_si_cua_toi: true }))))
    POST.mockResolvedValue(ok(CT({ trang_thai: 'da_dong' })))
    dung({ 'chat.handle': 'day_du' })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Tiếp tục'))
    await u.click(await screen.findByText('Kết thúc tư vấn'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/tu-van/{hoi_thoai_id}/dong')
  })
})
