/**
 * Mã phiên của khách vãng lai, dùng để ghi lịch sử xem sản phẩm (header `X-Ma-Phien`, spec 06 mục 3.13).
 * Chuỗi ngẫu nhiên 22 ký tự `[A-Za-z0-9_-]`, lưu ở localStorage để giữ giữa các lần tải trang. KHÔNG chứa thông tin cá
 * nhân và không dùng cho xác thực. Trình duyệt chặn lưu trữ thì mỗi lần một mã mới (hoặc `null` nếu cũng không có crypto).
 */
const KHOA = 'ma_phien_khach'
export const MAU_MA_PHIEN = /^[A-Za-z0-9_-]{8,64}$/

function sinhMaPhien(): string | null {
  try {
    const byte = new Uint8Array(16)
    globalThis.crypto.getRandomValues(byte)
    return btoa(String.fromCharCode(...byte))
      .replaceAll('+', '-')
      .replaceAll('/', '_')
      .replaceAll('=', '')
  } catch {
    return null
  }
}

export function layMaPhien(): string | null {
  try {
    const cu = globalThis.localStorage.getItem(KHOA)
    if (cu && MAU_MA_PHIEN.test(cu)) return cu
  } catch {
    // bỏ qua: dùng mã tạm bên dưới
  }
  const moi = sinhMaPhien()
  if (moi) {
    try {
      globalThis.localStorage.setItem(KHOA, moi)
    } catch {
      // không lưu được: mã chỉ sống trong lần gọi này
    }
  }
  return moi
}
