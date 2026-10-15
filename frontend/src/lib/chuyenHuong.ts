/**
 * Đường dẫn quay lại sau khi đăng nhập (`?tiep=/gio-hang`). Chỉ nhận đường dẫn nội bộ: bắt đầu bằng đúng một `/`,
 * không phải `//host`, `/\host` hay URL tuyệt đối, để không bị lợi dụng làm trang đăng nhập chuyển người dùng sang
 * trang lừa đảo (open redirect).
 */
export function duongTiepTheo(tham: string | null, macDinh = '/'): string {
  if (!tham || !tham.startsWith('/') || tham.startsWith('//') || tham.includes('\\')) return macDinh
  // Ký tự điều khiển (xuống dòng, tab...) bị trình duyệt bỏ đi khi phân tích URL, nên `/\t/host` thành `//host`.
  // eslint-disable-next-line no-control-regex
  if (/[\u0000-\u001f\u007f]/.test(tham)) return macDinh
  if (tham.startsWith('/dang-nhap') || tham.startsWith('/dang-ky') || tham.startsWith('/quen-mat-khau')) return macDinh
  return tham
}
