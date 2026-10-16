import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangTuongTac from './TrangTuongTac'
import type { TuongTac } from './tuongTac'

vi.setConfig({ testTimeout: 60_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
const POST = vi.fn()
const PUT = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', () => ({
  api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a), PUT: (...a: unknown[]) => PUT(...a), DELETE: (...a: unknown[]) => DELETE(...a) },
}))

const ok = (data: unknown, status = 200) => ({ data, response: { ok: true, status } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })
const khongThan = { response: { ok: true, status: 204 } }

const TT = (ghiDe: Partial<TuongTac> = {}): TuongTac => ({
  hoat_chat_a_id: 3,
  ten_hoat_chat_a: 'Aspirin',
  hoat_chat_b_id: 9,
  ten_hoat_chat_b: 'Warfarin',
  muc_do: 'chong_chi_dinh',
  co_che: 'Cộng hợp chống đông',
  khuyen_cao: 'Không dùng chung',
  nguon_tham_khao: 'BNF',
  nguoi_cap_nhat: 'Dược sĩ An',
  updated_at: '2026-10-10T03:00:00Z',
  phien_ban: 'aaaaaaaaaaaaaaaa',
  ...ghiDe,
})
const DANH_SACH = [TT(), TT({ hoat_chat_a_id: 4, ten_hoat_chat_a: 'Ibuprofen', hoat_chat_b_id: 5, ten_hoat_chat_b: 'Aspirin', muc_do: 'trung_binh', khuyen_cao: 'Uống cách nhau', co_che: null, nguon_tham_khao: null, nguoi_cap_nhat: null, updated_at: null })]
const HOAT_CHAT = [
  { id: 3, ten: 'Aspirin', ten_khac: null, mo_ta: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 1 },
  { id: 9, ten: 'Warfarin', ten_khac: null, mo_ta: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 1 },
]

function dung(duong = '/nhan-vien/tuong-tac', quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'DS', vaiTro: 'PHARMACIST' }, quyen: { 'content.professional.edit': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <TrangTuongTac />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const nutChu = (chu: string, khung: HTMLElement = document.body) => {
  const el = within(khung).getAllByText(chu).map((e) => e.closest('button')).find(Boolean)
  if (!el) throw new Error(`Không có nút "${chu}"`)
  return el as HTMLButtonElement
}
const hopThoai = async () => within(await screen.findByRole('dialog', { hidden: true }))
const query = (m: ReturnType<typeof vi.fn>, duong: string) => m.mock.calls.filter((c) => c[0] === duong).at(-1)?.[1]

async function chon(nguoi: ReturnType<typeof userEvent.setup>, nhan: string, chu: string) {
  await nguoi.click(screen.getByLabelText(nhan))
  // Chữ có thể trùng ở ô khác (bảng, danh sách của ô chọn kia đã đóng): chỉ nhận dòng trong danh sách đang mở.
  // Lấy dòng CUỐI: danh sách của ô vừa chọn xong còn đang chạy hiệu ứng đóng (pointer-events: none) và nằm trước trong DOM.
  const trongDanhSachMo = () => screen.queryAllByText(chu).filter((d) => d.closest('.ant-select-dropdown:not(.ant-select-dropdown-hidden)')).at(-1)
  await waitFor(() => expect(trongDanhSachMo()).toBeTruthy())
  await nguoi.click(trongDanhSachMo() as HTMLElement)
}

beforeEach(() => {
  for (const m of [GET, POST, PUT, DELETE]) m.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/tuong-tac') return ok({ du_lieu: DANH_SACH, tong: 2, trang: 1, kich_thuoc: 20 })
    if (duong === '/api/v1/noi-bo/hoat-chat') return ok({ du_lieu: HOAT_CHAT, tong: 2, trang: 1, kich_thuoc: 20 })
    throw new Error(`GET chưa giả lập: ${duong}`)
  })
})

describe('TrangTuongTac', () => {
  it('hiện từng tương tác với nhãn mức độ, khuyến cáo và người cập nhật', async () => {
    dung()
    const hang = (await screen.findByText('Warfarin')).closest('tr') as HTMLElement
    expect(within(hang).getByText('Aspirin')).toBeInTheDocument()
    expect(within(hang).getByText('Chống chỉ định')).toBeInTheDocument()
    expect(within(hang).getByText('Không dùng chung')).toBeInTheDocument()
    expect(within(hang).getByText(/Dược sĩ An/)).toBeInTheDocument()
    const hang2 = (await screen.findByText('Ibuprofen')).closest('tr') as HTMLElement
    expect(within(hang2).getByText('Trung bình')).toBeInTheDocument()
  })

  it('bộ lọc trên URL được gửi lên máy chủ; mức độ lạ bị bỏ qua', async () => {
    dung('/nhan-vien/tuong-tac?q=aspirin&muc_do=nghiem_trong&trang=2')
    await screen.findByText('Warfarin')
    expect(query(GET, '/api/v1/noi-bo/tuong-tac').params.query).toEqual({ q: 'aspirin', muc_do: 'nghiem_trong', trang: 2, kich_thuoc: 20 })
    GET.mockClear()
    dung('/nhan-vien/tuong-tac?muc_do=hack')
    await screen.findAllByText('Warfarin')
    expect(query(GET, '/api/v1/noi-bo/tuong-tac').params.query.muc_do).toBeUndefined()
  })

  it('thêm: kiểm tra từng ô trước, rồi POST đủ thân và làm mới', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(ok(TT(), 201))
    dung()
    await screen.findByText('Warfarin')
    await nguoi.click(nutChu('Thêm tương tác'))
    const h = await hopThoai()
    await nguoi.click(nutChu('Thêm', await screen.findByRole('dialog', { hidden: true })))
    expect(await h.findByText('Vui lòng chọn hoạt chất thứ nhất')).toBeInTheDocument()
    expect(h.getByText('Vui lòng chọn mức độ')).toBeInTheDocument()
    expect(h.getByText('Vui lòng nhập khuyến cáo')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    await chon(nguoi, 'Hoạt chất thứ nhất', 'Warfarin')
    await chon(nguoi, 'Hoạt chất thứ hai', 'Aspirin')
    await nguoi.click(screen.getByLabelText('Mức độ'))
    await nguoi.click(await screen.findByText('Nghiêm trọng', { selector: '.ant-select-item-option-content' }))
    await nguoi.type(screen.getByLabelText('Khuyến cáo cho người dùng'), '  Tránh dùng chung  ')
    await nguoi.click(nutChu('Thêm', await screen.findByRole('dialog', { hidden: true })))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0]).toEqual([
      '/api/v1/noi-bo/tuong-tac',
      { body: { hoat_chat_1_id: 9, hoat_chat_2_id: 3, muc_do: 'nghiem_trong', co_che: null, khuyen_cao: 'Tránh dùng chung', nguon_tham_khao: null } },
    ])
    expect(await screen.findByText('Đã thêm tương tác')).toBeInTheDocument()
  })

  it('hai hoạt chất giống nhau bị chặn ở giao diện', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Warfarin')
    await nguoi.click(nutChu('Thêm tương tác'))
    await hopThoai()
    await chon(nguoi, 'Hoạt chất thứ nhất', 'Aspirin')
    await chon(nguoi, 'Hoạt chất thứ hai', 'Aspirin')
    await nguoi.click(nutChu('Thêm', await screen.findByRole('dialog', { hidden: true })))
    expect(await screen.findByText('Hai hoạt chất phải khác nhau')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('thêm trùng cặp: thông điệp 409 của máy chủ hiện trong hộp thoại, dữ liệu còn nguyên', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'Đã có tương tác cho cặp hoạt chất này, hãy sửa bản ghi đó'))
    dung()
    await screen.findByText('Warfarin')
    await nguoi.click(nutChu('Thêm tương tác'))
    await hopThoai()
    await chon(nguoi, 'Hoạt chất thứ nhất', 'Warfarin')
    await chon(nguoi, 'Hoạt chất thứ hai', 'Aspirin')
    await nguoi.click(screen.getByLabelText('Mức độ'))
    await nguoi.click(await screen.findByText('Nhẹ', { selector: '.ant-select-item-option-content' }))
    await nguoi.type(screen.getByLabelText('Khuyến cáo cho người dùng'), 'Theo dõi')
    await nguoi.click(nutChu('Thêm', await screen.findByRole('dialog', { hidden: true })))
    expect(await screen.findByText(/Đã có tương tác cho cặp hoạt chất này/)).toBeInTheDocument()
    expect(screen.getByLabelText('Khuyến cáo cho người dùng')).toHaveValue('Theo dõi')
  })

  it('sửa: cặp hoạt chất cố định, PUT kèm phien_ban của dòng', async () => {
    const nguoi = userEvent.setup()
    PUT.mockResolvedValue(ok(TT({ muc_do: 'nhe' })))
    dung()
    const hang = (await screen.findByText('Warfarin')).closest('tr') as HTMLElement
    await nguoi.click(nutChu('Sửa', hang))
    await hopThoai()
    expect(screen.getByLabelText('Hoạt chất thứ nhất')).toBeDisabled()
    expect(screen.getByLabelText('Khuyến cáo cho người dùng')).toHaveValue('Không dùng chung')
    const khuyenCao = screen.getByLabelText('Khuyến cáo cho người dùng')
    await nguoi.clear(khuyenCao)
    await nguoi.type(khuyenCao, 'Cấm dùng chung')
    await nguoi.click(nutChu('Lưu', await screen.findByRole('dialog', { hidden: true })))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0]).toEqual([
      '/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}',
      { params: { path: { hoat_chat_1_id: 3, hoat_chat_2_id: 9 } }, body: { phien_ban: 'aaaaaaaaaaaaaaaa', muc_do: 'chong_chi_dinh', co_che: 'Cộng hợp chống đông', khuyen_cao: 'Cấm dùng chung', nguon_tham_khao: 'BNF' } },
    ])
    expect(await screen.findByText('Đã lưu tương tác')).toBeInTheDocument()
  })

  it('sửa gặp 409: lấy bản mới, giữ chữ đang gõ, báo rõ; lưu lại dùng phien_ban mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    const hang = (await screen.findByText('Warfarin')).closest('tr') as HTMLElement
    await nguoi.click(nutChu('Sửa', hang))
    await hopThoai()
    PUT.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Tương tác này vừa được người khác thay đổi'))
    GET.mockImplementation(async (duong: string) => {
      if (duong === '/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}') return ok(TT({ khuyen_cao: 'Bản của người khác', phien_ban: 'bbbbbbbbbbbbbbbb' }))
      if (duong === '/api/v1/noi-bo/tuong-tac') return ok({ du_lieu: DANH_SACH, tong: 2, trang: 1, kich_thuoc: 20 })
      return ok({ du_lieu: HOAT_CHAT, tong: 2, trang: 1, kich_thuoc: 20 })
    })
    const khuyenCao = screen.getByLabelText('Khuyến cáo cho người dùng')
    await nguoi.clear(khuyenCao)
    await nguoi.type(khuyenCao, 'Chữ tôi gõ')
    await nguoi.click(nutChu('Lưu', await screen.findByRole('dialog', { hidden: true })))
    expect(await screen.findByText(/vừa được người khác thay đổi\. Giá trị bạn đang gõ vẫn còn nguyên/)).toBeInTheDocument()
    expect(screen.getByLabelText('Khuyến cáo cho người dùng')).toHaveValue('Chữ tôi gõ')
    PUT.mockResolvedValueOnce(ok(TT()))
    await nguoi.click(nutChu('Lưu', await screen.findByRole('dialog', { hidden: true })))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(2))
    expect(PUT.mock.calls[1][1].body.phien_ban).toBe('bbbbbbbbbbbbbbbb')
  })

  it('xóa: xác nhận rồi DELETE kèm phien_ban; lỗi 409 báo thông điệp máy chủ', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Tương tác này vừa được người khác thay đổi')).mockResolvedValueOnce(khongThan)
    dung()
    const hang = (await screen.findByText('Warfarin')).closest('tr') as HTMLElement
    await nguoi.click(nutChu('Xóa', hang))
    await nguoi.click(await screen.findByText('Xóa', { selector: '.ant-popover .ant-btn-primary span, .ant-popconfirm .ant-btn-primary span' }))
    expect(await screen.findByText('Tương tác này vừa được người khác thay đổi')).toBeInTheDocument()
    await nguoi.click(nutChu('Xóa', (await screen.findByText('Warfarin')).closest('tr') as HTMLElement))
    await nguoi.click(await screen.findByText('Xóa', { selector: '.ant-popover .ant-btn-primary span, .ant-popconfirm .ant-btn-primary span' }))
    expect(await screen.findByText('Đã xóa tương tác')).toBeInTheDocument()
    expect(DELETE.mock.calls[1]).toEqual(['/api/v1/noi-bo/tuong-tac/{hoat_chat_1_id}/{hoat_chat_2_id}', { params: { path: { hoat_chat_1_id: 3, hoat_chat_2_id: 9 }, query: { phien_ban: 'aaaaaaaaaaaaaaaa' } } }])
  })

  it('chỉ xem: thấy dữ liệu nhưng không có nút Thêm, Sửa, Xóa', async () => {
    dung('/nhan-vien/tuong-tac', 'chi_xem')
    await screen.findByText('Warfarin')
    expect(() => nutChu('Thêm tương tác')).toThrow()
    expect(() => nutChu('Sửa')).toThrow()
    expect(() => nutChu('Xóa')).toThrow()
  })

  it('rỗng và lỗi tải', async () => {
    GET.mockImplementation(async () => ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 20 }))
    const { unmount } = dung()
    expect(await screen.findByText('Chưa có tương tác nào')).toBeInTheDocument()
    unmount()
    GET.mockImplementation(async () => loi(500, 'LOI_HE_THONG', 'x'))
    dung()
    expect(await screen.findByText('Không tải được danh sách tương tác')).toBeInTheDocument()
  })
})
