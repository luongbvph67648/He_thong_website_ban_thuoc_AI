import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Drawer, Input, Popconfirm, Skeleton, Space, Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { NoiDungMarkdown } from '../../../components/NoiDungMarkdown'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { lienKetAnToan } from '../../../lib/lienKet'

type TomTat = components['schemas']['BaiVietTomTat']
const KHOA = ['nhan-vien', 'bai-viet-cho-duyet'] as const
const KICH_THUOC = 20

/** Dược sĩ đọc và duyệt bài viết sức khỏe do Admin soạn (DS10). Duyệt đúng bản đã đọc: Admin sửa giữa chừng thì 409. */
export default function TrangBaiVietChoDuyet() {
  const [q, setQ] = useState('')
  const [trang, setTrang] = useState(1)
  const [mo, setMo] = useState<number | null>(null)

  const ds = useQuery({
    queryKey: [...KHOA, 'ds', q, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bai-viet-cho-duyet', { params: { query: { q: q.trim() || undefined, trang, kich_thuoc: KICH_THUOC } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })

  const cot: ColumnsType<TomTat> = [
    {
      title: 'Bài viết',
      key: 'tieu_de',
      render: (_, b) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => setMo(b.id)}>
          {b.tieu_de}
        </Button>
      ),
    },
    { title: 'Người soạn', dataIndex: 'tac_gia', key: 'tac_gia', width: 180 },
    { title: 'Soạn lúc', key: 'created_at', width: 160, render: (_, b) => dinhDangNgay(b.created_at, 'ngayGio') },
  ]

  return (
    <>
      <Typography.Title level={3}>Bài viết chờ duyệt</Typography.Title>
      <Typography.Paragraph type="secondary">
        Bài viết sức khỏe do Admin soạn chỉ hiện trên website sau khi bạn đọc và duyệt. Bài được sửa sau khi duyệt sẽ quay lại danh sách này.
      </Typography.Paragraph>
      <Input.Search allowClear aria-label="Tìm theo tiêu đề" placeholder="Tìm theo tiêu đề" style={{ width: 280, marginBottom: 12 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
      {ds.isError && !ds.data ? (
        <Alert type="error" showIcon title="Không tải được danh sách" action={<Button onClick={() => void ds.refetch()}>Thử lại</Button>} />
      ) : (
        <Table
          rowKey="id"
          loading={ds.isPending}
          dataSource={ds.data?.du_lieu ?? []}
          columns={cot}
          locale={{ emptyText: 'Không có bài viết nào đang chờ duyệt' }}
          pagination={{ current: trang, pageSize: KICH_THUOC, total: ds.data?.tong ?? 0, showSizeChanger: false, onChange: setTrang, hideOnSinglePage: true }}
        />
      )}
      {mo !== null && <DocVaDuyet key={mo} baiId={mo} onDong={() => setMo(null)} />}
    </>
  )
}

function DocVaDuyet({ baiId, onDong }: { baiId: number; onDong: () => void }) {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [thongDiep, setThongDiep] = useState<string | null>(null)
  const [dangDuyet, setDangDuyet] = useState(false)

  const chiTiet = useQuery({
    queryKey: [...KHOA, 'chi-tiet', baiId],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bai-viet-cho-duyet/{bai_viet_id}', { params: { path: { bai_viet_id: baiId } } })
      if (error || !data) throw error ?? new Error('Không tải được bài viết')
      return data
    },
    // `phien_ban` gửi khi duyệt PHẢI là bản dược sĩ đã đọc: không làm mới ngầm (nếu không, bài vừa sửa được duyệt khi chưa đọc).
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })

  const duyet = async () => {
    if (!chiTiet.data) return
    setDangDuyet(true)
    const kq = await goi(() =>
      api.POST('/api/v1/noi-bo/bai-viet-cho-duyet/{bai_viet_id}/duyet', { params: { path: { bai_viet_id: baiId } }, body: { phien_ban: chiTiet.data.phien_ban } }),
    )
    setDangDuyet(false)
    if (kq.ok) {
      void message.success('Đã duyệt, bài được đăng lên website')
      void queryClient.invalidateQueries({ queryKey: KHOA })
      return onDong()
    }
    if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
      setThongDiep('Bài viết vừa được sửa (hoặc không còn chờ duyệt). Hãy đọc lại nội dung mới bên dưới rồi duyệt.')
      void chiTiet.refetch()
      void queryClient.invalidateQueries({ queryKey: [...KHOA, 'ds'] })
      return
    }
    setThongDiep(thongDiepChung(kq.loi))
  }

  const b = chiTiet.data
  const anh = lienKetAnToan(b?.anh_bia_url)
  return (
    <Drawer open size="large" title={b?.tieu_de ?? 'Bài viết'} onClose={onDong} destroyOnHidden>
      {chiTiet.isPending ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : !b ? (
        <Alert type="error" showIcon title="Không tải được bài viết (có thể bài đã được duyệt hoặc gỡ)" action={<Button onClick={() => void chiTiet.refetch()}>Thử lại</Button>} />
      ) : (
        <Space orientation="vertical" size={16} style={{ width: '100%' }}>
          {thongDiep && <Alert type="warning" showIcon title={thongDiep} />}
          <Space wrap>
            <Typography.Text type="secondary">Người soạn: {b.tac_gia}</Typography.Text>
            <Typography.Text type="secondary">Soạn lúc {dinhDangNgay(b.created_at, 'ngayGio')}</Typography.Text>
            {b.dua_vao_ai && <Tag color="purple">Sẽ đưa vào kho tri thức AI</Tag>}
          </Space>
          {anh && <img src={anh} alt="" style={{ maxWidth: '100%', maxHeight: 240, objectFit: 'cover' }} />}
          <NoiDungMarkdown noiDung={b.noi_dung} />
          <YeuCauQuyen ma="content.approve" kieu="nut">
            <Popconfirm
              title="Duyệt bài viết này?"
              description="Bài sẽ hiện trên website ngay. Bạn xác nhận đã đọc toàn bộ nội dung."
              okText="Duyệt"
              cancelText="Chưa"
              onConfirm={duyet}
            >
              <Button type="primary" loading={dangDuyet}>
                Duyệt bài
              </Button>
            </Popconfirm>
          </YeuCauQuyen>
        </Space>
      )}
    </Drawer>
  )
}
