import { docGoiY, xoaGoiY } from '../lib/goiYPhien'
import { usePhien } from '../stores/phien'
import { api } from './client'
import { lamMoiPhien } from './xacThuc'

async function chay(): Promise<void> {
  const loai = docGoiY()
  if (loai === null) return
  if (loai !== 'khach') {
    // Phiên nội bộ được khôi phục cùng đăng nhập nội bộ (T1.3).
    xoaGoiY()
    return
  }
  const { token, hetPhien } = await lamMoiPhien('khach')
  if (!token) {
    if (hetPhien) xoaGoiY() // lỗi mạng thì giữ gợi ý để lần tải sau thử lại
    return
  }
  try {
    const { data } = await api.GET('/api/v1/toi', { headers: { Authorization: `Bearer ${token}` } })
    if (data) {
      usePhien.getState().dangNhap({ accessToken: token, loai: 'khach', hoSo: { id: data.id, hoTen: data.ho_ten }, quyen: {} })
    }
  } catch {
    // Mất mạng giữa chừng: coi như chưa đăng nhập, lần tải sau sẽ thử lại.
  }
}

let dangChay: Promise<void> | null = null

/**
 * Lấy lại phiên đăng nhập của khách khi tải trang (QĐ-08): refresh token nằm trong cookie httpOnly nên JS không thấy;
 * có "gợi ý" đã đăng nhập thì gọi làm mới rồi lấy hồ sơ. Chỉ chạy một lần mỗi lần tải trang (làm mới hai lần bằng cùng
 * một cookie sẽ bị coi là dùng lại token cũ), kể cả khi React StrictMode gọi hai lần.
 */
export function khoiPhucPhien(): Promise<void> {
  dangChay ??= chay().finally(() => usePhien.setState({ daKhoiPhuc: true }))
  return dangChay
}
