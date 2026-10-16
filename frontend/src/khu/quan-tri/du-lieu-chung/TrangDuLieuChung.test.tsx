import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangDuLieuChung from './TrangDuLieuChung'

vi.setConfig({ testTimeout: 30_000 })

const GET = vi.fn()
const POST = vi.fn()
const PATCH = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', () => ({
  api: {
    GET: (...a: unknown[]) => GET(...a),
    POST: (...a: unknown[]) => POST(...a),
    PATCH: (...a: unknown[]) => PATCH(...a),
    DELETE: (...a: unknown[]) => DELETE(...a),
  },
}))

const THUONG_HIEU = [
  { id: 1, ten: 'Sanofi', logo_url: 'https://cdn.example.com/sanofi.png', created_at: '2026-10-01T03:00:00Z', so_san_pham: 3 },
  { id: 2, ten: 'Chưa dùng', logo_url: null, created_at: '2026-09-15T20:00:00Z', so_san_pham: 0 },
]
const NHA_SAN_XUAT = [{ id: 7, ten: 'Pymepharco', quoc_gia: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 0 }]
const HOAT_CHAT = [
  { id: 9, ten: 'Paracetamol', ten_khac: 'Acetaminophen', mo_ta: 'Giảm đau, hạ sốt', created_at: '2026-10-01T03:00:00Z', so_san_pham: 4 },
  { id: 10, ten: 'Penicillin', ten_khac: null, mo_ta: null, created_at: '2026-10-02T03:00:00Z', so_san_pham: 0 },
]
const DU_LIEU: Record<string, unknown[]> = {
  '/api/v1/noi-bo/thuong-hieu': THUONG_HIEU,
  '/api/v1/noi-bo/nha-san-xuat': NHA_SAN_XUAT,
  '/api/v1/noi-bo/hoat-chat': HOAT_CHAT,
}
const trang = (du_lieu: unknown[]) => ({ data: { du_lieu, tong: du_lieu.length, trang: 1, kich_thuoc: 20 }, response: { ok: true, status: 200 } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({
  error: { ma_loi, thong_diep, chi_tiet },
  response: { ok: false, status },
})
const khongThan = { response: { ok: true, status: 204 } }

function ViTriHienTai() {
  const v = useLocation()
  return <div data-testid="vitri">{v.pathname + v.search}</div>
}

function dung(duong = '/du-lieu-chung', quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'master_data.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path="/du-lieu-chung" element={<TrangDuLieuChung />} />
            </Routes>
            <ViTriHienTai />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const thamSoGanNhat = () => GET.mock.calls.at(-1)?.[1]?.params?.query
const duongGanNhat = () => GET.mock.calls.at(-1)?.[0]
const dong = async (ten: string) => (await screen.findByText(ten)).closest('tr') as HTMLElement
const hopThoai = async () => within(await screen.findByRole('dialog', { hidden: true }))

beforeEach(() => {
  for (const m of [GET, POST, PATCH, DELETE]) m.mockReset()
  GET.mockImplementation(async (duong: string) => trang(DU_LIEU[duong] ?? []))
})

describe('TrangDuLieuChung: danh sách', () => {
  it('mặc định là tab Thương hiệu: tên, logo, số sản phẩm, ngày theo giờ Việt Nam', async () => {
    dung()
    const hang = await dong('Sanofi')
    expect(duongGanNhat()).toBe('/api/v1/noi-bo/thuong-hieu')
    expect(thamSoGanNhat()).toEqual({ q: undefined, sap_xep: undefined, trang: 1, kich_thuoc: 20 })
    expect(within(hang).getByRole('img', { hidden: true, name: 'Logo Sanofi' })).toHaveAttribute('src', 'https://cdn.example.com/sanofi.png')
    expect(within(hang).getByText('3')).toBeInTheDocument()
    expect(within(hang).getByText('01/10/2026')).toBeInTheDocument()
    const hangTrong = await dong('Chưa dùng')
    expect(within(hangTrong).getByText('—')).toBeInTheDocument() // không logo
    expect(within(hangTrong).getByText('16/09/2026')).toBeInTheDocument() // 20:00 UTC đã sang ngày sau theo giờ VN
  })

  it('đổi tab đưa nhóm lên URL và gọi API của nhóm đó; mở thẳng từ URL cũng đúng', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('Sanofi')
    await nguoi.click(screen.getByRole('tab', { hidden: true, name: 'Hoạt chất' }))
    const hang = await dong('Paracetamol')
    expect(screen.getByTestId('vitri')).toHaveTextContent('/du-lieu-chung?nhom=hoat-chat')
    expect(duongGanNhat()).toBe('/api/v1/noi-bo/hoat-chat')
    expect(within(hang).getByText('Acetaminophen')).toBeInTheDocument()
    expect(within(hang).getByText('Giảm đau, hạ sốt')).toBeInTheDocument()
    expect(within(await dong('Penicillin')).getAllByText('—').length).toBe(2) // không tên khác, không mô tả
    await nguoi.click(screen.getByRole('tab', { hidden: true, name: 'Nhà sản xuất' }))
    expect(within(await dong('Pymepharco')).getByText('—')).toBeInTheDocument() // không quốc gia
    expect(screen.getByTestId('vitri')).toHaveTextContent('?nhom=nha-san-xuat')
  })

  it('tìm kiếm, sắp xếp và trang nằm trên URL; mở trang từ URL thì gọi API đúng các tham số đó', async () => {
    const nguoi = userEvent.setup()
    dung('/du-lieu-chung?nhom=hoat-chat&q=para&sap_xep=-so_san_pham&trang=2')
    await screen.findByText('Paracetamol')
    expect(thamSoGanNhat()).toEqual({ q: 'para', sap_xep: '-so_san_pham', trang: 2, kich_thuoc: 20 })
    const o = screen.getByPlaceholderText(/Tìm theo tên hoặc tên khác/)
    expect(o).toHaveValue('para')
    await nguoi.clear(o)
    await nguoi.type(o, 'peni{Enter}')
    await waitFor(() => expect(thamSoGanNhat()).toEqual({ q: 'peni', sap_xep: '-so_san_pham', trang: 1, kich_thuoc: 20 }))
    expect(screen.getByTestId('vitri')).toHaveTextContent('nhom=hoat-chat&q=peni&sap_xep=-so_san_pham')
  })

  it('bấm tiêu đề cột để sắp xếp: tăng dần, giảm dần, bỏ sắp xếp; tham số lạ trên URL bị bỏ qua', async () => {
    const nguoi = userEvent.setup()
    dung('/du-lieu-chung?sap_xep=id')
    await screen.findByText('Sanofi')
    expect(thamSoGanNhat().sap_xep).toBeUndefined()
    const tieuDe = screen.getByRole('columnheader', { hidden: true, name: /Ngày tạo/ })
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBe('created_at'))
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBe('-created_at'))
    await nguoi.click(tieuDe)
    await waitFor(() => expect(thamSoGanNhat().sap_xep).toBeUndefined())
  })

  it('lỗi tải hiện thông báo', async () => {
    GET.mockResolvedValue(loi(500, 'LOI_HE_THONG', 'Lỗi hệ thống'))
    dung()
    expect(await screen.findByText('Không tải được danh sách thương hiệu')).toBeInTheDocument()
  })
})

describe('TrangDuLieuChung: thêm và sửa', () => {
  it('thêm thương hiệu: kiểm tra phía giao diện trước, rồi gửi body đã gọn (ô trống thành null)', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue({ data: { ...THUONG_HIEU[1], id: 3, ten: 'Mới' }, response: { ok: true, status: 201 } })
    dung()
    await screen.findByText('Sanofi')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm thương hiệu' }))
    const h = await hopThoai()
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await h.findByText('Vui lòng nhập tên')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    await nguoi.type(h.getByLabelText('Tên thương hiệu'), '  Hàng   mới ')
    await nguoi.type(h.getByLabelText(/Đường dẫn logo/), 'javascript:alert(1)')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await h.findByText(/Đường dẫn phải bắt đầu bằng/)).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    await nguoi.clear(h.getByLabelText(/Đường dẫn logo/))
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/thuong-hieu', { body: { ten: 'Hàng mới', logo_url: null } })
    expect(await screen.findByText('Đã thêm thương hiệu')).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.length).toBeGreaterThan(1)) // danh sách được tải lại
  })

  it('trùng tên: lỗi 409 gắn vào ô tên và hộp thoại vẫn mở để sửa', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'Đã có thương hiệu cùng tên', { truong: 'ten' }))
    dung()
    await screen.findByText('Sanofi')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm thương hiệu' }))
    const h = await hopThoai()
    await nguoi.type(h.getByLabelText('Tên thương hiệu'), 'SANOFI')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await h.findByText('Đã có thương hiệu cùng tên')).toBeInTheDocument()
    expect(screen.getByRole('dialog', { hidden: true })).toBeInTheDocument()
  })

  it('lỗi khác (mất mạng) hiện thông báo chung, không gắn vào ô nào', async () => {
    const nguoi = userEvent.setup()
    POST.mockRejectedValue(new TypeError('Failed to fetch'))
    dung('/du-lieu-chung?nhom=nha-san-xuat')
    await screen.findByText('Pymepharco')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm nhà sản xuất' }))
    const h = await hopThoai()
    await nguoi.type(h.getByLabelText('Tên nhà sản xuất'), 'Roche')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await screen.findByText(/Không kết nối được máy chủ/)).toBeInTheDocument()
  })

  it('sửa nhà sản xuất: ô điền sẵn, PATCH đúng id, quốc gia xóa trống gửi null', async () => {
    const nguoi = userEvent.setup()
    PATCH.mockResolvedValue({ data: NHA_SAN_XUAT[0], response: { ok: true, status: 200 } })
    GET.mockImplementation(async () => trang([{ ...NHA_SAN_XUAT[0], quoc_gia: 'Việt Nam' }]))
    dung('/du-lieu-chung?nhom=nha-san-xuat')
    const hang = await dong('Pymepharco')
    await nguoi.click(within(hang).getByRole('button', { hidden: true, name: 'Sửa' }))
    const h = await hopThoai()
    expect(h.getByLabelText('Tên nhà sản xuất')).toHaveValue('Pymepharco')
    expect(h.getByLabelText(/Quốc gia/)).toHaveValue('Việt Nam')
    await nguoi.clear(h.getByLabelText(/Quốc gia/))
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Lưu' }))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH).toHaveBeenCalledWith('/api/v1/noi-bo/nha-san-xuat/{ban_ghi_id}', {
      params: { path: { ban_ghi_id: 7 } },
      body: { ten: 'Pymepharco', quoc_gia: null },
    })
    expect(await screen.findByText('Đã lưu nhà sản xuất')).toBeInTheDocument()
  })

  it('thêm hoạt chất: mô tả nhiều dòng giữ xuống dòng, tên khác trống thành null', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue({ data: HOAT_CHAT[1], response: { ok: true, status: 201 } })
    dung('/du-lieu-chung?nhom=hoat-chat')
    await screen.findByText('Paracetamol')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm hoạt chất' }))
    const h = await hopThoai()
    await nguoi.type(h.getByLabelText('Tên hoạt chất'), 'Ibuprofen')
    await nguoi.type(h.getByLabelText(/Mô tả/), 'Dòng một{Enter}Dòng hai')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/hoat-chat', { body: { ten: 'Ibuprofen', ten_khac: null, mo_ta: 'Dòng một\nDòng hai' } })
  })
})

describe('TrangDuLieuChung: xóa', () => {
  it('thương hiệu còn sản phẩm: nút xóa bị tắt; chưa dùng thì xóa sau khi xác nhận', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValue(khongThan)
    dung()
    const dangDung = await dong('Sanofi')
    expect(within(dangDung).getByRole('button', { hidden: true, name: 'Xóa' })).toBeDisabled()
    const chuaDung = await dong('Chưa dùng')
    await nguoi.click(within(chuaDung).getByRole('button', { hidden: true, name: 'Xóa' }))
    await nguoi.click(screen.getAllByRole('button', { hidden: true, name: 'Xóa' }).at(-1)!) // nút xác nhận trong hộp xác nhận (nằm cuối DOM)
    await waitFor(() => expect(DELETE).toHaveBeenCalledTimes(1))
    expect(DELETE).toHaveBeenCalledWith('/api/v1/noi-bo/thuong-hieu/{ban_ghi_id}', { params: { path: { ban_ghi_id: 2 } } })
    expect(await screen.findByText('Đã xóa “Chưa dùng”')).toBeInTheDocument()
  })

  it('máy chủ từ chối vì đang được dùng: hiện thông điệp chung và tải lại số liệu', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValue(loi(409, 'DU_LIEU_DANG_DUOC_SU_DUNG', 'Không xóa được vì hoạt chất này đang được sử dụng trong hệ thống'))
    dung('/du-lieu-chung?nhom=hoat-chat')
    const hang = await dong('Penicillin') // 0 sản phẩm nhưng có thể nằm trong dị ứng của khách mà Admin không thấy
    const truoc = GET.mock.calls.length
    await nguoi.click(within(hang).getByRole('button', { hidden: true, name: 'Xóa' }))
    await nguoi.click(screen.getAllByRole('button', { hidden: true, name: 'Xóa' }).at(-1)!)
    expect(await screen.findByText(/đang được sử dụng trong hệ thống/)).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.length).toBeGreaterThan(truoc))
  })

  it('hoạt chất có sản phẩm vẫn để máy chủ quyết định (không tắt nút), vì còn tương tác và dị ứng không đếm được', async () => {
    dung('/du-lieu-chung?nhom=hoat-chat')
    const hang = await dong('Paracetamol')
    expect(within(hang).getByRole('button', { hidden: true, name: 'Xóa' })).toBeEnabled()
  })
})

describe('TrangDuLieuChung: quyền', () => {
  it('dược sĩ (chỉ xem) đọc được nhưng không có nút thêm, sửa, xóa', async () => {
    dung('/du-lieu-chung', 'chi_xem')
    const hang = await dong('Sanofi')
    // Không dùng `hidden: true` ở đây: hộp thoại thêm/sửa luôn nằm trong DOM (ẩn) và có nút "Thêm" của riêng nó.
    expect(within(hang).queryByRole('button')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Thêm/ })).not.toBeInTheDocument()
  })
})
