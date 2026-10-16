import { InboxOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Modal, Select, Space, Table, Tag, Typography, Upload } from 'antd'
import type { UploadFile } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { loiTepBangChung } from '../../../lib/doiTra'

type Hoan = components['schemas']['HoanTienRa']
type TrangThaiGd = components['schemas']['TrangThaiGiaoDich']

const NHAN_CONG: Record<Hoan['cong_thanh_toan'], string> = { cod: 'COD', vnpay: 'VNPay', momo: 'MoMo', tien_mat: 'Tiền mặt', chuyen_khoan: 'Chuyển khoản' }

function XacNhan({ h, dong }: { h: Hoan; dong: () => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [tep, setTep] = useState<UploadFile[]>([])
  const [loi, setLoi] = useState<string | null>(null)
  const gui = useMutation({
    mutationFn: async () => {
      const f = tep[0]?.originFileObj
      const r = await goi(() =>
        api.POST('/api/v1/noi-bo/hoan-tien/{gd_id}/xac-nhan', {
          params: { path: { gd_id: h.id } },
          body: {},
          bodySerializer: () => {
            const fd = new FormData()
            if (f) fd.append('chung_tu', f)
            return fd
          },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => {
      void message.success(h.tu_dong_qua_cong ? 'Cổng thanh toán đã hoàn tiền' : 'Đã ghi nhận chuyển khoản hoàn tiền')
      void qc.invalidateQueries({ queryKey: ['noi-bo', 'hoan-tien'] })
      dong()
    },
    onError: (e: Error) => setLoi(e.message),
  })
  const tk = h.thong_tin_nhan_hoan as { ngan_hang?: string; so_tai_khoan?: string; chu_tai_khoan?: string } | null
  const thieuChungTu = !h.tu_dong_qua_cong && tep.length === 0
  return (
    <Modal
      title={`Xác nhận hoàn ${dinhDangTien(h.so_tien)} cho đơn ${h.ma_don}`}
      open
      onCancel={dong}
      okText={h.tu_dong_qua_cong ? `Hoàn qua ${NHAN_CONG[h.cong_thanh_toan]}` : 'Đã chuyển khoản'}
      cancelText="Đóng"
      confirmLoading={gui.isPending}
      okButtonProps={{ disabled: thieuChungTu || h.thieu_tai_khoan }}
      onOk={() => gui.mutate()}
      destroyOnHidden
    >
      {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
      {h.tu_dong_qua_cong ? (
        <Alert type="info" showIcon title={`Hệ thống gọi API hoàn tiền của ${NHAN_CONG[h.cong_thanh_toan]} theo giao dịch gốc.`} />
      ) : (
        <Space orientation="vertical" style={{ width: '100%' }}>
          {h.thieu_tai_khoan ? (
            <Alert type="warning" showIcon title="Khách chưa cung cấp tài khoản nhận hoàn, chưa thể xác nhận." />
          ) : tk ? (
            <Descriptions
              size="small"
              bordered
              column={1}
              items={[
                { key: 'nh', label: 'Ngân hàng', children: tk.ngan_hang },
                { key: 'stk', label: 'Số tài khoản', children: tk.so_tai_khoan },
                { key: 'ct', label: 'Chủ tài khoản', children: tk.chu_tai_khoan },
              ]}
            />
          ) : (
            <Alert type="info" showIcon title="Chuyển về tài khoản khách đã dùng khi thanh toán rồi đính kèm chứng từ." />
          )}
          <Upload.Dragger
            maxCount={1}
            listType="picture"
            accept="image/jpeg,image/png,image/webp"
            fileList={tep}
            onChange={(e) => setTep(e.fileList)}
            beforeUpload={(f) => {
              const l = loiTepBangChung(f)
              if (l || f.type === 'video/mp4') {
                setLoi(l ?? 'Chứng từ phải là ảnh')
                return Upload.LIST_IGNORE
              }
              return false
            }}
          >
            <p className="ant-upload-drag-icon"><InboxOutlined /></p>
            <p>Ảnh chứng từ chuyển khoản</p>
          </Upload.Dragger>
        </Space>
      )}
    </Modal>
  )
}

/** AD17: danh sách giao dịch hoàn tiền; VNPay/MoMo hoàn qua cổng, còn lại chuyển khoản tay kèm chứng từ. */
export default function TrangHoanTien() {
  const [loc, setLoc] = useState<TrangThaiGd>('khoi_tao')
  const [chon, setChon] = useState<Hoan | null>(null)
  const ds = useQuery({
    queryKey: ['noi-bo', 'hoan-tien', loc],
    gcTime: 0, // URL chứng từ ký có hạn
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/hoan-tien', { params: { query: { trang_thai: loc } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Hoàn tiền</Typography.Title>
      <Select<TrangThaiGd>
        value={loc}
        onChange={setLoc}
        style={{ width: 220 }}
        options={[{ value: 'khoi_tao', label: 'Chờ xác nhận' }, { value: 'thanh_cong', label: 'Đã hoàn' }]}
      />
      <Table<Hoan>
        rowKey="id"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Không có giao dịch hoàn tiền' }}
        columns={[
          { title: 'Đơn', dataIndex: 'ma_don' },
          { title: 'Khách', dataIndex: 'ten_khach' },
          { title: 'Số tiền', dataIndex: 'so_tien', align: 'right', render: (v: string) => dinhDangTien(v) },
          { title: 'Phương thức', dataIndex: 'cong_thanh_toan', render: (v: Hoan['cong_thanh_toan']) => NHAN_CONG[v] },
          { title: 'Nguồn', render: (_, r) => (r.nguon === 'doi_tra' ? `Đổi trả ${r.ma_yeu_cau}` : 'Hủy đơn') },
          { title: 'Tạo lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          {
            title: '',
            render: (_, r) =>
              r.trang_thai === 'khoi_tao' ? (
                r.thieu_tai_khoan ? (
                  <Tag color="gold">Chờ khách nhập tài khoản</Tag>
                ) : (
                  <Button type="link" onClick={() => setChon(r)}>Xác nhận</Button>
                )
              ) : (
                <Space>
                  <Tag color="green">Đã hoàn {dinhDangNgay(r.xu_ly_luc, 'ngayGio')}</Tag>
                  {r.chung_tu && <a href={r.chung_tu} target="_blank" rel="noreferrer">Chứng từ</a>}
                </Space>
              ),
          },
        ]}
      />
      {chon && <XacNhan h={chon} dong={() => setChon(null)} />}
    </Space>
  )
}
