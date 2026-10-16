import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Empty, Input, Pagination, Space, Typography } from 'antd'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { usePhien } from '../../../stores/phien'

const KICH_THUOC = 10

/** KTV15: hỏi đáp công khai trên trang sản phẩm; chỉ khách đăng nhập mới đặt câu hỏi. */
export default function HoiDapSanPham({ slug }: { slug: string }) {
  const qc = useQueryClient()
  const khach = usePhien((s) => s.loai === 'khach' && s.daKhoiPhuc)
  const [trang, setTrang] = useState(1)
  const [cauHoi, setCauHoi] = useState('')
  const [loi, setLoi] = useState<string | null>(null)
  const [daGui, setDaGui] = useState(false)
  const ds = useQuery({
    queryKey: ['hoi-dap', slug, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/san-pham/{slug}/hoi-dap', { params: { path: { slug }, query: { trang, kich_thuoc: KICH_THUOC } } })
      if (error || !data) throw error ?? new Error('Không tải được hỏi đáp')
      return data
    },
  })
  const gui = useMutation({
    mutationFn: async () => {
      const r = await goi(() => api.POST('/api/v1/san-pham/{slug}/hoi-dap', { params: { path: { slug } }, body: { cau_hoi: cauHoi.trim() } }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => {
      setCauHoi('')
      setLoi(null)
      setDaGui(true)
      void qc.invalidateQueries({ queryKey: ['hoi-dap', slug] })
      void qc.invalidateQueries({ queryKey: ['toi', 'hoi-dap'] })
    },
    onError: (e: Error) => setLoi(e.message),
  })
  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      {khach ? (
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Input.TextArea aria-label="Câu hỏi của bạn" rows={3} maxLength={1000} showCount placeholder="Đặt câu hỏi cho dược sĩ về sản phẩm này" value={cauHoi} onChange={(e) => { setCauHoi(e.target.value); setDaGui(false) }} />
          {loi && <Alert type="error" showIcon title={loi} />}
          {daGui && <Alert type="success" showIcon title="Đã gửi câu hỏi. Bạn sẽ nhận thông báo khi dược sĩ trả lời." />}
          <Button type="primary" loading={gui.isPending} disabled={cauHoi.trim().length < 5} onClick={() => gui.mutate()}>Gửi câu hỏi</Button>
        </Space>
      ) : (
        <Alert type="info" showIcon title={<span><Link to="/dang-nhap">Đăng nhập</Link> để đặt câu hỏi cho dược sĩ.</span>} />
      )}
      {ds.data?.du_lieu.length === 0 && <Empty description="Chưa có câu hỏi nào" />}
      {ds.data?.du_lieu.map((h) => (
        <article key={h.id} style={{ borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
          <Space size={8} wrap>
            <Typography.Text strong>{h.ten_hien_thi}</Typography.Text>
            <Typography.Text type="secondary">{dinhDangNgay(h.created_at, 'ngay')}</Typography.Text>
          </Space>
          <Typography.Paragraph style={{ marginTop: 4, whiteSpace: 'pre-wrap' }}>{h.cau_hoi}</Typography.Paragraph>
          {h.tra_loi ? <Alert type="info" title="Dược sĩ trả lời" description={h.tra_loi} /> : <Typography.Text type="secondary">Chưa có câu trả lời</Typography.Text>}
        </article>
      ))}
      {(ds.data?.tong ?? 0) > KICH_THUOC && <Pagination current={trang} pageSize={KICH_THUOC} total={ds.data?.tong} onChange={setTrang} showSizeChanger={false} />}
    </Space>
  )
}
