import { useQueryClient } from '@tanstack/react-query'
import { App, Button } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { KHOA_GIO_HANG, NHAN_LY_DO } from '../gio-hang/gioHang'

/** KTV08: đưa các dòng của đơn cũ vào giỏ; dòng không mua lại được (thuốc kê đơn, ngừng bán...) báo kèm lý do. */
export default function MuaLaiNut({ maDon, tenTheoId = {} }: { maDon: string; tenTheoId?: Record<number, string> }) {
  const { message, modal } = App.useApp()
  const qc = useQueryClient()
  const dieuHuong = useNavigate()
  const [dang, setDang] = useState(false)

  async function muaLai() {
    setDang(true)
    const r = await goi(() => api.POST('/api/v1/toi/don-hang/{ma_don}/mua-lai', { params: { path: { ma_don: maDon } } }))
    setDang(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void qc.invalidateQueries({ queryKey: KHOA_GIO_HANG })
    const boQua = r.data.bo_qua
    if (boQua.length === 0) {
      void message.success('Đã thêm các sản phẩm vào giỏ hàng')
      return void dieuHuong('/gio-hang')
    }
    modal.warning({
      title: 'Một số sản phẩm không thêm vào giỏ được',
      content: (
        <ul style={{ paddingLeft: 20, margin: 0 }}>
          {boQua.map((b) => (
            <li key={`${b.san_pham_id}-${b.don_vi_id}`}>{tenTheoId[b.san_pham_id] ?? `Sản phẩm #${b.san_pham_id}`}: {NHAN_LY_DO[b.ly_do]}</li>
          ))}
        </ul>
      ),
      okText: 'Xem giỏ hàng',
      onOk: () => dieuHuong('/gio-hang'),
    })
  }

  return <Button loading={dang} onClick={() => void muaLai()}>Mua lại</Button>
}
