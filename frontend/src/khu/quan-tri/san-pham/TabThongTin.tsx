import { useMutation } from '@tanstack/react-query'
import { Alert, App, Button, Space } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { FormThongTin } from './FormThongTin'
import { THONG_DIEP_XUNG_DOT, type SanPhamChiTiet, type SanPhamSua, type TuyChonDanhMuc } from './sanPham'
import { thongTinRaSua, thongTinTuApi } from './thongTin'
import { useThongTin } from './useThongTin'

interface Props {
  ban: SanPhamChiTiet
  cay: TuyChonDanhMuc[]
  coQuyenGhi: boolean
  capNhat: (ban: SanPhamChiTiet) => void
  lamMoi: () => Promise<SanPhamChiTiet | undefined>
}

/**
 * Tab "Thông tin": chỉ gửi những trường người dùng đã đổi so với lúc mở (không gửi cả form), kèm `phien_ban` đã thấy.
 * Gặp xung đột thì tải bản mới nhưng giữ nguyên chữ đang gõ.
 */
export function TabThongTin({ ban, cay, coQuyenGhi, capNhat, lamMoi }: Props) {
  const { message } = App.useApp()
  const [goc, setGoc] = useState(() => thongTinTuApi(ban))
  const tt = useThongTin(goc)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const sua = useMutation({
    mutationFn: (body: SanPhamSua) =>
      goi(() => api.PATCH('/api/v1/noi-bo/san-pham/{san_pham_id}', { params: { path: { san_pham_id: ban.id } }, body })),
  })

  const luu = async () => {
    setThongDiep(null)
    if (!tt.batDauLuu()) return setThongDiep('Còn thông tin chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')
    const thayDoi = thongTinRaSua(tt.giaTri, goc)
    if (Object.keys(thayDoi).length === 0) return void message.info('Chưa có thay đổi nào để lưu')
    const kq = await sua.mutateAsync({ phien_ban: ban.phien_ban, ...thayDoi })
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return setThongDiep(THONG_DIEP_XUNG_DOT)
      }
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      tt.datLoiMayChu(theoTruong)
      return setThongDiep(Object.keys(theoTruong).length > 0 ? 'Máy chủ từ chối một số thông tin, hãy xem các ô báo đỏ.' : thongDiepChung(kq.loi))
    }
    const moi = thongTinTuApi(kq.data)
    setGoc(moi)
    tt.datLai(moi)
    capNhat(kq.data)
    void message.success('Đã lưu thông tin sản phẩm')
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} />}
      {tt.loiKhac.map((l) => (
        <Alert key={l} type="error" showIcon title={l} />
      ))}
      <FormThongTin value={tt.giaTri} onChange={tt.doi} loi={tt.loi} cay={cay} disabled={!coQuyenGhi || sua.isPending} />
      {coQuyenGhi && (
        <Button type="primary" loading={sua.isPending} onClick={() => void luu()}>
          Lưu thông tin
        </Button>
      )}
    </Space>
  )
}
