import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Form, Input, Modal, Popconfirm, Radio, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'

type Ncc = components['schemas']['NhaCungCapRa']
type TrangThai = 'dang_hop_tac' | 'ngung' | 'tat_ca'
const KHOA = ['nhan-vien', 'nha-cung-cap'] as const
const TRUONG = ['ten', 'ma_so_thue', 'dia_chi', 'nguoi_lien_he', 'so_dien_thoai', 'email'] as const

/** KHO01: danh sách, thêm, sửa, ngừng hợp tác (xóa mềm) và hợp tác lại nhà cung cấp. Admin chỉ xem. */
export default function TrangNhaCungCap() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const coGhi = coQuyen(usePhien((s) => s.quyen), 'supplier.manage')
  const [q, setQ] = useState('')
  const [trangThai, setTrangThai] = useState<TrangThai>('dang_hop_tac')
  const [trang, setTrang] = useState(1)
  const [soan, setSoan] = useState<Ncc | 'moi' | null>(null)
  const [form] = Form.useForm()
  const [dangLuu, setDangLuu] = useState(false)
  const [thongDiep, setThongDiep] = useState<string | null>(null)

  const ds = useQuery({
    queryKey: [...KHOA, q, trangThai, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nha-cung-cap', { params: { query: { q: q.trim() || undefined, trang_thai: trangThai, trang, kich_thuoc: 20 } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
    placeholderData: (truoc) => truoc,
  })
  const lamMoi = () => void queryClient.invalidateQueries({ queryKey: KHOA })

  const mo = (n: Ncc | 'moi') => {
    setSoan(n)
    setThongDiep(null)
    form.resetFields()
    if (n !== 'moi') form.setFieldsValue(Object.fromEntries(TRUONG.map((t) => [t, n[t] ?? ''])))
  }

  const luu = async () => {
    if (soan === null) return
    const v = (await form.validateFields()) as Record<string, string | undefined>
    const giaTri = Object.fromEntries(TRUONG.map((t) => [t, (v[t] ?? '').trim() || null]))
    setDangLuu(true)
    const kq = await goi(() =>
      soan === 'moi'
        ? api.POST('/api/v1/noi-bo/nha-cung-cap', { body: giaTri as never })
        : api.PATCH('/api/v1/noi-bo/nha-cung-cap/{nha_cung_cap_id}', { params: { path: { nha_cung_cap_id: soan.id } }, body: { ...giaTri, phien_ban: soan.phien_ban } as never }),
    )
    setDangLuu(false)
    if (!kq.ok) {
      const theoTruong = kq.loi ? loiTheoTruong(kq.loi) : {}
      form.setFields(Object.entries(theoTruong).map(([name, loi]) => ({ name, errors: [loi] })))
      setThongDiep(thongDiepChung(kq.loi))
      if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') lamMoi()
      return
    }
    void message.success(soan === 'moi' ? 'Đã thêm nhà cung cấp' : 'Đã lưu')
    setSoan(null)
    lamMoi()
  }

  const ngung = async (n: Ncc) => {
    const kq = await goi(() => api.DELETE('/api/v1/noi-bo/nha-cung-cap/{nha_cung_cap_id}', { params: { path: { nha_cung_cap_id: n.id }, query: { phien_ban: n.phien_ban } } }))
    if (!kq.ok) void message.error(thongDiepChung(kq.loi))
    else void message.success('Đã ngừng hợp tác')
    lamMoi()
  }
  const hopTacLai = async (n: Ncc) => {
    const kq = await goi(() => api.POST('/api/v1/noi-bo/nha-cung-cap/{nha_cung_cap_id}/hop-tac-lai', { params: { path: { nha_cung_cap_id: n.id } } }))
    if (!kq.ok) void message.error(thongDiepChung(kq.loi))
    else void message.success('Đã hợp tác lại')
    lamMoi()
  }

  const cot: ColumnsType<Ncc> = [
    { title: 'Tên', dataIndex: 'ten', key: 'ten' },
    { title: 'Mã số thuế', dataIndex: 'ma_so_thue', key: 'mst', width: 150 },
    { title: 'Người liên hệ', dataIndex: 'nguoi_lien_he', key: 'lh', width: 160 },
    { title: 'Điện thoại', dataIndex: 'so_dien_thoai', key: 'sdt', width: 130 },
    { title: 'Email', dataIndex: 'email', key: 'email' },
    { title: 'Trạng thái', key: 'tt', width: 130, render: (_, n) => <Tag color={n.dang_hop_tac ? 'green' : 'default'}>{n.dang_hop_tac ? 'Đang hợp tác' : 'Đã ngừng'}</Tag> },
    {
      title: 'Thao tác',
      key: 'tt2',
      width: 190,
      render: (_, n) =>
        coGhi && (
          <Space>
            <Button size="small" onClick={() => mo(n)}>
              Sửa
            </Button>
            {n.dang_hop_tac ? (
              <Popconfirm title="Ngừng hợp tác với nhà cung cấp này?" okText="Ngừng" cancelText="Hủy" onConfirm={() => void ngung(n)}>
                <Button size="small" danger>
                  Ngừng
                </Button>
              </Popconfirm>
            ) : (
              <Button size="small" onClick={() => void hopTacLai(n)}>
                Hợp tác lại
              </Button>
            )}
          </Space>
        ),
    },
  ]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Space wrap>
        <Input.Search allowClear placeholder="Tên, mã số thuế, người liên hệ, điện thoại" style={{ width: 340 }} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Radio.Group value={trangThai} onChange={(e) => { setTrangThai(e.target.value as TrangThai); setTrang(1) }}>
          <Radio.Button value="dang_hop_tac">Đang hợp tác</Radio.Button>
          <Radio.Button value="ngung">Đã ngừng</Radio.Button>
          <Radio.Button value="tat_ca">Tất cả</Radio.Button>
        </Radio.Group>
        {coGhi && (
          <Button type="primary" onClick={() => mo('moi')}>
            Thêm nhà cung cấp
          </Button>
        )}
      </Space>
      {ds.isError && <Alert type="error" showIcon message="Không tải được danh sách nhà cung cấp" />}
      <Table<Ncc>
        rowKey="id"
        columns={cot}
        dataSource={ds.data?.du_lieu ?? []}
        loading={ds.isLoading}
        pagination={{ current: trang, pageSize: 20, total: ds.data?.tong ?? 0, onChange: setTrang, showSizeChanger: false }}
      />
      <Modal title={soan === 'moi' ? 'Thêm nhà cung cấp' : 'Sửa nhà cung cấp'} open={soan !== null} onCancel={() => setSoan(null)} onOk={() => void luu()} confirmLoading={dangLuu} okText="Lưu" cancelText="Hủy" mask={{ closable: false }} destroyOnHidden>
        {thongDiep && <Alert type="error" showIcon message={thongDiep} style={{ marginBottom: 12 }} />}
        <Form form={form} layout="vertical">
          <Form.Item name="ten" label="Tên nhà cung cấp" rules={[{ required: true, whitespace: true, message: 'Vui lòng nhập tên' }, { max: 200, message: 'Tối đa 200 ký tự' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="ma_so_thue" label="Mã số thuế (10 hoặc 13 số)">
            <Input />
          </Form.Item>
          <Form.Item name="nguoi_lien_he" label="Người liên hệ">
            <Input />
          </Form.Item>
          <Form.Item name="so_dien_thoai" label="Số điện thoại">
            <Input />
          </Form.Item>
          <Form.Item name="email" label="Email">
            <Input />
          </Form.Item>
          <Form.Item name="dia_chi" label="Địa chỉ">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  )
}
