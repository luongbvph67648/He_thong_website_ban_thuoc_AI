import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { ConfigProvider } from 'antd'
import viVN from 'antd/locale/vi_VN'
import { createMemoryRouter, RouterProvider } from 'react-router-dom'
import { taoRoutes } from '../router'
import type { QuyenCuaToi } from '../lib/quyen'
import { usePhien, type LoaiPhien } from '../stores/phien'

export interface PhienGia {
  loai: LoaiPhien
  vaiTro?: string
  quyen?: QuyenCuaToi
  phaiDoiMatKhau?: boolean
}

/** Dựng ứng dụng thật (router + provider) tại một đường dẫn, với phiên đăng nhập giả tùy chọn. */
export function renderTai(duong: string, phien?: PhienGia) {
  usePhien.getState().dangXuat()
  if (phien) {
    usePhien.getState().dangNhap({
      accessToken: 'token-thu',
      loai: phien.loai,
      hoSo: { id: 1, hoTen: 'Người dùng thử', vaiTro: phien.vaiTro },
      quyen: phien.quyen ?? {},
      phaiDoiMatKhau: phien.phaiDoiMatKhau,
    })
  }
  const router = createMemoryRouter(taoRoutes(), { initialEntries: [duong] })
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const ketQua = render(
    <ConfigProvider locale={viVN}>
      <QueryClientProvider client={client}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </ConfigProvider>,
  )
  return { router, ...ketQua }
}
