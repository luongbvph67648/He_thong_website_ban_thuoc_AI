import { screen, waitFor, within } from '@testing-library/react'
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
/** Kỳ trước: doanh thu thuần 4.000.000 (kỳ này tăng 20%), hoàn tiền 100.000 (kỳ này tăng 100%, tô đỏ). */
const BC_TRUOC = { ...BC, doanh_thu: '4100000.00', hoan_tien: '100000.00', doanh_thu_thuan: '4000000.00', loi_nhuan_gop: '2000000.00', so_don_hoan_tat: 12 }
const CANH_BAO = {
  ton_thap: { tong: 4, du_lieu: [{ san_pham_id: 7, sku: 'SKU-7', ten: 'Oresol', ton_kha_dung: 0, ton_toi_thieu: 20 }] },
  can_han: { tong: 1, du_lieu: [] },
  het_han: { tong: 2, du_lieu: [{ lo_id: 9, san_pham_id: 8, sku: 'SKU-8', ten_san_pham: 'Siro ho', so_lo: 'H09', han_su_dung: '2026-10-01', trang_thai: 'het_han', so_luong_ton: 6, so_luong_biet_tru: 0 }] },
}
const HOAN = [
  { id: 1, ma_don: 'DH1', ten_khach: 'An', so_tien: '150000.00', cong_thanh_toan: 'vnpay', trang_thai: 'khoi_tao', nguon: 'huy_don', ma_yeu_cau: null, tong_da_thanh_toan: '150000.00', tu_dong_qua_cong: true, thong_tin_nhan_hoan: null, thieu_tai_khoan: false },
  { id: 2, ma_don: 'DH2', ten_khach: 'Bình', so_tien: '50000.50', cong_thanh_toan: 'cod', trang_thai: 'khoi_tao', nguon: 'doi_tra', ma_yeu_cau: 'DT1', tong_da_thanh_toan: '50000.50', tu_dong_qua_cong: false, thong_tin_nhan_hoan: null, thieu_tai_khoan: true },
]
const ADMIN = {
  'report.all': 'day_du', 'stock.alert.view': 'chi_xem', 'stock_doc.approve': 'day_du', 'refund.confirm': 'day_du', 'recall.create': 'day_du', 'order.view': 'chi_xem', 'ai.monitor': 'day_du',
} as const
const admin = (quyen: Record<string, string> = ADMIN) => renderTai('/quan-tri', { loai: 'noi_bo', vaiTro: 'ADMIN', quyen: quyen as never })
const trang = (du_lieu: unknown[], tong = du_lieu.length) => ok({ du_lieu, tong, trang: 1, kich_thuoc: 20 })

/** Trả dữ liệu theo đường dẫn; `rieng` ghi đè từng đường dẫn. Báo cáo kỳ trước nhận ra vì `den_ngay` < kỳ đang xem. */
function giaLap(rieng: Record<string, (q: Record<string, unknown>) => unknown> = {}) {
  let kyNay: string | undefined
  GET.mockImplementation(async (d: string, o?: { params?: { query?: Record<string, unknown> } }) => {
    const q = o?.params?.query ?? {}
    if (rieng[d]) return rieng[d](q)
    switch (d) {
      case '/api/v1/noi-bo/bao-cao/tong-hop':
        kyNay ??= String(q.den_ngay)
        return ok(String(q.den_ngay) < kyNay ? BC_TRUOC : BC)
      case '/api/v1/noi-bo/canh-bao-kho':
        return ok(CANH_BAO)
      case '/api/v1/noi-bo/duyet-phieu':
        return trang([], 3)
      case '/api/v1/noi-bo/hoan-tien':
        return ok(HOAN)
      case '/api/v1/noi-bo/thu-hoi':
        return trang([{ id: 1, ma_lenh: 'TH1', san_pham_ten: 'X', so_lo: null, can_cu: 'CV 1', muc_do: null, trang_thai: 'dang_thu_hoi', so_khach: 5, so_khach_da_xu_ly: 2, created_at: '2026-10-10T00:00:00Z' }])
      case '/api/v1/noi-bo/don-hang':
        return trang([], q.trang_thai === 'giao_that_bai' ? 2 : 0)
      default:
        return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
    }
  })
}

beforeEach(() => {
  GET.mockReset()
  giaLap()
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: () => 'blob:x', revokeObjectURL: () => {} }))
})

describe('Tổng quan Admin (AD14)', () => {
  it('chỉ số kinh doanh so với kỳ liền trước, biểu đồ, bán chạy, tồn kho, AI', async () => {
    admin()
    expect(await screen.findByText(/Paracetamol 500/)).toBeInTheDocument()
    await screen.findByText(/20,0% so với kỳ trước/)
    expect(screen.getAllByText(/4\.800\.000/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/1\.800\.000/).length).toBeGreaterThan(0)
    expect(screen.getByText(/Biên lợi nhuận 37,5%/)).toBeInTheDocument()
    expect(screen.getByText(/100,0% so với kỳ trước/)).toHaveStyle({ color: '#cf1322' })
    expect(screen.getByText(/10,0% so với kỳ trước/)).toHaveStyle({ color: '#cf1322' }) // lợi nhuận giảm
    expect(screen.getByText(/Trung bình 416\.667/)).toBeInTheDocument()
    expect(screen.getAllByText(/25\.000\.000/).length).toBeGreaterThan(0)
    expect(screen.getByText('25 ngày')).toBeInTheDocument()
    expect(screen.getByText('25,0%')).toBeInTheDocument()
    expect(screen.getByLabelText('Biểu đồ doanh thu theo ngày').querySelectorAll('rect')).toHaveLength(3)
    const ky = GET.mock.calls.filter((c) => c[0] === '/api/v1/noi-bo/bao-cao/tong-hop').map((c) => c[1].params.query)
    expect(ky.length).toBeGreaterThanOrEqual(2)
    expect(ky.every((q) => /^\d{4}-\d{2}-\d{2}$/.test(q.tu_ngay))).toBe(true)
  })

  it('việc cần xử lý: số lượng, mô tả và liên kết tới trang xử lý; việc gấp lên trước', async () => {
    admin()
    const hoan = await screen.findByTestId('viec-hoan-tien')
    expect(within(hoan).getByText('2')).toBeInTheDocument()
    expect(within(hoan).getByText(/200\.001 ₫ · 1 khoản khách chưa gửi tài khoản/)).toBeInTheDocument()
    expect(within(hoan).getByText(/Xác nhận hoàn/).closest('a')).toHaveAttribute('href', '/quan-tri/hoan-tien')
    expect(within(await screen.findByTestId('viec-phieu')).getByText('3')).toBeInTheDocument()
    expect(within(screen.getByTestId('viec-thu-hoi')).getByText('Còn 3 khách chưa được liên hệ')).toBeInTheDocument()
    expect(within(screen.getByTestId('viec-het-han')).getByText('2')).toBeInTheDocument()
    expect(within(await screen.findByTestId('viec-giao-that-bai')).getByText(/Xem đơn/).closest('a')).toHaveAttribute('href', '/quan-tri/xem/don-hang?trang_thai=giao_that_bai')
    expect(await screen.findByText(/Có 4 nhóm việc cần bạn xử lý ngay/)).toBeInTheDocument()
    // việc bằng 0 gom vào dòng "Đã ổn", không chiếm ô
    expect(screen.queryByTestId('viec-cho-xac-nhan')).not.toBeInTheDocument()
    const thuTu = [...document.querySelectorAll('[data-testid^="viec-"]')].map((e) => e.getAttribute('data-testid'))
    expect(thuTu.indexOf('viec-giao-that-bai')).toBeGreaterThan(thuTu.indexOf('viec-het-han'))
  })

  it('không có quyền thì không gọi nguồn đó và không hiện ô', async () => {
    admin({ 'report.all': 'day_du' })
    await screen.findByText(/Paracetamol 500/)
    const duong = GET.mock.calls.map((c) => c[0])
    for (const d of ['/api/v1/noi-bo/hoan-tien', '/api/v1/noi-bo/duyet-phieu', '/api/v1/noi-bo/thu-hoi', '/api/v1/noi-bo/canh-bao-kho', '/api/v1/noi-bo/don-hang']) expect(duong).not.toContain(d)
    expect(screen.queryByTestId('viec-hoan-tien')).not.toBeInTheDocument()
    expect(screen.getByText('Bạn chưa có quyền xem đơn hàng')).toBeInTheDocument()
  })

  it('không còn việc nào thì báo ổn', async () => {
    const rong = () => trang([], 0)
    giaLap({
      '/api/v1/noi-bo/duyet-phieu': rong, '/api/v1/noi-bo/thu-hoi': rong, '/api/v1/noi-bo/don-hang': rong, '/api/v1/noi-bo/hoan-tien': () => ok([]),
      '/api/v1/noi-bo/canh-bao-kho': () => ok({ ton_thap: { tong: 0, du_lieu: [] }, can_han: { tong: 0, du_lieu: [] }, het_han: { tong: 0, du_lieu: [] } }),
      '/api/v1/noi-bo/bao-cao/tong-hop': () => ok({ ...BC, hieu_qua_ai: { ...BC.hieu_qua_ai, so_gan_co: 0 } }),
    })
    admin()
    expect(await screen.findByText('Không có việc nào đang chờ bạn')).toBeInTheDocument()
    expect(screen.getByText('Phiếu kho chờ duyệt')).toBeInTheDocument() // trong dòng "Đã ổn"
  })

  it('đổi mẫu kỳ thì tải lại báo cáo với khoảng mới', async () => {
    admin()
    await screen.findByText(/Paracetamol 500/)
    const u = userEvent.setup()
    await u.click(screen.getByText('7 ngày'))
    await waitFor(() => {
      const q = GET.mock.calls.filter((c) => c[0] === '/api/v1/noi-bo/bao-cao/tong-hop').map((c) => c[1].params.query)
      expect(q.some((x) => (new Date(x.den_ngay).getTime() - new Date(x.tu_ngay).getTime()) / 86_400_000 === 6)).toBe(true)
    })
  })

  it('xuất Excel gọi API tải về dạng blob', async () => {
    giaLap({ '/api/v1/noi-bo/bao-cao/tong-hop/excel': () => ok(new Blob(['x'])) })
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
