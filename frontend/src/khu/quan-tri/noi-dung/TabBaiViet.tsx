import { PlusOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Input, Popconfirm, Select, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { TrinhSoanBai } from './TrinhSoanBai'
import { KHOA_QUERY_NOI_DUNG, KICH_THUOC_BANG, LOAI_BAI, nhanBai, type BaiVietTomTat, type LoaiBai, type TrangThaiBai } from './noiDungWeb'

const TRANG_THAI: { value: TrangThaiBai; label: string }[] = [
  { value: 'nhap', label: 'Chờ duyệt / nháp' },
  { value: 'da_duyet', label: 'Đang đăng' },
  { value: 'luu_tru', label: 'Đã gỡ' },
]

/** Danh sách và soạn bài viết sức khỏe, chính sách hoặc FAQ (AD07). */
export function TabBaiViet({ loai, coGhi }: { loai: LoaiBai; coGhi: boolean }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const mo = LOAI_BAI.find((l) => l.value === loai)!
  const [trangThai, setTrangThai] = useState<TrangThaiBai | undefined>()
  const [q, setQ] = useState('')
  const [trang, setTrang] = useState(1)
  const [soan, setSoan] = useState<{ id: number | null } | null>(null)
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const khoa = [...KHOA_QUERY_NOI_DUNG, 'bai', loai]

  const ds = useQuery({
    queryKey: [...khoa, { trangThai, q, trang }],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bai-viet', {
        params: { query: { loai, trang_thai: trangThai, q: q.trim() || undefined, trang, kich_thuoc: KICH_THUOC_BANG } },
      })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })

  /** Gỡ / đăng lại cần đúng `phien_ban`: đọc bản mới nhất của bài ngay trước khi gửi (một cú bấm, không có form để giữ). */
  const chuyen = async (b: BaiVietTomTat, hanhDong: 'go' | 'dang') => {
    const hienTai = await goi(() => api.GET('/api/v1/noi-bo/bai-viet/{bai_viet_id}', { params: { path: { bai_viet_id: b.id } } }))
    if (!hienTai.ok) return setThongDiep(thongDiepChung(hienTai.loi))
    const params = { path: { bai_viet_id: b.id } }
    const body = { phien_ban: hienTai.data.phien_ban }
    const kq = await goi(() =>
      hanhDong === 'go' ? api.POST('/api/v1/noi-bo/bai-viet/{bai_viet_id}/go', { params, body }) : api.POST('/api/v1/noi-bo/bai-viet/{bai_viet_id}/dang', { params, body }),
    )
    if (!kq.ok) {
      setThongDiep(thongDiepChung(kq.loi))
    } else {
      setThongDiep(null)
      void message.success(hanhDong === 'go' ? 'Đã gỡ bài khỏi website' : kq.data.trang_thai === 'nhap' ? 'Đã đăng lại, bài chờ dược sĩ duyệt' : 'Đã đăng lại')
    }
    void queryClient.invalidateQueries({ queryKey: khoa })
  }

  const cot: ColumnsType<BaiVietTomTat> = [
    {
      title: 'Tiêu đề',
      key: 'tieu_de',
      render: (_, b) =>
        b.trang_thai === 'da_duyet' ? (
          <a href={`${b.loai === 'chinh_sach' ? '/chinh-sach' : b.loai === 'faq' ? '/hoi-dap' : '/bai-viet'}${b.loai === 'faq' ? '' : `/${b.slug}`}`} target="_blank" rel="noopener noreferrer">
            {b.tieu_de}
          </a>
        ) : (
          b.tieu_de
        ),
    },
    { title: 'Trạng thái', key: 'trang_thai', width: 170, render: (_, b) => <Tag color={nhanBai(b.loai, b.trang_thai).mau}>{nhanBai(b.loai, b.trang_thai).nhan}</Tag> },
    { title: 'Kho tri thức AI', key: 'ai', width: 120, render: (_, b) => (b.dua_vao_ai ? <Tag color="purple">Có</Tag> : <Typography.Text type="secondary">Không</Typography.Text>) },
    { title: 'Người soạn', dataIndex: 'tac_gia', key: 'tac_gia', width: 160 },
    { title: 'Cập nhật', key: 'cap_nhat', width: 150, render: (_, b) => dinhDangNgay(b.updated_at ?? b.created_at, 'ngayGio') },
    {
      title: 'Thao tác',
      key: 'thao_tac',
      width: 200,
      render: (_, b) =>
        coGhi && (
          <Space>
            <Button size="small" onClick={() => setSoan({ id: b.id })}>
              Sửa
            </Button>
            {b.trang_thai === 'luu_tru' ? (
              <Button size="small" onClick={() => void chuyen(b, 'dang')}>
                Đăng lại
              </Button>
            ) : (
              <Popconfirm title="Gỡ bài khỏi website?" description="Bài chuyển sang trạng thái đã gỡ, có thể đăng lại sau." okText="Gỡ" cancelText="Hủy" onConfirm={() => chuyen(b, 'go')}>
                <Button size="small">Gỡ</Button>
              </Popconfirm>
            )}
          </Space>
        ),
    },
  ]

  return (
    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
      {thongDiep && <Alert type="error" showIcon title={thongDiep} closable={{ onClose: () => setThongDiep(null) }} />}
      <Space style={{ justifyContent: 'space-between', width: '100%' }} wrap>
        <Space wrap>
          <Input.Search
            allowClear
            placeholder="Tìm theo tiêu đề"
            aria-label="Tìm theo tiêu đề"
            style={{ width: 260 }}
            onSearch={(v) => {
              setQ(v)
              setTrang(1)
            }}
          />
          <Select<TrangThaiBai> allowClear placeholder="Mọi trạng thái" aria-label="Trạng thái" style={{ width: 180 }} options={TRANG_THAI} value={trangThai} onChange={(v) => { setTrangThai(v); setTrang(1) }} />
        </Space>
        <YeuCauQuyen ma="cms.manage" kieu="nut">
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setSoan({ id: null })}>
            Soạn {mo.so_nhieu === 'câu hỏi' ? 'câu hỏi' : mo.so_nhieu.replace(/s$/, '')} mới
          </Button>
        </YeuCauQuyen>
      </Space>
      {ds.isError && !ds.data ? (
        <Alert type="error" showIcon title="Không tải được danh sách" action={<Button onClick={() => void ds.refetch()}>Thử lại</Button>} />
      ) : (
        <Table
          rowKey="id"
          size="middle"
          loading={ds.isPending}
          dataSource={ds.data?.du_lieu ?? []}
          columns={cot}
          locale={{ emptyText: `Chưa có ${mo.so_nhieu}` }}
          pagination={{ current: trang, pageSize: KICH_THUOC_BANG, total: ds.data?.tong ?? 0, showSizeChanger: false, onChange: setTrang, hideOnSinglePage: true }}
        />
      )}
      {soan && (
        <TrinhSoanBai
          key={soan.id ?? 'moi'}
          loai={loai}
          baiId={soan.id}
          onDong={() => setSoan(null)}
          onXong={() => {
            setSoan(null)
            void queryClient.invalidateQueries({ queryKey: khoa })
          }}
        />
      )}
    </Space>
  )
}
