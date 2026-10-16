import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { mauDoTinCay } from './thuocTrenDon'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const QUYEN = { 'rx_request.review': 'day_du', 'rx_order.create': 'day_du' } as never
const DONG = (id: number, ten: string, rieng: object = {}) => ({ id, do_duoc_si_nhap: false, ten_thuoc_tren_don: ten, ham_luong: '500 mg', so_luong_ke: '10 viên', do_tin_cay_ai: '0.920', san_pham_id: null, ten_san_pham: null, ...rieng })
const YC = (rieng: object = {}) => ({
  id: 2, ma_yeu_cau: 'YC2', ho_ten: 'Trần B', so_dien_thoai: '0912345679', ghi_chu: null, trang_thai: 'dang_tu_van', khoa_luc: '2026-10-16T01:00:00Z',
  het_khoa_luc: '2026-10-16T01:30:00Z', la_thanh_vien: false, anh: [], ket_qua_ai: { trang_thai: 'xong', ngay_ke: '2026-10-10', co_chu_ky_bac_si: true },
  thuoc_tren_don: [DONG(11, 'Amoxicillin', { ten_san_pham: 'Amoxicillin 500', san_pham_id: 5 }), DONG(12, 'Chữ khó đọc', { do_tin_cay_ai: '0.300' })],
  checklist: null, trung_anh: [], ho_so_suc_khoe: null, ...rieng,
})

beforeEach(() => {
  GET.mockReset(); POST.mockReset(); PUT.mockReset()
  GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/don-thuoc/{yc_id}' ? ok(YC()) : ok([])))
})

describe('màu độ tin cậy', () => {
  it.each([[0.2, 'red'], [0.49, 'red'], [0.5, 'orange'], [0.79, 'orange'], [0.8, 'green'], [1, 'green']])('%s -> %s', (v, mau) => expect(mauDoTinCay(v)).toBe(mau))
})

describe('Thuốc trên đơn do AI06 đọc (DS04)', () => {
  it('hiện dòng AI kèm độ tin cậy, sản phẩm gợi ý và ngày kê; chưa sửa thì nút Lưu bị khóa', async () => {
    renderTai('/nhan-vien/don-thuoc/2', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN })
    expect(await screen.findByText('AI 92%')).toBeInTheDocument()
    expect(screen.getByText('AI 30%')).toBeInTheDocument()
    expect(screen.getByText('Amoxicillin 500')).toBeInTheDocument()
    expect(screen.getByText(/ngày kê 2026-10-10, có chữ ký bác sĩ/)).toBeInTheDocument()
    expect(screen.getByText('Lưu danh sách thuốc').closest('button')!).toBeDisabled()
  })

  it('sửa một dòng thì chuyển thành "Dược sĩ nhập", thêm dòng, xóa dòng rồi lưu đúng nội dung', async () => {
    PUT.mockResolvedValue(ok(YC({ thuoc_tren_don: [DONG(11, 'Amoxicillin', { ten_san_pham: 'Amoxicillin 500', san_pham_id: 5 }), DONG(13, 'Thuốc thêm', { do_tin_cay_ai: null, do_duoc_si_nhap: true })] })))
    renderTai('/nhan-vien/don-thuoc/2', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN })
    const u = userEvent.setup()
    const o = await screen.findByDisplayValue('Chữ khó đọc')
    await u.clear(o)
    await u.type(o, 'Cefuroxime')
    expect(screen.getAllByText('Dược sĩ nhập').length).toBe(1)
    await u.click(screen.getByText('Thêm thuốc').closest('button')!)
    const trong = screen.getAllByLabelText('Tên thuốc trên đơn').at(-1)!
    await u.type(trong, 'Thuốc thêm')
    await u.click(screen.getByLabelText('Xóa dòng Cefuroxime'))
    await u.click(screen.getByText('Lưu danh sách thuốc').closest('button')!)
    await waitFor(() => expect(PUT).toHaveBeenCalled())
    expect(PUT.mock.calls[0][0]).toBe('/api/v1/noi-bo/don-thuoc/{yc_id}/thuoc-tren-don')
    expect(PUT.mock.calls[0][1].body.dong).toEqual([
      { id: 11, ten_thuoc_tren_don: 'Amoxicillin', ham_luong: '500 mg', so_luong_ke: '10 viên', san_pham_id: 5 },
      { id: null, ten_thuoc_tren_don: 'Thuốc thêm', ham_luong: null, so_luong_ke: null, san_pham_id: null },
    ])
    expect(await screen.findByText('Đã lưu danh sách thuốc trên đơn')).toBeInTheDocument()
    expect(screen.getByText('Lưu danh sách thuốc').closest('button')!).toBeDisabled()
  })

  it('tên thuốc trống bị chặn ở client; lỗi máy chủ hiện thông điệp', async () => {
    PUT.mockResolvedValue({ error: { ma_loi: 'KHONG_CO_QUYEN', thong_diep: 'Yêu cầu này không đang khóa cho bạn', chi_tiet: null }, response: { ok: false, status: 403 } })
    renderTai('/nhan-vien/don-thuoc/2', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN })
    const u = userEvent.setup()
    await screen.findByDisplayValue('Amoxicillin')
    await u.click(screen.getByText('Thêm thuốc').closest('button')!)
    await u.click(screen.getByText('Lưu danh sách thuốc').closest('button')!)
    expect(await screen.findByText('Tên thuốc không được để trống')).toBeInTheDocument()
    expect(PUT).not.toHaveBeenCalled()
    await u.type(screen.getAllByLabelText('Tên thuốc trên đơn').at(-1)!, 'X')
    await u.click(screen.getByText('Lưu danh sách thuốc').closest('button')!)
    expect(await screen.findByText('Yêu cầu này không đang khóa cho bạn')).toBeInTheDocument()
  })

  it('AI lỗi: báo nhập tay; nút tìm sản phẩm điền ô tìm kiếm', async () => {
    GET.mockImplementation(async (d: string) => (d === '/api/v1/noi-bo/don-thuoc/{yc_id}' ? ok(YC({ ket_qua_ai: { trang_thai: 'loi', ly_do: 'ai_loi', lan_thu: 3 }, thuoc_tren_don: [DONG(11, 'Amoxicillin')] })) : ok([])))
    renderTai('/nhan-vien/don-thuoc/2', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN })
    const u = userEvent.setup()
    expect(await screen.findByText(/AI chưa đọc được ảnh đơn này/)).toBeInTheDocument()
    await u.click(screen.getByLabelText('Tìm sản phẩm cho Amoxicillin'))
    await waitFor(() => expect(screen.getByPlaceholderText(/Tìm theo tên thuốc/)).toHaveValue('Amoxicillin'))
  })

  it('chỉ xem: không có nút thêm/lưu', async () => {
    renderTai('/nhan-vien/don-thuoc/2', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'rx_request.review': 'chi_xem' } as never })
    await screen.findByText('AI 92%')
    expect(screen.queryByText('Thêm thuốc')).not.toBeInTheDocument()
  })
})
