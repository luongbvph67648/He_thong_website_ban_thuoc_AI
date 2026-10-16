/** Hằng và hàm dùng chung của các file AD04 (không phải component nên tách khỏi `.tsx`). */
import type { components } from '../../../api/schema'
import { TRANG_THAI, type NhanHienThi } from '../../../lib/trangThai'
import type { NutCay } from '../danh-muc/cayDanhMuc'

export type SanPhamTomTat = components['schemas']['SanPhamTomTat']
export type SanPhamChiTiet = components['schemas']['SanPhamChiTiet']
export type SanPhamSua = components['schemas']['SanPhamSua']
export type NutDanhMuc = components['schemas']['DanhMucNut']
export type LoaiSanPham = components['schemas']['LoaiSanPham']
export type TrangThaiKinhDoanh = components['schemas']['TrangThaiKinhDoanh']

/** Mọi truy vấn của AD04 nằm dưới khóa này: làm mới một lần là cả danh sách lẫn chi tiết cùng cập nhật. */
export const KHOA_QUERY_SAN_PHAM = ['noi-bo', 'san-pham'] as const

const tuyChon = <T extends string>(bang: Record<string, NhanHienThi>) => Object.entries(bang).map(([value, { nhan }]) => ({ value: value as T, label: nhan }))
export const TUY_CHON_LOAI = tuyChon<LoaiSanPham>(TRANG_THAI.loai_san_pham)
export const TUY_CHON_KINH_DOANH = tuyChon<TrangThaiKinhDoanh>(TRANG_THAI.kinh_doanh)

export interface TuyChonDanhMuc {
  value: number
  title: string
  children: TuyChonDanhMuc[]
}

/** Cây danh mục thành dữ liệu cho `TreeSelect` (danh mục đang ẩn có chú thích để Admin biết). */
export function cayChoTreeSelect(cay: readonly (NutDanhMuc & NutCay)[]): TuyChonDanhMuc[] {
  return cay.map((n) => ({
    value: n.id,
    title: n.dang_hien_thi ? n.ten : `${n.ten} (đang ẩn)`,
    children: cayChoTreeSelect(n.con),
  }))
}

export const THONG_DIEP_XUNG_DOT =
  'Sản phẩm vừa được người khác thay đổi. Đã tải bản mới; giá trị bạn nhập vẫn được giữ nguyên, hãy kiểm tra rồi bấm Lưu lần nữa.'

/** Truy vấn chi tiết một sản phẩm. Khóa lạc quan cần `phien_ban` là bản người dùng đã thấy, nên chi tiết không tự làm mới. */
export const khoaChiTiet = (id: number) => [...KHOA_QUERY_SAN_PHAM, 'chi-tiet', id] as const
