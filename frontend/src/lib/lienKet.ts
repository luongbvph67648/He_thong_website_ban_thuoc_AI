/**
 * Liên kết do dữ liệu quyết định (banner, tệp hướng dẫn sử dụng): chỉ nhận đường dẫn nội bộ `/...` hoặc `http(s)://...`.
 * `javascript:`, `data:`, `//host` (giao thức tương đối) và đường dẫn có ký tự điều khiển bị bỏ, không bao giờ vào `href`.
 */
// eslint-disable-next-line no-control-regex
const KY_TU_CAM = /[\u0000-\u001f\u007f\s\\]/

export function laLienKetNgoai(url: string): boolean {
  return /^https?:\/\//i.test(url)
}

export function lienKetAnToan(url: string | null | undefined): string | null {
  if (!url || KY_TU_CAM.test(url)) return null
  if (url.startsWith('/')) return url.startsWith('//') ? null : url
  if (/^https?:\/\/[^/]/i.test(url)) {
    try {
      const u = new URL(url)
      return u.protocol === 'http:' || u.protocol === 'https:' ? url : null
    } catch {
      return null
    }
  }
  return null
}
