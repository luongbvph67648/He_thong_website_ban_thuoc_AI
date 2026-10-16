import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import { Alert, Button, Input, Table } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { thanhPhanMoi, type ThanhPhanForm } from '../../../lib/sanPham'
import { ChonDuLieuChung } from '../../../components/ChonDuLieuChung'

interface Props {
  value: ThanhPhanForm[]
  onChange: (v: ThanhPhanForm[]) => void
  /** Kết quả của `kiemTraThanhPhan`; `null` khi chưa bấm lưu. */
  loi: { chung: string[]; theoDong: Record<number, string> } | null
  disabled?: boolean
}

/** Thành phần hoạt chất và hàm lượng của sản phẩm (AD04). Một hoạt chất chỉ xuất hiện một lần. */
export function BangThanhPhan({ value, onChange, loi, disabled }: Props) {
  const doiDong = (i: number, thayDoi: Partial<ThanhPhanForm>) => onChange(value.map((t, j) => (j === i ? { ...t, ...thayDoi } : t)))

  const cot: ColumnsType<ThanhPhanForm> = [
    {
      title: 'Hoạt chất',
      key: 'hoat_chat',
      render: (_, t, i) => (
        <div>
          <ChonDuLieuChung
            ma="hoat-chat"
            batBuoc
            disabled={disabled}
            placeholder="Chọn hoạt chất"
            id={`hoat-chat-${i}`}
            nhan={`Hoạt chất thành phần ${i + 1}`}
            value={t.hoat_chat_id === null ? null : { value: t.hoat_chat_id, label: t.ten_hoat_chat }}
            onChange={(v) => doiDong(i, { hoat_chat_id: v?.value ?? null, ten_hoat_chat: v?.label ?? '' })}
          />
          {loi?.theoDong[i] && (
            <div role="alert" style={{ color: 'var(--ant-color-error, #ff4d4f)', fontSize: 12, marginTop: 2 }}>
              {loi.theoDong[i]}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'Hàm lượng',
      key: 'ham_luong',
      width: 220,
      render: (_, t, i) => <Input value={t.ham_luong} disabled={disabled} placeholder="Ví dụ 500 mg" aria-label={`Hàm lượng thành phần ${i + 1}`} autoComplete="off" onChange={(e) => doiDong(i, { ham_luong: e.target.value })} />,
    },
    {
      key: 'xoa',
      width: 56,
      render: (_, __, i) => <Button type="text" danger icon={<DeleteOutlined />} disabled={disabled} aria-label={`Xóa thành phần ${i + 1}`} onClick={() => onChange(value.filter((_, j) => j !== i))} />,
    },
  ]

  return (
    <div>
      {loi?.chung.map((c) => (
        <Alert key={c} type="error" showIcon title={c} style={{ marginBottom: 8 }} />
      ))}
      <Table<ThanhPhanForm> rowKey="khoa" size="small" columns={cot} dataSource={value} pagination={false} locale={{ emptyText: 'Chưa có thành phần nào' }} />
      <Button style={{ marginTop: 8 }} icon={<PlusOutlined />} disabled={disabled} onClick={() => onChange([...value, thanhPhanMoi()])}>
        Thêm thành phần
      </Button>
    </div>
  )
}
