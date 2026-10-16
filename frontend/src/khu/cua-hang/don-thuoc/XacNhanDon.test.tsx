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
const DON = (rieng: object = {}) => ({
  ma_don: 'DH77', trang_thai: 'cho_khach_xac_nhan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: null, hinh_thuc_nhan: 'giao_tan_noi', tam_tinh: '30000.00',
  giam_gia: '0.00', phi_van_chuyen: '0.00', tong_tien: '30000.00', han_thanh_toan: null, han_xac_nhan: '2026-10-17T01:00:00Z', ma_giam_gia: null,
  ten_nguoi_nhan: 'Nguyễn A', sdt_nguoi_nhan: '0912345678', dia_chi_giao: null, ghi_chu: 'Uống sau ăn', created_at: '2026-10-16T01:00:00Z', lich_su: [], van_don: [],
  dong: [{ san_pham_id: 1, ten_san_pham: 'Augmentin', ten_don_vi: 'viên', so_luong: 2, don_gia: '15000.00', giam_gia_phan_bo: '0.00', thanh_tien: '30000.00' }], ...rieng,
})
const CHO = { don: DON(), co_the_xac_nhan: true, co_the_thanh_toan: false }
const TOKEN = 'a'.repeat(43)

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  sessionStorage.clear()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/xac-nhan-don/{token}') return ok(CHO)
    if (duong === '/api/v1/dia-gioi/tinh') return ok([{ ma: '201', ten: 'Hà Nội' }])
    return ok([])
  })
})

describe('Xác nhận đơn từ đơn thuốc qua link (KTV07)', () => {
  it('link sai: báo không hợp lệ', async () => {
    GET.mockImplementation(async () => ({ error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 404 } }))
    renderTai(`/xac-nhan-don/${TOKEN}`)
    expect(await screen.findByText('Liên kết không hợp lệ')).toBeInTheDocument()
  })

  it('khách vãng lai chọn nhận tại nhà thuốc + COD: gửi đúng body qua token, không cần đăng nhập', async () => {
    POST.mockResolvedValue(ok({ ...CHO, don: DON({ trang_thai: 'da_xac_nhan' }), co_the_xac_nhan: false }))
    renderTai(`/xac-nhan-don/${TOKEN}`)
    expect(await screen.findByText('Lời dặn của dược sĩ')).toBeInTheDocument()
    expect(screen.getByText('Tính sau khi chọn địa chỉ')).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText('Nhận tại nhà thuốc'))
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận đơn' }))
    await waitFor(() => expect(POST).toHaveBeenCalled())
    expect(POST.mock.calls[0][0]).toBe('/api/v1/xac-nhan-don/{token}/xac-nhan')
    expect(POST.mock.calls[0][1].params.path.token).toBe(TOKEN)
    expect(POST.mock.calls[0][1].body).toMatchObject({ hinh_thuc_nhan: 'nhan_tai_nha_thuoc', phuong_thuc_tt: 'cod' })
  })

  it('giao tận nơi bắt buộc nhập địa chỉ trước khi gửi', async () => {
    renderTai(`/xac-nhan-don/${TOKEN}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Xác nhận đơn' }))
    expect(await screen.findByText('Nhập địa chỉ (số nhà, đường)')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('đơn chờ thanh toán online: nút Thanh toán lưu token để trang kết quả đọc lại', async () => {
    GET.mockImplementation(async () => ok({ don: DON({ trang_thai: 'cho_thanh_toan', phuong_thuc_tt: 'vnpay', han_thanh_toan: '2026-10-16T02:00:00Z' }), co_the_xac_nhan: false, co_the_thanh_toan: true }))
    POST.mockResolvedValue(ok({ url_thanh_toan: '/thanh-toan-gia?giao_dich=DH77-1', han_thanh_toan: null }))
    const { chuyenSangCong } = await import('../gio-hang/thanhToanOnline')
    const di = vi.spyOn(chuyenSangCong, 'di').mockImplementation(() => {})
    renderTai(`/xac-nhan-don/${TOKEN}`)
    await userEvent.click(await screen.findByRole('button', { name: 'Thanh toán ngay' }))
    await waitFor(() => expect(di).toHaveBeenCalledWith('/thanh-toan-gia?giao_dich=DH77-1'))
    expect(sessionStorage.getItem('xacNhanDon:DH77')).toBe(TOKEN)
  })
})
