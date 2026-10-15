import type { ItemType } from 'antd/es/menu/interface'
import { Link } from 'react-router-dom'
import type { MucDieuHuong } from '../lib/dieuHuong'
import { coMotTrong, type QuyenCuaToi } from '../lib/quyen'

export function duongDayDu(goc: string, duong: string) {
  return duong === '/' ? goc : goc + duong
}

/** Menu chỉ gồm mục người dùng có quyền (mức xem trở lên), gom theo nhóm theo thứ tự xuất hiện. */
export function xayMenu(goc: string, muc: readonly MucDieuHuong[], quyen: QuyenCuaToi): ItemType[] {
  const theoNhom = new Map<string, ItemType[]>()
  for (const m of muc) {
    if (m.trongMenu === false || !coMotTrong(quyen, m.quyen, 'xem')) continue
    const key = duongDayDu(goc, m.duong)
    const ds = theoNhom.get(m.nhom ?? '') ?? []
    ds.push({ key, label: <Link to={key}>{m.nhan}</Link> })
    theoNhom.set(m.nhom ?? '', ds)
  }
  return [...theoNhom].map(([nhom, children]) =>
    nhom ? { type: 'group' as const, key: `nhom:${nhom}`, label: nhom, children } : (children[0] as ItemType),
  )
}
