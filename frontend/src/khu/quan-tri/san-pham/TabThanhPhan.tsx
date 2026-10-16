import { useMutation } from '@tanstack/react-query'
import { Alert, App, Button, Space } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import { chuoiHoacNull } from '../../../lib/duLieuChung'
import { kiemTraThanhPhan, khoaMoi, loiThanhPhanTuApi, type ThanhPhanForm } from '../../../lib/sanPham'
import { BangThanhPhan } from './BangThanhPhan'
import { THONG_DIEP_XUNG_DOT, type SanPhamChiTiet } from './sanPham'

interface Props {
  ban: SanPhamChiTiet
  coQuyenGhi: boolean
  capNhat: (ban: SanPhamChiTiet) => void
  lamMoi: () => Promise<unknown>
}

const tuApi = (ban: SanPhamChiTiet): ThanhPhanForm[] =>
  ban.thanh_phan.map((t) => ({ khoa: `${khoaMoi()}-${t.hoat_chat_id}`, hoat_chat_id: t.hoat_chat_id, ten_hoat_chat: t.ten_hoat_chat, ham_luong: t.ham_luong ?? '' }))

/** Tab "Thành phần": hoạt chất và hàm lượng, lưu cả danh sách một lần. */
export function TabThanhPhan({ ban, coQuyenGhi, capNhat, lamMoi }: Props) {
  const { message } = App.useApp()
  const [ds, setDs] = useState<ThanhPhanForm[]>(() => tuApi(ban))
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiMayChu, setLoiMayChu] = useState<ReturnType<typeof loiThanhPhanTuApi> | null>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const thay = useMutation({
    mutationFn: (danhSach: ThanhPhanForm[]) =>
      goi(() =>
        api.PUT('/api/v1/noi-bo/san-pham/{san_pham_id}/thanh-phan', {
          params: { path: { san_pham_id: ban.id } },
          body: {
            phien_ban: ban.phien_ban,
            thanh_phan: danhSach.map((t) => ({ hoat_chat_id: t.hoat_chat_id as number, ham_luong: chuoiHoacNull(t.ham_luong) })),
          },
        }),
      ),
  })

  const luu = async () => {
    setThongDiep(null)
    setLoiMayChu(null)
    setDaThuLuu(true)
    if (kiemTraThanhPhan(ds).coLoi) return setThongDiep('Còn thông tin chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')
    const kq = await thay.mutateAsync(ds)
    if (!kq.ok) {
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await lamMoi()
        return setThongDiep(THONG_DIEP_XUNG_DOT)
      }
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      if (Object.keys(theoTruong).length > 0) {
        setLoiMayChu(loiThanhPhanTuApi(theoTruong))
        return setThongDiep('Máy chủ từ chối một số thông tin, hãy xem các ô báo đỏ.')
      }
      return setThongDiep(thongDiepChung(kq.loi))
    }
    setDs(tuApi(kq.data))
    setDaThuLuu(false)
    capNhat(kq.data)
    void message.success('Đã lưu thành phần')
  }

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} />}
      <BangThanhPhan
        value={ds}
        onChange={(v) => {
          setDs(v)
          setLoiMayChu(null)
        }}
        loi={loiMayChu ?? (daThuLuu ? kiemTraThanhPhan(ds) : null)}
        disabled={!coQuyenGhi || thay.isPending}
      />
      {coQuyenGhi && (
        <Button type="primary" loading={thay.isPending} onClick={() => void luu()}>
          Lưu thành phần
        </Button>
      )}
    </Space>
  )
}
