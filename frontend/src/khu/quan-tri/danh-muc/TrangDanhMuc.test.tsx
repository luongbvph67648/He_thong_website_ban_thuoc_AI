import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangDanhMuc from './TrangDanhMuc'

vi.setConfig({ testTimeout: 30_000 })

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

interface Nut {
  id: number
  ten: string
  slug: string
  danh_muc_cha_id: number | null
  anh_url: string | null
  thu_tu: number
  dang_hien_thi: boolean
  cap: number
  so_san_pham: number
  con: Nut[]
}
const nut = (id: number, ten: string, cap: number, chaId: number | null, rieng: Partial<Nut> = {}, con: Nut[] = []): Nut => ({
  id,
  ten,
  slug: `dm-${id}`,
  danh_muc_cha_id: chaId,
  anh_url: null,
  thu_tu: id,
  dang_hien_thi: true,
  cap,
  so_san_pham: 0,
  con,
  ...rieng,
})

/** Thuốc > Giảm đau > Paracetamol (cấp 3, còn 5 sản phẩm); Thuốc > Ho (đang ẩn); Dụng cụ (lá, trống). */
const CAY = (): Nut[] => [
  nut(1, 'Thuốc', 1, null, {}, [
    nut(2, 'Giảm đau', 2, 1, {}, [nut(3, 'Paracetamol', 3, 2, { so_san_pham: 5 })]),
    nut(4, 'Ho', 2, 1, { dang_hien_thi: false, anh_url: '/anh/ho.png' }),
  ]),
  nut(7, 'Dụng cụ', 1, null),
]
const ok = (data: unknown, status = 200) => ({ data, response: { ok: true, status } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })
const khongThan = { response: { ok: true, status: 204 } }

function dung(quyen: 'day_du' | 'chi_xem' = 'day_du') {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'category.manage': quyen } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <TrangDanhMuc />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

/** Dòng (nút Tree) chứa tên danh mục. */
const dong = async (ten: string) => (await screen.findByText(ten)).closest('.ant-tree-treenode') as HTMLElement
const hopThoai = async () => within(await screen.findByRole('dialog', { hidden: true }))

beforeEach(() => {
  for (const m of [GET, POST, PATCH, PUT, DELETE]) m.mockReset()
  GET.mockImplementation(async () => ok(CAY()))
})

describe('TrangDanhMuc', () => {
  it('hiện cả cây đã mở sẵn: nhãn đang ẩn, số sản phẩm, cấp 3 sâu nhất', async () => {
    dung()
    expect(await dong('Thuốc')).toBeInTheDocument()
    expect(await dong('Paracetamol')).toBeInTheDocument() // cấp 3 hiện ngay, không phải bấm mở
    expect(within(await dong('Ho')).getByText('Đang ẩn')).toBeInTheDocument()
    expect(within(await dong('Giảm đau')).queryByText('Đang ẩn')).not.toBeInTheDocument()
    expect(within(await dong('Paracetamol')).getByText('5 sản phẩm')).toBeInTheDocument()
    expect(GET).toHaveBeenCalledWith('/api/v1/noi-bo/danh-muc')
  })

  it('cây rỗng hiện thông báo; lỗi tải hiện cảnh báo', async () => {
    GET.mockImplementation(async () => ok([]))
    const { unmount } = dung()
    expect(await screen.findByText('Chưa có danh mục nào')).toBeInTheDocument()
    unmount()
    GET.mockImplementation(async () => loi(500, 'LOI_HE_THONG', 'Lỗi hệ thống'))
    dung()
    expect(await screen.findByText('Không tải được danh mục')).toBeInTheDocument()
  })

  it('thêm danh mục gốc: kiểm tra tên trước, rồi gửi POST với cha null', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(ok(nut(9, 'Mới', 1, null), 201))
    dung()
    await dong('Thuốc')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm danh mục gốc' }))
    const h = await hopThoai()
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await h.findByText('Vui lòng nhập tên')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
    await nguoi.type(h.getByLabelText('Tên danh mục'), '  Thực phẩm   chức năng ')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST).toHaveBeenCalledWith('/api/v1/noi-bo/danh-muc', { body: { ten: 'Thực phẩm chức năng', anh_url: null, dang_hien_thi: true, danh_muc_cha_id: null } })
    expect(await screen.findByText('Đã thêm danh mục')).toBeInTheDocument()
  })

  it('thêm danh mục con gửi id cha; danh mục cấp 3 không có nút Thêm con', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(ok(nut(9, 'Mới', 3, 4), 201))
    dung()
    expect(within(await dong('Paracetamol')).queryByRole('button', { hidden: true, name: 'Thêm con' })).not.toBeInTheDocument()
    await nguoi.click(within(await dong('Ho')).getByRole('button', { hidden: true, name: 'Thêm con' }))
    const h = await hopThoai()
    expect(screen.getByText('Thêm danh mục con của “Ho”')).toBeInTheDocument()
    await nguoi.type(h.getByLabelText('Tên danh mục'), 'Ho khan')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][1].body).toMatchObject({ ten: 'Ho khan', danh_muc_cha_id: 4 })
  })

  it('trùng tên anh em: lỗi 409 gắn vào ô tên, hộp thoại vẫn mở', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'Đã có danh mục cùng tên trong cùng danh mục cha', { truong: 'ten' }))
    dung()
    await dong('Thuốc')
    await nguoi.click(screen.getByRole('button', { hidden: true, name: 'Thêm danh mục gốc' }))
    const h = await hopThoai()
    await nguoi.type(h.getByLabelText('Tên danh mục'), 'dụng cụ')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Thêm' }))
    expect(await h.findByText('Đã có danh mục cùng tên trong cùng danh mục cha')).toBeInTheDocument()
  })

  it('máy chủ báo lỗi (hoặc dữ liệu làm mới) không xóa chữ người dùng đang gõ trong hộp thoại', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(loi(409, 'TRUNG_DU_LIEU', 'Đã có danh mục cùng tên trong cùng danh mục cha', { truong: 'ten' }))
    dung()
    await dong('Thuốc')
    await nguoi.click(screen.getByRole('button', { name: 'Thêm danh mục gốc' }))
    const h = await hopThoai()
    await nguoi.type(h.getByLabelText('Tên danh mục'), 'Dụng cụ')
    await nguoi.type(h.getByLabelText(/Đường dẫn ảnh/), '/anh/dung-cu.png')
    await nguoi.click(h.getByRole('button', { name: 'Thêm' }))
    expect(await h.findByText('Đã có danh mục cùng tên trong cùng danh mục cha')).toBeInTheDocument()
    expect(h.getByLabelText('Tên danh mục')).toHaveValue('Dụng cụ') // trước đây về rỗng vì effect chạy lại khi trang render lại
    expect(h.getByLabelText(/Đường dẫn ảnh/)).toHaveValue('/anh/dung-cu.png')
  })

  it('sửa: điền sẵn, đường dẫn ảnh sai bị chặn, PATCH đúng id', async () => {
    const nguoi = userEvent.setup()
    PATCH.mockResolvedValue(ok(nut(4, 'Ho khan', 2, 1)))
    dung()
    await nguoi.click(within(await dong('Ho')).getByRole('button', { hidden: true, name: 'Sửa' }))
    const h = await hopThoai()
    expect(h.getByLabelText('Tên danh mục')).toHaveValue('Ho')
    expect(h.getByLabelText(/Đường dẫn ảnh/)).toHaveValue('/anh/ho.png')
    expect(h.getByRole('switch', { hidden: true })).not.toBeChecked() // đang ẩn
    await nguoi.clear(h.getByLabelText(/Đường dẫn ảnh/))
    await nguoi.type(h.getByLabelText(/Đường dẫn ảnh/), 'data:image/png;base64,AAAA')
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Lưu' }))
    expect(await h.findByText(/Đường dẫn phải bắt đầu bằng/)).toBeInTheDocument()
    expect(PATCH).not.toHaveBeenCalled()
    await nguoi.clear(h.getByLabelText(/Đường dẫn ảnh/))
    await nguoi.clear(h.getByLabelText('Tên danh mục'))
    await nguoi.type(h.getByLabelText('Tên danh mục'), 'Ho khan')
    await nguoi.click(h.getByRole('switch', { hidden: true }))
    await nguoi.click(h.getByRole('button', { hidden: true, name: 'Lưu' }))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH).toHaveBeenCalledWith('/api/v1/noi-bo/danh-muc/{danh_muc_id}', {
      params: { path: { danh_muc_id: 4 } },
      body: { ten: 'Ho khan', anh_url: null, dang_hien_thi: true },
    })
  })

  it('ẩn/hiện chỉ gửi trường hiển thị', async () => {
    const nguoi = userEvent.setup()
    PATCH.mockResolvedValue(ok(nut(2, 'Giảm đau', 2, 1)))
    dung()
    await nguoi.click(within(await dong('Giảm đau')).getByRole('button', { hidden: true, name: 'Ẩn' }))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(1))
    expect(PATCH).toHaveBeenLastCalledWith('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: 2 } }, body: { dang_hien_thi: false } })
    await nguoi.click(within(await dong('Ho')).getByRole('button', { hidden: true, name: 'Hiện' }))
    await waitFor(() => expect(PATCH).toHaveBeenCalledTimes(2))
    expect(PATCH).toHaveBeenLastCalledWith('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: 4 } }, body: { dang_hien_thi: true } })
  })

  it('xóa: danh mục còn sản phẩm hoặc còn con bị tắt nút; danh mục trống xóa sau khi xác nhận', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValue(khongThan)
    dung()
    expect(within(await dong('Paracetamol')).getByRole('button', { hidden: true, name: 'Xóa' })).toBeDisabled() // còn 5 sản phẩm
    expect(within(await dong('Thuốc')).getByRole('button', { hidden: true, name: 'Xóa' })).toBeDisabled() // còn danh mục con
    await nguoi.click(within(await dong('Dụng cụ')).getByRole('button', { hidden: true, name: 'Xóa' }))
    await nguoi.click(screen.getAllByRole('button', { hidden: true, name: 'Xóa' }).at(-1)!) // nút xác nhận
    await waitFor(() => expect(DELETE).toHaveBeenCalledTimes(1))
    expect(DELETE).toHaveBeenCalledWith('/api/v1/noi-bo/danh-muc/{danh_muc_id}', { params: { path: { danh_muc_id: 7 } } })
    expect(await screen.findByText('Đã xóa “Dụng cụ”')).toBeInTheDocument()
  })

  it('số liệu cũ: máy chủ từ chối xóa thì hiện thông điệp của máy chủ và tải lại cây', async () => {
    const nguoi = userEvent.setup()
    DELETE.mockResolvedValue(loi(409, 'DANH_MUC_CON_SAN_PHAM', 'Danh mục còn 2 sản phẩm, hãy chuyển hoặc xóa chúng trước'))
    dung()
    await nguoi.click(within(await dong('Dụng cụ')).getByRole('button', { hidden: true, name: 'Xóa' }))
    const truoc = GET.mock.calls.length
    await nguoi.click(screen.getAllByRole('button', { hidden: true, name: 'Xóa' }).at(-1)!)
    expect(await screen.findByText('Danh mục còn 2 sản phẩm, hãy chuyển hoặc xóa chúng trước')).toBeInTheDocument()
    await waitFor(() => expect(GET.mock.calls.length).toBeGreaterThan(truoc))
  })

  it('chỉ xem: không có nút nào để ghi', async () => {
    dung('chi_xem')
    await dong('Thuốc')
    // Không dùng `hidden: true`: hộp thoại thêm/sửa luôn nằm trong DOM (ẩn) cùng nút của nó.
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
    expect(document.querySelector('.ant-tree-draggable-icon')).toBeNull()
    expect(document.querySelector('[draggable="true"]')).toBeNull()
  })
})
