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
const QUYEN = { 'rx_request.review': 'day_du', 'rx_order.create': 'day_du' } as never
const dung = (duong: string) => renderTai(duong, { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: QUYEN })
const HANG = [
  { id: 1, ma_yeu_cau: 'YC1', ho_ten: 'Nguyễn A', so_dien_thoai: '0912345678', trang_thai: 'cho_duyet', so_anh: 1, la_thanh_vien: false, khoa_boi_toi: false, khoa_luc: null, created_at: '2026-10-16T01:00:00Z' },
  { id: 2, ma_yeu_cau: 'YC2', ho_ten: 'Trần B', so_dien_thoai: '0912345679', trang_thai: 'dang_tu_van', so_anh: 2, la_thanh_vien: true, khoa_boi_toi: true, khoa_luc: '2026-10-16T01:00:00Z', created_at: '2026-10-16T00:00:00Z' },
]
const YC = (rieng: object = {}) => ({
  id: 2, ma_yeu_cau: 'YC2', ho_ten: 'Trần B', so_dien_thoai: '0912345679', ghi_chu: 'đau họng', trang_thai: 'dang_tu_van', khoa_luc: '2026-10-16T01:00:00Z',
  het_khoa_luc: '2026-10-16T01:30:00Z', la_thanh_vien: true, anh: ['/api/v1/tep-rieng/don-thuoc/a.png?het_han=1&ky=a'], ket_qua_ai: null, thuoc_tren_don: [], checklist: null,
  trung_anh: [], ho_so_suc_khoe: { dong_y_su_dung: true, dong_y_luc: null, nam_sinh: 1980, benh_nen: 'tiểu đường', dang_mang_thai: false, dang_cho_con_bu: false, di_ung: [{ hoat_chat_id: 7, ten_hoat_chat: 'Amoxicillin', ghi_chu: null }] },
  ...rieng,
})
const SP = [{ id: 11, ten: 'Augmentin 625', loai_san_pham: 'thuoc_ke_don', don_vi_co_so: 'viên', ton_kha_dung: 40, hoat_chat: ['Amoxicillin'], don_vi: [{ id: 31, ten_don_vi: 'viên', he_so: 1, gia_ban: '15000.00' }] }]
const CANH_BAO = { tuong_tac: [], di_ung: [{ loai: 'di_ung', muc_do: 'chong_chi_dinh', san_pham_id: 11, ten_san_pham: 'Augmentin 625', hoat_chat_id: 7, ten_hoat_chat: 'Amoxicillin' }], can_ghi_chu_tu_van: true }

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/don-thuoc') return ok(HANG)
    if (duong === '/api/v1/noi-bo/don-thuoc/{yc_id}') return ok(YC())
    if (duong === '/api/v1/noi-bo/don-thuoc/{yc_id}/san-pham') return ok(SP)
    return ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })
  })
})

describe('Hàng chờ đơn thuốc (DS04)', () => {
  it('hiện yêu cầu chờ duyệt và yêu cầu tôi đang xử lý; nhận xử lý gọi API rồi mở màn duyệt', async () => {
    POST.mockResolvedValue(ok(YC({ id: 1 })))
    const { router } = dung('/nhan-vien/don-thuoc')
    expect(await screen.findByText('YC1')).toBeInTheDocument()
    expect(screen.getByText('Tôi đang xử lý')).toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: 'Nhận xử lý' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/don-thuoc/{yc_id}/nhan')
    await waitFor(() => expect(router.state.location.pathname).toBe('/nhan-vien/don-thuoc/1'))
  })
})

describe('Màn duyệt đơn thuốc (DS04, DS05)', () => {
  it('yêu cầu không khóa cho tôi: báo và dẫn về hàng chờ', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'KHONG_CO_QUYEN', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 403 } }))
    dung('/nhan-vien/don-thuoc/2')
    expect(await screen.findByText('Yêu cầu này không đang khóa cho bạn')).toBeInTheDocument()
  })

  it('hiện ảnh, hồ sơ dị ứng; chỉ tạo được đơn khi đủ sản phẩm, checklist và ghi chú cho cảnh báo nặng', async () => {
    POST.mockImplementation(async (duong: string) => {
      if (duong.endsWith('/canh-bao')) return ok(CANH_BAO)
      return ok({ don: { ma_don: 'DH99' }, lien_ket_xac_nhan: 'http://x/xac-nhan-don/tok' })
    })
    dung('/nhan-vien/don-thuoc/2')
    expect(await screen.findByAltText('Ảnh đơn thuốc')).toBeInTheDocument()
    expect(screen.getByText('Amoxicillin')).toBeInTheDocument()
    expect(screen.getByText('tiểu đường')).toBeInTheDocument()
    const tao = screen.getByRole('button', { name: 'Tạo đơn gửi khách' })
    expect(tao).toBeDisabled()
    await userEvent.type(screen.getByPlaceholderText('Tìm theo tên thuốc hoặc hoạt chất'), 'augmentin')
    await userEvent.click(await screen.findByRole('button', { name: 'Thêm' }))
    expect(await screen.findByText(/khách khai dị ứng/)).toBeInTheDocument()
    for (const cb of screen.getAllByRole('checkbox')) await userEvent.click(cb)
    expect(tao).toBeDisabled() // thiếu ghi chú tư vấn cho cảnh báo chống chỉ định
    await userEvent.type(screen.getByPlaceholderText(/Bắt buộc: ghi chú tư vấn/), 'Đã trao đổi với khách')
    await waitFor(() => expect(tao).toBeEnabled())
    await userEvent.click(tao)
    expect(await screen.findByText('Đã tạo đơn DH99')).toBeInTheDocument()
    const goi = POST.mock.calls.find((c) => c[0].endsWith('/tao-don'))![1].body
    expect(goi.dong).toEqual([{ san_pham_id: 11, don_vi_id: 31, so_luong: 1 }])
    expect(goi.ghi_chu_tu_van).toBe('Đã trao đổi với khách')
    expect(Object.values(goi.checklist).every(Boolean)).toBe(true)
    expect(screen.getByText('http://x/xac-nhan-don/tok')).toBeInTheDocument()
  })

  it('từ chối bắt buộc lý do', async () => {
    POST.mockResolvedValue({ response: { ok: true, status: 204 } })
    dung('/nhan-vien/don-thuoc/2')
    await userEvent.click(await screen.findByRole('button', { name: 'Từ chối yêu cầu' }))
    const nut = await screen.findByRole('button', { name: 'Từ chối' })
    expect(nut).toBeDisabled()
    await userEvent.type(screen.getByPlaceholderText(/Lý do/), 'Đơn mờ')
    await userEvent.click(nut)
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][1].body).toEqual({ ly_do: 'Đơn mờ' })
  })
})
