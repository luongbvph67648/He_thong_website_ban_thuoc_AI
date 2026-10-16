/** Kiểu dữ liệu và khóa query của phần nội dung website phía khách (KVL11). */
import type { components } from '../../api/schema'

export type BaiVietTomTatCongKhai = components['schemas']['BaiVietCongKhaiTomTat']
export type BaiVietCongKhai = components['schemas']['BaiVietCongKhai']
export type LoaiBaiCongKhai = BaiVietCongKhai['loai']

export const KHOA_QUERY_BAI_VIET = ['cua-hang', 'bai-viet'] as const
export const KICH_THUOC_DS_BAI = 9

/** Đường dẫn công khai của một bài theo loại: bài sức khỏe, chính sách; FAQ chỉ có một trang chung. */
export function duongDanBai(loai: LoaiBaiCongKhai, slug: string): string {
  const goc = encodeURIComponent(slug)
  if (loai === 'chinh_sach') return `/chinh-sach/${goc}`
  if (loai === 'faq') return '/hoi-dap'
  return `/bai-viet/${goc}`
}
