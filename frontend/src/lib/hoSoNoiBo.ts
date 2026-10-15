import type { components } from '../api/schema'
import type { HoSoPhien } from '../stores/phien'
import type { QuyenCuaToi } from './quyen'

export type NhanVienToi = components['schemas']['NhanVienToi']

/** Đổi hồ sơ nhân viên từ API (`/noi-bo/toi`, đăng nhập, đổi mật khẩu) sang dạng lưu trong store phiên. */
export function phienTuNhanVien(nv: NhanVienToi): { hoSo: HoSoPhien; quyen: QuyenCuaToi; phaiDoiMatKhau: boolean } {
  return {
    hoSo: {
      id: nv.id,
      hoTen: nv.ho_ten,
      vaiTro: nv.vai_tro.ma,
      maNhanVien: nv.ma_nhan_vien,
      email: nv.email,
      soDienThoai: nv.so_dien_thoai,
    },
    quyen: nv.quyen,
    phaiDoiMatKhau: nv.phai_doi_mat_khau,
  }
}

/** Trang tài khoản cá nhân của nhân viên: hồ sơ và đổi mật khẩu (dùng chung cho cả ba vai trò). */
export const DUONG_TAI_KHOAN_NOI_BO = '/nhan-vien/tai-khoan'
export const DUONG_DANG_NHAP_NOI_BO = '/nhan-vien/dang-nhap'
