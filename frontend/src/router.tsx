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
import TrangChiTietSanPhamCuaHang from './khu/cua-hang/TrangChiTietSanPham'
import TrangDanhMucCuaHang from './khu/cua-hang/TrangDanhMuc'
import TrangTimKiem from './khu/cua-hang/TrangTimKiem'
import TrangBaiViet from './khu/cua-hang/TrangBaiViet'
import TrangDanhSachBaiViet from './khu/cua-hang/TrangDanhSachBaiViet'
import TrangHoiDap from './khu/cua-hang/TrangHoiDap'
import NhanVienLayout, { TrangDauNhanVien } from './khu/nhan-vien/NhanVienLayout'
import TrangBaiVietChoDuyet from './khu/nhan-vien/chuyen-mon/TrangBaiVietChoDuyet'
import TrangNoiDungChuyenMon from './khu/nhan-vien/chuyen-mon/TrangNoiDungChuyenMon'
import TrangSoanNoiDung from './khu/nhan-vien/chuyen-mon/TrangSoanNoiDung'
import TrangTuongTac from './khu/nhan-vien/chuyen-mon/TrangTuongTac'
import TrangBaoCaoNxt from './khu/nhan-vien/kho/TrangBaoCaoNxt'
import TrangGioHang from './khu/cua-hang/gio-hang/TrangGioHang'
import TrangChiTietDonCuaToi from './khu/cua-hang/don-hang/TrangChiTietDonCuaToi'
import TrangDonHangCuaToi from './khu/cua-hang/don-hang/TrangDonHangCuaToi'
import TrangKetQuaDatHang from './khu/cua-hang/gio-hang/TrangKetQuaDatHang'
import TrangCongGia from './khu/cua-hang/gio-hang/TrangCongGia'
import TrangThanhToan from './khu/cua-hang/gio-hang/TrangThanhToan'
import TrangThongBao from './khu/cua-hang/thong-bao/TrangThongBao'
import TrangDanhGiaCuaToi from './khu/cua-hang/danh-gia/TrangDanhGiaCuaToi'
import TrangKiemDuyet from './khu/nhan-vien/kiem-duyet/TrangKiemDuyet'
import TrangHangTraVe from './khu/nhan-vien/hang-tra-ve/TrangHangTraVe'
import TrangXuLyDoiTra from './khu/nhan-vien/doi-tra/TrangXuLyDoiTra'
import TrangDoiTraCuaToi from './khu/cua-hang/doi-tra/TrangDoiTraCuaToi'
import TrangPos from './khu/nhan-vien/pos/TrangPos'
import TrangDuyetDonThuoc from './khu/nhan-vien/don-thuoc/TrangDuyetDonThuoc'
import TrangHangChoDonThuoc from './khu/nhan-vien/don-thuoc/TrangHangChoDonThuoc'
import TrangDonThuocCuaToi from './khu/cua-hang/don-thuoc/TrangDonThuocCuaToi'
import TrangXacNhanDon from './khu/cua-hang/don-thuoc/TrangXacNhanDon'
import TrangGuiDonThuoc from './khu/cua-hang/don-thuoc/TrangGuiDonThuoc'
import TrangSucKhoe from './khu/cua-hang/tai-khoan/TrangSucKhoe'
import TrangTaiKhoan from './khu/cua-hang/tai-khoan/TrangTaiKhoan'
import TrangKhuyenMai from './khu/quan-tri/khuyen-mai/TrangKhuyenMai'
import TrangCanhBao from './khu/nhan-vien/kho/TrangCanhBao'
import TrangDieuChinh from './khu/nhan-vien/kho/TrangDieuChinh'
import TrangKiemKe from './khu/nhan-vien/kho/TrangKiemKe'
import TrangChiTietDon from './khu/nhan-vien/don-hang/TrangChiTietDon'
import TrangGiaoTaiQuay from './khu/nhan-vien/don-hang/TrangGiaoTaiQuay'
import TrangTaoDonHo from './khu/nhan-vien/don-hang/TrangTaoDonHo'
import TrangQuanLyDon from './khu/nhan-vien/don-hang/TrangQuanLyDon'
import TrangNhaCungCap from './khu/nhan-vien/kho/TrangNhaCungCap'
import TrangPhieuSoan from './khu/nhan-vien/kho/TrangPhieuSoan'
import TrangSoanHang from './khu/nhan-vien/kho/TrangSoanHang'
import TrangPhieuKho from './khu/nhan-vien/kho/TrangPhieuKho'
import TrangPhieuNhap from './khu/nhan-vien/kho/TrangPhieuNhap'
import TrangTaoPhieuNhap from './khu/nhan-vien/kho/TrangTaoPhieuNhap'
import TrangTonKho from './khu/nhan-vien/kho/TrangTonKho'
import { MUC_NHAN_VIEN } from './khu/nhan-vien/menu'
import TrangDangNhapNoiBo from './khu/nhan-vien/TrangDangNhap'
import TrangTaiKhoanNoiBo from './khu/nhan-vien/TrangTaiKhoan'
import QuanTriLayout from './khu/quan-tri/QuanTriLayout'
import TrangNhanVien from './khu/quan-tri/nhan-vien/TrangNhanVien'
import TrangCauHinh from './khu/quan-tri/cau-hinh/TrangCauHinh'
import TrangChiTietKhachHang from './khu/quan-tri/khach-hang/TrangChiTietKhachHang'
import TrangDanhMuc from './khu/quan-tri/danh-muc/TrangDanhMuc'
import TrangDuLieuChung from './khu/quan-tri/du-lieu-chung/TrangDuLieuChung'
import TrangKhachHang from './khu/quan-tri/khach-hang/TrangKhachHang'
import TrangChiTietSanPham from './khu/quan-tri/san-pham/TrangChiTietSanPham'
import TrangSanPham from './khu/quan-tri/san-pham/TrangSanPham'
import TrangDuyetPhieu from './khu/quan-tri/duyet-phieu/TrangDuyetPhieu'
import TrangHoanTien from './khu/quan-tri/hoan-tien/TrangHoanTien'
import TrangNhatKy from './khu/quan-tri/nhat-ky/TrangNhatKy'
import TrangNoiDung from './khu/quan-tri/noi-dung/TrangNoiDung'
import TrangVaiTro from './khu/quan-tri/vai-tro/TrangVaiTro'
import { MUC_QUAN_TRI } from './khu/quan-tri/menu'

/** Route của một khu nội bộ: mỗi trang bọc `YeuCauQuyen` (mức xem; nút thao tác tự kiểm tra mức đầy đủ). */
function routeCuaKhu(muc: readonly MucDieuHuong[], trangThat: Record<string, ReactNode> = {}): RouteObject[] {
  return muc.map((m) => {
    const trang = (
      <YeuCauQuyen ma={m.quyen} muc="xem">
        {trangThat[m.duong] ?? <TrangDangXayDung ten={m.nhan} chucNang={m.chucNang} />}
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
  '/danh-muc/:slug': <TrangDanhMucCuaHang />,
  '/san-pham/:slug': <TrangChiTietSanPhamCuaHang />,
  '/tim-kiem': <TrangTimKiem />,
  '/bai-viet': <TrangDanhSachBaiViet />,
  '/bai-viet/:slug': <TrangBaiViet loai="bai_viet" />,
  '/chinh-sach/:slug': <TrangBaiViet loai="chinh_sach" />,
  '/hoi-dap': <TrangHoiDap />,
  '/gio-hang': <TrangGioHang />,
  '/thanh-toan': <TrangThanhToan />,
  '/thanh-toan/ket-qua': <TrangKetQuaDatHang />,
  '/thanh-toan-gia': <TrangCongGia />,
  '/tai-khoan': <TrangTaiKhoan />,
  '/gui-don-thuoc': <TrangGuiDonThuoc />,
  '/xac-nhan-don/:token': <TrangXacNhanDon />,
  '/tai-khoan/don-thuoc': <TrangDonThuocCuaToi />,
  '/tai-khoan/doi-tra': <TrangDoiTraCuaToi />,
  '/tai-khoan/danh-gia': <TrangDanhGiaCuaToi />,
  '/tai-khoan/thong-bao': <TrangThongBao />,
  '/tai-khoan/suc-khoe': <TrangSucKhoe />,
  '/tai-khoan/don-hang': <TrangDonHangCuaToi />,
  '/tai-khoan/don-hang/:ma': <TrangChiTietDonCuaToi />,
}

/** Trang khu nhân viên đã làm thật (khóa là đường dẫn trong `MUC_NHAN_VIEN`); còn lại là trang giữ chỗ. */
const TRANG_NHAN_VIEN_THAT: Record<string, ReactNode> = {
  '/noi-dung-chuyen-mon': <TrangNoiDungChuyenMon />,
  '/noi-dung-chuyen-mon/:id': <TrangSoanNoiDung />,
  '/tuong-tac': <TrangTuongTac />,
  '/bai-viet-cho-duyet': <TrangBaiVietChoDuyet />,
  '/don-hang': <TrangQuanLyDon />,
  '/don-hang/tao': <TrangTaoDonHo />,
  '/don-hang/:id': <TrangChiTietDon />,
  '/giao-tai-quay': <TrangGiaoTaiQuay />,
  '/pos': <TrangPos />,
  '/doi-tra': <TrangXuLyDoiTra />,
  '/hang-tra-ve': <TrangHangTraVe />,
  '/kiem-duyet': <TrangKiemDuyet />,
  '/don-thuoc': <TrangHangChoDonThuoc />,
  '/don-thuoc/:id': <TrangDuyetDonThuoc />,
  '/soan-hang': <TrangSoanHang />,
  '/soan-hang/:id': <TrangPhieuSoan />,
  '/nha-cung-cap': <TrangNhaCungCap />,
  '/phieu-nhap': <TrangPhieuNhap />,
  '/phieu-nhap/tao': <TrangTaoPhieuNhap />,
  '/ton-kho': <TrangTonKho />,
  '/canh-bao': <TrangCanhBao />,
  '/kiem-ke': <TrangKiemKe />,
  '/dieu-chinh': <TrangDieuChinh />,
  '/phieu-huy': <TrangPhieuKho loai="huy" />,
  '/xuat-tra': <TrangPhieuKho loai="xuat-tra" />,
  '/bao-cao-nxt': <TrangBaoCaoNxt />,
}

/** Trang khu quản trị đã làm thật (khóa là đường dẫn trong `MUC_QUAN_TRI`); còn lại là trang giữ chỗ. */
const TRANG_QUAN_TRI_THAT: Record<string, ReactNode> = {
  '/nhan-vien': <TrangNhanVien />,
  '/vai-tro': <TrangVaiTro />,
  '/khach-hang': <TrangKhachHang />,
  '/khach-hang/:id': <TrangChiTietKhachHang />,
  '/danh-muc': <TrangDanhMuc />,
  '/du-lieu-chung': <TrangDuLieuChung />,
  '/san-pham': <TrangSanPham />,
  '/san-pham/moi': <TrangChiTietSanPham />,
  '/san-pham/:id': <TrangChiTietSanPham />,
  '/noi-dung': <TrangNoiDung />,
  '/khuyen-mai': <TrangKhuyenMai />,
  '/cau-hinh': <TrangCauHinh />,
  '/nhat-ky': <TrangNhatKy />,
  '/duyet-phieu': <TrangDuyetPhieu />,
  '/hoan-tien': <TrangHoanTien />,
}

/** Toàn bộ route của ứng dụng (tách khỏi `createBrowserRouter` để test dựng bằng memory router). */
export function taoRoutes(): RouteObject[] {
  return [
    {
      path: '/nhan-vien/dang-nhap',
      element: <TrangDangNhapNoiBo />,
    },
    // Ngoài layout nhân viên/quản trị: dùng chung cho cả ba vai trò và là nơi tài khoản bị bắt đổi mật khẩu bị chuyển tới.
    {
      path: '/nhan-vien/tai-khoan',
      element: <TrangTaiKhoanNoiBo />,
    },
    {
      path: '/nhan-vien',
      element: <NhanVienLayout />,
      children: [
        { index: true, element: <TrangDauNhanVien /> },
        ...routeCuaKhu(MUC_NHAN_VIEN, TRANG_NHAN_VIEN_THAT),
        { path: '*', element: <Trang404 veTrang="/nhan-vien" nhanVe="Về trang đầu" /> },
      ],
    },
    {
      path: '/quan-tri',
      element: <QuanTriLayout />,
      children: [...routeCuaKhu(MUC_QUAN_TRI, TRANG_QUAN_TRI_THAT), { path: '*', element: <Trang404 veTrang="/quan-tri" nhanVe="Về tổng quan" /> }],
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
