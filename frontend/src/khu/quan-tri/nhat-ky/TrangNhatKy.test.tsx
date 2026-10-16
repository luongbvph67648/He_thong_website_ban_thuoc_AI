import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangNhatKy from './TrangNhatKy'

vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a) } }))

const NHAN_VIEN = { id: 3, ma_nhan_vien: 'NV0003', ho_ten: 'Trần Văn Kho' }
const DONG = [
  { id: 30, created_at: '2026-10-15T17:30:45Z', nhan_vien: NHAN_VIEN, hanh_dong: 'sua', bang: 'cau_hinh', ban_ghi_id: 'nguong_can_han_ngay', gia_tri_cu: 90, gia_tri_moi: 45, ip: '10.0.0.9' },
  { id: 29, created_at: '2026-10-15T10:00:00Z', nhan_vien: null, hanh_dong: 'dang_nhap_that_bai', bang: 'nhan_vien', ban_ghi_id: null, gia_tri_cu: null, gia_tri_moi: null, ip: null },
  { id: 28, created_at: '2026-10-14T10:00:00Z', nhan_vien: NHAN_VIEN, hanh_dong: 'sua', bang: 'vai_tro_quyen', ban_ghi_id: 'WAREHOUSE', gia_tri_cu: { bo: ['order.pick:day_du'], doi_muc: [] }, gia_tri_moi: { them: ['return.review:chi_xem'] }, ip: '10.0.0.9' },
  { id: 27, created_at: '2026-10-14T09:00:00Z', nhan_vien: NHAN_VIEN, hanh_dong: 'doc_suc_khoe', bang: 'ho_so_suc_khoe', ban_ghi_id: '42', gia_tri_cu: null, gia_tri_moi: null, ip: '10.0.0.9' },
  { id: 26, created_at: '2026-10-13T09:00:00Z', nhan_vien: NHAN_VIEN, hanh_dong: 'sua', bang: 'san_pham', ban_ghi_id: '5', gia_tri_cu: { ten: 'A', gia: '1000' }, gia_tri_moi: { ten: 'B', gia: '1000' }, ip: null },
]
const ok = (data: unknown) => ({ data, response: { status: 200 } })
const trang = (du_lieu: unknown[], tong = du_lieu.length) => ok({ du_lieu, tong, trang: 1, kich_thuoc: 20 })

function dung(duong = '/nhat-ky') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'audit.view': 'day_du' } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <TrangNhatKy />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const thamSoLanGoiNhatKy = () => GET.mock.calls.filter(([d]) => d === '/api/v1/noi-bo/nhat-ky').at(-1)?.[1]?.params?.query
const hang = async (ten: string) => (await screen.findByText(ten)).closest('tr') as HTMLElement

beforeEach(() => {
  GET.mockReset()
  GET.mockImplementation(async (duong: string) => {
    if (duong === '/api/v1/noi-bo/nhat-ky') return trang(DONG)
    if (duong === '/api/v1/noi-bo/nhat-ky/gia-tri-loc') return ok({ bang: ['cau_hinh', 'nhan_vien', 'san_pham'], hanh_dong: ['sua', 'tao'] })
    if (duong === '/api/v1/noi-bo/nhan-vien') return ok({ du_lieu: [NHAN_VIEN, { id: 4, ma_nhan_vien: 'NV0004', ho_ten: 'Lê Dược Sĩ' }], tong: 2, trang: 1, kich_thuoc: 100 })
    throw new Error(`GET không mong đợi: ${duong}`)
  })
})

describe('TrangNhatKy', () => {
  it('liệt kê: thời gian đến giây theo giờ Việt Nam, người thực hiện, hành động tiếng Việt, bảng, bản ghi, IP', async () => {
    dung()
    const h = await hang('16/10/2026 00:30:45')
    expect(within(h).getByText('Trần Văn Kho (NV0003)')).toBeInTheDocument()
    expect(within(h).getByText('Sửa')).toBeInTheDocument()
    expect(within(h).getByText('cau_hinh')).toBeInTheDocument()
    expect(within(h).getByText('nguong_can_han_ngay')).toBeInTheDocument()
    expect(within(h).getByText('10.0.0.9')).toBeInTheDocument()
    const hThongKe = await hang('15/10/2026 17:00:00')
    expect(within(hThongKe).getByText('Hệ thống hoặc chưa xác định')).toBeInTheDocument()
    expect(within(hThongKe).getByText('dang_nhap_that_bai')).toBeInTheDocument() // hành động chưa có nhãn: giữ nguyên mã
    expect(thamSoLanGoiNhatKy()).toEqual({ bang: undefined, ban_ghi_id: undefined, nhan_vien_id: undefined, hanh_dong: undefined, tu_ngay: undefined, den_ngay: undefined, trang: 1, kich_thuoc: 20 })
  })

  it('mở rộng một dòng: giá trị đơn lẻ hiện cũ và mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    const h = await hang('16/10/2026 00:30:45')
    await nguoi.click(within(h).getByRole('button', { name: /Mở rộng/ }))
    const chiTiet = await screen.findByTestId('so-sanh-30')
    expect(within(chiTiet).getByText('90')).toBeInTheDocument()
    expect(within(chiTiet).getByText('45')).toBeInTheDocument()
  })

  it('mở rộng dòng nhiều trường: tô nổi bật trường đổi, trường không đổi để thường', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await hang('13/10/2026 16:00:00')).getByRole('button', { name: /Mở rộng/ }))
    const chiTiet = await screen.findByTestId('so-sanh-26')
    expect(within(chiTiet).getByText('ten').closest('tr')).toHaveAttribute('data-doi', 'true')
    expect(within(chiTiet).getByText('gia').closest('tr')).toHaveAttribute('data-doi', 'false')
  })

  it('dòng thay đổi quyền (danh sách trong đối tượng) hiện từng phần tử đọc được', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await hang('14/10/2026 17:00:00')).getByRole('button', { name: /Mở rộng/ }))
    const chiTiet = await screen.findByTestId('so-sanh-28')
    expect(within(chiTiet).getByText(/order\.pick:day_du/)).toBeInTheDocument()
    expect(within(chiTiet).getByText(/return\.review:chi_xem/)).toBeInTheDocument()
  })

  it('dữ liệu sức khỏe: nói rõ giá trị không được lưu, không có ô cũ/mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await hang('14/10/2026 16:00:00')).getByRole('button', { name: /Mở rộng/ }))
    const chiTiet = await screen.findByTestId('so-sanh-27')
    expect(within(chiTiet).getByText(/Giá trị không được lưu \(dữ liệu sức khỏe\)/)).toBeInTheDocument()
  })

  it('dòng không có giá trị cũ lẫn mới thì báo rõ', async () => {
    const nguoi = userEvent.setup()
    dung()
    await nguoi.click(within(await hang('15/10/2026 17:00:00')).getByRole('button', { name: /Mở rộng/ }))
    expect(await screen.findByText('Dòng này không ghi giá trị cũ hay mới')).toBeInTheDocument()
  })

  it('mở trang từ URL thì gọi API đúng các bộ lọc; tham số hỏng bị bỏ qua', async () => {
    dung('/nhat-ky?bang=cau_hinh&hanh_dong=sua&ban_ghi_id=abc&nhan_vien_id=3&tu_ngay=2026-10-01&den_ngay=2026-10-15&trang=2')
    await screen.findByText('16/10/2026 00:30:45')
    expect(thamSoLanGoiNhatKy()).toEqual({ bang: 'cau_hinh', ban_ghi_id: 'abc', nhan_vien_id: 3, hanh_dong: 'sua', tu_ngay: '2026-10-01', den_ngay: '2026-10-15', trang: 2, kich_thuoc: 20 })
  })

  it('URL có giá trị hỏng (nhan_vien_id chữ, ngày sai, trang 2.5) thì không gửi lên máy chủ', async () => {
    dung('/nhat-ky?nhan_vien_id=abc&tu_ngay=khong-phai-ngay&den_ngay=2026-13-45&trang=2.5')
    await screen.findByText('16/10/2026 00:30:45')
    expect(thamSoLanGoiNhatKy()).toMatchObject({ nhan_vien_id: undefined, tu_ngay: undefined, den_ngay: undefined, trang: 1 })
  })

  it('ngày ngoài miền 2000..2100 trên URL bị bỏ qua (máy chủ từ chối nên không gửi lên)', async () => {
    dung('/nhat-ky?tu_ngay=0001-01-01&den_ngay=9999-12-31')
    await screen.findByText('16/10/2026 00:30:45')
    expect(thamSoLanGoiNhatKy()).toMatchObject({ tu_ngay: undefined, den_ngay: undefined })
    dung('/nhat-ky?tu_ngay=2000-01-01&den_ngay=2100-12-31')
    await waitFor(() => expect(thamSoLanGoiNhatKy()).toMatchObject({ tu_ngay: '2000-01-01', den_ngay: '2100-12-31' }))
  })

  it('chọn bảng từ ô lọc: gọi lại với bảng đó và về trang 1; ô lọc dựng từ giá trị máy chủ trả về', async () => {
    const nguoi = userEvent.setup()
    dung('/nhat-ky?trang=3')
    await screen.findByText('16/10/2026 00:30:45')
    await nguoi.click(screen.getByRole('combobox', { name: 'Lọc theo bảng' }))
    await nguoi.click(await screen.findByTitle('san_pham'))
    await waitFor(() => expect(thamSoLanGoiNhatKy()).toMatchObject({ bang: 'san_pham', trang: 1 }))
  })

  it('lọc theo nhân viên lấy danh sách từ API nhân viên', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('16/10/2026 00:30:45')
    await nguoi.click(screen.getByRole('combobox', { name: 'Lọc theo người thực hiện' }))
    await nguoi.click(await screen.findByTitle('NV0004 · Lê Dược Sĩ'))
    await waitFor(() => expect(thamSoLanGoiNhatKy()).toMatchObject({ nhan_vien_id: 4 }))
  })

  it('tìm theo id bản ghi bằng Enter', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('16/10/2026 00:30:45')
    await nguoi.type(screen.getByPlaceholderText('Id bản ghi'), '42{Enter}')
    await waitFor(() => expect(thamSoLanGoiNhatKy()).toMatchObject({ ban_ghi_id: '42', trang: 1 }))
  })

  it('bấm trang 2: gọi với trang 2 và giữ bộ lọc', async () => {
    GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/nhat-ky' ? trang(DONG, 45) : duong.endsWith('gia-tri-loc') ? ok({ bang: [], hanh_dong: [] }) : ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 100 })))
    const nguoi = userEvent.setup()
    dung('/nhat-ky?bang=cau_hinh')
    await screen.findByText('16/10/2026 00:30:45')
    await nguoi.click(screen.getByTitle('2'))
    await waitFor(() => expect(thamSoLanGoiNhatKy()).toMatchObject({ bang: 'cau_hinh', trang: 2 }))
  })

  it('không có dòng nào và lỗi tải', async () => {
    GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/nhat-ky' ? trang([]) : duong.endsWith('gia-tri-loc') ? ok({ bang: [], hanh_dong: [] }) : ok({ du_lieu: [], tong: 0, trang: 1, kich_thuoc: 100 })))
    const { unmount } = dung()
    expect(await screen.findByText('Không có dòng nhật ký phù hợp')).toBeInTheDocument()
    unmount()
    GET.mockImplementation(async (duong: string) => (duong === '/api/v1/noi-bo/nhat-ky' ? { error: { ma_loi: 'LOI_HE_THONG', thong_diep: 'x', chi_tiet: null }, response: { status: 500 } } : ok({ bang: [], hanh_dong: [], du_lieu: [] })))
    dung()
    expect(await screen.findByText('Không tải được nhật ký hệ thống')).toBeInTheDocument()
  })

  it('không có nút sửa hay xóa nào: nhật ký chỉ đọc', async () => {
    dung()
    await screen.findByText('16/10/2026 00:30:45')
    expect(screen.queryByRole('button', { name: /Sửa|Xóa|Lưu/ })).not.toBeInTheDocument()
  })
})
