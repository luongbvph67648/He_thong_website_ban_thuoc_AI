import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, Empty, Pagination, Space, Tag, Typography } from 'antd'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { dinhDangNgay } from '../../../lib/dinhDang'

const KICH_THUOC = 20
const noiBo = (l: string | null): l is string => !!l && l.startsWith('/') && !l.startsWith('//') && !l.includes('\\')

/** KTV13, KTV14: danh sách thông báo của khách (đơn hàng, đơn thuốc, đổi trả, nhắc mua lại). */
export default function TrangThongBao() {
  const [trang, setTrang] = useState(1)
  const dieuHuong = useNavigate()
  const qc = useQueryClient()
  const ds = useQuery({
    queryKey: ['toi', 'thong-bao', 'trang', trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/thong-bao', { params: { query: { trang, kich_thuoc: KICH_THUOC } } })
      if (error || !data) throw error ?? new Error('Không tải được thông báo')
      return data
    },
  })
  const lamMoi = () => qc.invalidateQueries({ queryKey: ['toi', 'thong-bao'] })
  const daDoc = useMutation({
    mutationFn: async (id: number) => { await api.POST('/api/v1/toi/thong-bao/{thong_bao_id}/da-doc', { params: { path: { thong_bao_id: id } } }) },
    onSettled: lamMoi,
  })
  const tatCa = useMutation({
    mutationFn: async () => { await api.POST('/api/v1/toi/thong-bao/da-doc-tat-ca') },
    onSettled: lamMoi,
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <Typography.Title level={2} style={{ margin: 0 }}>Thông báo</Typography.Title>
        <Button onClick={() => tatCa.mutate()} disabled={tatCa.isPending}>Đánh dấu tất cả đã đọc</Button>
      </Space>
      {ds.data?.du_lieu.length === 0 && <Empty description="Chưa có thông báo" />}
      {ds.data?.du_lieu.map((tb) => (
        <button
          key={tb.id}
          type="button"
          onClick={() => { if (!tb.da_doc) daDoc.mutate(tb.id); if (noiBo(tb.lien_ket)) dieuHuong(tb.lien_ket) }}
          style={{ textAlign: 'left', border: 0, borderBottom: '1px solid #f0f0f0', padding: '8px 4px', cursor: 'pointer', background: tb.da_doc ? 'transparent' : '#f6ffed', font: 'inherit' }}
        >
          <div><Typography.Text strong={!tb.da_doc}>{tb.tieu_de}</Typography.Text> {!tb.da_doc && <Tag color="green">Mới</Tag>}</div>
          {tb.noi_dung && <div>{tb.noi_dung}</div>}
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>{dinhDangNgay(tb.created_at, 'ngayGio')}</Typography.Text>
        </button>
      ))}
      {(ds.data?.tong ?? 0) > KICH_THUOC && <Pagination current={trang} pageSize={KICH_THUOC} total={ds.data?.tong} onChange={setTrang} showSizeChanger={false} />}
    </Space>
  )
}
