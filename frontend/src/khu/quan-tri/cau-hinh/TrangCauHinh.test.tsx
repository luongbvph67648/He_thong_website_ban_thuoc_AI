import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangCauHinh from './TrangCauHinh'

vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), PUT: (...a: unknown[]) => PUT(...a) } }))

const co = (khoa: string, nhom: string, nhan: string, tuyChon: Record<string, unknown>) => ({
  khoa,
  nhom,
  nhan,
  mo_ta: `Mô tả ${khoa}`,
  kieu: 'so',
  don_vi: 'ngày',
  toi_thieu: 1,
  toi_da: 730,
  truong: [],
  gia_tri: 90,
  phien_ban: 'a'.repeat(16),
  nhan_vien_cap_nhat: null,
  updated_at: null,
  ...tuyChon,
})
const MUC = () => [
  co('nguong_can_han_ngay', 'Hàng và hạn dùng', 'Ngưỡng cận hạn', { phien_ban: '1'.repeat(16) }),
  co('han_su_dung_toi_thieu_nhap_ngay', 'Hàng và hạn dùng', 'Hạn dùng tối thiểu khi nhập', {
    toi_da: 1095,
    gia_tri: 180,
    nhan_vien_cap_nhat: { id: 3, ma_nhan_vien: 'NV0003', ho_ten: 'Quản trị viên' },
    updated_at: '2026-10-14T03:00:00Z',
  }),
  co('phi_ship_mac_dinh', 'Vận chuyển', 'Phí vận chuyển mặc định', { kieu: 'tien', don_vi: 'đồng', toi_thieu: 0, toi_da: 1_000_000, gia_tri: 30000 }),
  co('gioi_han_otp', 'Bảo mật đăng nhập', 'Giới hạn gửi mã OTP', {
    kieu: 'nhom_so',
    don_vi: null,
    toi_thieu: null,
    toi_da: null,
    gia_tri: { moi_sdt_moi_gio: 5, moi_ip_moi_gio: 20 },
    truong: [
      { ten: 'moi_sdt_moi_gio', nhan: 'Mỗi số điện thoại mỗi giờ', don_vi: 'lần', toi_thieu: 1, toi_da: 20 },
      { ten: 'moi_ip_moi_gio', nhan: 'Mỗi địa chỉ IP mỗi giờ', don_vi: 'lần', toi_thieu: 1, toi_da: 200 },
    ],
  }),
  co('gio_lam_viec_duoc_si', 'Giờ làm việc', 'Giờ làm việc của dược sĩ', {
    kieu: 'gio_lam_viec',
    don_vi: null,
    toi_thieu: null,
    toi_da: null,
    gia_tri: { bat_dau: '08:00', ket_thuc: '21:00', ngay_trong_tuan: [1, 2, 3, 4, 5] },
  }),
  co('thoi_han_doi_tra_ngay', 'Đơn hàng và thanh toán', 'Thời hạn đổi trả', { gia_tri: null, toi_da: 365 }),
]
const ok = (data: unknown) => ({ data, response: { status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { status } })

function dung(quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'config.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <TrangCauHinh />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const o = (nhan: string) => screen.getByRole('spinbutton', { name: nhan })
const hang = (nhan: string) => screen.getByText(nhan).closest('[data-khoa]') as HTMLElement
const luu = (nhan: string) => within(hang(nhan)).getByRole('button', { name: 'Lưu' })
const goTrong = async (nguoi: ReturnType<typeof userEvent.setup>, nhan: string, so: string) => {
  await nguoi.clear(o(nhan))
  if (so) await nguoi.type(o(nhan), so)
}

beforeEach(() => {
  GET.mockReset()
  PUT.mockReset()
  GET.mockImplementation(async () => ok(MUC()))
})

describe('TrangCauHinh', () => {
  it('nhóm theo chủ đề, mỗi khóa có nhãn, mô tả, giá trị, khoảng cho phép và người cập nhật gần nhất', async () => {
    dung()
    for (const nhom of ['Hàng và hạn dùng', 'Vận chuyển', 'Bảo mật đăng nhập', 'Giờ làm việc', 'Đơn hàng và thanh toán']) {
      expect(await screen.findByText(nhom)).toBeInTheDocument()
    }
    expect(o('Ngưỡng cận hạn')).toHaveValue('90')
    expect(screen.getByText('Mô tả nguong_can_han_ngay')).toBeInTheDocument()
    expect(within(hang('Ngưỡng cận hạn')).getByText(/từ 1 đến 730 ngày/)).toBeInTheDocument()
    expect(o('Phí vận chuyển mặc định')).toHaveValue('30.000')
    expect(within(hang('Hạn dùng tối thiểu khi nhập')).getByText(/Cập nhật bởi Quản trị viên \(NV0003\) lúc 14\/10\/2026 10:00/)).toBeInTheDocument()
    expect(within(hang('Ngưỡng cận hạn')).getByText('Chưa có ai chỉnh, đang dùng giá trị mặc định')).toBeInTheDocument()
    expect(within(hang('Thời hạn đổi trả')).getByText('Chưa thiết lập')).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/cau-hinh')
  })

  it('chưa sửa gì thì không có nút Lưu bật; sửa mới có, hoàn tác trả về giá trị cũ', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Ngưỡng cận hạn')
    expect(luu('Ngưỡng cận hạn')).toBeDisabled()
    await goTrong(nguoi, 'Ngưỡng cận hạn', '60')
    expect(luu('Ngưỡng cận hạn')).toBeEnabled()
    expect(luu('Hạn dùng tối thiểu khi nhập')).toBeDisabled() // khóa khác không bị ảnh hưởng
    await nguoi.click(within(hang('Ngưỡng cận hạn')).getByRole('button', { name: 'Hoàn tác' }))
    expect(o('Ngưỡng cận hạn')).toHaveValue('90')
    expect(luu('Ngưỡng cận hạn')).toBeDisabled()
  })

  it('giá trị ngoài khoảng hiện lỗi ngay và không cho lưu', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Ngưỡng cận hạn')
    await goTrong(nguoi, 'Ngưỡng cận hạn', '0')
    expect(await within(hang('Ngưỡng cận hạn')).findByText(/Phải là số nguyên từ 1 đến 730 ngày/, { selector: '[role="alert"]' })).toBeInTheDocument()
    expect(luu('Ngưỡng cận hạn')).toBeDisabled()
    await goTrong(nguoi, 'Ngưỡng cận hạn', '')
    expect(luu('Ngưỡng cận hạn')).toBeDisabled() // để trống cũng không hợp lệ
  })

  it('ô tiền: xóa trắng là KHÔNG hợp lệ (không âm thầm thành 0, vì 0 nghĩa là miễn phí vận chuyển)', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Phí vận chuyển mặc định')
    await goTrong(nguoi, 'Phí vận chuyển mặc định', '')
    expect(o('Phí vận chuyển mặc định')).toHaveValue('')
    expect(await within(hang('Phí vận chuyển mặc định')).findByText(/Phải là số nguyên từ 0 đến 1\.000\.000 đồng/, { selector: '[role="alert"]' })).toBeInTheDocument()
    expect(luu('Phí vận chuyển mặc định')).toBeDisabled()
    await goTrong(nguoi, 'Phí vận chuyển mặc định', '0') // gõ 0 thật thì hợp lệ
    expect(luu('Phí vận chuyển mặc định')).toBeEnabled()
  })

  it('lưu: gửi PUT đúng khóa kèm phien_ban đã đọc, báo thành công và tải lại', async () => {
    PUT.mockResolvedValueOnce(ok(MUC()[0]))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Ngưỡng cận hạn')
    await goTrong(nguoi, 'Ngưỡng cận hạn', '60')
    const truoc = GET.mock.calls.length
    await nguoi.click(luu('Ngưỡng cận hạn'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT).toHaveBeenCalledWith('/api/v1/noi-bo/cau-hinh/{khoa}', {
      params: { path: { khoa: 'nguong_can_han_ngay' } },
      body: { gia_tri: 60, phien_ban: '1'.repeat(16) },
    })
    expect(await screen.findByText('Đã lưu: Ngưỡng cận hạn')).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.length).toBeGreaterThan(truoc))
  })

  it('nhóm số: gửi cả đối tượng, các trường không sửa giữ nguyên; lỗi một trường chỉ hiện ở trường đó', async () => {
    PUT.mockResolvedValueOnce(ok(MUC()[3]))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Giới hạn gửi mã OTP')
    await goTrong(nguoi, 'Giới hạn gửi mã OTP: Mỗi số điện thoại mỗi giờ', '99')
    expect(await within(hang('Giới hạn gửi mã OTP')).findByText(/từ 1 đến 20 lần/)).toBeInTheDocument()
    expect(luu('Giới hạn gửi mã OTP')).toBeDisabled()
    await goTrong(nguoi, 'Giới hạn gửi mã OTP: Mỗi số điện thoại mỗi giờ', '3')
    await nguoi.click(luu('Giới hạn gửi mã OTP'))
    await waitFor(() => expect(PUT.mock.calls[0][1].body.gia_tri).toEqual({ moi_sdt_moi_gio: 3, moi_ip_moi_gio: 20 }))
  })

  it('giờ làm việc: đổi giờ và ngày, ngày được gửi theo thứ tự tăng dần; bắt đầu không trước kết thúc thì báo lỗi', async () => {
    PUT.mockResolvedValueOnce(ok(MUC()[4]))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Giờ làm việc của dược sĩ')
    const gioBatDau = screen.getByLabelText('Giờ bắt đầu')
    expect(gioBatDau).toHaveValue('08:00')
    fireEvent.change(gioBatDau, { target: { value: '22:00' } })
    expect(await within(hang('Giờ làm việc của dược sĩ')).findByText('Giờ kết thúc phải sau giờ bắt đầu')).toBeInTheDocument()
    expect(luu('Giờ làm việc của dược sĩ')).toBeDisabled()
    fireEvent.change(gioBatDau, { target: { value: '07:30' } })
    await nguoi.click(screen.getByRole('checkbox', { name: 'Thứ bảy' }))
    await nguoi.click(screen.getByRole('checkbox', { name: 'Thứ hai' })) // bỏ
    await nguoi.click(luu('Giờ làm việc của dược sĩ'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0][1].body.gia_tri).toEqual({ bat_dau: '07:30', ket_thuc: '21:00', ngay_trong_tuan: [2, 3, 4, 5, 6] })
  })

  it('bỏ hết các ngày trong tuần thì báo lỗi và không cho lưu', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Giờ làm việc của dược sĩ')
    for (const ngay of ['Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu']) await nguoi.click(screen.getByRole('checkbox', { name: ngay }))
    expect(await within(hang('Giờ làm việc của dược sĩ')).findByText('Chọn ít nhất một ngày trong tuần')).toBeInTheDocument()
    expect(luu('Giờ làm việc của dược sĩ')).toBeDisabled()
  })

  it('máy chủ từ chối (400): hiện lý do theo trường, giữ nguyên giá trị đang gõ', async () => {
    PUT.mockResolvedValueOnce(loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'gia_tri.moi_ip_moi_gio', loi: 'Thiếu trường này' }]))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Giới hạn gửi mã OTP')
    await goTrong(nguoi, 'Giới hạn gửi mã OTP: Mỗi số điện thoại mỗi giờ', '4')
    await nguoi.click(luu('Giới hạn gửi mã OTP'))
    expect(await screen.findByText('Thiếu trường này')).toBeInTheDocument()
    expect(o('Giới hạn gửi mã OTP: Mỗi số điện thoại mỗi giờ')).toHaveValue('4')
  })

  it('Admin khác vừa sửa (409): cảnh báo, tải lại bản mới nhưng GIỮ giá trị người dùng đang gõ để họ quyết định', async () => {
    PUT.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Cấu hình này vừa được người khác thay đổi'))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Ngưỡng cận hạn')
    await goTrong(nguoi, 'Ngưỡng cận hạn', '60')
    GET.mockImplementation(async () => ok(MUC().map((m) => (m.khoa === 'nguong_can_han_ngay' ? { ...m, gia_tri: 45, phien_ban: '2'.repeat(16) } : m))))
    await nguoi.click(luu('Ngưỡng cận hạn'))
    expect(await screen.findByText(/vừa được người khác thay đổi/)).toBeInTheDocument()
    await waitFor(() => expect(within(hang('Ngưỡng cận hạn')).getByText(/Giá trị hiện tại trên máy chủ: 45/)).toBeInTheDocument())
    expect(o('Ngưỡng cận hạn')).toHaveValue('60') // vẫn là điều người dùng đang gõ
    PUT.mockResolvedValueOnce(ok(MUC()[0]))
    await nguoi.click(luu('Ngưỡng cận hạn'))
    await waitFor(() => expect(PUT.mock.calls[1][1].body).toEqual({ gia_tri: 60, phien_ban: '2'.repeat(16) })) // lưu lại bằng phiên bản mới
  })

  it('lỗi kết nối khi lưu báo thông điệp chung, không báo thành công', async () => {
    PUT.mockResolvedValueOnce({ error: undefined, data: undefined })
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Ngưỡng cận hạn')
    await goTrong(nguoi, 'Ngưỡng cận hạn', '60')
    await nguoi.click(luu('Ngưỡng cận hạn'))
    expect(await screen.findByText(/Không kết nối được máy chủ/)).toBeInTheDocument()
    expect(screen.queryByText(/Đã lưu/)).not.toBeInTheDocument()
  })

  it('chỉ có quyền xem: mọi ô nhập bị khóa và không có nút Lưu', async () => {
    dung('chi_xem')
    await screen.findByText('Ngưỡng cận hạn')
    expect(o('Ngưỡng cận hạn')).toBeDisabled()
    expect(screen.getByLabelText('Giờ bắt đầu')).toBeDisabled()
    expect(screen.queryByRole('button', { name: 'Lưu' })).not.toBeInTheDocument()
  })

  it('lỗi tải danh sách hiện thông báo thay vì trang trống', async () => {
    GET.mockImplementation(async () => loi(500, 'LOI_HE_THONG', 'x'))
    dung()
    expect(await screen.findByText('Không tải được cấu hình hệ thống')).toBeInTheDocument()
  })
})
