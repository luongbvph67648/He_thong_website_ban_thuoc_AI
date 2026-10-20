import { App } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../../api/client'
import { goi, thongDiepChung } from '../../../../api/goi'
import { maDonTuGiaoDich } from '../thanhToanOnline'

/** Nguồn của giao dịch ở máy chủ MÔ PHỎNG (`mo_phong`): URL thanh toán đã ký của VNPay, hoặc token trong `payUrl` của MoMo. */
export type NguonMoPhong = { cong: 'vnpay'; query: string } | { cong: 'momo'; token: string }

export type GiaoDichGia = {
  giao_dich: string
  ma_don: string
  so_tien: number
  cong: 'vnpay' | 'momo' | string
  trang_thai: string
  het_han_luc?: string | null
  /** Có khi chạy với máy chủ mô phỏng: kết quả gửi cho đối tác mô phỏng (IPN đúng giao thức) thay vì cổng giả. */
  nguon?: NguonMoPhong
}

/** Kết quả khách chọn trên trang đối tác mô phỏng (mã theo từng cổng, xem `tich_hop/mo_phong/`). */
export type MaKetQua = 'thanh_cong' | 'khach_huy' | 'khong_du_so_du' | 'the_chua_dang_ky' | 'sai_otp' | 'tu_choi'

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
 * Báo kết quả thanh toán cho đối tác (cổng thật cũng báo cho máy chủ cửa hàng qua IPN, không qua trình duyệt), hiện kết
 * quả vài giây rồi đưa khách về trang kết quả đơn, nơi trạng thái luôn đọc lại từ máy chủ. Chế độ `gia`: IPN giả ký
 * bằng khóa giả; chế độ `mo_phong`: máy chủ mô phỏng gửi IPN đúng định dạng VNPay/MoMo rồi trả `ReturnUrl` có chữ ký.
 */
export function useHoanTat(giaoDich: string, nguon?: NguonMoPhong) {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [dang, datDang] = useState(false)
  const [ketQua, datKetQua] = useState<KetQua | null>(null)
  const [diaChiVe, datDiaChiVe] = useState<string | null>(null)
  const veTrangKetQua = () => {
    if (diaChiVe) window.location.assign(diaChiVe) // ReturnUrl/redirectUrl của cổng, mang tham số đã ký
    else navigate(`/thanh-toan/ket-qua?ma=${encodeURIComponent(maDonTuGiaoDich(giaoDich))}`)
  }

  useEffect(() => {
    if (!ketQua) return
    const id = window.setTimeout(veTrangKetQua, CHO_QUAY_VE_MS)
    return () => window.clearTimeout(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ketQua])

  async function hoanTat(thanhCong: boolean, lyDo?: string, ma?: MaKetQua, nganHang = 'NCB') {
    datDang(true)
    if (nguon?.cong === 'vnpay') {
      const kq = await goi(() =>
        api.POST('/api/v1/mo-phong/vnpay/thanh-toan', {
          body: { query: nguon.query, ngan_hang: nganHang, ket_qua: ma === 'tu_choi' || !ma ? (thanhCong ? 'thanh_cong' : 'khach_huy') : ma },
        }),
      )
      datDang(false)
      if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
      datDiaChiVe(kq.data.redirect_url)
    } else if (nguon?.cong === 'momo') {
      const kq = await goi(() =>
        api.POST('/api/v1/mo-phong/momo/thanh-toan', {
          body: { token: nguon.token, ket_qua: thanhCong ? 'thanh_cong' : 'tu_choi' },
        }),
      )
      datDang(false)
      if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
      datDiaChiVe(kq.data.redirect_url)
    } else {
      const r = await goi(() => api.POST('/api/v1/webhook/gia-ipn', { body: { giao_dich: giaoDich, thanh_cong: thanhCong } }))
      datDang(false)
      if (!r.ok) return void message.error(thongDiepChung(r.loi))
    }
    datKetQua({ thanhCong, lyDo })
  }
  return { dang, ketQua, hoanTat, veTrangKetQua }
}
