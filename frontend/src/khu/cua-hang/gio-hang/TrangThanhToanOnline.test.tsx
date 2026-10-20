import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderTai } from '../../../test/render'
import { useGioCucBo } from './gioHang'
import { chuyenSangCong, maDonTuGiaoDich } from './thanhToanOnline'

vi.setConfig({ testTimeout: 60_000 })
const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: vi.fn(), DELETE: vi.fn() },
}))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const loi = (ma_loi: string, thong_diep: string, status = 409) => ({ error: { ma_loi, thong_diep, chi_tiet: null }, response: { ok: false, status } })
const DV = { id: 5, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00' }
const GIO = {
  dong: [{ dong_id: 11, san_pham: { id: 1, ten: 'Paracetamol', slug: 'paracetamol', anh_chinh_url: null, can_tu_van: false }, don_vi: DV, don_vi_co_the_chon: [DV], so_luong: 2, thanh_tien: '2000.00', toi_da_don_vi: null, ton_kha_dung_don_vi: 50, mua_duoc: true, ly_do: null }],
  tam_tinh: '2000.00',
  tong_so_luong: 2,
}
const DIA_CHI = [{ id: 7, ten_nguoi_nhan: 'Nguyễn An', so_dien_thoai: '0912345678', dia_chi_chi_tiet: '12 Lê Lợi', ma_tinh: '01', ten_tinh: 'Hà Nội', ma_phuong_xa: '0001', ten_phuong_xa: 'Phường A', la_mac_dinh: true }]
const TONG = { tam_tinh: '2000.00', giam_gia: '0.00', phi_van_chuyen: '25000.00', tong_tien: '27000.00', ma_giam_gia: null }
const HAN_TUONG_LAI = new Date(Date.now() + 10 * 60_000).toISOString()
/** GET mặc định đủ cho giỏ/địa chỉ (MiniGioHang cần `dong`), chỉ đổi đơn trả về. */
function giaLapDon(d: object) {
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok(d)
    if (duong === '/api/v1/toi/gio-hang') return ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 })
    return ok([])
  })
}
const don = (rieng: object = {}) => ({ ma_don: 'DHABCD2345', trang_thai: 'cho_thanh_toan', trang_thai_tt: 'chua_thanh_toan', phuong_thuc_tt: 'vnpay', hinh_thuc_nhan: 'giao_tan_noi', ...TONG, han_thanh_toan: HAN_TUONG_LAI, ma_giam_gia: null, ten_nguoi_nhan: 'Nguyễn An', sdt_nguoi_nhan: '0912345678', dia_chi_giao: '12 Lê Lợi', ghi_chu: null, created_at: '2026-10-16T00:00:00Z', dong: [], ...rieng })

beforeEach(() => {
  for (const m of [GET, POST]) m.mockReset()
  localStorage.clear()
  useGioCucBo.setState({ dong: [] })
  vi.spyOn(chuyenSangCong, 'di').mockImplementation(() => undefined)
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/toi/gio-hang') return ok(GIO)
    if (duong === '/api/v1/toi/dia-chi') return ok(DIA_CHI)
    if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok(don())
    throw new Error(`Chưa giả lập ${duong}`)
  })
})

describe('thanh toán online (KTV03)', () => {
  it('maDonTuGiaoDich lấy phần trước dấu - cuối', () => {
    expect(maDonTuGiaoDich('DHABCD2345-17')).toBe('DHABCD2345')
    expect(maDonTuGiaoDich('khongco')).toBe('')
  })

  it('đặt hàng VNPay: hiện QR cùng thông tin đơn và tạo giao dịch với khóa mới', async () => {
    POST.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/don-hang') return ok(don())
      if (duong === '/api/v1/toi/don-hang/{ma_don}/thanh-toan') return ok({ url_thanh_toan: 'https://cong.test/pay?x=1', han_thanh_toan: HAN_TUONG_LAI })
      return ok(TONG)
    })
    renderTai('/thanh-toan', { loai: 'khach' })
    const u = userEvent.setup()
    const nut = await screen.findByRole('button', { name: /Đặt hàng/ })
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    expect(await screen.findByText('Quét mã để thanh toán')).toBeInTheDocument()
    expect(screen.getByText('DHABCD2345')).toBeInTheDocument()
    expect(screen.getByText('Số tiền cần thanh toán').parentElement).toHaveTextContent(/27\.000/)
    expect(screen.getByRole('link', { name: 'Mở trang thanh toán' })).toHaveAttribute('href', 'https://cong.test/pay?x=1')
    expect(chuyenSangCong.di).not.toHaveBeenCalled()
    const goi = POST.mock.calls.find((c) => c[0] === '/api/v1/toi/don-hang/{ma_don}/thanh-toan')!
    expect(goi[1].params.path.ma_don).toBe('DHABCD2345')
    expect(goi[1].params.header['Idempotency-Key']).toMatch(/^[0-9a-f-]{36}$/)
  })

  it('chọn MoMo thì báo trước mã QR sẽ hiện sau khi đặt hàng', async () => {
    renderTai('/thanh-toan', { loai: 'khach' })
    await userEvent.setup().click(await screen.findByLabelText('MoMo'))
    expect(screen.getByText(/mã QR MoMo sẽ hiện cùng mã đơn, số tiền và hạn thanh toán/)).toBeInTheDocument()
  })

  it('không mở được cổng: vẫn vào trang kết quả để thanh toán lại', async () => {
    POST.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/toi/don-hang') return ok(don())
      if (duong === '/api/v1/toi/don-hang/{ma_don}/thanh-toan') return loi('LOI_DOI_TAC', 'Cổng thanh toán đang lỗi', 502)
      return ok(TONG)
    })
    renderTai('/thanh-toan', { loai: 'khach' })
    const u = userEvent.setup()
    const nut = await screen.findByRole('button', { name: /Đặt hàng/ })
    await waitFor(() => expect(nut).toBeEnabled())
    await u.click(nut)
    expect(await screen.findByText('Đơn hàng đang chờ thanh toán')).toBeInTheDocument()
    expect(chuyenSangCong.di).not.toHaveBeenCalled()
  })
})

describe('trang kết quả đọc trạng thái từ máy chủ, không tin URL', () => {
  const vao = () => renderTai('/thanh-toan/ket-qua?ma=DHABCD2345&vnp_ResponseCode=00&vnp_TransactionStatus=00', { loai: 'khach' })

  it('URL báo thành công nhưng máy chủ nói còn chờ thanh toán: hiện chờ thanh toán', async () => {
    giaLapDon(don())
    vao()
    expect(await screen.findByText('Đơn hàng đang chờ thanh toán')).toBeInTheDocument()
    expect(screen.queryByText('Thanh toán thành công')).not.toBeInTheDocument()
  })

  it('đã thanh toán: hiện thành công', async () => {
    giaLapDon(don({ trang_thai: 'cho_xac_nhan', trang_thai_tt: 'da_thanh_toan' }))
    vao()
    expect(await screen.findByText('Thanh toán thành công')).toBeInTheDocument()
  })

  it('thanh toán lại: tạo giao dịch mới và chuyển sang cổng', async () => {
    giaLapDon(don())
    POST.mockResolvedValue(ok({ url_thanh_toan: 'https://cong.test/lai', han_thanh_toan: HAN_TUONG_LAI }))
    vao()
    await userEvent.setup().click(await screen.findByText('Thanh toán lại'))
    await waitFor(() => expect(chuyenSangCong.di).toHaveBeenCalledWith('https://cong.test/lai'))
  })

  it('thanh toán lại bị từ chối (quá hạn): hiện lỗi của máy chủ, không chuyển cổng', async () => {
    POST.mockResolvedValue(loi('CHUYEN_TRANG_THAI_KHONG_HOP_LE', 'Đơn hàng đã quá hạn thanh toán'))
    vao()
    await userEvent.setup().click(await screen.findByText('Thanh toán lại'))
    expect(await screen.findByText('Đơn hàng đã quá hạn thanh toán')).toBeInTheDocument()
    expect(chuyenSangCong.di).not.toHaveBeenCalled()
  })

  it('đơn đã hủy kèm khoản chờ hoàn: báo sẽ được hoàn tiền', async () => {
    giaLapDon(don({ trang_thai: 'da_huy', trang_thai_tt: 'cho_hoan_tien' }))
    vao()
    expect(await screen.findByText('Đơn hàng đã bị hủy')).toBeInTheDocument()
    expect(screen.getByText(/đang chờ hoàn tiền/)).toBeInTheDocument()
    expect(screen.queryByText('Thanh toán lại')).not.toBeInTheDocument()
  })
})

describe('cổng thanh toán giả', () => {
  const GD = (cong: string, rieng: object = {}) => ({ giao_dich: 'DHABCD2345-17', ma_don: 'DHABCD2345', so_tien: 27000, cong, trang_thai: 'khoi_tao', het_han_luc: HAN_TUONG_LAI, ...rieng })
  function giaLapCong(gd: object) {
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/webhook/gia-giao-dich') return ok(gd)
      if (duong === '/api/v1/toi/don-hang/{ma_don}') return ok(don())
      if (duong === '/api/v1/toi/gio-hang') return ok({ dong: [], tam_tinh: '0.00', tong_so_luong: 0 })
      return ok([])
    })
    POST.mockResolvedValue(ok({ RspCode: '00', Message: 'Confirm Success' }))
  }
  const IPN = (thanh_cong: boolean) => ['/api/v1/webhook/gia-ipn', { body: { giao_dich: 'DHABCD2345-17', thanh_cong } }]

  it('VNPay: thẻ thử nghiệm đúng, nhập OTP đúng thì gửi IPN thành công và báo kết quả', async () => {
    giaLapCong(GD('vnpay'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17', { loai: 'khach' })
    const u = userEvent.setup()
    expect(await screen.findByText(/Môi trường mô phỏng/)).toBeInTheDocument()
    expect(screen.getByText('27.000 ₫')).toBeInTheDocument()
    await u.click(screen.getByText('Tiếp tục'))
    await u.type(screen.getByLabelText('Số thẻ'), '9704198526191432198')
    await u.type(screen.getByLabelText('Tên chủ thẻ'), 'NGUYEN VAN A')
    await u.type(screen.getByLabelText('Ngày phát hành'), '07/15')
    await u.click(screen.getByText('Tiếp tục'))
    await u.type(await screen.findByLabelText('Mã OTP'), '123456')
    await u.click(screen.getByText('Xác nhận'))
    await waitFor(() => expect(POST).toHaveBeenCalledWith(...IPN(true)))
    expect(await screen.findByText('Giao dịch thành công')).toBeInTheDocument()
  })

  it('VNPay: thông tin thẻ sai thì báo lỗi và chưa gửi IPN', async () => {
    giaLapCong(GD('vnpay'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    const u = userEvent.setup()
    await u.click(await screen.findByText('Tiếp tục'))
    await u.type(screen.getByLabelText('Số thẻ'), '1111222233334444')
    await u.type(screen.getByLabelText('Tên chủ thẻ'), 'NGUYEN VAN A')
    await u.type(screen.getByLabelText('Ngày phát hành'), '07/15')
    await u.click(screen.getByText('Tiếp tục'))
    expect(await screen.findByText(/Thông tin thẻ không chính xác/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('VNPay: thẻ không đủ số dư, OTP đúng thì giao dịch thất bại kèm lý do', async () => {
    giaLapCong(GD('vnpay'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    const u = userEvent.setup()
    await u.click(await screen.findByText('Tiếp tục'))
    await u.type(screen.getByLabelText('Số thẻ'), '9704195798459170488')
    await u.type(screen.getByLabelText('Tên chủ thẻ'), 'NGUYEN VAN A')
    await u.type(screen.getByLabelText('Ngày phát hành'), '07/15')
    await u.click(screen.getByText('Tiếp tục'))
    await u.type(await screen.findByLabelText('Mã OTP'), '123456')
    await u.click(screen.getByText('Xác nhận'))
    await waitFor(() => expect(POST).toHaveBeenCalledWith(...IPN(false)))
    expect(await screen.findByText('Giao dịch không thành công')).toBeInTheDocument()
    expect(screen.getByText(/không đủ số dư/)).toBeInTheDocument()
  })

  it('VNPay: nhập sai OTP ba lần thì giao dịch thất bại', async () => {
    giaLapCong(GD('vnpay'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    const u = userEvent.setup()
    await u.click(await screen.findByText('Tiếp tục'))
    await u.type(screen.getByLabelText('Số thẻ'), '9704198526191432198')
    await u.type(screen.getByLabelText('Tên chủ thẻ'), 'NGUYEN VAN A')
    await u.type(screen.getByLabelText('Ngày phát hành'), '07/15')
    await u.click(screen.getByText('Tiếp tục'))
    const o = await screen.findByLabelText('Mã OTP')
    for (let i = 0; i < 3; i++) {
      await u.clear(o)
      await u.type(o, '000000')
      await u.click(screen.getByText('Xác nhận'))
    }
    await waitFor(() => expect(POST).toHaveBeenCalledWith(...IPN(false)))
  })

  it('MoMo: quét giả lập rồi nhập PIN đúng thì thành công; Hủy giao dịch thì thất bại', async () => {
    giaLapCong(GD('momo'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    const u = userEvent.setup()
    await u.click(await screen.findByText(/Mô phỏng: mở ứng dụng MoMo/))
    await u.type(screen.getByLabelText('Mã PIN'), '123456')
    await u.click(screen.getByText('Xác nhận'))
    await waitFor(() => expect(POST).toHaveBeenCalledWith(...IPN(true)))
  })

  it('Hủy giao dịch gửi thanh_cong=false', async () => {
    giaLapCong(GD('momo'))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    await userEvent.setup().click(await screen.findByText('Hủy giao dịch'))
    await waitFor(() => expect(POST).toHaveBeenCalledWith(...IPN(false)))
  })

  it('giao dịch đã xử lý: không cho thanh toán lại, dẫn tới đơn hàng', async () => {
    giaLapCong(GD('vnpay', { trang_thai: 'thanh_cong' }))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    expect(await screen.findByText('Giao dịch này đã được xử lý')).toBeInTheDocument()
    expect(screen.queryByText('Hủy giao dịch')).not.toBeInTheDocument()
  })

  it('giao dịch quá hạn: báo hết hạn', async () => {
    giaLapCong(GD('vnpay', { het_han_luc: new Date(Date.now() - 1000).toISOString() }))
    renderTai('/thanh-toan-gia?giao_dich=DHABCD2345-17')
    expect(await screen.findByText('Giao dịch đã hết hạn')).toBeInTheDocument()
  })

  it('giao dịch không có: báo không tìm thấy', async () => {
    GET.mockResolvedValue({ error: { ma_loi: 'KHONG_TIM_THAY', thong_diep: 'x', chi_tiet: null }, response: { ok: false, status: 404 } })
    renderTai('/thanh-toan-gia?giao_dich=rac')
    expect(await screen.findByText('Không tìm thấy giao dịch')).toBeInTheDocument()
  })

  it('thiếu giao_dich: báo lỗi, không có nút', async () => {
    giaLapDon(don())
    renderTai('/thanh-toan-gia')
    expect(await screen.findByText('Thiếu mã giao dịch')).toBeInTheDocument()
    expect(screen.queryByText('Tiếp tục')).not.toBeInTheDocument()
  })
})
