import { InboxOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Empty, Image, Input, Modal, Rate, Space, Table, Tabs, Tag, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { loiTepBangChung } from '../../../lib/doiTra'

type Dong = components['schemas']['DongCoTheDanhGia']

function FormDanhGia({ d, dong }: { d: Dong; dong: () => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [sao, setSao] = useState(0)
  const [noiDung, setNoiDung] = useState('')
  const [tep, setTep] = useState<UploadFile[]>([])
  const [loi, setLoi] = useState<string | null>(null)
  const gui = useMutation({
    mutationFn: async () => {
      const r = await goi(() =>
        api.POST('/api/v1/toi/danh-gia', {
          body: { ct_don_hang_id: d.ct_don_hang_id, so_sao: sao, tep: [] },
          bodySerializer: () => {
            const fd = new FormData()
            fd.append('ct_don_hang_id', String(d.ct_don_hang_id))
            fd.append('so_sao', String(sao))
            if (noiDung.trim()) fd.append('noi_dung', noiDung.trim())
            tep.forEach((f) => f.originFileObj && fd.append('tep', f.originFileObj))
            return fd
          },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => {
      void message.success('Cảm ơn bạn đã đánh giá')
      void qc.invalidateQueries({ queryKey: ['toi', 'danh-gia'] })
      dong()
    },
    onError: (e: Error) => setLoi(e.message),
  })
  return (
    <Modal title={`Đánh giá ${d.ten_san_pham}`} open onCancel={dong} okText="Gửi đánh giá" cancelText="Đóng" confirmLoading={gui.isPending} okButtonProps={{ disabled: sao === 0 }} onOk={() => gui.mutate()} destroyOnHidden>
      {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
      <Space orientation="vertical" style={{ width: '100%' }}>
        <Rate aria-label="Số sao" value={sao} onChange={setSao} />
        <Input.TextArea aria-label="Nhận xét" rows={4} maxLength={2000} showCount placeholder="Chia sẻ trải nghiệm của bạn" value={noiDung} onChange={(e) => setNoiDung(e.target.value)} />
        <Upload.Dragger multiple maxCount={3} listType="picture" accept="image/jpeg,image/png,image/webp" fileList={tep} onChange={(e) => setTep(e.fileList)}
          beforeUpload={(f) => { const l = loiTepBangChung(f); if (l || f.type === 'video/mp4') { setLoi(l ?? 'Chỉ nhận ảnh'); return Upload.LIST_IGNORE } return false }}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p>
          <p>Thêm ảnh (tối đa 3)</p>
        </Upload.Dragger>
      </Space>
    </Modal>
  )
}

/** KTV10, KTV15: đánh giá sản phẩm đã mua và theo dõi câu hỏi của tôi. */
export default function TrangDanhGiaCuaToi() {
  const [chon, setChon] = useState<Dong | null>(null)
  const cho = useQuery({ queryKey: ['toi', 'danh-gia', 'cho'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/toi/danh-gia/cho'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const da = useQuery({ queryKey: ['toi', 'danh-gia', 'da'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/toi/danh-gia'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const hoi = useQuery({ queryKey: ['toi', 'hoi-dap'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/toi/hoi-dap'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đánh giá và hỏi đáp</Typography.Title>
      <Tabs
        items={[
          {
            key: 'cho',
            label: `Chờ đánh giá (${cho.data?.length ?? 0})`,
            children: (
              <Table<Dong> rowKey="ct_don_hang_id" size="small" pagination={false} loading={cho.isLoading} dataSource={cho.data ?? []} locale={{ emptyText: 'Không có sản phẩm nào chờ đánh giá' }}
                columns={[{ title: 'Sản phẩm', dataIndex: 'ten_san_pham' }, { title: 'Đơn', dataIndex: 'ma_don' }, { title: '', render: (_, r) => <Button type="link" onClick={() => setChon(r)}>Đánh giá</Button> }]} />
            ),
          },
          {
            key: 'da',
            label: 'Đã đánh giá',
            children: !da.data?.length ? <Empty description="Chưa có đánh giá" /> : (
              <Space orientation="vertical" style={{ width: '100%' }}>
                {da.data.map((x) => (
                  <article key={x.id} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}>
                    <Space wrap><Link to={`/san-pham/${x.san_pham_slug}`}>{x.san_pham_ten}</Link><Rate disabled value={x.so_sao} style={{ fontSize: 14 }} />{!x.dang_hien && <Tag>Đang bị ẩn</Tag>}</Space>
                    {x.noi_dung && <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{x.noi_dung}</Typography.Paragraph>}
                    <Space wrap>{x.anh.map((u) => <Image key={u} src={u} width={60} alt="Ảnh đánh giá" />)}</Space>
                    {x.phan_hoi && <Alert type="info" title="Phản hồi từ nhà thuốc" description={x.phan_hoi} />}
                  </article>
                ))}
              </Space>
            ),
          },
          {
            key: 'hoi',
            label: `Câu hỏi của tôi (${hoi.data?.length ?? 0})`,
            children: !hoi.data?.length ? <Empty description="Bạn chưa đặt câu hỏi nào" /> : (
              <Space orientation="vertical" style={{ width: '100%' }}>
                {hoi.data.map((h) => (
                  <article key={h.id} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 8 }}>
                    <Link to={`/san-pham/${h.san_pham_slug}`}>{h.san_pham_ten}</Link> <Typography.Text type="secondary">{dinhDangNgay(h.created_at, 'ngay')}</Typography.Text>
                    <Typography.Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{h.cau_hoi}</Typography.Paragraph>
                    {h.tra_loi ? <Alert type="info" title="Dược sĩ trả lời" description={h.tra_loi} /> : <Typography.Text type="secondary">Chưa có câu trả lời</Typography.Text>}
                  </article>
                ))}
              </Space>
            ),
          },
        ]}
      />
      {chon && <FormDanhGia d={chon} dong={() => setChon(null)} />}
    </Space>
  )
}
