/** Trang của khu cửa hàng ngoài trang chủ, theo docs/spec/09-frontend.md mục 2.1. Trang thật thay dần ở T1.x–T6.x. */
export interface TrangCuaHang {
  duong: string
  ten: string
  chucNang: readonly string[]
}

export const TRANG_CUA_HANG: readonly TrangCuaHang[] = [
  { duong: '/danh-muc/:slug', ten: 'Danh sách theo danh mục', chucNang: ['KVL02'] },
  { duong: '/san-pham/:slug', ten: 'Chi tiết sản phẩm', chucNang: ['KVL03', 'KTV10', 'KTV15'] },
  { duong: '/tim-kiem', ten: 'Kết quả tìm kiếm', chucNang: ['KVL04'] },
  { duong: '/gio-hang', ten: 'Giỏ hàng', chucNang: ['KVL07'] },
  { duong: '/thanh-toan', ten: 'Thanh toán', chucNang: ['KTV02', 'KTV03', 'KTV04'] },
  { duong: '/thanh-toan/ket-qua', ten: 'Kết quả thanh toán', chucNang: ['KTV03'] },
  { duong: '/thanh-toan-gia', ten: 'Cổng thanh toán giả (dev)', chucNang: ['KTV03'] },
  { duong: '/gui-don-thuoc', ten: 'Gửi đơn thuốc', chucNang: ['KVL08', 'KTV07'] },
  { duong: '/xac-nhan-don/:token', ten: 'Xác nhận đơn từ đơn thuốc', chucNang: ['DS05', 'KTV07'] },
  { duong: '/tra-cuu-anh', ten: 'Tra cứu thuốc bằng ảnh', chucNang: ['KVL06'] },
  { duong: '/bai-viet', ten: 'Bài viết', chucNang: ['KVL11'] },
  { duong: '/bai-viet/:slug', ten: 'Chi tiết bài viết', chucNang: ['KVL11'] },
  { duong: '/chinh-sach/:slug', ten: 'Chính sách', chucNang: ['KVL11'] },
  { duong: '/hoi-dap', ten: 'Hỏi đáp', chucNang: ['KVL11'] },
  { duong: '/dang-ky', ten: 'Đăng ký tài khoản', chucNang: ['KVL09'] },
  { duong: '/dang-nhap', ten: 'Đăng nhập', chucNang: ['KVL10'] },
  { duong: '/quen-mat-khau', ten: 'Quên mật khẩu', chucNang: ['KVL10'] },
  { duong: '/tai-khoan', ten: 'Tài khoản của tôi', chucNang: ['KTV01'] },
  { duong: '/tai-khoan/don-hang', ten: 'Đơn hàng của tôi', chucNang: ['KTV05', 'KTV06', 'KTV08', 'KTV09'] },
  { duong: '/tai-khoan/don-hang/:ma', ten: 'Chi tiết đơn hàng', chucNang: ['KTV05', 'KTV06', 'KTV08', 'KTV09'] },
  { duong: '/tai-khoan/don-thuoc', ten: 'Đơn thuốc của tôi', chucNang: ['KTV07'] },
  { duong: '/tai-khoan/doi-tra', ten: 'Yêu cầu đổi trả của tôi', chucNang: ['KTV09'] },
  { duong: '/tai-khoan/danh-gia', ten: 'Đánh giá của tôi', chucNang: ['KTV10'] },
  { duong: '/tai-khoan/suc-khoe', ten: 'Hồ sơ sức khỏe', chucNang: ['KTV11'] },
  { duong: '/tai-khoan/thong-bao', ten: 'Thông báo', chucNang: ['KTV13', 'KTV14'] },
]
