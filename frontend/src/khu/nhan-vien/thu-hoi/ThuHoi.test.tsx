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
const LENH = { id: 4, ma_lenh: 'TH260001', san_pham_ten: 'Panadol', so_lo: 'L01', can_cu: 'CV 1', muc_do: null, trang_thai: 'dang_thu_hoi', so_khach: 1, so_khach_da_xu_ly: 0, created_at: '2026-10-16T03:00:00Z', dong_luc: null }
const KHACH = { id: 8, ma_don: 'DHABC', ten_khach: 'An', so_dien_thoai: '0912345678', so_luong_da_ban: 3, so_luong_da_thu_ve: 0, ket_qua_lien_he: 'chua_lien_he', ghi_chu: null, cap_nhat_luc: null }

beforeEach(() => {
  GET.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => {
    if (d === '/api/v1/noi-bo/thu-hoi/lien-he') return ok({ du_lieu: [LENH], tong: 1, trang: 1, kich_thuoc: 20 })
    if (d.endsWith('/khach')) return ok([KHACH])
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
  PUT.mockResolvedValue(ok({}))
})

describe('Liên hệ khách thu hồi (DS13)', () => {
  it('ghi kết quả liên hệ cho một đơn', async () => {
    renderTai('/nhan-vien/thu-hoi', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'recall.contact': 'day_du' } as never })
    const u = userEvent.setup()
    await u.click(await screen.findByText('Danh sách khách'))
    expect(await screen.findByText('DHABC')).toBeInTheDocument()
    await u.click(screen.getByText('Ghi kết quả'))
    await u.click(await screen.findByText('Lưu'))
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][0]).toBe('/api/v1/noi-bo/thu-hoi/lien-he/khach/{ct_id}')
    expect(PUT.mock.calls[0][1].params.path.ct_id).toBe(8)
  })
})
