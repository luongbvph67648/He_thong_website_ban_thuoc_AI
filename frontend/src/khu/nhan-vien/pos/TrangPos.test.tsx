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
const dung = () => renderTai('/nhan-vien/pos', { loai: 'noi_bo', vaiTro: 'PHARMACIST', quyen: { 'pos.sell': 'day_du' } as never })
const SP = (rieng: object = {}) => ({
  id: 1, ten: 'Panadol Extra', loai_san_pham: 'thuoc_khong_ke_don', don_vi_co_so: 'viên', ton_quay: 50, co_lo_can_han: true, hoat_chat: ['Paracetamol'],
  don_vi: [
    { id: 10, ten_don_vi: 'viên', he_so: 1, gia_ban: '1000.00', ma_vach: null },
    { id: 11, ten_don_vi: 'hộp', he_so: 10, gia_ban: '9000.00', ma_vach: '8934001' },
  ],
  don_vi_khop_ma_vach: null, ...rieng,
})
const HOA_DON = {
  ten_nha_thuoc: 'Nhà thuốc AI', ma_don: 'DHPOS0001', thoi_diem: '2026-10-16T03:00:00Z', nhan_vien: 'Dược sĩ A', khach: null,
  dong: [{ ten_san_pham: 'Panadol Extra', ten_don_vi: 'hộp', so_luong: 1, don_gia: '9000.00', thanh_tien: '9000.00' }],
  tam_tinh: '9000.00', giam_gia: '0.00', tong_tien: '9000.00', phuong_thuc_thu: 'tien_mat', tien_khach_dua: '10000.00', tien_thua: '1000.00', co_thuoc_ke_don: false,
}
let tim: unknown[] = []

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  tim = [SP()]
  GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/pos/san-pham' ? ok(tim) : ok({ so_chua_doc: 0, du_lieu: [], tong: 0 })))
  POST.mockImplementation(async (duong: string) => {
    if (duong.endsWith('/canh-bao')) return ok({ tuong_tac: [], di_ung: [], can_xac_nhan: false })
    if (duong.endsWith('/pos/don')) return ok({ don_id: 5, hoa_don: HOA_DON })
    return ok({})
  })
})

describe('POS (DS08)', () => {
  it('tìm thuốc, thêm theo đơn vị, thiếu tiền thì chưa bán; đủ tiền thì bán và hiện hóa đơn', async () => {
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText(/Quét mã vạch/), 'panadol{Enter}')
    expect(await screen.findByText(/Có lô cận hạn/)).toBeInTheDocument()
    await u.click(await screen.findByRole('button', { name: 'Thêm' }))
    expect(await screen.findByText('Tổng: 1.000 ₫')).toBeInTheDocument()
    const ban = screen.getByRole('button', { name: 'Thanh toán và in hóa đơn' })
    expect(ban).toBeDisabled() // tiền mặt chưa nhập tiền khách đưa
    await u.type(screen.getByLabelText('Tiền khách đưa'), '500')
    expect(await screen.findByText(/Còn thiếu/)).toBeInTheDocument()
    expect(ban).toBeDisabled()
    await u.clear(screen.getByLabelText('Tiền khách đưa'))
    await u.type(screen.getByLabelText('Tiền khách đưa'), '2000')
    expect(await screen.findByText(/Tiền thối: 1.000/)).toBeInTheDocument()
    await waitFor(() => expect(ban).toBeEnabled())
    await u.click(ban)
    expect(await screen.findByText('HÓA ĐƠN BÁN HÀNG')).toBeInTheDocument()
    const goiBan = POST.mock.calls.find((c) => c[0].endsWith('/pos/don'))![1]
    expect(goiBan.body).toMatchObject({ phuong_thuc_thu: 'tien_mat', tien_khach_dua: '2000', yeu_cau_don_thuoc_id: null })
    expect(goiBan.body.dong).toEqual([{ san_pham_id: 1, don_vi_id: 10, so_luong: 1 }])
    expect(goiBan.headers['Idempotency-Key']).toBeTruthy()
    expect(screen.getByText('Số: DHPOS0001')).toBeInTheDocument()
  })

  it('quét mã vạch khớp đúng một sản phẩm thì tự thêm đúng đơn vị', async () => {
    tim = [SP({ don_vi_khop_ma_vach: 11 })]
    dung()
    await userEvent.type(await screen.findByPlaceholderText(/Quét mã vạch/), '8934001{Enter}')
    expect(await screen.findByText('Tổng: 9.000 ₫')).toBeInTheDocument()
    expect(screen.getAllByText('hộp').length).toBeGreaterThan(0)
  })

  it('thuốc kê đơn: chặn bán cho tới khi lập yêu cầu đơn thuốc; chuyển khoản không cần tiền khách đưa', async () => {
    tim = [SP({ loai_san_pham: 'thuoc_ke_don', ten: 'Augmentin' })]
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText(/Quét mã vạch/), 'aug{Enter}')
    await u.click(await screen.findByRole('button', { name: 'Thêm' }))
    expect(await screen.findByText('Đơn thuốc (bắt buộc cho thuốc kê đơn)')).toBeInTheDocument()
    await u.click(screen.getByLabelText('Chuyển khoản'))
    const ban = screen.getByRole('button', { name: 'Thanh toán và in hóa đơn' })
    expect(ban).toBeDisabled() // chưa có yêu cầu đơn thuốc
    POST.mockImplementation(async (duong: string) => {
      if (duong.endsWith('/canh-bao')) return ok({ tuong_tac: [], di_ung: [], can_xac_nhan: false })
      if (duong.endsWith('/pos/don-thuoc')) return ok({ id: 9, ma_yeu_cau: 'YCQ1', ho_ten: 'Lê C', trung_anh: [] })
      return ok({ don_id: 5, hoa_don: { ...HOA_DON, co_thuoc_ke_don: true, tien_khach_dua: null, tien_thua: null, phuong_thuc_thu: 'chuyen_khoan' } })
    })
    await u.type(screen.getByLabelText('Họ tên người bệnh'), 'Lê C')
    await u.upload(document.querySelector('input[type=file]') as HTMLInputElement, new File([new Uint8Array(10)], 'don.png', { type: 'image/png' }))
    await u.click(screen.getByRole('button', { name: 'Lập yêu cầu đơn thuốc' }))
    expect(await screen.findByText(/Đã lập yêu cầu YCQ1/)).toBeInTheDocument()
    await waitFor(() => expect(ban).toBeEnabled())
    await u.click(ban)
    await screen.findByText('HÓA ĐƠN BÁN HÀNG')
    const body = POST.mock.calls.find((c) => c[0].endsWith('/pos/don'))![1].body
    expect(body).toMatchObject({ yeu_cau_don_thuoc_id: 9, phuong_thuc_thu: 'chuyen_khoan', tien_khach_dua: null })
    expect(screen.getByText(/bán theo đơn của bác sĩ/)).toBeInTheDocument()
  })

  it('cảnh báo nặng: phải tick xác nhận đã tư vấn mới bán được', async () => {
    POST.mockImplementation(async (duong: string) => {
      if (duong.endsWith('/canh-bao'))
        return ok({
          tuong_tac: [{ loai: 'tuong_tac', muc_do: 'nghiem_trong', hoat_chat_a_id: 1, ten_hoat_chat_a: 'A', san_pham_a_id: 1, hoat_chat_b_id: 2, ten_hoat_chat_b: 'B', san_pham_b_id: 2, co_che: null, khuyen_cao: 'Tránh dùng chung' }],
          di_ung: [], can_xac_nhan: true,
        })
      return ok({ don_id: 5, hoa_don: HOA_DON })
    })
    dung()
    const u = userEvent.setup()
    await u.type(await screen.findByPlaceholderText(/Quét mã vạch/), 'pan{Enter}')
    await u.click(await screen.findByRole('button', { name: 'Thêm' }))
    await u.click(screen.getByLabelText('Chuyển khoản'))
    expect(await screen.findByText('Tránh dùng chung')).toBeInTheDocument()
    const ban = screen.getByRole('button', { name: 'Thanh toán và in hóa đơn' })
    expect(ban).toBeDisabled()
    await u.click(screen.getByLabelText(/Tôi đã tư vấn cho khách/))
    await waitFor(() => expect(ban).toBeEnabled())
  })
})
