import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Form, Input, InputNumber, Select, Space, Switch, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'

const NHAN_MODULE: Record<string, string> = {
  tim_kiem: 'Tìm kiếm thông minh',
  chat: 'Chatbot tư vấn',
  tra_anh: 'Tra cứu thuốc bằng ảnh',
  doc_don_thuoc: 'Đọc đơn thuốc',
  goi_y: 'Gợi ý sản phẩm',
  du_bao: 'Dự báo nhu cầu',
}
interface GiaTri { ai_module: Record<string, boolean>; ai_dau_hieu_nguy_hiem: string[]; ai_nguong_chuyen_duoc_si: number | null; ai_loi_nhac_bo_sung: string }

/** AD09: bật/tắt từng module AI, dấu hiệu nguy hiểm, ngưỡng chuyển dược sĩ, lời nhắc bổ sung. */
export default function TrangCauHinhAi() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [form] = Form.useForm<GiaTri>()
  const [loi, setLoi] = useState<string | null>(null)
  const q = useQuery({
    queryKey: ['quan-tri', 'cau-hinh-ai'],
    staleTime: Infinity,
    gcTime: 0, // phien_ban phải là bản người dùng ĐÃ THẤY
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/cau-hinh-ai')
      if (error || !data) throw error ?? new Error('Không tải được cấu hình AI')
      return data
    },
  })
  useEffect(() => { if (q.data) form.setFieldsValue(q.data) }, [q.data, form])
  const luu = useMutation({
    mutationFn: async (v: GiaTri) => {
      const r = await goi(() => api.PUT('/api/v1/noi-bo/cau-hinh-ai', { body: { ...v, ai_nguong_chuyen_duoc_si: v.ai_nguong_chuyen_duoc_si ?? undefined, phien_ban: q.data!.phien_ban } }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return r.data
    },
    onSuccess: (d) => { setLoi(null); void message.success('Đã lưu cấu hình AI'); qc.setQueryData(['quan-tri', 'cau-hinh-ai'], d) },
    onError: (e: Error) => setLoi(e.message),
  })
  if (q.isLoading || !q.data) return <Typography.Text>Đang tải…</Typography.Text>
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 720 }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Cấu hình AI</Typography.Title>
      {loi && <Alert type="error" showIcon title={loi} action={<Button size="small" onClick={() => void q.refetch()}>Tải lại bản mới</Button>} />}
      <Form form={form} layout="vertical" onFinish={(v) => luu.mutate(v)}>
        <Typography.Title level={5}>Bật/tắt module</Typography.Title>
        {Object.keys(NHAN_MODULE).map((k) => (
          <Form.Item key={k} name={['ai_module', k]} label={NHAN_MODULE[k]} valuePropName="checked" layout="horizontal"><Switch /></Form.Item>
        ))}
        <Form.Item name="ai_dau_hieu_nguy_hiem" label="Dấu hiệu nguy hiểm (chatbot dừng tư vấn, khuyên đi khám/gọi 115)" extra="Nhập cụm từ rồi Enter. So khớp không phân biệt dấu và hoa thường.">
          <Select mode="tags" tokenSeparators={[',']} open={false} placeholder="Ví dụ: đau ngực" />
        </Form.Item>
        <Form.Item name="ai_nguong_chuyen_duoc_si" label="Ngưỡng độ tin cậy chuyển dược sĩ (0 đến 1)" rules={[{ required: true, type: 'number', min: 0.01, max: 1, message: 'Nhập số trong khoảng (0, 1]' }]}>
          <InputNumber step={0.05} style={{ width: 160 }} stringMode={false} />
        </Form.Item>
        <Form.Item name="ai_loi_nhac_bo_sung" label="Lời nhắc bổ sung cho chatbot (nối vào cuối hướng dẫn hệ thống)"><Input.TextArea rows={4} maxLength={2000} showCount /></Form.Item>
        <YeuCauQuyen ma="ai.config" kieu="nut"><Button type="primary" htmlType="submit" loading={luu.isPending}>Lưu</Button></YeuCauQuyen>
      </Form>
    </Space>
  )
}
