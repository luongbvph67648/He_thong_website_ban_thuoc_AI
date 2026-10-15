import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangVaiTro from './TrangVaiTro'

vi.setConfig({ testTimeout: 20_000 })

const GET = vi.fn()
const PUT = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), PUT: (...a: unknown[]) => PUT(...a) } }))

const q = (ma: string, nhom: string, muc: 'day_du' | 'chi_xem' | null, tuyChinh: Record<string, unknown> = {}) => ({
  ma,
  nhom,
  mo_ta: `Mô tả ${ma}`,
  muc,
  bat_buoc: false,
  chi_cho_vai_tro: null,
  ...tuyChinh,
})
const DANH_SACH = [
  { ma: 'PHARMACIST', ten: 'Dược sĩ bán hàng', mo_ta: null, so_nhan_vien: 2, so_quyen: 4, chinh_sua_duoc: true },
  { ma: 'WAREHOUSE', ten: 'Nhân viên kho', mo_ta: null, so_nhan_vien: 1, so_quyen: 2, chinh_sua_duoc: true },
  { ma: 'ADMIN', ten: 'Quản trị', mo_ta: null, so_nhan_vien: 1, so_quyen: 3, chinh_sua_duoc: false },
]
const chiTiet = (ma: string) => ({
  ma,
  ten: ma,
  mo_ta: null,
  so_nhan_vien: 1,
  chinh_sua_duoc: ma !== 'ADMIN',
  quyen: [
    q('profile.self', 'profile', 'day_du', { bat_buoc: true }),
    q('order.view', 'order', ma === 'ADMIN' ? 'chi_xem' : 'day_du'),
    q('pos.sell', 'order', ma === 'PHARMACIST' ? 'day_du' : null),
    q('stock.view', 'stock', ma === 'WAREHOUSE' ? 'day_du' : 'chi_xem'),
    q('content.approve', 'content', ma === 'PHARMACIST' ? 'day_du' : null, { chi_cho_vai_tro: 'PHARMACIST' }),
  ],
})
const ok = (data: unknown) => ({ data, response: { status: 200 } })

function dung() {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'role.manage': 'day_du' } })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter>
            <TrangVaiTro />
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

const nhomMuc = (ma: string) => screen.getByRole('radiogroup', { name: `Mức của ${ma}` })
const chon = async (nguoi: ReturnType<typeof userEvent.setup>, ma: string, nhan: string) =>
  nguoi.click(within(nhomMuc(ma)).getByText(nhan)) // bấm nhãn: ô radio thật có pointer-events: none

beforeEach(() => {
  GET.mockReset()
  PUT.mockReset()
  GET.mockImplementation(async (duong: string, tuyChon?: { params?: { path?: { ma?: string } } }) =>
    duong.endsWith('/vai-tro') ? ok(DANH_SACH) : ok(chiTiet(tuyChon?.params?.path?.ma ?? 'PHARMACIST')),
  )
})

describe('TrangVaiTro', () => {
  it('hiện ma trận theo nhóm với mức hiện tại của vai trò đầu tiên', async () => {
    dung()
    expect(await screen.findByText('pos.sell')).toBeInTheDocument()
    expect(within(nhomMuc('pos.sell')).getByRole('radio', { name: 'Đầy đủ' })).toBeChecked()
    expect(within(nhomMuc('stock.view')).getByRole('radio', { name: 'Chỉ xem' })).toBeChecked()
    expect(screen.getByText('Bắt buộc')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Lưu phân quyền/ })).toBeDisabled() // chưa có thay đổi
  })

  it('đổi mức thì nút lưu đếm số thay đổi; hoàn tác trả về bản máy chủ', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    await chon(nguoi, 'pos.sell', 'Không có')
    await chon(nguoi, 'stock.view', 'Đầy đủ')
    expect(screen.getByRole('button', { name: 'Lưu phân quyền (2 thay đổi)' })).toBeEnabled()
    await nguoi.click(screen.getByRole('button', { name: 'Hoàn tác' }))
    expect(within(nhomMuc('pos.sell')).getByRole('radio', { name: 'Đầy đủ' })).toBeChecked()
    expect(screen.getByRole('button', { name: /Lưu phân quyền/ })).toBeDisabled()
  })

  it('lưu: xác nhận kèm danh sách thay đổi, gửi PUT với đúng các mã còn quyền, mã bị gỡ vắng mặt', async () => {
    PUT.mockResolvedValueOnce(ok(chiTiet('PHARMACIST')))
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    await chon(nguoi, 'pos.sell', 'Không có')
    await chon(nguoi, 'stock.view', 'Đầy đủ')
    await nguoi.click(screen.getByRole('button', { name: /Lưu phân quyền/ }))
    const hop = await screen.findByRole('dialog')
    expect(within(hop).getAllByText(/Đầy đủ →/).length).toBeGreaterThan(0)
    const danhSach = within(hop).getByLabelText('Các thay đổi quyền')
    expect(within(danhSach).getByText('pos.sell')).toBeInTheDocument()
    expect(within(danhSach).getByText('stock.view')).toBeInTheDocument()
    expect(PUT).not.toHaveBeenCalled()
    await nguoi.click(within(hop).getByRole('button', { name: 'Lưu' }))
    await waitFor(() => expect(PUT).toHaveBeenCalledTimes(1))
    expect(PUT).toHaveBeenCalledWith('/api/v1/noi-bo/vai-tro/{ma}/quyen', {
      params: { path: { ma: 'PHARMACIST' } },
      body: { quyen: { 'profile.self': 'day_du', 'order.view': 'day_du', 'stock.view': 'day_du', 'content.approve': 'day_du' } },
    })
    expect(await screen.findByText(/Đã lưu phân quyền/)).toBeInTheDocument()
  })

  it('đổi vai trò thì bỏ các thay đổi chưa lưu của vai trò trước', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    await chon(nguoi, 'pos.sell', 'Không có')
    await nguoi.click(screen.getByText(/Nhân viên kho \(1\)/))
    await waitFor(() => expect(within(nhomMuc('stock.view')).getByRole('radio', { name: 'Đầy đủ' })).toBeChecked())
    expect(screen.getByRole('button', { name: /Lưu phân quyền/ })).toBeDisabled()
  })

  it('profile.self chỉ được ở mức đầy đủ; quyền chỉ của dược sĩ bị khóa ở vai trò khác', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    expect(within(nhomMuc('profile.self')).getByRole('radio', { name: 'Không có' })).toBeDisabled()
    expect(within(nhomMuc('profile.self')).getByRole('radio', { name: 'Chỉ xem' })).toBeDisabled()
    expect(within(nhomMuc('content.approve')).getByRole('radio', { name: 'Chỉ xem' })).toBeEnabled() // dược sĩ: cấp được

    await nguoi.click(screen.getByText(/Nhân viên kho \(1\)/))
    await waitFor(() => expect(within(nhomMuc('content.approve')).getByRole('radio', { name: 'Đầy đủ' })).toBeDisabled())
    expect(within(nhomMuc('content.approve')).getByRole('radio', { name: 'Chỉ xem' })).toBeDisabled()
    expect(within(nhomMuc('content.approve')).getByRole('radio', { name: 'Không có' })).toBeEnabled()
  })

  it('vai trò Admin chỉ xem: mọi lựa chọn bị khóa, nút lưu tắt, có giải thích', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    await nguoi.click(screen.getByText(/Quản trị \(1\)/))
    expect(await screen.findByText('Quyền của vai trò Quản trị không thay đổi được')).toBeInTheDocument()
    for (const ma of ['order.view', 'stock.view', 'pos.sell']) {
      for (const r of within(nhomMuc(ma)).getAllByRole('radio')) expect(r).toBeDisabled()
    }
    expect(screen.getByRole('button', { name: /Lưu phân quyền/ })).toBeDisabled()
  })

  it('máy chủ từ chối thì hiện lý do cụ thể từ chi tiết lỗi', async () => {
    PUT.mockResolvedValueOnce({
      error: { ma_loi: 'DU_LIEU_KHONG_HOP_LE', thong_diep: 'Dữ liệu không hợp lệ', chi_tiet: [{ truong: 'quyen.content.approve', loi: 'Quyền này chỉ dành cho vai trò PHARMACIST' }] },
      response: { status: 400 },
    })
    const nguoi = userEvent.setup()
    dung()
    await screen.findByText('pos.sell')
    await chon(nguoi, 'pos.sell', 'Không có')
    await nguoi.click(screen.getByRole('button', { name: /Lưu phân quyền/ }))
    await nguoi.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Lưu' }))
    expect(await screen.findByText('Quyền này chỉ dành cho vai trò PHARMACIST')).toBeInTheDocument()
  })

  it('quyền chỉ xem thì không có nút lưu', async () => {
    dung()
    usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'A', vaiTro: 'ADMIN' }, quyen: { 'role.manage': 'chi_xem' } })
    await waitFor(() => expect(screen.queryByRole('button', { name: /Lưu phân quyền/ })).not.toBeInTheDocument())
  })
})
