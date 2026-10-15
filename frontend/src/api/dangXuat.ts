import { usePhien } from '../stores/phien'
import { api } from './client'

/** Đăng xuất nhân viên: như khách nhưng gọi endpoint nội bộ (cookie refresh riêng, Path `/api/v1/noi-bo/auth`). */
export async function dangXuatNoiBo(): Promise<void> {
  try {
    await api.POST('/api/v1/noi-bo/auth/dang-xuat')
  } catch {
    // Mất mạng: vẫn xóa phiên phía trình duyệt.
  }
  usePhien.getState().dangXuat()
}

/** Đăng xuất khách: thu hồi phiên trên máy chủ (xóa cookie refresh) rồi xóa phiên trong bộ nhớ, kể cả khi gọi lỗi. */
export async function dangXuatKhach(): Promise<void> {
  try {
    await api.POST('/api/v1/auth/dang-xuat')
  } catch {
    // Mất mạng: phiên phía trình duyệt vẫn bị xóa; refresh token còn hạn tới khi hết hạn hoặc đăng nhập lại.
  }
  usePhien.getState().dangXuat()
}
