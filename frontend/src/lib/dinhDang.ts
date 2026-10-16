/** Định dạng hiển thị theo chuẩn Việt Nam (frontend/CLAUDE.md mục Hiển thị). */

const NBSP = ' '
const KHONG_CO = '—'
const MUI_GIO_VN = 'Asia/Ho_Chi_Minh'

/**
 * Tiền VND: `125000.00` -> `125.000 ₫`. API trả tiền dạng chuỗi nên xử lý bằng BigInt, không qua float (không mất
 * chính xác với số lớn). Làm tròn half-up về đồng như backend (`core/tien.py`), số âm làm tròn ra xa số 0.
 * Giá trị thiếu hoặc không hợp lệ hiện `—`, không bao giờ hiện `NaN`.
 */
export function dinhDangTien(gia: string | number | null | undefined): string {
  const chuoi = typeof gia === 'number' ? (Number.isFinite(gia) ? String(gia) : '') : (gia ?? '').trim()
  const khop = /^(-?)(\d+)(?:\.(\d+))?$/.exec(chuoi)
  if (!khop) return KHONG_CO
  const [, dau, nguyen, le = ''] = khop
  let dong = BigInt(nguyen)
  if (le !== '' && le[0] >= '5') dong += 1n
  const nhom = dong.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  return `${dong === 0n ? '' : dau}${nhom}${NBSP}₫`
}

export type KieuNgay = 'ngay' | 'gio' | 'ngayGio' | 'ngayGioGiay'

function hopLeNgayThuan(nam: number, thang: number, ngay: number): boolean {
  const d = new Date(Date.UTC(nam, thang - 1, ngay))
  return d.getUTCFullYear() === nam && d.getUTCMonth() === thang - 1 && d.getUTCDate() === ngay
}

/**
 * Ngày giờ theo múi giờ Asia/Ho_Chi_Minh. Chuỗi ngày thuần `YYYY-MM-DD` (hạn sử dụng) giữ nguyên, không dịch múi
 * giờ và không có giờ. Chuỗi giờ không kèm múi giờ được hiểu là UTC, vì backend lưu và trả UTC.
 */
export function dinhDangNgay(gia: string | Date | null | undefined, kieu: KieuNgay = 'ngay'): string {
  if (gia == null || gia === '') return KHONG_CO

  if (typeof gia === 'string') {
    const thuan = /^(\d{4})-(\d{2})-(\d{2})$/.exec(gia)
    if (thuan) {
      const [, nam, thang, ngay] = thuan
      if (!hopLeNgayThuan(Number(nam), Number(thang), Number(ngay))) return KHONG_CO
      return kieu === 'gio' ? KHONG_CO : `${ngay}/${thang}/${nam}`
    }
  }

  const coMuiGio = typeof gia !== 'string' || /(Z|[+-]\d{2}:?\d{2})$/i.test(gia)
  const thoiDiem = gia instanceof Date ? gia : new Date(coMuiGio ? gia : `${gia}Z`)
  if (Number.isNaN(thoiDiem.getTime())) return KHONG_CO

  const phan = Object.fromEntries(
    new Intl.DateTimeFormat('vi-VN', {
      timeZone: MUI_GIO_VN,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hourCycle: 'h23',
    })
      .formatToParts(thoiDiem)
      .map((p) => [p.type, p.value]),
  )
  const ngayStr = `${phan.day}/${phan.month}/${phan.year}`
  const gioStr = `${phan.hour}:${phan.minute}`
  if (kieu === 'ngay') return ngayStr
  if (kieu === 'gio') return gioStr
  return `${ngayStr} ${gioStr}${kieu === 'ngayGioGiay' ? `:${phan.second}` : ''}`
}
