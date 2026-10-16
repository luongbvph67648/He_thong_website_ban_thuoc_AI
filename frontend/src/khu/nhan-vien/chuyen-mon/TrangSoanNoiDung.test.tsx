import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import type { NoiDungSanPham, PhienBanNoiDung } from './noiDung'
import TrangSoanNoiDung from './TrangSoanNoiDung'

vi.setConfig({ testTimeout: 60_000 }) // antd + jsdom chậm; CI chỉ có 2 vCPU mà chạy song song nhiều file

const GET = vi.fn()
const POST = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a), POST: (...a: unknown[]) => POST(...a) } }))

const ok = (data: unknown, status = 200) => ({ data, response: { ok: true, status } })
const loi = (status: number, ma_loi: string, thong_diep: string, chi_tiet: unknown = null) => ({ error: { ma_loi, thong_diep, chi_tiet }, response: { ok: false, status } })
const NGUOI = { id: 5, ma_nhan_vien: 'NV0005', ho_ten: 'Dược sĩ An' }

const ban = (phien_ban: number, trang_thai: PhienBanNoiDung['trang_thai'], ghiDe: Partial<PhienBanNoiDung> = {}): PhienBanNoiDung => ({
  id: 100 + phien_ban,
  san_pham_id: 11,
  phien_ban,
  trang_thai,
  chi_dinh: 'Giảm đau, hạ sốt',
  chong_chi_dinh: null,
  lieu_dung_tham_khao: '500 mg mỗi 6 giờ',
  tac_dung_phu: null,
  than_trong: null,
  tuong_tac_thuoc: null,
  phu_nu_co_thai_cho_con_bu: null,
  tre_em: null,
  qua_lieu_xu_tri: null,
  bao_quan: null,
  file_hdsd_url: null,
  nguoi_soan: NGUOI,
  duoc_si_duyet: trang_thai === 'da_duyet' || trang_thai === 'luu_tru' ? NGUOI : null,
  ngay_duyet: trang_thai === 'da_duyet' || trang_thai === 'luu_tru' ? '2026-10-10T03:00:00Z' : null,
  created_at: '2026-10-09T03:00:00Z',
  ...ghiDe,
})

const DU = (cac: PhienBanNoiDung[]): NoiDungSanPham => ({
  san_pham: { id: 11, sku: 'PARA500', ten: 'Paracetamol 500mg', loai_san_pham: 'thuoc_khong_ke_don' },
  phien_ban_hien_thi: cac.find((p) => p.trang_thai === 'da_duyet')?.phien_ban ?? null,
  phien_ban: [...cac].sort((a, b) => b.phien_ban - a.phien_ban),
})

let hienTai: NoiDungSanPham

function dung(duong = '/nhan-vien/noi-dung-chuyen-mon/11', quyen: Record<string, 'day_du' | 'chi_xem'> = { 'content.professional.edit': 'day_du', 'content.approve': 'day_du' }) {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'DS', vaiTro: 'PHARMACIST' }, quyen })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={client}>
          <MemoryRouter initialEntries={[duong]}>
            <Routes>
              <Route path="/nhan-vien/noi-dung-chuyen-mon" element={<div>DANH SÁCH</div>} />
              <Route path="/nhan-vien/noi-dung-chuyen-mon/:id" element={<TrangSoanNoiDung />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

/** Nút theo chữ hiển thị (tra theo vai trò chậm trong antd + jsdom, xem frontend/CLAUDE.md). */
const nutChu = (chu: string, khung: HTMLElement = document.body) => {
  const el = within(khung).getAllByText(chu).map((e) => e.closest('button')).find(Boolean)
  if (!el) throw new Error(`Không có nút "${chu}"`)
  return el as HTMLButtonElement
}
const lanGoi = (m: ReturnType<typeof vi.fn>, duong: string) => m.mock.calls.filter((c) => c[0] === duong)
const GET_CHI_TIET = '/api/v1/noi-bo/chuyen-mon/san-pham/{san_pham_id}'

beforeEach(() => {
  GET.mockReset()
  POST.mockReset()
  hienTai = DU([ban(1, 'luu_tru'), ban(2, 'da_duyet', { chi_dinh: 'Giảm đau' })])
  GET.mockImplementation(async () => ok(hienTai))
})

describe('TrangSoanNoiDung: soạn bản mới', () => {
  it('điền sẵn từ bản còn hiệu lực mới nhất và hiện sản phẩm cùng bản đang hiển thị', async () => {
    dung()
    expect(await screen.findByRole('heading', { name: 'Paracetamol 500mg' })).toBeInTheDocument()
    expect(screen.getByText('Đang hiển thị bản 2.')).toBeInTheDocument()
    expect(screen.getByLabelText('Chỉ định')).toHaveValue('Giảm đau') // bản 2, không phải bản 1 đã lưu trữ
    expect(lanGoi(GET, GET_CHI_TIET)[0][1]).toEqual({ params: { path: { san_pham_id: 11 } } })
  })

  it('chưa đổi gì thì không gọi máy chủ; kiểm tra ô sai (độ dài, ký tự điều khiển) chặn trước', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    expect(await screen.findByText('Chưa có thay đổi nào so với phiên bản hiện có.')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
    await nguoi.type(screen.getByLabelText('Tờ hướng dẫn sử dụng gốc (đường dẫn)'), 'javascript:alert(1)')
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    expect(await screen.findByText('Còn ô chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')).toBeInTheDocument()
    expect(POST).not.toHaveBeenCalled()
  })

  it('lưu: POST kèm phien_ban_co_so là số lớn nhất (kể cả bản lưu trữ), ô trống thành null; xong làm mới và sang tab Phiên bản', async () => {
    const nguoi = userEvent.setup()
    POST.mockImplementation(async () => {
      hienTai = DU([ban(1, 'luu_tru'), ban(2, 'da_duyet', { chi_dinh: 'Giảm đau' }), ban(3, 'nhap', { chi_dinh: 'Giảm đau mạnh' })])
      return ok(ban(3, 'nhap'), 201)
    })
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    const chiDinh = screen.getByLabelText('Chỉ định')
    await nguoi.clear(chiDinh)
    await nguoi.type(chiDinh, 'Giảm đau mạnh')
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/chuyen-mon/san-pham/{san_pham_id}')
    expect(POST.mock.calls[0][1].params).toEqual({ path: { san_pham_id: 11 } })
    expect(POST.mock.calls[0][1].body).toMatchObject({ phien_ban_co_so: 2, chi_dinh: 'Giảm đau mạnh', lieu_dung_tham_khao: '500 mg mỗi 6 giờ', tac_dung_phu: null, file_hdsd_url: null })
    expect(await screen.findByText('Đã lưu bản nháp 3')).toBeInTheDocument()
    expect(await screen.findByText('Bản nháp')).toBeInTheDocument() // tab Phiên bản đang mở với bản mới
    expect(lanGoi(GET, GET_CHI_TIET)).toHaveLength(2)
  })

  it('409 (có bản mới hơn): tải lại danh sách phiên bản, chữ đang gõ còn nguyên, lưu lại dùng số mới', async () => {
    const nguoi = userEvent.setup()
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    POST.mockResolvedValueOnce(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Đã có phiên bản mới hơn'))
    hienTai = DU([ban(1, 'luu_tru'), ban(2, 'da_duyet'), ban(3, 'nhap', { chi_dinh: 'Của người khác' })])
    const chiDinh = screen.getByLabelText('Chỉ định')
    await nguoi.clear(chiDinh)
    await nguoi.type(chiDinh, 'Chữ tôi gõ')
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    expect(await screen.findByText(/Đã có phiên bản mới hơn phiên bản bạn đang soạn/)).toBeInTheDocument()
    expect(screen.getByLabelText('Chỉ định')).toHaveValue('Chữ tôi gõ')
    expect(lanGoi(GET, GET_CHI_TIET)).toHaveLength(2)

    POST.mockResolvedValueOnce(ok(ban(4, 'nhap'), 201))
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(2))
    expect(POST.mock.calls[1][1].body.phien_ban_co_so).toBe(3)
  })

  it('máy chủ từ chối một ô: lỗi gắn vào đúng ô', async () => {
    const nguoi = userEvent.setup()
    POST.mockResolvedValue(loi(400, 'DU_LIEU_KHONG_HOP_LE', 'Dữ liệu không hợp lệ', [{ truong: 'tre_em', loi: 'Tối đa 20000 ký tự' }]))
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.type(screen.getByLabelText('Trẻ em'), 'Từ 12 tuổi')
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    expect(await screen.findByText('Tối đa 20000 ký tự')).toBeInTheDocument()
    expect(screen.getByText('Máy chủ từ chối nội dung, hãy xem các ô báo đỏ.')).toBeInTheDocument()
  })

  it('sản phẩm chưa có phiên bản nào: form trống, cơ sở null, báo chưa có nội dung duyệt', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([])
    POST.mockResolvedValue(ok(ban(1, 'nhap'), 201))
    dung()
    expect(await screen.findByText(/Chưa có nội dung nào được duyệt/)).toBeInTheDocument()
    expect(screen.getByLabelText('Chỉ định')).toHaveValue('')
    await nguoi.type(screen.getByLabelText('Chỉ định'), 'Giảm đau')
    await nguoi.click(nutChu('Lưu thành bản nháp mới'))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][1].body.phien_ban_co_so).toBeNull()
  })

  it('không tự tải lại chi tiết khi cửa sổ được focus lại (phien_ban_co_so phải là bản đã thấy)', async () => {
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    window.dispatchEvent(new Event('visibilitychange'))
    window.dispatchEvent(new Event('focus'))
    await new Promise((r) => setTimeout(r, 50))
    expect(lanGoi(GET, GET_CHI_TIET)).toHaveLength(1)
  })

  it('id sai định dạng hoặc không tồn tại: trang không tìm thấy; id sai không gọi máy chủ', async () => {
    GET.mockImplementation(async () => loi(404, 'KHONG_TIM_THAY', 'Không tìm thấy'))
    const { unmount } = dung('/nhan-vien/noi-dung-chuyen-mon/999')
    expect(await screen.findByText('Không tìm thấy sản phẩm')).toBeInTheDocument()
    unmount()
    GET.mockClear()
    dung('/nhan-vien/noi-dung-chuyen-mon/abc')
    expect(await screen.findByText('Không tìm thấy sản phẩm')).toBeInTheDocument()
    expect(GET).not.toHaveBeenCalled()
  })

  it('chỉ xem (Admin): đọc được nhưng không có nút lưu, ô nhập bị tắt', async () => {
    dung('/nhan-vien/noi-dung-chuyen-mon/11', { 'content.professional.edit': 'chi_xem', 'content.approve': 'chi_xem' })
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    expect(screen.queryByText('Lưu thành bản nháp mới')).not.toBeInTheDocument()
    expect(screen.getByLabelText('Chỉ định')).toBeDisabled()
  })
})

describe('TrangSoanNoiDung: phiên bản, duyệt, so sánh', () => {
  const moTabPhienBan = async (nguoi: ReturnType<typeof userEvent.setup>) => {
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: /Phiên bản/ }))
  }

  it('bảng phiên bản: nút Duyệt, Bỏ bản nháp chỉ ở bản nháp; bản đã duyệt và lưu trữ không có nút', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'luu_tru'), ban(2, 'da_duyet'), ban(3, 'nhap')])
    dung()
    await moTabPhienBan(nguoi)
    const hang = (cho: string) => screen.getByText(cho, { selector: '.ant-table-row .ant-tag' }).closest('tr') as HTMLElement
    const nhap = hang('Bản nháp')
    expect(within(nhap).getByText('Duyệt')).toBeInTheDocument()
    expect(within(nhap).getByText('Bỏ bản nháp')).toBeInTheDocument()
    expect(within(hang('Đang hiển thị')).queryByText('Duyệt')).not.toBeInTheDocument()
    expect(within(hang('Đã lưu trữ')).queryByText('Bỏ bản nháp')).not.toBeInTheDocument()
    expect(within(hang('Đang hiển thị')).getAllByText(/Dược sĩ An/).length).toBeGreaterThanOrEqual(2) // người soạn và người duyệt
  })

  it('duyệt: xác nhận rồi POST /duyet và làm mới', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'luu_tru'), ban(2, 'nhap')])
    POST.mockImplementation(async () => {
      hienTai = DU([ban(1, 'luu_tru'), ban(2, 'da_duyet')])
      return ok(ban(2, 'da_duyet'))
    })
    dung()
    await moTabPhienBan(nguoi)
    await nguoi.click(nutChu('Duyệt'))
    await nguoi.click(await screen.findByText('Duyệt', { selector: '.ant-popover .ant-btn-primary span, .ant-popconfirm .ant-btn-primary span' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0]).toEqual(['/api/v1/noi-bo/chuyen-mon/{phien_ban_id}/duyet', { params: { path: { phien_ban_id: 102 } } }])
    expect(await screen.findByText(/Đã duyệt bản 2/)).toBeInTheDocument()
    expect(await screen.findByText('Đang hiển thị bản 2.')).toBeInTheDocument()
  })

  it('duyệt gặp 409 (bản đã bị người khác duyệt hoặc bỏ): báo thông điệp máy chủ và tải lại', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'nhap')])
    POST.mockResolvedValue(loi(409, 'DU_LIEU_DA_THAY_DOI', 'Phiên bản này không còn là bản nháp'))
    dung()
    await moTabPhienBan(nguoi)
    await nguoi.click(nutChu('Duyệt'))
    await nguoi.click(await screen.findByText('Duyệt', { selector: '.ant-popover .ant-btn-primary span, .ant-popconfirm .ant-btn-primary span' }))
    expect(await screen.findByText('Phiên bản này không còn là bản nháp')).toBeInTheDocument()
    await waitFor(() => expect(lanGoi(GET, GET_CHI_TIET)).toHaveLength(2))
  })

  it('bỏ bản nháp: POST /luu-tru', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'da_duyet'), ban(2, 'nhap')])
    POST.mockResolvedValue(ok(ban(2, 'luu_tru')))
    dung()
    await moTabPhienBan(nguoi)
    await nguoi.click(nutChu('Bỏ bản nháp'))
    await nguoi.click(await screen.findByText('Bỏ bản nháp', { selector: '.ant-popover .ant-btn span, .ant-popconfirm .ant-btn span' }))
    await waitFor(() => expect(POST).toHaveBeenCalledTimes(1))
    expect(POST.mock.calls[0][0]).toBe('/api/v1/noi-bo/chuyen-mon/{phien_ban_id}/luu-tru')
    expect(await screen.findByText('Đã bỏ bản nháp 2')).toBeInTheDocument()
  })

  it('dược sĩ chỉ có quyền soạn: thấy nút Bỏ bản nháp nhưng không có nút Duyệt', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'nhap')])
    dung('/nhan-vien/noi-dung-chuyen-mon/11', { 'content.professional.edit': 'day_du' })
    await moTabPhienBan(nguoi)
    expect(nutChu('Bỏ bản nháp')).toBeInTheDocument()
    expect(() => nutChu('Duyệt')).toThrow() // chữ "Duyệt" còn ở tiêu đề cột nhưng không có nút
  })

  it('so sánh: mặc định hai bản mới nhất, chỉ hiện trường khác nhau; tắt công tắc thì hiện đủ', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'luu_tru', { tre_em: 'Trên 6 tuổi' }), ban(2, 'da_duyet', { tre_em: 'Trên 12 tuổi', tac_dung_phu: 'Buồn nôn' })])
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'So sánh' }))
    const treEm = await screen.findByTestId('so-sanh-tre_em')
    expect(within(treEm).getByText('Trên 6 tuổi')).toBeInTheDocument()
    expect(within(treEm).getByText('Trên 12 tuổi')).toBeInTheDocument()
    expect(screen.getByTestId('so-sanh-tac_dung_phu')).toBeInTheDocument()
    expect(screen.queryByTestId('so-sanh-chi_dinh')).not.toBeInTheDocument() // giống nhau nên ẩn
    await nguoi.click(screen.getByLabelText('Chỉ hiện trường khác nhau'))
    expect(await screen.findByTestId('so-sanh-chi_dinh')).toBeInTheDocument()
  })

  it('so sánh cần ít nhất hai bản', async () => {
    const nguoi = userEvent.setup()
    hienTai = DU([ban(1, 'nhap')])
    dung()
    await screen.findByRole('heading', { name: 'Paracetamol 500mg' })
    await nguoi.click(screen.getByRole('tab', { name: 'So sánh' }))
    expect(await screen.findByText('Cần ít nhất hai phiên bản để so sánh')).toBeInTheDocument()
  })
})
