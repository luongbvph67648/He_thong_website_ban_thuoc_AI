export type MucQuyen = 'day_du' | 'chi_xem'
/** Mức của một mã quyền trong vai trò; `null` là không có quyền đó. */
export type MucHoacKhong = MucQuyen | null

export interface ThayDoiQuyen {
  ma: string
  tu: MucHoacKhong
  den: MucHoacKhong
}

/** Các mã quyền có mức khác nhau giữa hai bản (theo thứ tự mã), để hiện tóm tắt trước khi lưu. */
export function tinhThayDoiQuyen(truoc: Record<string, MucHoacKhong>, sau: Record<string, MucHoacKhong>): ThayDoiQuyen[] {
  const ma = new Set([...Object.keys(truoc), ...Object.keys(sau)])
  return [...ma]
    .sort()
    .map((m) => ({ ma: m, tu: truoc[m] ?? null, den: sau[m] ?? null }))
    .filter((d) => d.tu !== d.den)
}

/** Thân `PUT /noi-bo/vai-tro/{ma}/quyen`: chỉ gửi mã có quyền, mã nào vắng mặt là bị gỡ. */
export function thanCapNhatQuyen(quyen: Record<string, MucHoacKhong>): Record<string, MucQuyen> {
  const than: Record<string, MucQuyen> = {}
  for (const [ma, muc] of Object.entries(quyen)) if (muc) than[ma] = muc
  return than
}

export function nhanMuc(muc: MucHoacKhong): string {
  return muc === 'day_du' ? 'Đầy đủ' : muc === 'chi_xem' ? 'Chỉ xem' : 'Không có'
}
