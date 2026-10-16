import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const dung = () => renderTai('/quan-tri/giam-sat-ai', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'ai.monitor': 'day_du' } as never })
const TK = { tu_ngay: '2026-09-17', den_ngay: '2026-10-16', tong_hoi_thoai: 40, so_chuyen_duoc_si: 10, ty_le_chuyen_duoc_si: '0.2500', so_gan_co: 3, tong_token: 12345, tong_chi_phi_usd: '1.234500',
  cau_hoi_pho_bien: [{ y_dinh: 'hoi_san_pham', so_luong: 20 }, { y_dinh: 'chinh_sach', so_luong: 5 }], danh_gia: { khach_huu_ich: 8, khach_khong_huu_ich: 2, duoc_si_dung: 4, duoc_si_sai: 1 } }
const TOM = { id: 9, created_at: '2026-10-15T01:00:00Z', loai: 'duoc_si', trang_thai: 'da_dong', bi_gan_co: true, ly_do_gan_co: 'dau_hieu_nguy_hiem', so_tin_nhan: 3, so_khach_bao_sai: 0, so_duoc_si_danh_gia: 0, cau_hoi_dau: 'Tôi [tên], [SĐT] bị ho', tong_token: 100, chi_phi: '0.01' }

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async (d: string) => {
    if (d.endsWith('/thong-ke')) return ok(TK)
    if (d.endsWith('/hoi-thoai')) return ok({ du_lieu: [TOM], tong: 1, trang: 1, kich_thuoc: 20 })
    if (d.endsWith('/hoi-thoai/{hoi_thoai_id}')) return ok({ ...TOM, tin_nhan: [{ id: 1, vai_tro: 'khach', noi_dung: 'Tôi [tên], [SĐT] bị ho', y_dinh: 'trieu_chung', dau_hieu_nguy_hiem: true, created_at: TOM.created_at, danh_gia: [] }] })
    if (d.endsWith('/tim-kiem-khong-ket-qua')) return ok([{ tu_khoa: 'thuốc lạ', so_lan: 3, lan_cuoi: '2026-10-15T01:00:00Z' }])
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
})

describe('Giám sát AI (AD11)', () => {
  it('thống kê: tỉ lệ chuyển dược sĩ, chi phí, câu hỏi phổ biến, đánh giá; gửi khoảng ngày lên máy chủ', async () => {
    dung()
    expect(await screen.findByText('25.0%')).toBeInTheDocument()
    expect(screen.getByText('1.234500')).toBeInTheDocument()
    expect(screen.getByText('Hỏi sản phẩm')).toBeInTheDocument()
    expect(screen.getByText('Chính sách')).toBeInTheDocument()
    const goi = GET.mock.calls.find((c) => String(c[0]).endsWith('/thong-ke'))!
    expect(goi[1].params.query.tu_ngay).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(goi[1].params.query.den_ngay).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('hội thoại đã ẩn danh: mở xem nội dung đã che, không có thông tin định danh', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Hội thoại'))
    expect(await screen.findByText('Tôi [tên], [SĐT] bị ho')).toBeInTheDocument()
    await u.click(screen.getByText('Tôi [tên], [SĐT] bị ho'))
    expect(await screen.findByLabelText('Nội dung hội thoại đã ẩn danh')).toBeInTheDocument()
    expect(screen.getByText('Dấu hiệu nguy hiểm')).toBeInTheDocument()
    expect(screen.getByText(/Đã che số điện thoại, email và tên/)).toBeInTheDocument()
  })

  it('tìm kiếm không có kết quả', async () => {
    dung()
    const u = userEvent.setup()
    await u.click(await screen.findByText('Tìm kiếm không có kết quả'))
    expect(await screen.findByText('thuốc lạ')).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.some((c) => String(c[0]).endsWith('/tim-kiem-khong-ket-qua'))).toBe(true))
  })

  it('lỗi tải thống kê thì báo lỗi', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 500 } }))
    dung()
    expect(await screen.findByText('Không tải được thống kê')).toBeInTheDocument()
  })
})
