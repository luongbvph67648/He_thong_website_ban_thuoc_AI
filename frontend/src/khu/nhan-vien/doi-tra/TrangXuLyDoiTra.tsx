import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Drawer, Image, Input, Modal, Radio, Select, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { NHAN_HUONG_XU_LY, NHAN_LY_DO_DOI_TRA, NHAN_TRANG_THAI_DOI_TRA, type HuongXuLy, type TrangThaiDoiTra } from '../../../lib/doiTra'

type Tom = components['schemas']['DoiTraNoiBoTom']

/** DS09: xử lý đổi trả. Duyệt (chọn hướng, tạo vận đơn trả), từ chối, tạo hoàn tiền hoặc gửi hàng thay thế sau khi kho nhận. */
export default function TrangXuLyDoiTra() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [loc, setLoc] = useState<TrangThaiDoiTra | undefined>()
  const [xem, setXem] = useState<number | null>(null)
  const [huong, setHuong] = useState<HuongXuLy>('hoan_tien')
  const [moTuChoi, setMoTuChoi] = useState(false)
  const [lyDo, setLyDo] = useState('')

  const ds = useQuery({
    queryKey: ['noi-bo', 'doi-tra', 'ds', loc],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/doi-tra', { params: { query: { trang_thai: loc } } })
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  const ct = useQuery({
    queryKey: ['noi-bo', 'doi-tra', 'ct', xem],
    enabled: xem !== null,
    gcTime: 0, // URL ảnh ký có hạn
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/doi-tra/{yc_id}', { params: { path: { yc_id: xem! } } })
      if (error || !data) throw error ?? new Error('Không tải được chi tiết')
      return data
    },
  })
  const lamMoi = () => void qc.invalidateQueries({ queryKey: ['noi-bo', 'doi-tra'] })
  const hanhDong = useMutation({
    mutationFn: async (f: () => Promise<{ ok: boolean; loi?: Parameters<typeof thongDiepChung>[0] }>) => {
      const r = await f()
      if (!r.ok) throw new Error(thongDiepChung(r.loi ?? null))
    },
    onSuccess: () => {
      lamMoi()
      setMoTuChoi(false)
      setLyDo('')
    },
    onError: (e: Error) => void message.error(e.message),
  })

  const d = ct.data
  const id = xem as number
  const post = (duong: '/duyet' | '/hoan-tien' | '/thay-the', body?: { huong_xu_ly: HuongXuLy }) =>
    hanhDong.mutate(() =>
      duong === '/duyet'
        ? goi(() => api.POST('/api/v1/noi-bo/doi-tra/{yc_id}/duyet', { params: { path: { yc_id: id } }, body: body! }))
        : duong === '/hoan-tien'
          ? goi(() => api.POST('/api/v1/noi-bo/doi-tra/{yc_id}/hoan-tien', { params: { path: { yc_id: id } } }))
          : goi(() => api.POST('/api/v1/noi-bo/doi-tra/{yc_id}/thay-the', { params: { path: { yc_id: id } } })),
    )

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Xử lý đổi trả</Typography.Title>
      <Select<TrangThaiDoiTra>
        allowClear
        placeholder="Đang cần xử lý (mặc định)"
        style={{ width: 280 }}
        value={loc}
        onChange={setLoc}
        options={(Object.keys(NHAN_TRANG_THAI_DOI_TRA) as TrangThaiDoiTra[]).map((k) => ({ value: k, label: NHAN_TRANG_THAI_DOI_TRA[k].nhan }))}
      />
      <Table<Tom>
        rowKey="id"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Không có yêu cầu đổi trả nào' }}
        columns={[
          { title: 'Mã', dataIndex: 'ma_yeu_cau' },
          { title: 'Đơn', dataIndex: 'ma_don' },
          { title: 'Khách', render: (_, r) => `${r.ten_khach}${r.so_dien_thoai_khach ? ` · ${r.so_dien_thoai_khach}` : ''}` },
          { title: 'Lý do', dataIndex: 'ly_do', render: (v: Tom['ly_do']) => NHAN_LY_DO_DOI_TRA[v] },
          { title: 'Gửi lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          { title: 'Trạng thái', dataIndex: 'trang_thai', render: (t: Tom['trang_thai']) => <Tag color={NHAN_TRANG_THAI_DOI_TRA[t].mau}>{NHAN_TRANG_THAI_DOI_TRA[t].nhan}</Tag> },
          { title: '', render: (_, r) => <Button type="link" onClick={() => setXem(r.id)}>Xử lý</Button> },
        ]}
      />
      <Drawer title={d ? `Đổi trả ${d.ma_yeu_cau}` : 'Đổi trả'} open={xem !== null} onClose={() => setXem(null)} size="large">
        {ct.isLoading && <Spin />}
        {d && (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <Tag color={NHAN_TRANG_THAI_DOI_TRA[d.trang_thai].mau}>{NHAN_TRANG_THAI_DOI_TRA[d.trang_thai].nhan}</Tag>
            <Descriptions
              size="small"
              bordered
              column={1}
              items={[
                { key: 'k', label: 'Khách', children: `${d.ten_khach}${d.so_dien_thoai_khach ? ` · ${d.so_dien_thoai_khach}` : ''}` },
                { key: 'd', label: 'Đơn gốc', children: `${d.ma_don} (đã thanh toán ${dinhDangTien(d.tong_da_thanh_toan)})` },
                { key: 'l', label: 'Lý do', children: NHAN_LY_DO_DOI_TRA[d.ly_do] },
                ...(d.mo_ta ? [{ key: 'm', label: 'Mô tả', children: d.mo_ta }] : []),
                ...(d.huong_xu_ly ? [{ key: 'h', label: 'Hướng xử lý', children: NHAN_HUONG_XU_LY[d.huong_xu_ly] }] : []),
                ...(d.huong_xu_ly === 'hoan_tien' && d.so_tien_hoan ? [{ key: 's', label: 'Số tiền hoàn', children: dinhDangTien(d.so_tien_hoan) }] : []),
                ...(d.ma_van_don ? [{ key: 'v', label: 'Vận đơn trả hàng', children: d.ma_van_don }] : []),
                ...(d.ket_qua_kiem_hang ? [{ key: 'kh', label: 'Kết quả kiểm hàng', children: d.ket_qua_kiem_hang }] : []),
                ...(d.ly_do_tu_choi ? [{ key: 'tc', label: 'Lý do từ chối', children: d.ly_do_tu_choi }] : []),
              ]}
            />
            <Table
              size="small"
              pagination={false}
              rowKey="ct_don_hang_id"
              dataSource={d.dong}
              columns={[
                { title: 'Sản phẩm', render: (_, r) => `${r.ten_san_pham} (${r.ten_don_vi})` },
                { title: 'Trả', align: 'right', render: (_, r) => `${r.so_luong_tra}/${r.so_luong_mua}` },
                { title: 'Giá trị', align: 'right', render: (_, r) => dinhDangTien(r.thanh_tien) },
                { title: 'Kho nhận', align: 'right', dataIndex: 'so_luong_nhan' },
              ]}
            />
            <Image.PreviewGroup>
              <Space wrap>{d.anh.filter((u) => !u.includes('.mp4')).map((u) => <Image key={u} src={u} width={120} alt="Bằng chứng đổi trả" />)}</Space>
            </Image.PreviewGroup>
            {d.anh.filter((u) => u.includes('.mp4')).map((u) => <video key={u} src={u} controls style={{ maxWidth: '100%' }} />)}
            {d.trang_thai === 'cho_duyet' && (
              <Space orientation="vertical">
                <Radio.Group
                  value={huong}
                  onChange={(e) => setHuong(e.target.value)}
                  options={(Object.keys(NHAN_HUONG_XU_LY) as HuongXuLy[]).map((k) => ({ value: k, label: NHAN_HUONG_XU_LY[k] }))}
                />
                <Space>
                  <Button type="primary" loading={hanhDong.isPending} onClick={() => post('/duyet', { huong_xu_ly: huong })}>Duyệt, tạo vận đơn trả</Button>
                  <Button danger onClick={() => setMoTuChoi(true)}>Từ chối</Button>
                </Space>
              </Space>
            )}
            {d.trang_thai === 'da_duyet' && <Alert type="info" showIcon title="Đang chờ kho nhận hàng trả về" />}
            {d.trang_thai === 'kho_da_nhan' && (
              <Space>
                {d.huong_xu_ly === 'hoan_tien' && !d.da_co_giao_dich_hoan && (
                  <Button type="primary" loading={hanhDong.isPending} onClick={() => post('/hoan-tien')}>Tạo giao dịch hoàn tiền</Button>
                )}
                {d.huong_xu_ly === 'hoan_tien' && d.da_co_giao_dich_hoan && <Alert type="success" showIcon title="Đã tạo giao dịch hoàn tiền, chờ Admin xác nhận chuyển tiền" />}
                {d.huong_xu_ly === 'gui_hang_thay_the' && (
                  <Button type="primary" loading={hanhDong.isPending} onClick={() => post('/thay-the')}>Gửi hàng thay thế</Button>
                )}
                {!d.da_co_giao_dich_hoan && <Button danger onClick={() => setMoTuChoi(true)}>Từ chối (kiểm không đạt)</Button>}
              </Space>
            )}
          </Space>
        )}
      </Drawer>
      <Modal
        title="Từ chối yêu cầu đổi trả"
        open={moTuChoi}
        okText="Từ chối"
        cancelText="Đóng"
        okButtonProps={{ danger: true, disabled: lyDo.trim().length < 3, loading: hanhDong.isPending }}
        onCancel={() => setMoTuChoi(false)}
        onOk={() => hanhDong.mutate(() => goi(() => api.POST('/api/v1/noi-bo/doi-tra/{yc_id}/tu-choi', { params: { path: { yc_id: id } }, body: { ly_do: lyDo.trim() } })))}
        destroyOnHidden
      >
        <Input.TextArea rows={3} maxLength={500} placeholder="Lý do (bắt buộc, khách sẽ nhận được)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
      </Modal>
    </Space>
  )
}
