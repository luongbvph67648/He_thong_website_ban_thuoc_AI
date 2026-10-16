import type { components } from '../api/schema'

/** Logic thuần cho trang Cấu hình (AD08). Backend kiểm tra lại toàn bộ; đây chỉ để báo lỗi ngay khi gõ. */
export type MucCauHinh = components['schemas']['CauHinhDoc']

const KHOA_CHUNG = 'gia_tri'
const GIO = /^([01][0-9]|2[0-3]):[0-5][0-9]$/ // [0-9] chứ không phải \d: \d của JS chỉ nhận ASCII nhưng giữ đồng nhất với backend

const dinhDangSo = (n: number) => n.toLocaleString('vi-VN')

function laSoNguyen(v: unknown): v is number {
  return typeof v === 'number' && Number.isSafeInteger(v)
}

function loiKhoang(toiThieu: number, toiDa: number, donVi: string | null): string {
  return `Phải là số nguyên từ ${dinhDangSo(toiThieu)} đến ${dinhDangSo(toiDa)}${donVi ? ` ${donVi}` : ''}`
}

const laDoiTuong = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)

/** Lỗi theo trường (`gia_tri` cho lỗi chung); bảng rỗng là hợp lệ. */
export function kiemTraGiaTri(muc: MucCauHinh, giaTri: unknown): Record<string, string> {
  const loi: Record<string, string> = {}
  if (muc.kieu === 'so' || muc.kieu === 'tien') {
    if (!laSoNguyen(giaTri) || giaTri < (muc.toi_thieu ?? 0) || giaTri > (muc.toi_da ?? 0)) {
      loi[KHOA_CHUNG] = loiKhoang(muc.toi_thieu ?? 0, muc.toi_da ?? 0, muc.don_vi)
    }
    return loi
  }
  if (muc.kieu === 'nhom_so') {
    if (!laDoiTuong(giaTri)) return { [KHOA_CHUNG]: `Phải gồm các trường: ${muc.truong.map((t) => t.ten).join(', ')}` }
    for (const t of muc.truong) {
      const v = giaTri[t.ten]
      if (v === undefined) loi[t.ten] = 'Thiếu trường này'
      else if (!laSoNguyen(v) || v < t.toi_thieu || v > t.toi_da) loi[t.ten] = loiKhoang(t.toi_thieu, t.toi_da, t.don_vi)
    }
    return loi
  }
  if (!laDoiTuong(giaTri)) return { [KHOA_CHUNG]: 'Giá trị không hợp lệ' }
  const { bat_dau: batDau, ket_thuc: ketThuc, ngay_trong_tuan: ngay } = giaTri
  const gioOk = (g: unknown): g is string => typeof g === 'string' && GIO.test(g)
  if (!gioOk(batDau)) loi.bat_dau = 'Phải có dạng HH:MM, từ 00:00 đến 23:59'
  if (!gioOk(ketThuc)) loi.ket_thuc = 'Phải có dạng HH:MM, từ 00:00 đến 23:59'
  else if (gioOk(batDau) && batDau >= ketThuc) loi.ket_thuc = 'Giờ kết thúc phải sau giờ bắt đầu'
  if (!Array.isArray(ngay) || ngay.length === 0 || !ngay.every((n) => laSoNguyen(n) && n >= 1 && n <= 7) || new Set(ngay).size !== ngay.length) {
    loi.ngay_trong_tuan = 'Chọn ít nhất một ngày trong tuần'
  }
  return loi
}

function chuanHoa(v: unknown): unknown {
  if (Array.isArray(v)) return v.map(chuanHoa)
  if (laDoiTuong(v)) return Object.fromEntries(Object.keys(v).sort().map((k) => [k, chuanHoa(v[k])]))
  return v
}

/** So hai giá trị JSON theo nội dung (không phụ thuộc thứ tự khóa của đối tượng; thứ tự của danh sách có nghĩa). */
export function bangNhau(a: unknown, b: unknown): boolean {
  return JSON.stringify(chuanHoa(a) ?? null) === JSON.stringify(chuanHoa(b) ?? null) && (a === undefined) === (b === undefined)
}

/** Lỗi `chi_tiet: [{truong, loi}]` của máy chủ thành bảng theo trường (bỏ tiền tố `gia_tri.`). */
export function loiTheoTruongCauHinh(chiTiet: unknown): Record<string, string> {
  if (!Array.isArray(chiTiet)) return {}
  const ket: Record<string, string> = {}
  for (const c of chiTiet) {
    if (laDoiTuong(c) && typeof c.truong === 'string' && typeof c.loi === 'string') ket[c.truong.replace(/^gia_tri\./, '')] = c.loi
  }
  return ket
}

/** Nhóm theo chủ đề, giữ thứ tự xuất hiện của nhóm và của khóa trong nhóm (máy chủ đã xếp sẵn). */
export function nhomTheoChuDe(ds: readonly MucCauHinh[]): [string, MucCauHinh[]][] {
  const nhom = new Map<string, MucCauHinh[]>()
  for (const m of ds) nhom.set(m.nhom, [...(nhom.get(m.nhom) ?? []), m])
  return [...nhom.entries()]
}
