import { ArrowDownOutlined, ArrowRightOutlined, ArrowUpOutlined, CheckCircleFilled, ExclamationCircleFilled, WarningFilled } from '@ant-design/icons'
import { Card, Skeleton, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { phanTram, type Viec } from './tongQuan'

const MAU = {
  gap: { nen: '#fff1f0', vien: '#ffccc7', chu: '#cf1322' },
  chu_y: { nen: '#fffbe6', vien: '#ffe58f', chu: '#d48806' },
} as const

/** Ô một việc cần xử lý: số lớn, màu theo mức độ, nút đi thẳng tới trang xử lý. */
export function TheViec({ viec, goc }: { viec: Viec; goc: string }) {
  const m = MAU[viec.mucDo]
  return (
    <div data-testid={`viec-${viec.khoa}`} style={{ background: m.nen, border: `1px solid ${m.vien}`, borderRadius: 10, padding: '14px 16px', height: '100%', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: m.chu }}>
        {viec.mucDo === 'gap' ? <ExclamationCircleFilled /> : <WarningFilled />}
        <Typography.Text strong style={{ color: m.chu }}>{viec.tieuDe}</Typography.Text>
      </div>
      <div style={{ fontSize: 32, fontWeight: 600, lineHeight: 1.1, color: m.chu }}>{viec.so}</div>
      <Typography.Text type="secondary" style={{ fontSize: 13, flex: 1 }}>{viec.moTa}</Typography.Text>
      {viec.duong && (
        <Link to={goc + viec.duong} style={{ fontWeight: 500 }}>
          {viec.nut ?? 'Xem'} <ArrowRightOutlined />
        </Link>
      )}
    </div>
  )
}

/** Dòng gọn cho các việc đang bằng 0, để mắt dồn vào việc còn tồn. */
export function DongDaOn({ ds }: { ds: readonly Viec[] }) {
  if (ds.length === 0) return null
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8 }}>
      <Typography.Text type="secondary">Đã ổn:</Typography.Text>
      {ds.map((v) => (
        <Tag key={v.khoa} color="success" icon={<CheckCircleFilled />} style={{ marginInlineEnd: 0 }}>{v.tieuDe}</Tag>
      ))}
    </div>
  )
}

/** Mũi tên và % thay đổi so với kỳ trước. `nguoc`: tăng là xấu (ví dụ hoàn tiền). */
export function ThayDoi({ ty, nguoc = false }: { ty: number | null; nguoc?: boolean }) {
  if (ty === null) return <Typography.Text type="secondary" style={{ fontSize: 12 }}>Chưa có số liệu kỳ trước</Typography.Text>
  if (Math.abs(ty) < 0.0005) return <Typography.Text type="secondary" style={{ fontSize: 12 }}>Không đổi so với kỳ trước</Typography.Text>
  const tang = ty > 0
  const tot = tang !== nguoc
  return (
    <Typography.Text style={{ fontSize: 12, color: tot ? '#389e0d' : '#cf1322' }}>
      {tang ? <ArrowUpOutlined /> : <ArrowDownOutlined />} {phanTram(Math.abs(ty))} so với kỳ trước
    </Typography.Text>
  )
}

/** Thẻ chỉ số kinh doanh: nhãn, giá trị lớn, so sánh kỳ trước và dòng phụ tùy chọn. */
export function TheChiSo({ nhan, giaTri, ty, nguoc, phu, dangTai }: { nhan: string; giaTri: ReactNode; ty: number | null; nguoc?: boolean; phu?: ReactNode; dangTai: boolean }) {
  return (
    <Card size="small" style={{ height: '100%' }} styles={{ body: { padding: '14px 16px' } }}>
      <Typography.Text type="secondary">{nhan}</Typography.Text>
      {dangTai ? (
        <Skeleton active paragraph={false} title={{ width: '70%' }} />
      ) : (
        <>
          <div style={{ fontSize: 24, fontWeight: 600, margin: '4px 0 2px' }}>{giaTri}</div>
          <ThayDoi ty={ty} nguoc={nguoc} />
          {phu && <div><Typography.Text type="secondary" style={{ fontSize: 12 }}>{phu}</Typography.Text></div>}
        </>
      )}
    </Card>
  )
}

/** Thanh ngang chia phần (tồn kho theo trạng thái lô) kèm chú thích. */
export function ThanhChiaPhan({ phan }: { phan: readonly { khoa: string; nhan: string; giaTri: number; mau: string; chu: string }[] }) {
  const tong = phan.reduce((s, p) => s + p.giaTri, 0)
  if (tong <= 0) return <Typography.Text type="secondary">Kho trống</Typography.Text>
  return (
    <div>
      <div role="img" aria-label="Tồn kho theo trạng thái lô" style={{ display: 'flex', height: 14, borderRadius: 7, overflow: 'hidden', background: '#f0f0f0' }}>
        {phan.filter((p) => p.giaTri > 0).map((p) => (
          <div key={p.khoa} title={`${p.nhan}: ${p.chu}`} style={{ width: `${(p.giaTri / tong) * 100}%`, background: p.mau }} />
        ))}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 12 }}>
        {phan.map((p) => (
          <div key={p.khoa} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: p.mau, flex: 'none' }} />
            <Typography.Text style={{ flex: 1 }}>{p.nhan}</Typography.Text>
            <Typography.Text type="secondary">{p.chu}</Typography.Text>
          </div>
        ))}
      </div>
    </div>
  )
}
