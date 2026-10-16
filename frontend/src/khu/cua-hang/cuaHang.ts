/**
 * Logic thuần của khu cửa hàng (KVL01–KVL03): bộ lọc trên URL, tham số gọi API, tính số sao. Không đụng DOM nên có test
 * bảng ca (`cuaHang.test.ts`). Quy tắc hợp lệ khớp backend (`modules/cua_hang/router.py`, spec 06 mục 3.13).
 */
import type { components } from '../../api/schema'

export type SanPhamThe = components['schemas']['SanPhamThe']
export type SanPhamChiTiet = components['schemas']['SanPhamChiTietCongKhai']
export type DanhMucNut = components['schemas']['DanhMucCongKhai']
export type BoLocApi = components['schemas']['BoLocSanPham']
export type LoaiSanPham = SanPhamThe['loai_san_pham']
export type NguonXem = 'trang_chu' | 'danh_muc' | 'tim_kiem' | 'goi_y_tuong_tu' | 'mua_kem' | 'danh_cho_ban' | 'chat_ai'
const NGUON_XEM: readonly NguonXem[] = ['trang_chu', 'danh_muc', 'tim_kiem', 'goi_y_tuong_tu', 'mua_kem', 'danh_cho_ban', 'chat_ai']

/** `?nguon=` do liên kết nội bộ gắn; giá trị lạ bị bỏ để không gửi lên API yêu cầu chắc chắn bị 400. */
export function docNguonXem(gia: string | null): NguonXem | undefined {
  return NGUON_XEM.find((n) => n === gia)
}

export const KHOA_QUERY_CUA_HANG = ['cua-hang'] as const
export const KICH_THUOC_TRANG = 12

export const LOAI_SAN_PHAM: readonly { value: LoaiSanPham; label: string }[] = [
  { value: 'thuoc_ke_don', label: 'Thuốc kê đơn' },
  { value: 'thuoc_khong_ke_don', label: 'Thuốc không kê đơn' },
  { value: 'thuc_pham_chuc_nang', label: 'Thực phẩm chức năng' },
  { value: 'duoc_my_pham', label: 'Dược mỹ phẩm' },
  { value: 'thiet_bi_y_te', label: 'Thiết bị y tế' },
]

export const SAP_XEP = [
  { value: 'moi', label: 'Mới nhất' },
  { value: 'ban_chay', label: 'Bán chạy' },
  { value: 'gia_tang', label: 'Giá tăng dần' },
  { value: 'gia_giam', label: 'Giá giảm dần' },
  { value: 'ten', label: 'Tên A–Z' },
] as const
export type SapXep = (typeof SAP_XEP)[number]['value']

export interface BoLocUrl {
  loai?: LoaiSanPham
  thuongHieu: number[]
  giaTu?: number
  giaDen?: number
  doiTuong?: string
  conHang: boolean
  sapXep: SapXep
  trang: number
}

const TOI_DA_THUONG_HIEU = 20
const GIA_TOI_DA = 10 ** 12
const ID_TOI_DA = 2_147_483_647

function soNguyenDuong(gia: string | null, toiDa: number, choPhepKhong = false): number | undefined {
  if (gia === null || !/^\d{1,13}$/.test(gia)) return undefined
  const so = Number(gia)
  return so <= toiDa && (choPhepKhong || so > 0) ? so : undefined
}

/** Đọc bộ lọc từ URL; giá trị lạ hoặc ngoài miền bị bỏ qua (URL do người dùng gõ có thể sai tùy ý). */
export function docBoLoc(tham: URLSearchParams): BoLocUrl {
  const loai = LOAI_SAN_PHAM.find((l) => l.value === tham.get('loai'))?.value
  const thuongHieu = [...new Set(tham.getAll('thuong_hieu').map((x) => soNguyenDuong(x, ID_TOI_DA)))]
    .filter((x): x is number => x !== undefined)
    .slice(0, TOI_DA_THUONG_HIEU)
  const doiTuong = (tham.get('doi_tuong') ?? '').trim().slice(0, 100)
  return {
    loai,
    thuongHieu,
    giaTu: soNguyenDuong(tham.get('gia_tu'), GIA_TOI_DA, true),
    giaDen: soNguyenDuong(tham.get('gia_den'), GIA_TOI_DA, true),
    doiTuong: doiTuong && !doiTuong.includes('\0') ? doiTuong : undefined,
    conHang: tham.get('con_hang') === '1',
    sapXep: SAP_XEP.find((s) => s.value === tham.get('sap_xep'))?.value ?? 'moi',
    trang: soNguyenDuong(tham.get('trang'), 1_000_000) ?? 1,
  }
}

/** Tham số gọi `GET /api/v1/san-pham`. `giaTu > giaDen` thì đổi chỗ (người dùng gõ ngược) để không dính 400. */
export function taoQuerySanPham(boLoc: BoLocUrl, danhMuc?: string) {
  const [giaTu, giaDen] =
    boLoc.giaTu !== undefined && boLoc.giaDen !== undefined && boLoc.giaTu > boLoc.giaDen
      ? [boLoc.giaDen, boLoc.giaTu]
      : [boLoc.giaTu, boLoc.giaDen]
  return {
    danh_muc: danhMuc,
    loai: boLoc.loai,
    thuong_hieu_id: boLoc.thuongHieu.length ? boLoc.thuongHieu : undefined,
    gia_tu: giaTu,
    gia_den: giaDen,
    doi_tuong: boLoc.doiTuong,
    con_hang: boLoc.conHang || undefined,
    sap_xep: boLoc.sapXep,
    trang: boLoc.trang,
    kich_thuoc: KICH_THUOC_TRANG,
  }
}

export type ThayDoiLoc = Partial<{
  loai: LoaiSanPham | undefined
  thuongHieu: number[]
  giaTu: number | undefined
  giaDen: number | undefined
  doiTuong: string | undefined
  conHang: boolean
  sapXep: SapXep
  trang: number
}>

/** URL mới sau khi đổi bộ lọc. Đổi bất kỳ bộ lọc nào (trừ chính `trang`) đưa về trang 1; giá trị mặc định không ghi lên URL. */
export function capNhatThamSo(tham: URLSearchParams, thayDoi: ThayDoiLoc): URLSearchParams {
  const hienTai = docBoLoc(tham)
  const moi = { ...hienTai, ...thayDoi }
  if (!('trang' in thayDoi)) moi.trang = 1
  const ra = new URLSearchParams()
  if (moi.loai) ra.set('loai', moi.loai)
  for (const id of moi.thuongHieu) ra.append('thuong_hieu', String(id))
  if (moi.giaTu !== undefined) ra.set('gia_tu', String(moi.giaTu))
  if (moi.giaDen !== undefined) ra.set('gia_den', String(moi.giaDen))
  if (moi.doiTuong) ra.set('doi_tuong', moi.doiTuong)
  if (moi.conHang) ra.set('con_hang', '1')
  if (moi.sapXep !== 'moi') ra.set('sap_xep', moi.sapXep)
  if (moi.trang > 1) ra.set('trang', String(moi.trang))
  return ra
}

/** Số bộ lọc đang bật (không tính sắp xếp và trang), để hiện nút "Xóa bộ lọc" và huy hiệu. */
export function soBoLocDangDung(boLoc: BoLocUrl): number {
  return (
    (boLoc.loai ? 1 : 0) +
    (boLoc.thuongHieu.length ? 1 : 0) +
    (boLoc.giaTu !== undefined || boLoc.giaDen !== undefined ? 1 : 0) +
    (boLoc.doiTuong ? 1 : 0) +
    (boLoc.conHang ? 1 : 0)
  )
}

/** Điểm trung bình (một chữ số thập phân, dấu phẩy kiểu VN) từ tổng sao và số đánh giá; `null` khi chưa có đánh giá. */
export function diemTrungBinh(tongSao: number, soLuong: number): string | null {
  if (soLuong <= 0) return null
  return (Math.round((tongSao / soLuong) * 10) / 10).toFixed(1).replace('.', ',')
}

export const DONG_KHONG_PHAI_THUOC = 'Thực phẩm này không phải là thuốc, không có tác dụng thay thế thuốc chữa bệnh.'

/** Các mục nội dung chuyên môn theo thứ tự hiển thị (spec 06 mục 3.12). */
export const MUC_NOI_DUNG_CHUYEN_MON = [
  ['chi_dinh', 'Chỉ định'],
  ['chong_chi_dinh', 'Chống chỉ định'],
  ['lieu_dung_tham_khao', 'Liều dùng tham khảo'],
  ['tac_dung_phu', 'Tác dụng phụ'],
  ['than_trong', 'Thận trọng'],
  ['tuong_tac_thuoc', 'Tương tác thuốc'],
  ['phu_nu_co_thai_cho_con_bu', 'Phụ nữ có thai, cho con bú'],
  ['tre_em', 'Trẻ em'],
  ['qua_lieu_xu_tri', 'Quá liều và xử trí'],
  ['bao_quan', 'Bảo quản'],
] as const
