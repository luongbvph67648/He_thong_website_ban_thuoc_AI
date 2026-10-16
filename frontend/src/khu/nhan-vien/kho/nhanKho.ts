import type { components } from '../../../api/schema'

export const NHAN_TRANG_THAI_LO: Record<components['schemas']['TrangThaiLo'], { nhan: string; mau: string }> = {
  dang_ban: { nhan: 'Đang bán', mau: 'green' },
  can_han: { nhan: 'Cận hạn', mau: 'orange' },
  khoa: { nhan: 'Khóa', mau: 'default' },
  het_han: { nhan: 'Hết hạn', mau: 'red' },
  thu_hoi: { nhan: 'Thu hồi', mau: 'volcano' },
}
