/** Nhãn và màu thống nhất cho trạng thái (docs/spec/09-frontend.md mục 3), khớp enum trong ERD và OpenAPI. */

export type LoaiTrangThai = 'don_hang' | 'thanh_toan' | 'kenh_ban' | 'loai_san_pham' | 'kinh_doanh' | 'noi_dung' | 'muc_do_tuong_tac'

export interface NhanHienThi {
  nhan: string
  /** Màu `Tag` của Ant Design. */
  mau: string
}

export const TRANG_THAI: Record<LoaiTrangThai, Record<string, NhanHienThi>> = {
  don_hang: {
    cho_khach_xac_nhan: { nhan: 'Chờ khách xác nhận', mau: 'gold' },
    cho_thanh_toan: { nhan: 'Chờ thanh toán', mau: 'gold' },
    cho_xac_nhan: { nhan: 'Chờ xác nhận', mau: 'processing' },
    da_xac_nhan: { nhan: 'Đã xác nhận', mau: 'processing' },
    dang_soan_hang: { nhan: 'Đang soạn hàng', mau: 'processing' },
    cho_lay_hang: { nhan: 'Chờ lấy hàng', mau: 'processing' },
    dang_giao: { nhan: 'Đang giao', mau: 'blue' },
    da_giao: { nhan: 'Đã giao', mau: 'success' },
    hoan_tat: { nhan: 'Hoàn tất', mau: 'success' },
    giao_that_bai: { nhan: 'Giao thất bại', mau: 'error' },
    hoan_ve_kho: { nhan: 'Hoàn về kho', mau: 'orange' },
    da_huy: { nhan: 'Đã hủy', mau: 'default' },
  },
  thanh_toan: {
    chua_thanh_toan: { nhan: 'Chưa thanh toán', mau: 'default' },
    da_thanh_toan: { nhan: 'Đã thanh toán', mau: 'success' },
    cho_hoan_tien: { nhan: 'Chờ hoàn tiền', mau: 'gold' },
    hoan_tien_mot_phan: { nhan: 'Hoàn tiền một phần', mau: 'orange' },
    da_hoan_tien: { nhan: 'Đã hoàn tiền', mau: 'purple' },
  },
  kenh_ban: {
    online: { nhan: 'Website', mau: 'blue' },
    dien_thoai: { nhan: 'Điện thoại', mau: 'cyan' },
    tai_quay: { nhan: 'Tại quầy', mau: 'geekblue' },
  },
  loai_san_pham: {
    thuoc_ke_don: { nhan: 'Thuốc kê đơn', mau: 'red' },
    thuoc_khong_ke_don: { nhan: 'Thuốc không kê đơn', mau: 'green' },
    thuc_pham_chuc_nang: { nhan: 'Thực phẩm chức năng', mau: 'cyan' },
    duoc_my_pham: { nhan: 'Dược mỹ phẩm', mau: 'magenta' },
    thiet_bi_y_te: { nhan: 'Thiết bị y tế', mau: 'blue' },
  },
  kinh_doanh: {
    dang_kinh_doanh: { nhan: 'Đang kinh doanh', mau: 'success' },
    ngung_kinh_doanh: { nhan: 'Ngừng kinh doanh', mau: 'default' },
  },
  noi_dung: {
    nhap: { nhan: 'Bản nháp', mau: 'processing' },
    da_duyet: { nhan: 'Đang hiển thị', mau: 'success' },
    luu_tru: { nhan: 'Đã lưu trữ', mau: 'default' },
  },
  muc_do_tuong_tac: {
    nhe: { nhan: 'Nhẹ', mau: 'blue' },
    trung_binh: { nhan: 'Trung bình', mau: 'gold' },
    nghiem_trong: { nhan: 'Nghiêm trọng', mau: 'orange' },
    chong_chi_dinh: { nhan: 'Chống chỉ định', mau: 'red' },
  },
}

/** Giá trị lạ (backend thêm trạng thái mới trước khi frontend kịp cập nhật) hiện nguyên văn, không làm vỡ trang. */
export function nhanTrangThai(loai: LoaiTrangThai, giaTri: string | null | undefined): NhanHienThi {
  if (!giaTri) return { nhan: '—', mau: 'default' }
  return TRANG_THAI[loai][giaTri] ?? { nhan: giaTri, mau: 'default' }
}
