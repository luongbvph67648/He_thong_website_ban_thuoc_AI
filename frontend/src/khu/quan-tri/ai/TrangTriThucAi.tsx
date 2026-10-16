import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Space, Statistic, Typography } from 'antd'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'

type KetQua = components['schemas']['KetQuaDongBo']
const NHAN_NGUON: Record<string, string> = { san_pham: 'Sản phẩm', bai_viet: 'Bài viết', chinh_sach: 'Chính sách', faq: 'Hỏi đáp thường gặp' }

/** AD10: thống kê kho tri thức và đồng bộ theo yêu cầu (hằng đêm đã có job). */
export default function TrangTriThucAi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const tk = useQuery({ queryKey: ['quan-tri', 'tri-thuc'], queryFn: async () => { const { data, error } = await api.GET('/api/v1/noi-bo/tri-thuc'); if (error || !data) throw error ?? new Error('Lỗi'); return data } })
  const dongBo = useMutation({
    mutationFn: async (): Promise<KetQua> => {
      const r = await goi(() => api.POST('/api/v1/noi-bo/tri-thuc/dong-bo'))
      if (!r.ok || !r.data) throw new Error(thongDiepChung(r.ok ? null : r.loi))
      return r.data
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: ['quan-tri', 'tri-thuc'] }) },
    onError: (e: Error) => void message.error(e.message),
  })
  const kq = dongBo.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 800 }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Kho tri thức AI</Typography.Title>
      {tk.data?.can_dong_bo_lai_vector && <Alert type="warning" showIcon title="Mô hình embedding đã đổi: đồng bộ sẽ tạo lại toàn bộ vector." />}
      {tk.data && (
        <Descriptions bordered size="small" column={1} items={[
          { key: 'tong', label: 'Tổng số đoạn', children: tk.data.tong_doan },
          ...Object.entries(tk.data.theo_nguon).map(([k, v]) => ({ key: k, label: NHAN_NGUON[k] ?? k, children: v })),
          { key: 'mh', label: 'Mô hình embedding', children: tk.data.mo_hinh_hien_tai },
          { key: 'cn', label: 'Cập nhật gần nhất', children: tk.data.cap_nhat_gan_nhat ? dinhDangNgay(String(tk.data.cap_nhat_gan_nhat), 'ngayGio') : '—' },
        ]} />
      )}
      <YeuCauQuyen ma="ai.knowledge.sync" kieu="nut"><Button type="primary" loading={dongBo.isPending} onClick={() => dongBo.mutate()}>Đồng bộ ngay</Button></YeuCauQuyen>
      {kq && (
        <Space size="large" wrap aria-label="Kết quả đồng bộ">
          <Statistic title="Thêm" value={kq.them} /><Statistic title="Sửa" value={kq.sua} /><Statistic title="Xóa" value={kq.xoa} /><Statistic title="Bỏ qua (không đổi)" value={kq.bo_qua} />
        </Space>
      )}
    </Space>
  )
}
