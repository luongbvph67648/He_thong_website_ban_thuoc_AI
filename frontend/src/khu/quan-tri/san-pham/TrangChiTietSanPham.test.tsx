import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import type { SanPhamChiTiet } from './sanPham'
import TrangChiTietSanPham from './TrangChiTietSanPham'

vi.setConfig({ testTimeout: 60_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
const POST = vi.fn()
const PATCH = vi.fn()
const PUT = vi.fn()
const DELETE = vi.fn()
vi.mock('../../../api/client', () => ({
  api: {
    GET: (...a: unknown[]) => GET(...a),
    POST: (...a: unknown[]) => POST(...a),
    PATCH: (...a: unknown[]) => PATCH(...a),
    PUT: (...a: unknown[]) => PUT(...a),
    DELETE: (...a: unknown[]) => DELETE(...a),
  },
}))

const ok = (data: unknown, status = 200) => ({ data, response: { ok: true, status } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })
const khongThan = { response: { ok: true, status: 204 } }

const nut = (id: number, ten: string, con: unknown[] = []) => ({ id, ten, slug: `dm-${id}`, danh_muc_cha_id: null, anh_url: null, thu_tu: id, dang_hien_thi: true, cap: 1, so_san_pham: 0, con })
const CAY = [nut(1, 'Thuốc', [{ ...nut(3, 'Giảm đau'), cap: 2, danh_muc_cha_id: 1 }]), nut(2, 'Dụng cụ')]
const THUONG_HIEU = [{ id: 7, ten: 'Hậu Giang', logo_url: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 1 }]
const HOAT_CHAT = [
  { id: 9, ten: 'Paracetamol', ten_khac: null, mo_ta: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 1 },
  { id: 10, ten: 'Caffeine', ten_khac: null, mo_ta: null, created_at: '2026-10-01T03:00:00Z', so_san_pham: 0 },
]
const trang = (du_lieu: unknown[]) => ok({ du_lieu, tong: du_lieu.length, trang: 1, kich_thuoc: 20 })

const SAN_PHAM = (ghiDe: Partial<SanPhamChiTiet> = {}): SanPhamChiTiet => ({
  id: 5,
  sku: 'PARA500',
  ten: 'Paracetamol 500mg',
  slug: 'paracetamol-500mg',
  loai_san_pham: 'thuoc_khong_ke_don',
  danh_muc_id: 3,
  ten_danh_muc: 'Giảm đau',
  thuong_hieu_id: 7,
  ten_thuong_hieu: 'Hậu Giang',
  nha_san_xuat_id: null,
  ten_nha_san_xuat: null,
  so_dang_ky: null,
  dang_bao_che: 'Viên nén',
  quy_cach: null,
  doi_tuong_su_dung: null,
  don_vi_co_so: 'Viên',
  ton_toi_thieu: 20,
  dung_dinh_ky: false,
  so_ngay_dung_moi_don_vi: null,
  so_luong_toi_da_moi_don: null,
  la_noi_bat: false,
  trang_thai: 'dang_kinh_doanh',
  created_at: '2026-10-01T03:00:00Z',
  updated_at: null,
  don_vi: [
    { id: 21, ten_don_vi: 'Viên', he_so: 1, gia_ban: '1000.00', ban_online: true, la_mac_dinh: false, ma_vach: null },
    { id: 22, ten_don_vi: 'Hộp', he_so: 100, gia_ban: '90000.00', ban_online: true, la_mac_dinh: true, ma_vach: '893001' },
  ],
  thanh_phan: [{ hoat_chat_id: 9, ten_hoat_chat: 'Paracetamol', ham_luong: '500 mg' }],
  anh: [
    { id: 31, url: '/api/v1/tep/san-pham/a.jpg', thu_tu: 0, la_anh_chinh: true },
    { id: 32, url: '/api/v1/tep/san-pham/b.png', thu_tu: 1, la_anh_chinh: false },
  ],
  phien_ban: 'aaaaaaaaaaaaaaaa',
  ...ghiDe,
})

function ViTri() {
  const v = useLocation()
  return <div data-testid="vitri">{v.pathname}</div>
}

function dung(duong: string, quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'product.commercial.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path="/quan-tri/san-pham" element={<div>DANH SÁCH SẢN PHẨM</div>} />
              <Route path="/quan-tri/san-pham/moi" element={<TrangChiTietSanPham />} />
              <Route path="/quan-tri/san-pham/:id" element={<TrangChiTietSanPham />} />
            </Routes>
            <ViTri />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

let hienTai: SanPhamChiTiet
const lanGoi = (m: ReturnType<typeof vi.fn>, duong: string) => m.mock.calls.filter((c) => c[0] === duong)

beforeEach(() => {
  for (const m of [GET, POST, PATCH, PUT, DELETE]) m.mockReset()
  hienTai = SAN_PHAM()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/danh-muc') return ok(CAY)
    if (duong === '/api/v1/noi-bo/thuong-hieu') return trang(THUONG_HIEU)
    if (duong === '/api/v1/noi-bo/nha-san-xuat') return trang([])
    if (duong === '/api/v1/noi-bo/hoat-chat') return trang(HOAT_CHAT)
    if (duong === '/api/v1/noi-bo/san-pham/{san_pham_id}') return ok(hienTai)
    throw new Error(`GET chưa giả lập: ${duong}`)
  })
})

/** Mở ô chọn có nhãn `nhan` rồi chọn dòng `chu`. */
async function chon(nguoi: ReturnType<typeof userEvent.setup>, nhan: string, chu: string) {
  await nguoi.click(screen.getByLabelText(nhan))
  const dong = await screen.findAllByText(chu)
  await nguoi.click(dong.find((d) => d.closest('.ant-select-dropdown, .ant-tree-select-dropdown')) ?? dong[0])
}

/** Nút theo chữ hiển thị (tra theo vai trò chậm trong antd + jsdom, xem frontend/CLAUDE.md). */
const nutChu = (chu: string, khung: HTMLElement | typeof document.body = document.body) => {
  const el = within(khung as HTMLElement).getAllByText(chu).map((e) => e.closest('button')).find(Boolean)
  if (!el) throw new Error(`Không có nút "${chu}"`)
  return el as HTMLButtonElement
}

describe('Thêm sản phẩm (/san-pham/moi)', () => {
  it('bấm lưu khi form trống: báo lỗi từng ô và không gọi máy chủ', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/moi')
    await nguoi.click(nutChu('Thêm sản phẩm'))
    expect(await screen.findByText('Vui lòng nhập SKU')).toBeInTheDocument()
    expect(screen.getAllByText('Vui lòng nhập tên')).toHaveLength(2) // tên sản phẩm và tên đơn vị cơ sở
    expect(screen.getByText('Vui lòng chọn loại sản phẩm')).toBeInTheDocument()
    expect(screen.getByText('Vui lòng chọn danh mục')).toBeInTheDocument()
    expect(screen.getByText('Còn thông tin chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('điền đủ rồi lưu: một POST chứa thông tin, đơn vị, thành phần; sau đó chuyển tới trang sửa của sản phẩm mới', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(ok(SAN_PHAM({ id: 77 }), 201))
    dung('/quan-tri/san-pham/moi')
    await nguoi.type(screen.getByLabelText('SKU'), ' para-1 ')
    await nguoi.type(screen.getByLabelText('Tên sản phẩm'), '  Thuốc   mới ')
    await chon(nguoi, 'Loại sản phẩm', 'Thuốc không kê đơn')
    await chon(nguoi, 'Danh mục', 'Giảm đau')
    await chon(nguoi, 'Thương hiệu', 'Hậu Giang')
    await nguoi.type(screen.getByLabelText('Tên đơn vị 1'), 'Viên')
    await nguoi.type(screen.getByLabelText('Giá bán đơn vị 1'), '1500')
    await nguoi.click(nutChu('Thêm đơn vị'))
    await nguoi.type(screen.getByLabelText('Tên đơn vị 2'), 'Hộp')
    await nguoi.type(screen.getByLabelText('Hệ số đơn vị 2'), '100')
    await nguoi.type(screen.getByLabelText('Giá bán đơn vị 2'), '140000')
    await nguoi.click(screen.getByLabelText('Mặc định đơn vị 2'))
    await nguoi.click(nutChu('Thêm thành phần'))
    await chon(nguoi, 'Hoạt chất thành phần 1', 'Paracetamol')
    await nguoi.type(screen.getByLabelText('Hàm lượng thành phần 1'), ' 500 mg ')
    await nguoi.click(nutChu('Thêm sản phẩm'))

    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    const [duong, tham] = POST.mock.calls[0]
    expect(duong).toBe('/api/v1/noi-bo/san-pham')
    expect(tham.body).toMatchObject({
      sku: 'PARA-1',
      ten: 'Thuốc mới',
      loai_san_pham: 'thuoc_khong_ke_don',
      danh_muc_id: 3,
      thuong_hieu_id: 7,
      nha_san_xuat_id: null,
      ton_toi_thieu: 0,
      dung_dinh_ky: false,
      so_ngay_dung_moi_don_vi: null,
      la_noi_bat: false,
      trang_thai: 'dang_kinh_doanh',
    })
    expect(tham.body.don_vi).toEqual([
      { ten_don_vi: 'Viên', he_so: 1, gia_ban: '1500', ban_online: true, la_mac_dinh: false, ma_vach: null },
      { ten_don_vi: 'Hộp', he_so: 100, gia_ban: '140000', ban_online: true, la_mac_dinh: true, ma_vach: null },
    ])
    expect(tham.body.thanh_phan).toEqual([{ hoat_chat_id: 9, ham_luong: '500 mg' }])
    await waitFor(() => expect(screen.getByTestId('vitri')).toHaveTextContent('/quan-tri/san-pham/77')) // giữ tiền tố khu, không bật ra cửa hàng
  })

  it('chọn thuốc kê đơn: hiện cảnh báo, tắt và bỏ "nổi bật"', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/moi')
    await nguoi.click(screen.getByLabelText('Sản phẩm nổi bật'))
    expect(screen.getByLabelText('Sản phẩm nổi bật')).toBeChecked()
    await chon(nguoi, 'Loại sản phẩm', 'Thuốc kê đơn')
    expect(await screen.findByText(/không vào giỏ hàng, không giảm giá/)).toBeInTheDocument()
    expect(screen.getByLabelText('Sản phẩm nổi bật')).not.toBeChecked()
    expect(screen.getByLabelText('Sản phẩm nổi bật')).toBeDisabled()
  })

  it('máy chủ báo SKU trùng và mã vạch trùng: lỗi hiện ở đúng ô, dữ liệu đã nhập còn nguyên', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(
      loi(409, 'TRUNG_DU_LIEU', 'Mã vạch đã dùng cho sản phẩm khác', { truong: 'don_vi.0.ma_vach' }),
    )
    dung('/quan-tri/san-pham/moi')
    await nguoi.type(screen.getByLabelText('SKU'), 'abc')
    await nguoi.type(screen.getByLabelText('Tên sản phẩm'), 'Thuốc A')
    await chon(nguoi, 'Loại sản phẩm', 'Thuốc không kê đơn')
    await chon(nguoi, 'Danh mục', 'Dụng cụ')
    await nguoi.type(screen.getByLabelText('Tên đơn vị 1'), 'Cái')
    await nguoi.type(screen.getByLabelText('Giá bán đơn vị 1'), '1000')
    await nguoi.click(nutChu('Thêm sản phẩm'))
    expect(await screen.findByText('Mã vạch đã dùng cho sản phẩm khác')).toBeInTheDocument()
    expect(screen.getByLabelText('SKU')).toHaveValue('abc')
    expect(screen.getByLabelText('Tên sản phẩm')).toHaveValue('Thuốc A')
    expect(screen.getByTestId('vitri')).toHaveTextContent('/quan-tri/san-pham/moi')

    POST.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'SKU đã tồn tại', { truong: 'sku' }))
    await nguoi.click(nutChu('Thêm sản phẩm'))
    expect(await screen.findByText('SKU đã tồn tại')).toBeInTheDocument()
    await nguoi.type(screen.getByLabelText('SKU'), 'x') // sửa ô thì lỗi của ô đó mất
    await waitFor(() => expect(screen.queryByText('SKU đã tồn tại')).not.toBeInTheDocument())
  })

  it('chỉ xem: trang tạo hiện 403, không có form', async () => {
    dung('/quan-tri/san-pham/moi', 'chi_xem')
    expect(await screen.findByText(/403|không có quyền/i)).toBeInTheDocument()
    expect(screen.queryByLabelText('SKU')).not.toBeInTheDocument()
  })
})

describe('Sửa sản phẩm (/san-pham/:id)', () => {
  it('hiện đầu trang và điền sẵn form từ máy chủ, kể cả tên thương hiệu', async () => {
    dung('/quan-tri/san-pham/5')
    expect(await screen.findByRole('heading', { name: 'Paracetamol 500mg' })).toBeInTheDocument()
    expect(screen.getByLabelText('SKU')).toHaveValue('PARA500')
    expect(screen.getByLabelText('Dạng bào chế')).toHaveValue('Viên nén')
    expect(screen.getByLabelText('Tồn tối thiểu (đơn vị cơ sở)')).toHaveValue('20')
    expect(screen.getByText('Hậu Giang')).toBeInTheDocument()
    expect(screen.getByText('Giảm đau')).toBeInTheDocument()
    expect(lanGoi(GET, '/api/v1/noi-bo/san-pham/{san_pham_id}')[0][1]).toEqual({ params: { path: { san_pham_id: 5 } } })
  })

  it('không có thay đổi thì không gọi máy chủ; có thay đổi thì PATCH chỉ chứa trường đã đổi cùng phien_ban', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(nutChu('Lưu thông tin'))
    expect(await screen.findByText('Chưa có thay đổi nào để lưu')).toBeInTheDocument()
    expect(PATCH).not.toHaveBeenCalled()

    PATCH.mockResolvedValue(ok(SAN_PHAM({ ten: 'Paracetamol 650mg', phien_ban: 'bbbbbbbbbbbbbbbb' })))
    const ten = screen.getByLabelText('Tên sản phẩm')
    await nguoi.clear(ten)
    await nguoi.type(ten, 'Paracetamol 650mg')
    await nguoi.clear(screen.getByLabelText('Dạng bào chế'))
    await nguoi.click(nutChu('Lưu thông tin'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH.mock.calls[0][0]).toBe('/api/v1/noi-bo/san-pham/{san_pham_id}')
    expect(PATCH.mock.calls[0][1]).toEqual({
      params: { path: { san_pham_id: 5 } },
      body: { phien_ban: 'aaaaaaaaaaaaaaaa', ten: 'Paracetamol 650mg', dang_bao_che: null },
    })
    expect(await screen.findByText('Đã lưu thông tin sản phẩm')).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: 'Paracetamol 650mg' })).toBeInTheDocument() // bản trả về thay vào trang
  })

  it('xung đột phiên bản: tải bản mới nhưng giữ chữ đang gõ; lưu lại dùng phien_ban mới', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    PATCH.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Dữ liệu đã bị người khác thay đổi', { phien_ban_hien_tai: 'cccccccccccccccc' }))
    hienTai = SAN_PHAM({ quy_cach: 'Hộp 10 vỉ', phien_ban: 'cccccccccccccccc' }) // người khác vừa đổi trường khác
    const ten = screen.getByLabelText('Tên sản phẩm')
    await nguoi.clear(ten)
    await nguoi.type(ten, 'Tên tôi gõ')
    await nguoi.click(nutChu('Lưu thông tin'))
    expect(await screen.findByText(/Sản phẩm vừa được người khác thay đổi/)).toBeInTheDocument()
    expect(screen.getByLabelText('Tên sản phẩm')).toHaveValue('Tên tôi gõ')
    expect(lanGoi(GET, '/api/v1/noi-bo/san-pham/{san_pham_id}').length).toBe(2) // đã tải lại

    PATCH.mockResolvedValueOnce(ok(SAN_PHAM({ ten: 'Tên tôi gõ', quy_cach: 'Hộp 10 vỉ', phien_ban: 'dddddddddddddddd' })))
    await nguoi.click(nutChu('Lưu thông tin'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(2))
    expect(PATCH.mock.calls[1][1].body).toEqual({ phien_ban: 'cccccccccccccccc', ten: 'Tên tôi gõ' }) // không ghi đè quy cách của người kia
  })

  it('không tự tải lại chi tiết khi cửa sổ được focus lại (phien_ban phải là bản người dùng đã thấy)', async () => {
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    window.dispatchEvent(new Event('visibilitychange'))
    window.dispatchEvent(new Event('focus'))
    await new Promise((r) => setTimeout(r, 50))
    expect(lanGoi(GET, '/api/v1/noi-bo/san-pham/{san_pham_id}').length).toBe(1)
  })

  it('đổi sang thuốc kê đơn khi đang nổi bật: PATCH gồm cả loai_san_pham và la_noi_bat = false', async () => {
    const nguoi = userEvent.setup()
    hienTai = SAN_PHAM({ la_noi_bat: true })
    PATCH.mockResolvedValue(ok(SAN_PHAM({ loai_san_pham: 'thuoc_ke_don', la_noi_bat: false, phien_ban: 'bbbbbbbbbbbbbbbb' })))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await chon(nguoi, 'Loại sản phẩm', 'Thuốc kê đơn')
    await nguoi.click(nutChu('Lưu thông tin'))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH.mock.calls[0][1].body).toEqual({ phien_ban: 'aaaaaaaaaaaaaaaa', loai_san_pham: 'thuoc_ke_don', la_noi_bat: false })
  })

  it('máy chủ từ chối một trường: lỗi gắn vào ô đó', async () => {
    const nguoi = userEvent.setup()
    PATCH.mockResolvedValue(loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'so_luong_toi_da_moi_don', loi: 'Phải từ 1 trở lên' }]))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.type(screen.getByLabelText('Số lượng tối đa mỗi đơn'), '5')
    await nguoi.click(nutChu('Lưu thông tin'))
    expect(await screen.findByText('Phải từ 1 trở lên')).toBeInTheDocument()
  })

  it('không tìm thấy hoặc id sai định dạng: hiện trang không tìm thấy, id sai không gọi máy chủ', async () => {
    GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/san-pham/{san_pham_id}' ? loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy') : ok(CAY)))
    const { unmount } = dung('/quan-tri/san-pham/999')
    expect(await screen.findByText('Không tìm thấy sản phẩm')).toBeInTheDocument()
    unmount()
    GET.mockClear()
    dung('/quan-tri/san-pham/abc')
    expect(await screen.findByText('Không tìm thấy sản phẩm')).toBeInTheDocument()
    expect(lanGoi(GET, '/api/v1/noi-bo/san-pham/{san_pham_id}')).toHaveLength(0)
  })

  it('xóa sản phẩm: xác nhận, DELETE kèm phien_ban rồi về danh sách; còn tồn kho thì báo và ở lại', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValueOnce(loi(409, 'SAN_PHAM_CON_TON_KHO', 'Sản phẩm còn 30 viên trong kho'))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(nutChu('Xóa sản phẩm'))
    await nguoi.click(await screen.findByText('Xóa sản phẩm', { selector: '.ant-popconfirm .ant-btn span, .ant-popover .ant-btn span' }))
    expect(await screen.findByText('Sản phẩm còn 30 viên trong kho')).toBeInTheDocument()
    expect(screen.getByTestId('vitri')).toHaveTextContent('/quan-tri/san-pham/5')

    DELETE.mockResolvedValueOnce(khongThan)
    await nguoi.click(nutChu('Xóa sản phẩm'))
    await nguoi.click(await screen.findByText('Xóa sản phẩm', { selector: '.ant-popconfirm .ant-btn span, .ant-popover .ant-btn span' }))
    expect(await screen.findByText('DANH SÁCH SẢN PHẨM')).toBeInTheDocument()
    expect(DELETE.mock.calls[1]).toEqual(['/api/v1/noi-bo/san-pham/{san_pham_id}', { params: { path: { san_pham_id: 5 }, query: { phien_ban: 'aaaaaaaaaaaaaaaa' } } }])
  })

  it('chỉ xem: hiện dữ liệu nhưng không có nút lưu, xóa, tải ảnh; ô nhập bị tắt', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5', 'chi_xem')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    expect(screen.queryByText('Lưu thông tin')).not.toBeInTheDocument()
    expect(screen.queryByText('Xóa sản phẩm')).not.toBeInTheDocument()
    expect(screen.getByLabelText('SKU')).toBeDisabled()
    await nguoi.click(screen.getByRole('tab', { name: 'Ảnh (2)' }))
    expect(await screen.findByAltText('Ảnh 1 của Paracetamol 500mg')).toBeInTheDocument()
    expect(screen.queryByText('Tải ảnh lên')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Xóa ảnh 1')).not.toBeInTheDocument()
  })
})

describe('Tab Đơn vị và giá', () => {
  it('lưu cả danh sách bằng PUT kèm phien_ban; giá là chuỗi số nguyên, id đơn vị được giữ', async () => {
    const nguoi = userEvent.setup()
    PUT.mockResolvedValue(ok(SAN_PHAM({ phien_ban: 'bbbbbbbbbbbbbbbb' })))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Đơn vị và giá' }))
    const gia = await screen.findByLabelText('Giá bán đơn vị 2')
    fireEvent.change(gia, { target: { value: '95000' } })
    await nguoi.click(nutChu('Lưu đơn vị'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0][0]).toBe('/api/v1/noi-bo/san-pham/{san_pham_id}/don-vi')
    expect(PUT.mock.calls[0][1]).toEqual({
      params: { path: { san_pham_id: 5 } },
      body: {
        phien_ban: 'aaaaaaaaaaaaaaaa',
        don_vi: [
          { id: 21, ten_don_vi: 'Viên', he_so: 1, gia_ban: '1000', ban_online: true, la_mac_dinh: false, ma_vach: null },
          { id: 22, ten_don_vi: 'Hộp', he_so: 100, gia_ban: '95000', ban_online: true, la_mac_dinh: true, ma_vach: '893001' },
        ],
      },
    })
    expect(await screen.findByText('Đã lưu đơn vị và giá bán')).toBeInTheDocument()
  })

  it('hai đơn vị cơ sở bị chặn ở giao diện; mã vạch trùng do máy chủ báo hiện ở đúng dòng', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Đơn vị và giá' }))
    fireEvent.change(await screen.findByLabelText('Hệ số đơn vị 2'), { target: { value: '1' } })
    await nguoi.click(nutChu('Lưu đơn vị'))
    expect(await screen.findByText('Phải có đúng một đơn vị cơ sở (hệ số 1)')).toBeInTheDocument()
    expect(PUT).not.toHaveBeenCalled()

    fireEvent.change(screen.getByLabelText('Hệ số đơn vị 2'), { target: { value: '100' } })
    PUT.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'Mã vạch 893001 đã dùng cho sản phẩm khác', { truong: 'don_vi.1.ma_vach' }))
    await nguoi.click(nutChu('Lưu đơn vị'))
    const loiMaVach = await screen.findByText('Mã vạch 893001 đã dùng cho sản phẩm khác')
    expect(loiMaVach.closest('tr')).toContainElement(screen.getByLabelText('Mã vạch đơn vị 2'))
  })

  it('đơn vị đang được tham chiếu không xóa được: hiện thông điệp của máy chủ, dữ liệu đang sửa còn nguyên', async () => {
    const nguoi = userEvent.setup()
    PUT.mockResolvedValue(loi(409, 'DU_LIEU_DANG_DUOC_SU_DUNG', 'Đơn vị Hộp đang được dùng trong đơn hàng'))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Đơn vị và giá' }))
    await nguoi.click(await screen.findByLabelText('Xóa đơn vị 2'))
    expect(screen.queryByLabelText('Tên đơn vị 2')).not.toBeInTheDocument()
    await nguoi.click(nutChu('Lưu đơn vị'))
    expect(await screen.findByText('Đơn vị Hộp đang được dùng trong đơn hàng')).toBeInTheDocument()
    expect(screen.queryByLabelText('Tên đơn vị 2')).not.toBeInTheDocument()
  })
})

describe('Tab Thành phần', () => {
  it('hiện thành phần hiện có; thêm dòng chưa chọn hoạt chất bị chặn, chọn xong lưu bằng PUT', async () => {
    const nguoi = userEvent.setup()
    PUT.mockResolvedValue(ok(SAN_PHAM({ phien_ban: 'bbbbbbbbbbbbbbbb' })))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Thành phần' }))
    expect(await screen.findByDisplayValue('500 mg')).toBeInTheDocument()
    await nguoi.click(nutChu('Thêm thành phần'))
    await nguoi.click(nutChu('Lưu thành phần'))
    expect(await screen.findByText('Chọn một hoạt chất')).toBeInTheDocument() // dòng mới chưa chọn
    expect(PUT).not.toHaveBeenCalled()
    await chon(nguoi, 'Hoạt chất thành phần 2', 'Caffeine')
    await nguoi.type(screen.getByLabelText('Hàm lượng thành phần 2'), '65 mg')
    await nguoi.click(nutChu('Lưu thành phần'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0][1]).toEqual({
      params: { path: { san_pham_id: 5 } },
      body: {
        phien_ban: 'aaaaaaaaaaaaaaaa',
        thanh_phan: [
          { hoat_chat_id: 9, ham_luong: '500 mg' },
          { hoat_chat_id: 10, ham_luong: '65 mg' },
        ],
      },
    })
  })

  it('chọn trùng hoạt chất bị chặn ở giao diện', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Thành phần' }))
    await nguoi.click(await screen.findByText('Thêm thành phần'))
    await chon(nguoi, 'Hoạt chất thành phần 2', 'Paracetamol')
    await nguoi.click(nutChu('Lưu thành phần'))
    expect(await screen.findByText('Mỗi hoạt chất chỉ được xuất hiện một lần')).toBeInTheDocument()
    expect(PUT).not.toHaveBeenCalled()
  })

  it('xóa thành phần rồi lưu gửi danh sách rỗng', async () => {
    const nguoi = userEvent.setup()
    PUT.mockResolvedValue(ok(SAN_PHAM({ thanh_phan: [], phien_ban: 'bbbbbbbbbbbbbbbb' })))
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Thành phần' }))
    await nguoi.click(await screen.findByLabelText('Xóa thành phần 1'))
    await nguoi.click(nutChu('Lưu thành phần'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0][1]).toEqual({ params: { path: { san_pham_id: 5 } }, body: { phien_ban: 'aaaaaaaaaaaaaaaa', thanh_phan: [] } })
  })
})

describe('Tab Ảnh', () => {
  const moTab = async (nguoi: ReturnType<typeof userEvent.setup>) => {
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Ảnh (2)' }))
    await screen.findByAltText('Ảnh 1 của Paracetamol 500mg')
  }

  it('hiện ảnh theo thứ tự và đánh dấu ảnh chính; chuyển, đặt ảnh chính, xóa đều gửi phien_ban đã thấy', async () => {
    const nguoi = userEvent.setup()
    dung('/quan-tri/san-pham/5')
    await moTab(nguoi)
    expect(screen.getAllByText('Ảnh chính')).toHaveLength(1)
    expect(screen.getByLabelText('Chuyển ảnh 1 lên')).toBeDisabled()
    expect(screen.getByLabelText('Chuyển ảnh 2 xuống')).toBeDisabled()

    PUT.mockResolvedValueOnce(ok(SAN_PHAM({ anh: [hienTai.anh[1], hienTai.anh[0]], phien_ban: 'bbbbbbbbbbbbbbbb' })))
    await nguoi.click(screen.getByLabelText('Chuyển ảnh 1 xuống'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT.mock.calls[0]).toEqual(['/api/v1/noi-bo/san-pham/{san_pham_id}/anh/thu-tu', { params: { path: { san_pham_id: 5 } }, body: { phien_ban: 'aaaaaaaaaaaaaaaa', ids: [32, 31] } }])

    PUT.mockResolvedValueOnce(ok(SAN_PHAM({ phien_ban: 'cccccccccccccccc' })))
    await nguoi.click(await screen.findByLabelText('Đặt ảnh 1 làm ảnh chính'))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(2))
    expect(PUT.mock.calls[1]).toEqual(['/api/v1/noi-bo/san-pham/{san_pham_id}/anh/{anh_id}/chinh', { params: { path: { san_pham_id: 5, anh_id: 32 } }, body: { phien_ban: 'bbbbbbbbbbbbbbbb' } }])

    DELETE.mockResolvedValueOnce(ok(SAN_PHAM({ anh: [hienTai.anh[0]], phien_ban: 'dddddddddddddddd' })))
    await nguoi.click(await screen.findByLabelText('Xóa ảnh 2'))
    await nguoi.click(await screen.findByText('Xóa', { selector: '.ant-popconfirm .ant-btn span, .ant-popover .ant-btn span' }))
    await waitFor(() => expect(DELETE).toHaveBeenCalledTimes(1))
    expect(DELETE.mock.calls[0]).toEqual(['/api/v1/noi-bo/san-pham/{san_pham_id}/anh/{anh_id}', { params: { path: { san_pham_id: 5, anh_id: 32 }, query: { phien_ban: 'cccccccccccccccc' } } }])
  })

  it('tải ảnh lên: gửi multipart có trường tep và phien_ban ở query; tệp sai loại hoặc quá lớn bị chặn ngay', async () => {
    const nguoi = userEvent.setup({ applyAccept: false })
    dung('/quan-tri/san-pham/5')
    await moTab(nguoi)
    const o = screen.getByLabelText('Chọn ảnh để tải lên') as HTMLInputElement

    await nguoi.upload(o, new File(['x'], 'ghi-chu.txt', { type: 'text/plain' }))
    expect(await screen.findByText('ghi-chu.txt: Chỉ nhận ảnh JPEG, PNG hoặc WebP')).toBeInTheDocument()
    const lon = new File(['x'], 'lon.png', { type: 'image/png' })
    Object.defineProperty(lon, 'size', { value: 5 * 1024 * 1024 + 1 })
    await nguoi.upload(o, lon)
    expect(await screen.findByText('lon.png: Ảnh tối đa 5 MB')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()

    POST.mockResolvedValue(ok(SAN_PHAM({ phien_ban: 'bbbbbbbbbbbbbbbb' }), 201))
    const tep = new File([new Uint8Array([0xff, 0xd8, 0xff])], 'anh.jpg', { type: 'image/jpeg' })
    await nguoi.upload(o, tep)
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    const [duong, tham] = POST.mock.calls[0]
    expect(duong).toBe('/api/v1/noi-bo/san-pham/{san_pham_id}/anh')
    expect(tham.params).toEqual({ path: { san_pham_id: 5 }, query: { phien_ban: 'aaaaaaaaaaaaaaaa' } })
    const form = tham.bodySerializer() as FormData
    expect(form).toBeInstanceOf(FormData)
    expect((form.get('tep') as File).name).toBe('anh.jpg')
    expect(await screen.findByText('Đã tải ảnh lên')).toBeInTheDocument()
  })

  it('máy chủ từ chối ảnh (quá lớn, sai định dạng thật): hiện thông điệp của máy chủ', async () => {
    const nguoi = userEvent.setup({ applyAccept: false })
    POST.mockResolvedValue(loi(413, 'TEP_QUA_LON', 'Ảnh vượt quá 5 MB'))
    dung('/quan-tri/san-pham/5')
    await moTab(nguoi)
    await nguoi.upload(screen.getByLabelText('Chọn ảnh để tải lên'), new File(['x'], 'a.jpg', { type: 'image/jpeg' }))
    expect(await screen.findByText('Ảnh vượt quá 5 MB')).toBeInTheDocument()
  })

  it('đủ 20 ảnh thì tắt nút tải lên; xung đột phiên bản báo thử lại và tải bản mới', async () => {
    const nguoi = userEvent.setup()
    hienTai = SAN_PHAM({ anh: Array.from({ length: 20 }, (_, i) => ({ id: 100 + i, url: `/api/v1/tep/san-pham/${i}.jpg`, thu_tu: i, la_anh_chinh: i === 0 })) })
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Ảnh (20)' }))
    await screen.findByAltText('Ảnh 1 của Paracetamol 500mg')
    expect(nutChu('Tải ảnh lên')).toBeDisabled()

    PUT.mockResolvedValue(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Dữ liệu đã bị người khác thay đổi'))
    await nguoi.click(screen.getByLabelText('Chuyển ảnh 1 xuống'))
    expect(await screen.findByText(/Đã tải bản mới, hãy thử lại thao tác/)).toBeInTheDocument()
    expect(lanGoi(GET, '/api/v1/noi-bo/san-pham/{san_pham_id}').length).toBe(2)
  })

  it('sản phẩm chưa có ảnh', async () => {
    const nguoi = userEvent.setup()
    hienTai = SAN_PHAM({ anh: [] })
    dung('/quan-tri/san-pham/5')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'Ảnh (0)' }))
    expect(await screen.findByText('Sản phẩm chưa có ảnh.')).toBeInTheDocument()
  })
})
