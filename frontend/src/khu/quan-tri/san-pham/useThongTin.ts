import { useState } from 'react'
import { kiemTraThongTin, loiThongTinTuApi, type GiaTriThongTin } from './thongTin'

type Loi = Partial<Record<keyof GiaTriThongTin, string>>

/**
 * Trạng thái của các ô thông tin (dùng cho form tạo và tab "Thông tin"): giá trị, lỗi kiểm tra phía giao diện (chỉ hiện
 * sau lần bấm lưu đầu để khỏi báo lỗi khi form mới mở) và lỗi máy chủ. Lỗi máy chủ của ô nào mất khi ô đó được sửa.
 */
export function useThongTin(khoiTao: GiaTriThongTin) {
  const [giaTri, setGiaTri] = useState(khoiTao)
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiMayChu, setLoiMayChu] = useState<Loi>({})
  const [loiKhac, setLoiKhac] = useState<string[]>([])

  const doi = (moi: GiaTriThongTin) => {
    setLoiMayChu((cu) => {
      const con = { ...cu }
      for (const k of Object.keys(moi) as (keyof GiaTriThongTin)[]) if (moi[k] !== giaTri[k]) delete con[k]
      return con
    })
    setGiaTri(moi)
  }

  return {
    giaTri,
    doi,
    loi: { ...(daThuLuu ? kiemTraThongTin(giaTri) : {}), ...loiMayChu } as Loi,
    loiKhac,
    /** Gọi khi bấm Lưu: bật hiển thị lỗi và xóa lỗi máy chủ cũ; trả `true` nếu các ô hợp lệ. */
    batDauLuu: () => {
      setDaThuLuu(true)
      setLoiMayChu({})
      setLoiKhac([])
      return Object.keys(kiemTraThongTin(giaTri)).length === 0
    },
    /** Gắn lỗi máy chủ (`loiTheoTruong`) vào ô; phần không thuộc ô nào trả về cho nơi gọi. */
    datLoiMayChu: (theoTruong: Record<string, string>) => {
      const { theoO, khac } = loiThongTinTuApi(theoTruong)
      setLoiMayChu(theoO)
      setLoiKhac(khac)
    },
    /** Đặt lại toàn bộ (sau khi lưu thành công hoặc khi sản phẩm đổi). */
    datLai: (g: GiaTriThongTin) => {
      setGiaTri(g)
      setDaThuLuu(false)
      setLoiMayChu({})
      setLoiKhac([])
    },
  }
}
