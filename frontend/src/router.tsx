import type { ReactNode } from 'react'
import { createBrowserRouter, type RouteObject } from 'react-router-dom'
import { Trang403 } from './components/Trang403'
import { Trang404 } from './components/Trang404'
import { TrangDangXayDung } from './components/TrangDangXayDung'
import { YeuCauQuyen } from './components/YeuCauQuyen'
import type { MucDieuHuong } from './lib/dieuHuong'
import CuaHangLayout from './khu/cua-hang/CuaHangLayout'
import TrangDangKy from './khu/cua-hang/dang-ky/TrangDangKy'
import TrangDangNhap from './khu/cua-hang/dang-nhap/TrangDangNhap'
import TrangQuenMatKhau from './khu/cua-hang/quen-mat-khau/TrangQuenMatKhau'
import { TRANG_CUA_HANG } from './khu/cua-hang/trang'
import TrangChu from './khu/cua-hang/TrangChu'
import NhanVienLayout, { TrangDauNhanVien } from './khu/nhan-vien/NhanVienLayout'
import { MUC_NHAN_VIEN } from './khu/nhan-vien/menu'
import TrangDangNhapNoiBo from './khu/nhan-vien/TrangDangNhap'
import QuanTriLayout from './khu/quan-tri/QuanTriLayout'
import { MUC_QUAN_TRI } from './khu/quan-tri/menu'

/** Route của một khu nội bộ: mỗi trang bọc `YeuCauQuyen` (mức xem; nút thao tác tự kiểm tra mức đầy đủ). */
function routeCuaKhu(muc: readonly MucDieuHuong[]): RouteObject[] {
  return muc.map((m) => {
    const trang = (
      <YeuCauQuyen ma={m.quyen} muc="xem">
        <TrangDangXayDung ten={m.nhan} chucNang={m.chucNang} />
      </YeuCauQuyen>
    )
    return m.duong === '/' ? { index: true, element: trang } : { path: m.duong.slice(1), element: trang }
  })
}

/** Trang khu cửa hàng đã làm thật; các trang còn lại trong `TRANG_CUA_HANG` là trang giữ chỗ. */
const TRANG_THAT: Record<string, ReactNode> = {
  '/dang-ky': <TrangDangKy />,
  '/dang-nhap': <TrangDangNhap />,
  '/quen-mat-khau': <TrangQuenMatKhau />,
}

/** Toàn bộ route của ứng dụng (tách khỏi `createBrowserRouter` để test dựng bằng memory router). */
export function taoRoutes(): RouteObject[] {
  return [
    {
      path: '/nhan-vien/dang-nhap',
      element: <TrangDangNhapNoiBo />,
    },
    {
      path: '/nhan-vien',
      element: <NhanVienLayout />,
      children: [
        { index: true, element: <TrangDauNhanVien /> },
        ...routeCuaKhu(MUC_NHAN_VIEN),
        { path: '*', element: <Trang404 veTrang="/nhan-vien" nhanVe="Về trang đầu" /> },
      ],
    },
    {
      path: '/quan-tri',
      element: <QuanTriLayout />,
      children: [...routeCuaKhu(MUC_QUAN_TRI), { path: '*', element: <Trang404 veTrang="/quan-tri" nhanVe="Về tổng quan" /> }],
    },
    {
      path: '/',
      element: <CuaHangLayout />,
      children: [
        { index: true, element: <TrangChu /> },
        ...TRANG_CUA_HANG.map((t) => ({
          path: t.duong.slice(1),
          element: TRANG_THAT[t.duong] ?? <TrangDangXayDung ten={t.ten} chucNang={t.chucNang} />,
        })),
        { path: '403', element: <Trang403 /> },
        { path: '*', element: <Trang404 /> },
      ],
    },
  ]
}

export const router = createBrowserRouter(taoRoutes())
