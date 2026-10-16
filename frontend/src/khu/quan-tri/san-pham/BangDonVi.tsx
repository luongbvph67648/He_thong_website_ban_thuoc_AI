import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Checkbox, Input, InputNumber, Space, Switch, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { ReactNode } from 'react'
import { donViMoi, type DonViForm, type LoiDonVi } from '../../../lib/sanPham'

interface Props {
  value: DonViForm[]
  onChange: (v: DonViForm[]) => void
  /** Kết quả của `kiemTraDonVi`; chỉ hiện sau khi người dùng bấm lưu lần đầu để khỏi báo lỗi khi mới mở form. */
  loi: LoiDonVi | null
  disabled?: boolean
}

/** Danh sách đơn vị quy đổi: đơn vị cơ sở có hệ số 1, đơn vị lớn hơn quy ra số đơn vị cơ sở. Sửa tại chỗ, lưu một lần. */
export function BangDonVi({ value, onChange, loi, disabled }: Props) {
  const doiDong = (i: number, thayDoi: Partial<DonViForm>) => onChange(value.map((d, j) => (j === i ? { ...d, ...thayDoi } : d)))
  const loiO = (i: number, truong: 'ten_don_vi' | 'he_so' | 'gia_ban' | 'ma_vach') => loi?.theoDong[i]?.[truong]
  const tieuDe = (i: number) => `đơn vị ${i + 1}`

  const o = (i: number, truong: 'ten_don_vi' | 'he_so' | 'gia_ban' | 'ma_vach', nodeO: ReactNode) => (
    <div>
      {nodeO}
      {loiO(i, truong) && (
        <div role="alert" style={{ color: 'var(--ant-color-error, #ff4d4f)', fontSize: 12, marginTop: 2 }}>
          {loiO(i, truong)}
        </div>
      )}
    </div>
  )

  const cot: ColumnsType<DonViForm> = [
    {
      title: 'Tên đơn vị',
      key: 'ten',
      width: 170,
      render: (_, d, i) =>
        o(i, 'ten_don_vi', <Input value={d.ten_don_vi} disabled={disabled} status={loiO(i, 'ten_don_vi') ? 'error' : undefined} aria-label={`Tên ${tieuDe(i)}`} autoComplete="off" onChange={(e) => doiDong(i, { ten_don_vi: e.target.value })} />),
    },
    {
      title: 'Hệ số quy đổi',
      key: 'he_so',
      width: 140,
      render: (_, d, i) =>
        o(i, 'he_so', <InputNumber<number> value={d.he_so} disabled={disabled} style={{ width: '100%' }} status={loiO(i, 'he_so') ? 'error' : undefined} aria-label={`Hệ số ${tieuDe(i)}`} changeOnWheel={false} onChange={(v) => doiDong(i, { he_so: v })} />),
    },
    {
      title: 'Giá bán (₫)',
      key: 'gia',
      width: 170,
      render: (_, d, i) =>
        o(i, 'gia_ban', <InputNumber<number> value={d.gia_ban} disabled={disabled} style={{ width: '100%' }} status={loiO(i, 'gia_ban') ? 'error' : undefined} aria-label={`Giá bán ${tieuDe(i)}`} changeOnWheel={false} onChange={(v) => doiDong(i, { gia_ban: v })} />),
    },
    {
      title: 'Mã vạch',
      key: 'ma_vach',
      width: 170,
      render: (_, d, i) =>
        o(i, 'ma_vach', <Input value={d.ma_vach} disabled={disabled} status={loiO(i, 'ma_vach') ? 'error' : undefined} aria-label={`Mã vạch ${tieuDe(i)}`} autoComplete="off" onChange={(e) => doiDong(i, { ma_vach: e.target.value })} />),
    },
    {
      title: 'Bán online',
      key: 'ban_online',
      width: 100,
      align: 'center',
      render: (_, d, i) => <Switch checked={d.ban_online} disabled={disabled} aria-label={`Bán online ${tieuDe(i)}`} onChange={(v) => doiDong(i, { ban_online: v })} />,
    },
    {
      title: 'Mặc định',
      key: 'mac_dinh',
      width: 90,
      align: 'center',
      render: (_, d, i) => (
        <Checkbox
          checked={d.la_mac_dinh}
          disabled={disabled}
          aria-label={`Mặc định ${tieuDe(i)}`}
          // Tối đa một đơn vị mặc định: chọn dòng này thì bỏ chọn dòng khác.
          onChange={(e) => onChange(value.map((x, j) => ({ ...x, la_mac_dinh: j === i ? e.target.checked : false })))}
        />
      ),
    },
    {
      key: 'xoa',
      width: 56,
      render: (_, __, i) => <Button type="text" danger icon={<DeleteOutlined />} disabled={disabled} aria-label={`Xóa ${tieuDe(i)}`} onClick={() => onChange(value.filter((_, j) => j !== i))} />,
    },
  ]

  return (
    <div>
      {loi?.chung.map((c) => (
        <Alert key={c} type="error" showIcon title={c} style={{ marginBottom: 8 }} />
      ))}
      <Table<DonViForm> rowKey="khoa" size="small" columns={cot} dataSource={value} pagination={false} locale={{ emptyText: 'Chưa có đơn vị nào' }} scroll={{ x: 'max-content' }} />
      <Space style={{ marginTop: 8 }}>
        <Button icon={<PlusOutlined />} disabled={disabled} onClick={() => onChange([...value, donViMoi(value.length === 0 ? { he_so: 1 } : {})])}>
          Thêm đơn vị
        </Button>
      </Space>
    </div>
  )
}
