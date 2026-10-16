import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Checkbox, Form, Input, InputNumber, Popconfirm, Select, Space, Spin, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { laLoiApi } from '../../../api/loi'
import { usePhien } from '../../../stores/phien'

interface FormSucKhoe {
  nam_sinh?: number | null
  benh_nen?: string | null
  dang_mang_thai?: boolean
  dang_cho_con_bu?: boolean
  di_ung: { value: number; label: string }[]
}
const KHOA = ['toi', 'ho-so-suc-khoe'] as const
const NAM_NAY = new Date().getFullYear()

/** KTV11: hồ sơ sức khỏe. Chỉ lưu sau khi khách đồng ý; xóa hồ sơ cũng là thu hồi đồng ý (QĐ-32). */
export default function TrangSucKhoe() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [form] = Form.useForm<FormSucKhoe>()
  const daKhoiPhuc = usePhien((s) => s.daKhoiPhuc)
  const khach = usePhien((s) => s.loai === 'khach')
  const [dongY, setDongY] = useState(false)
  const [tuKhoa, setTuKhoa] = useState('')

  const hoSo = useQuery({
    queryKey: KHOA,
    enabled: khach,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/toi/ho-so-suc-khoe')
      if (error || !data) throw error ?? new Error('Không tải được hồ sơ sức khỏe')
      return data
    },
  })
  const hoatChat = useQuery({
    queryKey: [...KHOA, 'hoat-chat', tuKhoa],
    enabled: khach && (hoSo.data?.dong_y_su_dung ?? false) || dongY,
    queryFn: async () =>
      (await api.GET('/api/v1/toi/ho-so-suc-khoe/hoat-chat', { params: { query: { q: tuKhoa || undefined } } })).data ?? [],
  })

  const daCoHoSo = hoSo.data?.dong_y_su_dung ?? false
  useEffect(() => {
    if (!hoSo.data) return
    form.setFieldsValue({
      nam_sinh: hoSo.data.nam_sinh,
      benh_nen: hoSo.data.benh_nen,
      dang_mang_thai: hoSo.data.dang_mang_thai ?? false,
      dang_cho_con_bu: hoSo.data.dang_cho_con_bu ?? false,
      di_ung: hoSo.data.di_ung.map((d) => ({ value: d.hoat_chat_id, label: d.ten_hoat_chat })),
    })
  }, [hoSo.data, form])

  const luu = useMutation({
    mutationFn: async (v: FormSucKhoe) => {
      const r = await api.PUT('/api/v1/toi/ho-so-suc-khoe', {
        body: {
          dong_y_su_dung: true,
          nam_sinh: v.nam_sinh ?? null,
          benh_nen: v.benh_nen?.trim() || null,
          dang_mang_thai: v.dang_mang_thai ?? null,
          dang_cho_con_bu: v.dang_cho_con_bu ?? null,
          di_ung: (v.di_ung ?? []).map((d) => ({ hoat_chat_id: d.value })),
        },
      })
      if (r.error) throw r.error
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: KHOA })
      void message.success('Đã lưu hồ sơ sức khỏe')
    },
    onError: (e) => void message.error(laLoiApi(e) ? e.thong_diep : 'Không lưu được hồ sơ'),
  })
  const xoa = useMutation({
    mutationFn: async () => {
      const r = await api.DELETE('/api/v1/toi/ho-so-suc-khoe')
      if (!r.response.ok) throw new Error('Không xóa được hồ sơ')
    },
    onSuccess: async () => {
      setDongY(false)
      form.resetFields()
      await qc.invalidateQueries({ queryKey: KHOA })
      void message.success('Đã xóa hồ sơ và thu hồi đồng ý')
    },
    onError: (e) => void message.error(laLoiApi(e) ? e.thong_diep : 'Không xóa được hồ sơ'),
  })

  if (!daKhoiPhuc) return <Spin />
  if (!khach) return <Navigate to="/dang-nhap?tiep=/tai-khoan/suc-khoe" replace />
  if (hoSo.isLoading) return <Spin />

  return (
    <Space orientation="vertical" size="large" style={{ width: '100%', maxWidth: 640 }}>
      <Link to="/tai-khoan">← Tài khoản</Link>
      <Typography.Title level={2} style={{ margin: 0 }}>Hồ sơ sức khỏe</Typography.Title>
      {!daCoHoSo && !dongY ? (
        <Card data-testid="man-dong-y" title="Đồng ý sử dụng dữ liệu sức khỏe">
          <Typography.Paragraph>
            Dị ứng, bệnh nền, tình trạng mang thai hoặc cho con bú là dữ liệu cá nhân nhạy cảm. Khi bạn đồng ý, nhà thuốc dùng dữ liệu này để
            cảnh báo dị ứng, tương tác thuốc và để AI lọc gợi ý. Quản trị viên không xem được. Dược sĩ chỉ xem khi đang xử lý yêu cầu đơn thuốc
            hoặc phiên chat của chính bạn. Bạn xóa được hồ sơ và thu hồi đồng ý bất kỳ lúc nào.
          </Typography.Paragraph>
          <Button type="primary" onClick={() => setDongY(true)}>Tôi đồng ý</Button>
        </Card>
      ) : (
        <Form form={form} layout="vertical" onFinish={(v) => luu.mutate(v)} initialValues={{ di_ung: [] }}>
          <Alert type="info" showIcon style={{ marginBottom: 16 }} title="Bạn đã đồng ý sử dụng dữ liệu sức khỏe. Chỉ khai những gì bạn muốn." />
          <Form.Item name="di_ung" label="Dị ứng hoạt chất">
            <Select
              mode="multiple"
              labelInValue
              showSearch={{ filterOption: false, onSearch: setTuKhoa }}
              placeholder="Gõ tên hoạt chất, ví dụ Amoxicillin"
              loading={hoatChat.isFetching}
              options={(hoatChat.data ?? []).map((h) => ({ value: h.id, label: h.ten }))}
              notFoundContent="Không có hoạt chất phù hợp"
            />
          </Form.Item>
          <Form.Item name="benh_nen" label="Bệnh nền">
            <Input.TextArea rows={3} maxLength={2000} showCount placeholder="Ví dụ: tiểu đường, huyết áp cao" />
          </Form.Item>
          <Form.Item name="nam_sinh" label="Năm sinh">
            <InputNumber min={1900} max={NAM_NAY} style={{ width: 160 }} />
          </Form.Item>
          <Form.Item name="dang_mang_thai" valuePropName="checked"><Checkbox>Đang mang thai</Checkbox></Form.Item>
          <Form.Item name="dang_cho_con_bu" valuePropName="checked"><Checkbox>Đang cho con bú</Checkbox></Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={luu.isPending}>Lưu hồ sơ</Button>
            {daCoHoSo && (
              <Popconfirm
                title="Xóa hồ sơ và thu hồi đồng ý?"
                description="Toàn bộ dị ứng, bệnh nền sẽ bị xóa vĩnh viễn."
                okText="Xóa"
                cancelText="Hủy"
                onConfirm={() => xoa.mutate()}
              >
                <Button danger loading={xoa.isPending}>Xóa hồ sơ</Button>
              </Popconfirm>
            )}
          </Space>
        </Form>
      )}
    </Space>
  )
}
