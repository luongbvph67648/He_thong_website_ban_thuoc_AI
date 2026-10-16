import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: (...a: unknown[]) => DELETE(...a) },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const KM = {
  id: 7, ten: 'Tuần lễ vàng', loai_giam: 'phan_tram', gia_tri: '10.00', giam_toi_da: '50000.00', don_toi_thieu: '100000.00',
  bat_dau: '2026-10-01T00:00:00Z', ket_thuc: '2026-12-01T00:00:00Z', tong_luot: 100, luot_moi_khach: 1, pham_vi: 'toan_bo',
  dang_hoat_dong: true, trang_thai: 'dang_hieu_luc', so_ma: 1, da_dung: 3,
}
const CHI_TIET = { ...KM, phien_ban: 'pv1', danh_muc: [], san_pham: [], ma_giam_gia: [{ id: 1, ma: 'GIAM10AB', so_luot_da_dung: 0 }, { id: 2, ma: 'DADUNG', so_luot_da_dung: 3 }] }
const admin = { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'promotion.manage': 'day_du' } } as const

beforeEach(() => {
  for (const m of [GET, POST, PUT, DELETE]) m.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/khuyen-mai') return ok({ du_lieu: [KM], tong: 1, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/khuyen-mai/{km_id}') return ok(CHI_TIET)
    if (duong === '/api/v1/noi-bo/danh-muc') return ok([])
    if (duong === '/api/v1/noi-bo/toi') return ok({})
    return ok([])
  })
})

describe('TrangKhuyenMai (AD06)', () => {
  it('hiện danh sách với mức giảm, trạng thái, lượt đã dùng', async () => {
    renderTai('/quan-tri/khuyen-mai', admin)
    expect(await screen.findByText('Tuần lễ vàng')).toBeInTheDocument()
    expect(screen.getByText('10% (tối đa 50.000 ₫)')).toBeInTheDocument()
    expect(screen.getByText('3 / 100')).toBeInTheDocument()
    expect(screen.getByText('Đang diễn ra')).toBeInTheDocument()
  })

  it('mở rộng dòng để sinh mã và chỉ xóa được mã chưa dùng', async () => {
    POST.mockResolvedValue(ok([{ id: 9, ma: 'NEWCODE1', so_luot_da_dung: 0 }]))
    DELETE.mockResolvedValue({ response: { ok: true, status: 204 } })
    renderTai('/quan-tri/khuyen-mai', admin)
    await screen.findByText('Tuần lễ vàng')
    const u = userEvent.setup()
    await u.click(document.querySelector('.ant-table-row-expand-icon')!)
    const dong1 = (await screen.findByText('GIAM10AB')).closest('tr')!
    const dong2 = screen.getByText('DADUNG').closest('tr')!
    expect(within(dong1).getByText('Xóa')).toBeInTheDocument()
    expect(within(dong2).queryByText('Xóa')).not.toBeInTheDocument()
    await u.click(screen.getByText('Sinh mã ngẫu nhiên'))
    await waitFor(() => expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/khuyen-mai/{km_id}/ma', { params: { path: { km_id: 7 } }, body: { so_luong: 1 } }))
  })

  it('không có quyền ghi thì ẩn nút tạo và sửa', async () => {
    renderTai('/quan-tri/khuyen-mai', { ...admin, quyen: { 'promotion.manage': 'chi_xem' } })
    await screen.findByText('Tuần lễ vàng')
    expect(screen.queryByRole('button', { name: 'Tạo khuyến mãi' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sửa' })).not.toBeInTheDocument()
  })

  it('tạo khuyến mãi phạm vi toàn bộ gửi đúng nội dung', async () => {
    POST.mockResolvedValue(ok(CHI_TIET))
    renderTai('/quan-tri/khuyen-mai', admin)
    const u = userEvent.setup()
    await u.click(await screen.findByRole('button', { name: 'Tạo khuyến mãi' }))
    await u.type(await screen.findByLabelText('Tên chương trình'), 'Giảm hè')
    await u.type(screen.getByLabelText('Phần trăm giảm'), '15')
    const kho = screen.getAllByPlaceholderText(/Start date|Ngày bắt đầu/i)[0]
    await u.click(kho)
    await u.type(kho, '01/11/2026 00:00{enter}')
    const ket = screen.getAllByPlaceholderText(/End date|Ngày kết thúc/i)[0]
    await u.click(ket)
    await u.type(ket, '30/11/2026 23:59{enter}')
    await u.click(screen.getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(POST).toHaveBeenCalled(), { timeout: 5000 })
    const body = POST.mock.calls[0][1].body
    expect(body).toMatchObject({ ten: 'Giảm hè', loai_giam: 'phan_tram', gia_tri: '15', pham_vi: 'toan_bo', danh_muc_ids: [], san_pham_ids: [], luot_moi_khach: 1 })
  })
})
