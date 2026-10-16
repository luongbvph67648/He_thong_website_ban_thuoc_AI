import { Empty, Select, Space, Switch, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { NhanTrangThai } from '../../../components/NhanTrangThai'
import { soSanh, type PhienBanNoiDung } from './noiDung'

/** So sánh từng trường của hai phiên bản (cũ bên trái, mới bên phải); trường khác nhau được đánh dấu. */
export function SoSanhPhienBan({ cac }: { cac: readonly PhienBanNoiDung[] }) {
  const theoSo = useMemo(() => [...cac].sort((a, b) => b.phien_ban - a.phien_ban), [cac])
  const [soCu, datSoCu] = useState<number | undefined>(theoSo[1]?.phien_ban)
  const [soMoi, datSoMoi] = useState<number | undefined>(theoSo[0]?.phien_ban)
  const [chiKhac, datChiKhac] = useState(true)

  if (theoSo.length < 2) return <Empty description="Cần ít nhất hai phiên bản để so sánh" />
  const cu = theoSo.find((p) => p.phien_ban === soCu)
  const moi = theoSo.find((p) => p.phien_ban === soMoi)
  const tuyChon = theoSo.map((p) => ({ value: p.phien_ban, label: `Bản ${p.phien_ban}` }))
  const dong = cu && moi ? soSanh(cu, moi) : []
  const hien = chiKhac ? dong.filter((d) => d.khac) : dong

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      <Space wrap align="center">
        <span>Bản cũ</span>
        <Select aria-label="Bản cũ" style={{ width: 120 }} value={soCu} options={tuyChon} onChange={datSoCu} />
        {cu && <NhanTrangThai loai="noi_dung" giaTri={cu.trang_thai} />}
        <span>so với bản mới</span>
        <Select aria-label="Bản mới" style={{ width: 120 }} value={soMoi} options={tuyChon} onChange={datSoMoi} />
        {moi && <NhanTrangThai loai="noi_dung" giaTri={moi.trang_thai} />}
        <Switch checked={chiKhac} onChange={datChiKhac} aria-label="Chỉ hiện trường khác nhau" />
        <span>Chỉ hiện trường khác nhau</span>
      </Space>
      {cu && moi && cu.phien_ban === moi.phien_ban && <Typography.Text type="warning">Hai bản đang chọn là một.</Typography.Text>}
      {hien.length === 0 ? (
        <Empty description={chiKhac ? 'Hai phiên bản giống nhau ở mọi trường' : 'Không có dữ liệu'} />
      ) : (
        hien.map((d) => (
          <div key={d.ten} data-testid={`so-sanh-${d.ten}`} style={{ border: '1px solid rgba(0,0,0,.12)', borderRadius: 8, padding: 12 }}>
            <Typography.Text strong>
              {d.nhan} {d.khac && <span style={{ color: '#d46b08' }}>(khác)</span>}
            </Typography.Text>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 8 }}>
              <div style={{ whiteSpace: 'pre-wrap', background: d.khac ? '#fff1f0' : undefined, padding: 8, borderRadius: 4 }}>{d.truoc ?? <em>(trống)</em>}</div>
              <div style={{ whiteSpace: 'pre-wrap', background: d.khac ? '#f6ffed' : undefined, padding: 8, borderRadius: 4 }}>{d.sau ?? <em>(trống)</em>}</div>
            </div>
          </div>
        ))
      )}
    </Space>
  )
}
