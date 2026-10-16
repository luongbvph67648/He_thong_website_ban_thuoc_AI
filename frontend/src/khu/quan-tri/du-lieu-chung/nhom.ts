/** Ba nhóm dữ liệu dùng chung của AD05: cấu hình hiển thị và ô nhập (hằng và hàm thuần, không phải component). */

export type MaNhom = 'thuong-hieu' | 'nha-san-xuat' | 'hoat-chat'

/** Mọi truy vấn của AD05 nằm dưới khóa này: làm mới một lần là cả ba nhóm cập nhật. */
export const KHOA_QUERY_DU_LIEU_CHUNG = ['noi-bo', 'du-lieu-chung'] as const

/** Một dòng của bất kỳ nhóm nào: các trường riêng của nhóm là tùy chọn (lấy từ schema API của nhóm đó). */
export interface BanGhi {
  id: number
  ten: string
  created_at: string
  so_san_pham: number
  logo_url?: string | null
  quoc_gia?: string | null
  ten_khac?: string | null
  mo_ta?: string | null
}

/** Giá trị form: mọi ô là chuỗi (rỗng nghĩa là không có). */
export type GiaTriForm = Record<string, string>

export interface TruongForm {
  ten: keyof BanGhi
  nhan: string
  /** `url`: đường dẫn `/...` hoặc `http(s)://...`; `van_ban`: một dòng; `nhieu_dong`: xuống dòng được. */
  loai: 'ten' | 'url' | 'van_ban' | 'nhieu_dong'
  toiDa: number
}

export interface CauHinhNhom {
  ma: MaNhom
  /** Nhãn của tab. */
  nhan: string
  /** Danh từ số ít trong thông điệp và tiêu đề hộp thoại, ví dụ "thương hiệu". */
  danhTu: string
  truong: readonly TruongForm[]
  /** Nhóm mà `so_san_pham` đếm đủ lý do chặn xóa (hoạt chất còn có thể nằm trong tương tác và hồ sơ dị ứng mà Admin không thấy). */
  dem_du_de_chan_xoa: boolean
}

export const CAC_NHOM: readonly CauHinhNhom[] = [
  {
    ma: 'thuong-hieu',
    nhan: 'Thương hiệu',
    danhTu: 'thương hiệu',
    truong: [
      { ten: 'ten', nhan: 'Tên thương hiệu', loai: 'ten', toiDa: 150 },
      { ten: 'logo_url', nhan: 'Đường dẫn logo (không bắt buộc)', loai: 'url', toiDa: 500 },
    ],
    dem_du_de_chan_xoa: true,
  },
  {
    ma: 'nha-san-xuat',
    nhan: 'Nhà sản xuất',
    danhTu: 'nhà sản xuất',
    truong: [
      { ten: 'ten', nhan: 'Tên nhà sản xuất', loai: 'ten', toiDa: 200 },
      { ten: 'quoc_gia', nhan: 'Quốc gia (không bắt buộc)', loai: 'van_ban', toiDa: 100 },
    ],
    dem_du_de_chan_xoa: true,
  },
  {
    ma: 'hoat-chat',
    nhan: 'Hoạt chất',
    danhTu: 'hoạt chất',
    truong: [
      { ten: 'ten', nhan: 'Tên hoạt chất', loai: 'ten', toiDa: 200 },
      { ten: 'ten_khac', nhan: 'Tên khác (không bắt buộc, dùng để tìm kiếm)', loai: 'van_ban', toiDa: 1000 },
      { ten: 'mo_ta', nhan: 'Mô tả (không bắt buộc)', loai: 'nhieu_dong', toiDa: 2000 },
    ],
    dem_du_de_chan_xoa: false,
  },
]

export function layNhom(ma: string | null): CauHinhNhom {
  return CAC_NHOM.find((n) => n.ma === ma) ?? CAC_NHOM[0]
}

/** Trường backend cho sắp xếp (spec 06 mục 3.10); giá trị khác trên URL bị bỏ qua. */
export const TRUONG_SAP_XEP = ['ten', 'created_at', 'so_san_pham'] as const
export type TruongSapXep = (typeof TRUONG_SAP_XEP)[number]

export function docSapXep(gia: string | null): { truong: TruongSapXep; giam: boolean } | null {
  const truong = gia?.replace(/^-/, '')
  return TRUONG_SAP_XEP.find((t) => t === truong) ? { truong: truong as TruongSapXep, giam: gia!.startsWith('-') } : null
}

/** Lý do không xóa được dựa trên số liệu đang hiển thị, hoặc `null` (backend vẫn quyết định cuối cùng). */
export function lyDoKhongXoa(nhom: CauHinhNhom, ban: Pick<BanGhi, 'so_san_pham'>): string | null {
  return nhom.dem_du_de_chan_xoa && ban.so_san_pham > 0 ? `Đang gắn với ${ban.so_san_pham} sản phẩm` : null
}
