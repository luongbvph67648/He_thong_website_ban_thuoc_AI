/** Phép tính thuần trên cây danh mục (AD03) cho kéo thả: không phụ thuộc React, antd hay API nên test được từng ca. */

/** Số cấp tối đa của cây danh mục (spec 05 mục AD03; backend cũng kiểm tra). */
export const SO_CAP_TOI_DA = 3

export interface NutCay {
  id: number
  ten: string
  con: NutCay[]
}

/** Vị trí đích theo đúng nghĩa của `PUT /noi-bo/danh-muc/{id}/vi-tri`: cha mới (null là gốc) và chỉ số trong các anh em SAU KHI bỏ nút đang kéo. */
export interface ViTriMoi {
  chaId: number | null
  viTri: number
}

/** Thả phía trên nút đích (`truoc`), phía dưới (`sau`) hay vào trong làm con (`trong`). */
export type HuongTha = 'truoc' | 'trong' | 'sau'

export interface KetQuaTim<T extends NutCay> {
  nut: T
  /** `null` nếu là nút gốc. */
  cha: T | null
  /** 1 đến 3. */
  cap: number
}

export function timNut<T extends NutCay>(cay: readonly T[], id: number, cha: T | null = null, cap = 1): KetQuaTim<T> | null {
  for (const nut of cay) {
    if (nut.id === id) return { nut, cha, cap }
    const trongCon = timNut(nut.con as T[], id, nut, cap + 1)
    if (trongCon) return trongCon
  }
  return null
}

/** Số cấp của cây con gốc `nut`, tính cả chính nó (lá là 1). */
export function chieuCao(nut: NutCay): number {
  return 1 + Math.max(0, ...nut.con.map(chieuCao))
}

/** `id` có nằm trong cây con của `nut` (kể cả chính `nut`) không. */
export function namTrongCayCon(nut: NutCay, id: number): boolean {
  return nut.id === id || nut.con.some((c) => namTrongCayCon(c, id))
}

/**
 * Vị trí đích khi kéo `idKeo` và thả vào/gần `idDich`. `null` khi không xác định được (id không có trong cây hoặc kéo vào
 * chính nó). Thả `trong` thì thành con cuối của đích.
 */
export function tinhViTriTha<T extends NutCay>(cay: readonly T[], idKeo: number, idDich: number, huong: HuongTha): ViTriMoi | null {
  if (idKeo === idDich) return null
  const dich = timNut(cay, idDich)
  if (!dich || !timNut(cay, idKeo)) return null
  if (huong === 'trong') return { chaId: dich.nut.id, viTri: dich.nut.con.filter((c) => c.id !== idKeo).length }
  const anhEm = (dich.cha ? dich.cha.con : cay).filter((c) => c.id !== idKeo)
  const chiSoDich = anhEm.findIndex((c) => c.id === idDich)
  return { chaId: dich.cha?.id ?? null, viTri: huong === 'truoc' ? chiSoDich : chiSoDich + 1 }
}

/** Lý do không thả được (để chặn ngay trên giao diện), hoặc `null` nếu hợp lệ. Backend vẫn kiểm tra lại. */
export function lyDoKhongThaDuoc<T extends NutCay>(cay: readonly T[], idKeo: number, idDich: number, huong: HuongTha): string | null {
  const keo = timNut(cay, idKeo)
  const dich = timNut(cay, idDich)
  if (!keo || !dich) return 'Không tìm thấy danh mục'
  if (idKeo === idDich) return 'Không thể thả danh mục vào chính nó'
  const vt = tinhViTriTha(cay, idKeo, idDich, huong)
  if (!vt) return 'Không xác định được vị trí thả'
  if (vt.chaId !== null && namTrongCayCon(keo.nut, vt.chaId)) return 'Không thể chuyển danh mục vào danh mục con của nó'
  const capMoi = vt.chaId === null ? 1 : (timNut(cay, vt.chaId)?.cap ?? 0) + 1
  if (capMoi + chieuCao(keo.nut) - 1 > SO_CAP_TOI_DA) return `Danh mục chỉ có tối đa ${SO_CAP_TOI_DA} cấp`
  return null
}

/** Thả đúng chỗ cũ (cùng cha, cùng chỉ số) thì không cần gọi API. */
export function giuNguyenViTri<T extends NutCay>(cay: readonly T[], idKeo: number, vt: ViTriMoi): boolean {
  const keo = timNut(cay, idKeo)
  if (!keo) return false
  const anhEm = keo.cha ? keo.cha.con : cay
  return (keo.cha?.id ?? null) === vt.chaId && anhEm.findIndex((c) => c.id === idKeo) === Math.min(vt.viTri, anhEm.length - 1)
}

/** Mọi `id` có con (để mở sẵn cả cây lần đầu). */
export function idCoCon(cay: readonly NutCay[]): number[] {
  return cay.flatMap((n) => (n.con.length ? [n.id, ...idCoCon(n.con)] : []))
}
