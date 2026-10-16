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
const TOM = { id: 3, ma_yeu_cau: 'DT0003', ma_don: 'DHABC', ten_khach: 'An', so_dien_thoai_khach: '0912345678', ly_do: 'hu_hong', trang_thai: 'cho_duyet', created_at: '2026-10-16T03:00:00Z' }
const CT = {
  ...TOM, mo_ta: 'Vỡ vỏ', tong_da_thanh_toan: '100000.00', huong_xu_ly: null, so_tien_hoan: null, ma_van_don: null, ket_qua_kiem_hang: null, ly_do_tu_choi: null,
  da_co_giao_dich_hoan: false, anh: [], dong: [{ ct_don_hang_id: 1, ten_san_pham: 'Panadol', ten_don_vi: 'hộp', so_luong_tra: 1, so_luong_mua: 2, thanh_tien: '50000.00', so_luong_nhan: null }],
}

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/doi-tra') return ok([TOM])
    if (duong === '/api/v1/noi-bo/doi-tra/{yc_id}') return ok(CT)
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
  POST.mockResolvedValue(ok({}))
})

describe('Xử lý đổi trả (DS09)', () => {
  it('liệt kê yêu cầu, mở chi tiết và duyệt với hướng hoàn tiền', async () => {
    renderTai('/nhan-vien/doi-tra', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'return.review': 'day_du' } as never })
    const u = userEvent.setup()
    expect(await screen.findByText('DT0003')).toBeInTheDocument()
    await u.click(screen.getByText('Xử lý'))
    expect(await screen.findByText('Vỡ vỏ')).toBeInTheDocument()
    await u.click(await screen.findByText('Duyệt, tạo vận đơn trả'))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/doi-tra/{yc_id}/duyet')
    expect(POST.mock.calls[0][1].body).toEqual({ huong_xu_ly: 'hoan_tien' })
  })
})
