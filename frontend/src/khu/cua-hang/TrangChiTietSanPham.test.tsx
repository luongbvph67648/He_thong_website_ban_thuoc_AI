import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { act } from '@testing-library/react'
import { usePhien } from '../../stores/phien'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { chiTiet, loi, ok, the } from '../../test/cuaHang'
import { renderTai } from '../../test/render'

vi.setConfig({ testTimeout: 60_000 })

const GET = vi.fn()
vi.mock('../../api/client', async (goc) => ({
  ...(await goc<typeof import('../../api/client')>()),
  api: { GET: (...a: unknown[]) => GET(...a), POST: vi.fn() },
}))

function dapUng(sp: () => unknown) {
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/danh-muc') return ok([])
    if (duong === '/api/v1/san-pham/{slug}') return sp()
    throw new Error(`Chưa giả lập ${duong}`)
  })
}
const lanGoiChiTiet = () => GET.mock.calls.filter((c) => c[0] === '/api/v1/san-pham/{slug}')
beforeEach(() => {
  GET.mockReset()
  localStorage.clear()
  usePhien.setState({ daKhoiPhuc: true })
})

describe('TrangChiTietSanPham: sản phẩm thường', () => {
  it('hiện tên, đường dẫn, giá theo đơn vị mặc định; đổi đơn vị đổi giá và tình trạng còn hàng', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg')
    expect(await screen.findByRole('heading', { name: 'Paracetamol 500mg', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Giảm đau' })).toHaveAttribute('href', '/danh-muc/giam-dau')
    expect(screen.getByLabelText('Giá')).toHaveTextContent('9.000 ₫')
    expect(screen.getByLabelText('Giá')).toHaveTextContent('/ vỉ')
    expect(screen.getByText('Còn hàng')).toBeInTheDocument()
    const u = userEvent.setup()
    await u.click(screen.getByText('hộp'))
    expect(screen.getByLabelText('Giá')).toHaveTextContent('80.000 ₫')
    expect(screen.getByText('Hết hàng')).toBeInTheDocument() // hộp cần 100 viên mà kho không đủ
    expect(screen.getByText(/1 hộp = 100 viên/)).toBeInTheDocument()
    await u.click(screen.getByText('viên'))
    expect(screen.getByLabelText('Giá')).toHaveTextContent('1.000 ₫')
    expect(screen.getByText('Còn hàng')).toBeInTheDocument()
  })

  it('không có nút "Cần tư vấn"; nút Thêm vào giỏ bị khóa vì giỏ hàng chưa mở', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg')
    const nut = (await screen.findByText('Thêm vào giỏ')).closest('button') as HTMLButtonElement
    expect(nut).toBeDisabled()
    expect(screen.queryByText('Cần tư vấn từ dược sĩ')).not.toBeInTheDocument()
  })

  it('đổi sang sản phẩm khác không giữ đơn vị đã chọn của sản phẩm trước', async () => {
    dapUng(() => ok(chiTiet()))
    const { router } = renderTai('/san-pham/paracetamol-500mg')
    await userEvent.setup().click(await screen.findByText('hộp'))
    dapUng(() => ok(chiTiet({ id: 9, slug: 'khac', ten: 'Sản phẩm khác' })))
    await router.navigate('/san-pham/khac')
    expect(await screen.findByRole('heading', { name: 'Sản phẩm khác', level: 1 })).toBeInTheDocument()
    expect(screen.getByLabelText('Giá')).toHaveTextContent('9.000 ₫')
  })

  it('tab thông tin, thành phần và nội dung chuyên môn đã duyệt; mục trống không hiện', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg', level: 1 })
    const u = userEvent.setup()
    expect(screen.getByText('VD-1234-20')).toBeInTheDocument()
    expect(screen.getByText('Hậu Giang')).toBeInTheDocument()
    await u.click(screen.getByRole('tab', { name: 'Thành phần' }))
    expect(await screen.findByText('500mg')).toBeInTheDocument()
    await u.click(screen.getByRole('tab', { name: 'Chỉ định, liều dùng' }))
    expect(await screen.findByRole('region', { name: 'Chỉ định' })).toHaveTextContent('Giảm đau, hạ sốt')
    expect(screen.getByRole('region', { name: 'Chống chỉ định' })).toBeInTheDocument()
    expect(screen.getByRole('region', { name: 'Bảo quản' })).toBeInTheDocument()
    expect(screen.queryByRole('region', { name: 'Tác dụng phụ' })).not.toBeInTheDocument()
    expect(screen.getByText(/bản 2, duyệt 10\/10\/2026/)).toBeInTheDocument()
  })

  it('chưa có nội dung chuyên môn đã duyệt thì nói rõ, không bịa nội dung', async () => {
    dapUng(() => ok(chiTiet({ noi_dung_chuyen_mon: null })))
    renderTai('/san-pham/paracetamol-500mg')
    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Chỉ định, liều dùng' }))
    expect(await screen.findByText('Nội dung chuyên môn đang được dược sĩ biên soạn')).toBeInTheDocument()
  })

  it('liên kết hướng dẫn sử dụng: chỉ nhận đường dẫn an toàn', async () => {
    const nd = chiTiet().noi_dung_chuyen_mon!
    dapUng(() => ok(chiTiet({ noi_dung_chuyen_mon: { ...nd, file_hdsd_url: 'https://example.com/hdsd.pdf' } })))
    renderTai('/san-pham/paracetamol-500mg')
    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Chỉ định, liều dùng' }))
    const lienKet = await screen.findByRole('link', { name: 'Tải hướng dẫn sử dụng' })
    expect(lienKet).toHaveAttribute('href', 'https://example.com/hdsd.pdf')
    expect(lienKet).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('liên kết hướng dẫn nguy hiểm bị bỏ', async () => {
    const nd = chiTiet().noi_dung_chuyen_mon!
    dapUng(() => ok(chiTiet({ noi_dung_chuyen_mon: { ...nd, file_hdsd_url: 'javascript:alert(1)' } })))
    renderTai('/san-pham/paracetamol-500mg')
    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Chỉ định, liều dùng' }))
    await screen.findByRole('region', { name: 'Chỉ định' })
    expect(screen.queryByRole('link', { name: 'Tải hướng dẫn sử dụng' })).not.toBeInTheDocument()
  })

  it('chọn ảnh trong thư viện', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg')
    const lon = (await screen.findAllByAltText('Paracetamol 500mg'))[0] as HTMLImageElement
    expect(lon).toHaveAttribute('src', '/api/v1/tep/san-pham/a.jpg')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Xem ảnh 2' }))
    expect(screen.getAllByAltText('Paracetamol 500mg')[0]).toHaveAttribute('src', '/api/v1/tep/san-pham/b.jpg')
  })

  it('sản phẩm tương tự, kèm nguồn xem', async () => {
    dapUng(() => ok(chiTiet({ tuong_tu: [the({ id: 5, ten: 'Ibuprofen 400mg', slug: 'ibuprofen' })] })))
    renderTai('/san-pham/paracetamol-500mg')
    const khu = await screen.findByRole('region', { name: 'Sản phẩm tương tự' })
    expect(within(khu).getByRole('link', { name: 'Ibuprofen 400mg' })).toHaveAttribute('href', '/san-pham/ibuprofen?nguon=goi_y_tuong_tu')
  })
})

describe('TrangChiTietSanPham: quy tắc thuốc kê đơn và thực phẩm chức năng', () => {
  it('thuốc kê đơn: nhãn đỏ, nút Cần tư vấn, KHÔNG có Thêm vào giỏ', async () => {
    dapUng(() => ok(chiTiet({ loai_san_pham: 'thuoc_ke_don', can_tu_van: true })))
    renderTai('/san-pham/amoxicillin')
    const nut = await screen.findByText('Cần tư vấn từ dược sĩ')
    expect(nut.closest('a')).toHaveAttribute('href', '/gui-don-thuoc')
    expect(screen.getAllByText('Thuốc kê đơn').length).toBeGreaterThan(0)
    expect(screen.queryByText('Thêm vào giỏ')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /giỏ/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('group', { name: 'Đơn vị tính' })).not.toBeInTheDocument() // không chọn đơn vị để mua
  })

  it('thực phẩm chức năng có dòng "không phải là thuốc"; sản phẩm khác thì không', async () => {
    dapUng(() => ok(chiTiet({ loai_san_pham: 'thuc_pham_chuc_nang', luu_y_khong_phai_thuoc: true })))
    renderTai('/san-pham/vitamin')
    expect(await screen.findByText(/không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh/)).toBeInTheDocument()
    GET.mockReset()
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/khac')
    await screen.findAllByRole('heading', { name: 'Paracetamol 500mg', level: 1 })
    expect(screen.getAllByText(/không phải là thuốc/)).toHaveLength(1) // chỉ ở lần dựng trước
  })

  it('sản phẩm chỉ bán tại quầy: không có giá online, không có nút mua', async () => {
    dapUng(() => ok(chiTiet({ chi_ban_tai_quay: true, don_vi: [] })))
    renderTai('/san-pham/may-do')
    expect(await screen.findByText('Sản phẩm này chỉ bán tại nhà thuốc')).toBeInTheDocument()
    expect(screen.queryByText('Thêm vào giỏ')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Giá')).not.toBeInTheDocument()
  })
})

describe('TrangChiTietSanPham: đánh giá', () => {
  it('chưa có đánh giá', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/x')
    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Đánh giá (0)' }))
    expect(await screen.findByText('Chưa có đánh giá')).toBeInTheDocument()
  })

  it('tổng hợp điểm, phân bố và đánh giá mới nhất kèm phản hồi', async () => {
    const dg = {
      so_luong: 5,
      tong_sao: 16,
      phan_bo: [1, 1, 0, 2, 1],
      moi_nhat: [
        { so_sao: 5, noi_dung: 'Dùng tốt', ten_hien_thi: 'Nguyễn A.', phan_hoi: 'Cảm ơn bạn', created_at: '2026-10-10T03:00:00Z' },
        { so_sao: 1, noi_dung: null, ten_hien_thi: 'Trần B.', phan_hoi: null, created_at: '2026-10-09T03:00:00Z' },
      ],
    }
    dapUng(() => ok(chiTiet({ danh_gia: dg })))
    renderTai('/san-pham/x')
    await userEvent.setup().click(await screen.findByRole('tab', { name: 'Đánh giá (5)' }))
    expect(await screen.findByText('3,2')).toBeInTheDocument()
    expect(screen.getByText('5 đánh giá')).toBeInTheDocument()
    expect(screen.getByText('Dùng tốt')).toBeInTheDocument()
    expect(screen.getByText('Cảm ơn bạn')).toBeInTheDocument()
    expect(screen.getByText('Nguyễn A.')).toBeInTheDocument()
  })
})

describe('TrangChiTietSanPham: lịch sử xem và lỗi', () => {
  it('gửi mã phiên của trình duyệt và nguồn hợp lệ; nguồn lạ bị bỏ', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg?nguon=tim_kiem')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg', level: 1 })
    const [, tham] = lanGoiChiTiet()[0]
    expect(tham.params.path).toEqual({ slug: 'paracetamol-500mg' })
    expect(tham.params.query).toEqual({ nguon: 'tim_kiem' })
    expect(tham.params.header['x-ma-phien']).toMatch(/^[A-Za-z0-9_-]{22}$/)
    expect(localStorage.getItem('ma_phien_khach')).toBe(tham.params.header['x-ma-phien'])
    GET.mockClear()
    renderTai('/san-pham/paracetamol-500mg?nguon=<script>')
    await waitFor(() => expect(lanGoiChiTiet().length).toBeGreaterThan(0))
    expect(lanGoiChiTiet()[0][1].params.query).toEqual({ nguon: undefined })
  })

  it('không tải lại khi chuyển cửa sổ (mỗi lần tải ghi lịch sử xem)', async () => {
    dapUng(() => ok(chiTiet()))
    renderTai('/san-pham/paracetamol-500mg')
    await screen.findByRole('heading', { name: 'Paracetamol 500mg', level: 1 })
    window.dispatchEvent(new Event('focus'))
    document.dispatchEvent(new Event('visibilitychange'))
    expect(lanGoiChiTiet()).toHaveLength(1)
  })

  it('chờ lấy lại phiên rồi mới gọi API, để lịch sử xem ghi đúng người', async () => {
    dapUng(() => ok(chiTiet()))
    usePhien.setState({ daKhoiPhuc: false }) // đang lấy lại phiên lúc tải trang
    renderTai('/san-pham/paracetamol-500mg')
    await new Promise((r) => setTimeout(r, 150))
    expect(lanGoiChiTiet()).toHaveLength(0)
    act(() => usePhien.setState({ daKhoiPhuc: true }))
    await waitFor(() => expect(lanGoiChiTiet()).toHaveLength(1))
    expect(await screen.findByRole('heading', { name: 'Paracetamol 500mg', level: 1 })).toBeInTheDocument()
  })

  it('sản phẩm không hiển thị là 404', async () => {
    dapUng(() => loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy sản phẩm'))
    renderTai('/san-pham/da-xoa')
    expect(await screen.findByText('Không tìm thấy sản phẩm')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Về trang chủ' })).toBeInTheDocument()
  })

  it('lỗi máy chủ có nút thử lại', async () => {
    dapUng(() => loi(500, 'LOI_HE_THONG', 'Lỗi'))
    renderTai('/san-pham/x')
    expect(await screen.findByText('Không tải được sản phẩm')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Thử lại/ })).toBeInTheDocument()
  })
})
