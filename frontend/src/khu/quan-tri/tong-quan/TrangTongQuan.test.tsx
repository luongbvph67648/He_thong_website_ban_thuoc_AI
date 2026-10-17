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
const BC = {
  tu_ngay: '2026-09-17', den_ngay: '2026-10-16', so_don_hoan_tat: 12, doanh_thu: '5000000.00', hoan_tien: '200000.00', doanh_thu_thuan: '4800000.00', gia_von: '3000000.00', loi_nhuan_gop: '1800000.00',
  doanh_thu_theo_ngay: [{ ngay: '2026-10-14', so_don: 2, doanh_thu: '100000.00' }, { ngay: '2026-10-15', so_don: 0, doanh_thu: '0.00' }, { ngay: '2026-10-16', so_don: 5, doanh_thu: '400000.00' }],
  ban_chay: [{ san_pham_id: 1, sku: 'SKU-1', ten: 'Paracetamol 500', so_luong_co_so: 300, doanh_thu: '900000.00' }],
  gia_tri_ton_kho: '25000000.00', ton_kho_theo_trang_thai: [{ trang_thai: 'dang_ban', so_luong: 1000, gia_tri: '24000000.00' }, { trang_thai: 'can_han', so_luong: 50, gia_tri: '1000000.00' }],
  so_lo_can_han: 1, lo_can_han: [{ lo_id: 3, sku: 'SKU-2', ten_san_pham: 'Vitamin C', so_lo: 'L01', han_su_dung: '2026-11-10', con_ngay: 25, so_luong_ton: 50, gia_tri: '1000000.00' }],
  hieu_qua_ai: { tu_ngay: '2026-09-17', den_ngay: '2026-10-16', tong_hoi_thoai: 40, so_chuyen_duoc_si: 10, ty_le_chuyen_duoc_si: '0.2500', so_gan_co: 3, tong_token: 1, tong_chi_phi_usd: '1.234500', cau_hoi_pho_bien: [], danh_gia: { khach_huu_ich: 8, khach_khong_huu_ich: 2, duoc_si_dung: 4, duoc_si_sai: 1 } },
}
const admin = () => renderTai('/quan-tri', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: { 'report.all': 'day_du' } as never })

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/bao-cao/tong-hop' ? ok(BC) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} }))
})

describe('Tổng quan Admin (AD14)', () => {
  it('hiện doanh thu, hoàn tiền, thuần, lợi nhuận, tồn kho, bán chạy, cận hạn, AI và biểu đồ', async () => {
    admin()
    expect(await screen.findByText('Paracetamol 500 (SKU-1)')).toBeInTheDocument()
    expect(screen.getAllByText(/5\.000\.000/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/1\.800\.000/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/25\.000\.000/).length).toBeGreaterThan(0)
    expect(screen.getByText('25 ngày')).toBeInTheDocument()
    expect(screen.getByText('25.0%')).toBeInTheDocument()
    expect(screen.getByLabelText('Biểu đồ doanh thu theo ngày').querySelectorAll('rect')).toHaveLength(3)
    const goi = GET.mock.calls.find((c) => c[0] === '/api/v1/noi-bo/bao-cao/tong-hop')!
    expect(goi[1].params.query.tu_ngay).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  })

  it('xuất Excel gọi API tải về dạng blob', async () => {
    GET.mockImplementation(async (d: string) => {
      if (d === '/api/v1/noi-bo/bao-cao/tong-hop') return ok(BC)
      if (d.endsWith('/tong-hop/excel')) return ok(new Blob(['x']))
      return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
    })
    admin()
    const u = userEvent.setup()
    await u.click((await screen.findByText('Xuất Excel')).closest('button')!)
    await waitFor(() => expect(GET.mock.calls.some((c) => String(c[0]).endsWith('/tong-hop/excel'))).toBe(true))
    expect(GET.mock.calls.find((c) => String(c[0]).endsWith('/tong-hop/excel'))![1].parseAs).toBe('blob')
  })

  it('lỗi tải báo cáo thì báo lỗi', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'DU_LIEU_KHONG_HOP_LE', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 400 } }))
    admin()
    expect(await screen.findByText(/Không tải được báo cáo/)).toBeInTheDocument()
  })
})
