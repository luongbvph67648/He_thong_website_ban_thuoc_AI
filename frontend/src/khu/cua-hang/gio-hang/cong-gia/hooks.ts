import { App } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../../api/client'
import { goi, thongDiepChung } from '../../../../api/goi'
import { maDonTuGiaoDich } from '../thanhToanOnline'

export type GiaoDichGia = {
  giao_dich: string
  ma_don: string
  so_tien: number
  cong: 'vnpay' | 'momo' | string
  trang_thai: string
  het_han_luc?: string | null
}

const TOI_DA_GIAY_MAC_DINH = 15 * 60
const CHO_QUAY_VE_MS = 2500

/** Số giây còn lại đến hạn thanh toán của đơn (mặc định 15 phút nếu đơn không có hạn). */
export function useDemNguoc(hetHanLuc: string | null | undefined): number {
  const [han] = useState(() => (hetHanLuc ? Date.parse(hetHanLuc) : Date.now() + TOI_DA_GIAY_MAC_DINH * 1000))
  const conLai = () => Math.max(0, Math.round((han - Date.now()) / 1000))
  const [giay, datGiay] = useState(conLai)
  useEffect(() => {
    const id = window.setInterval(() => datGiay(conLai()), 1000)
    return () => window.clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [han])
  return giay
}

export type KetQua = { thanhCong: boolean; lyDo?: string }

/**
 * Gửi IPN giả cho giao dịch (cổng thật cũng báo kết quả cho máy chủ qua IPN, không qua trình duyệt), hiện kết quả vài
 * giây rồi đưa khách về trang kết quả đơn, nơi trạng thái luôn đọc lại từ máy chủ.
 */
export function useHoanTat(giaoDich: string) {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [dang, datDang] = useState(false)
  const [ketQua, datKetQua] = useState<KetQua | null>(null)
  const veTrangKetQua = () => navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(maDonTuGiaoDich(giaoDich))}`)

  useEffect(() => {
    if (!ketQua) return
    const id = window.setTimeout(veTrangKetQua, CHO_QUAY_VE_MS)
    return () => window.clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ketQua])

  async function hoanTat(thanhCong: boolean, lyDo?: string) {
    datDang(true)
    const r = await goi(() => api.POST('/api/v1/webhook/gia-ipn', { body: { giao_dich: giaoDich, thanh_cong: thanhCong } }))
    datDang(false)
    if (!r.ok) {
      void message.error(thongDiepChung(r.loi))
      return
    }
    datKetQua({ thanhCong, lyDo })
  }
  return { dang, ketQua, hoanTat, veTrangKetQua }
}

