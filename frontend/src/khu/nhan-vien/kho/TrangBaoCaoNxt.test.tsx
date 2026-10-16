import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App, ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { usePhien } from '../../../stores/phien'
import TrangBaoCaoNxt from './TrangBaoCaoNxt'

vi.setConfig({ testTimeout: 90_000 })
const GET = vi.fn()
vi.mock('../../../api/client', () => ({ api: { GET: (...a: unknown[]) => GET(...a) } }))
const ok = (data: unknown) => ({ data, response: { ok: true, status: 200 } })
const DONG = { san_pham_id: 1, sku: 'PARA', ten: 'Paracetamol', ton_dau: 10, nhap_kho: 100, hoan_nhap: 0, nhan_tra_ve: 0, dieu_chinh: -2, xuat_ban: -30, huy_hang: -3, xuat_tra_ncc: 0, ton_cuoi: 75 }

function dung() {
  usePhien.getState().dangNhap({ accessToken: 't', loai: 'noi_bo', hoSo: { id: 1, hoTen: 'K', vaiTro: 'WAREHOUSE' }, quyen: { 'report.inventory': 'day_du' } })
  return render(
    <ConfigProvider locale={viVN}>
      <App>
        <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
          <TrangBaoCaoNxt />
        </QueryClientProvider>
      </App>
    </ConfigProvider>,
  )
}

beforeEach(() => {
  GET.mockReset()
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
  GET.mockImplementation(async (duong: string) => {
    if (duong.endsWith('/excel')) return ok(new Blob(['x']))
    return ok({ du_lieu: [DONG], tong: 1, trang: 1, kich_thuoc: 20 })
  })
})

describe('TrangBaoCaoNxt', () => {
  it('hiện số liệu và gọi lại với nhóm theo lô', async () => {
    dung()
    expect(await screen.findByText('Paracetamol')).toBeInTheDocument()
    expect(screen.getByText('75')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Theo lô'))
    await waitFor(() => expect(GET.mock.calls.some((c) => c[1]?.params?.query?.nhom === 'lo')).toBe(true))
  })

  it('xuất Excel gọi endpoint excel với cùng bộ lọc', async () => {
    dung()
    await screen.findByText('Paracetamol')
    await userEvent.click(screen.getByRole('button', { name: /Xuất Excel/ }))
    await waitFor(() => expect(URL.createObjectURL).toHaveBeenCalled())
    const goi = GET.mock.calls.find((c) => String(c[0]).endsWith('/excel'))!
    expect(goi[1].params.query.khu).toBe('kho_ban')
    expect(goi[1].parseAs).toBe('blob')
  })
})
