import { useMutation } from '@tanstack/react-query'
import { Alert, App, Button, Space } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { donViRaApi, donViTuApi, kiemTraDonVi, loiDonViTuApi, type DonViForm } from '../../../lib/sanPham'
import { BangDonVi } from './BangDonVi'
import { THONG_DIEP_XUNG_DOT, type SanPhamChiTiet } from './sanPham'

interface Props {
  ban: SanPhamChiTiet
  coQuyenGhi: boolean
  capNhat: (ban: SanPhamChiTiet) => void
  lamMoi: () => Promise<unknown>
}

/** Tab "Đơn vị và giá": sửa tại chỗ cả danh sách rồi lưu một lần (máy chủ thay cả danh sách trong một giao dịch). */
export function TabDonVi({ ban, coQuyenGhi, capNhat, lamMoi }: Props) {
  const { message } = App.useApp()
  const [donVi, setDonVi] = useState<DonViForm[]>(() => ban.don_vi.map(donViTuApi))
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiMayChu, setLoiMayChu] = useState<ReturnType<typeof loiDonViTuApi> | null>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const thay = useMutation({
    mutationFn: (danhSach: DonViForm[]) =>
      goi(() =>
        api.PUT('/api/v1/noi-bo/san-pham/{san_pham_id}/don-vi', {
          params: { path: { san_pham_id: ban.id } },
          body: { phien_ban: ban.phien_ban, don_vi: danhSach.map(donViRaApi) },
        }),
      ),
  })

  const luu = async () => {
    setThongDiep(null)
    setLoiMayChu(null)
    setDaThuLuu(true)
    if (kiemTraDonVi(donVi).coLoi) return setThongDiep('Còn thông tin chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')
    const kq = await thay.mutateAsync(donVi)
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return setThongDiep(THONG_DIEP_XUNG_DOT)
      }
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      if (Object.keys(theoTruong).length > 0) {
        setLoiMayChu(loiDonViTuApi(theoTruong))
        return setThongDiep('Máy chủ từ chối một số thông tin, hãy xem các ô báo đỏ.')
      }
      return setThongDiep(thongDiepChung(kq.loi))
    }
    setDonVi(kq.data.don_vi.map(donViTuApi))
    setDaThuLuu(false)
    capNhat(kq.data)
    void message.success('Đã lưu đơn vị và giá bán')
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Alert
        type="info"
        showIcon
        title="Đơn vị cơ sở (hệ số 1) là đơn vị tính tồn kho. Đơn vị lớn hơn quy ra số đơn vị cơ sở (ví dụ hộp = 100 viên). Sản phẩm đã có lô hàng thì không đổi được hệ số."
      />
      {thongDiep && <Alert type="error" showIcon title={thongDiep} />}
      <BangDonVi
        value={donVi}
        onChange={(v) => {
          setDonVi(v)
          setLoiMayChu(null)
        }}
        loi={loiMayChu ?? (daThuLuu ? kiemTraDonVi(donVi) : null)}
        disabled={!coQuyenGhi || thay.isPending}
      />
      {coQuyenGhi && (
        <Button type="primary" loading={thay.isPending} onClick={() => void luu()}>
          Lưu đơn vị
        </Button>
      )}
    </Space>
  )
}
