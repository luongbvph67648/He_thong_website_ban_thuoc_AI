import { Alert, App, Button, Card, Space } from 'antd'
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import {
  donViMoi,
  donViRaApi,
  kiemTraDonVi,
  kiemTraThanhPhan,
  loiDonViTuApi,
  loiThanhPhanTuApi,
  type DonViForm,
  type ThanhPhanForm,
} from '../../../lib/sanPham'
import { chuoiHoacNull } from '../../../lib/duLieuChung'
import { BangDonVi } from './BangDonVi'
import { BangThanhPhan } from './BangThanhPhan'
import { FormThongTin } from './FormThongTin'
import { KHOA_QUERY_SAN_PHAM } from './sanPham'
import { THONG_TIN_MAC_DINH, thongTinRaApi } from './thongTin'
import { useCayDanhMuc } from './useCayDanhMuc'
import { useThongTin } from './useThongTin'

/** Thêm sản phẩm (AD04): thông tin, đơn vị và thành phần cùng gửi trong MỘT lần để không có sản phẩm dở dang. */
export default function TaoSanPham() {
  const { message } = App.useApp()
  const dieuHuong = useNavigate()
  const queryClient = useQueryClient()
  const { tuyChon } = useCayDanhMuc()
  const tt = useThongTin(THONG_TIN_MAC_DINH)
  const [donVi, setDonVi] = useState<DonViForm[]>(() => [donViMoi({ he_so: 1 })])
  const [thanhPhan, setThanhPhan] = useState<ThanhPhanForm[]>([])
  const [daThuLuu, setDaThuLuu] = useState(false)
  const [loiDonVi, setLoiDonVi] = useState<ReturnType<typeof loiDonViTuApi> | null>(null)
  const [loiThanhPhan, setLoiThanhPhan] = useState<ReturnType<typeof loiThanhPhanTuApi> | null>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const tao = useMutation({
    mutationFn: () =>
      goi(() =>
        api.POST('/api/v1/noi-bo/san-pham', {
          body: {
            ...thongTinRaApi(tt.giaTri),
            don_vi: donVi.map(donViRaApi),
            thanh_phan: thanhPhan.map((t) => ({ hoat_chat_id: t.hoat_chat_id as number, ham_luong: chuoiHoacNull(t.ham_luong) })),
          },
        }),
      ),
  })

  const luu = async () => {
    setThongDiep(null)
    setLoiDonVi(null)
    setLoiThanhPhan(null)
    const thongTinHopLe = tt.batDauLuu()
    setDaThuLuu(true)
    const kd = kiemTraDonVi(donVi)
    const kt = kiemTraThanhPhan(thanhPhan)
    if (!thongTinHopLe || kd.coLoi || kt.coLoi) {
      setThongDiep('Còn thông tin chưa hợp lệ, hãy kiểm tra các ô báo đỏ.')
      return
    }
    const kq = await tao.mutateAsync()
    if (!kq.ok) {
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      tt.datLoiMayChu(theoTruong)
      setLoiDonVi(loiDonViTuApi(Object.fromEntries(Object.entries(theoTruong).filter(([k]) => k.startsWith('don_vi')))))
      setLoiThanhPhan(loiThanhPhanTuApi(Object.fromEntries(Object.entries(theoTruong).filter(([k]) => k.startsWith('thanh_phan')))))
      setThongDiep(Object.keys(theoTruong).length > 0 ? 'Máy chủ từ chối một số thông tin, hãy xem các ô báo đỏ.' : thongDiepChung(kq.loi))
      return
    }
    void message.success('Đã thêm sản phẩm')
    void queryClient.invalidateQueries({ queryKey: [...KHOA_QUERY_SAN_PHAM, 'danh-sach'] })
    // `..` theo đường dẫn: từ `/quan-tri/san-pham/moi` về `/quan-tri/san-pham/<id>`, giữ tiền tố của khu.
    dieuHuong(`../${kq.data.id}`, { relative: 'path', replace: true })
  }

  return (
    <div>
      <Space orientation="vertical" size={16} style={{ width: '100%' }}>
        {thongDiep && <Alert type="error" showIcon title={thongDiep} />}
        {tt.loiKhac.map((l) => (
          <Alert key={l} type="error" showIcon title={l} />
        ))}
        <Card title="Thông tin">
          <FormThongTin value={tt.giaTri} onChange={tt.doi} loi={tt.loi} cay={tuyChon} disabled={tao.isPending} />
        </Card>
        <Card title="Đơn vị và giá bán">
          <BangDonVi value={donVi} onChange={(v) => { setDonVi(v); setLoiDonVi(null) }} loi={loiDonVi ?? (daThuLuu ? { ...kiemTraDonVi(donVi) } : null)} disabled={tao.isPending} />
        </Card>
        <Card title="Thành phần">
          <BangThanhPhan value={thanhPhan} onChange={(v) => { setThanhPhan(v); setLoiThanhPhan(null) }} loi={loiThanhPhan ?? (daThuLuu ? kiemTraThanhPhan(thanhPhan) : null)} disabled={tao.isPending} />
        </Card>
        <Alert type="info" showIcon title="Ảnh sản phẩm tải lên được sau khi tạo sản phẩm." />
        <Space>
          <Button type="primary" loading={tao.isPending} onClick={() => void luu()}>
            Thêm sản phẩm
          </Button>
          <Link to=".." relative="path">
            <Button disabled={tao.isPending}>Hủy</Button>
          </Link>
        </Space>
      </Space>
    </div>
  )
}
