import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Image, Input, InputNumber, Modal, Radio, Select, Space, Table, Tabs, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { NHAN_LY_DO_DOI_TRA } from '../../../lib/doiTra'

type DoiTra = components['schemas']['DoiTraKhoRa']
type HoanVe = components['schemas']['HoanVeKhoRa']
type Dong = components['schemas']['DongKhoRa']
type TinhTrang = 'nguyen_niem_phong' | 'hu_hong'

const lamMoi = (qc: ReturnType<typeof useQueryClient>) => qc.invalidateQueries({ queryKey: ['noi-bo', 'nhan-hang'] })

function NhanDoiTra({ yc, dong }: { yc: DoiTra; dong: () => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [nhan, setNhan] = useState<Record<number, { lo?: number; sl: number }>>(
    Object.fromEntries(yc.dong.map((d) => [d.ct_don_hang_id, { lo: d.lo.length === 1 ? d.lo[0].lo_id : undefined, sl: d.so_luong }])),
  )
  const [ketQua, setKetQua] = useState('')
  const [loi, setLoi] = useState<string | null>(null)
  const gui = useMutation({
    mutationFn: async () => {
      const r = await goi(() =>
        api.POST('/api/v1/noi-bo/nhan-hang/doi-tra/{yc_id}', {
          params: { path: { yc_id: yc.id } },
          body: {
            ket_qua_kiem_hang: ketQua.trim(),
            dong: yc.dong.map((d) => ({ ct_don_hang_id: d.ct_don_hang_id, lo_id: nhan[d.ct_don_hang_id].sl > 0 ? nhan[d.ct_don_hang_id].lo : undefined, so_luong_nhan: nhan[d.ct_don_hang_id].sl })),
          },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
    },
    onSuccess: () => {
      void message.success('Đã nhận hàng, hàng vào khu biệt trữ')
      void lamMoi(qc)
      dong()
    },
    onError: (e: Error) => setLoi(e.message),
  })
  const thieuLo = yc.dong.some((d) => nhan[d.ct_don_hang_id].sl > 0 && !nhan[d.ct_don_hang_id].lo)
  return (
    <Modal title={`Nhận hàng trả ${yc.ma_yeu_cau}`} open onCancel={dong} width={760} okText="Xác nhận đã nhận" cancelText="Đóng" confirmLoading={gui.isPending} okButtonProps={{ disabled: thieuLo || ketQua.trim().length < 3 }} onOk={() => gui.mutate()}>
      {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
      <Typography.Paragraph>Đơn {yc.ma_don} · {NHAN_LY_DO_DOI_TRA[yc.ly_do]}{yc.ma_van_don ? ` · Vận đơn ${yc.ma_van_don}` : ''}{yc.mo_ta ? ` · ${yc.mo_ta}` : ''}</Typography.Paragraph>
      <Image.PreviewGroup><Space wrap>{yc.anh.filter((u) => !u.includes('.mp4')).map((u) => <Image key={u} src={u} width={80} alt="Bằng chứng của khách" />)}</Space></Image.PreviewGroup>
      <Table<Dong>
        size="small"
        pagination={false}
        rowKey="ct_don_hang_id"
        dataSource={yc.dong}
        columns={[
          { title: 'Sản phẩm', render: (_, d) => `${d.ten_san_pham} (${d.ten_don_vi})` },
          { title: 'Khách trả', dataIndex: 'so_luong', align: 'right' },
          {
            title: 'Lô',
            render: (_, d) => (
              <Select
                aria-label={`Lô ${d.ten_san_pham}`}
                style={{ minWidth: 200 }}
                placeholder="Chọn lô"
                value={nhan[d.ct_don_hang_id].lo}
                onChange={(lo) => setNhan((s) => ({ ...s, [d.ct_don_hang_id]: { ...s[d.ct_don_hang_id], lo } }))}
                options={d.lo.map((l) => ({ value: l.lo_id, label: `${l.so_lo} · HSD ${dinhDangNgay(l.han_su_dung, 'ngay')}` }))}
              />
            ),
          },
          {
            title: 'Thực nhận',
            render: (_, d) => (
              <InputNumber aria-label={`Thực nhận ${d.ten_san_pham}`} value={nhan[d.ct_don_hang_id].sl} onChange={(v) => setNhan((s) => ({ ...s, [d.ct_don_hang_id]: { ...s[d.ct_don_hang_id], sl: v ?? 0 } }))} />
            ),
          },
        ]}
      />
      <Input.TextArea aria-label="Kết quả kiểm hàng" style={{ marginTop: 12 }} rows={3} maxLength={1000} showCount placeholder="Kết quả kiểm hàng (đúng mô tả không, tình trạng, niêm phong)" value={ketQua} onChange={(e) => setKetQua(e.target.value)} />
    </Modal>
  )
}

function KiemHoanVe({ don, dong }: { don: HoanVe; dong: () => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [tt, setTt] = useState<Record<number, TinhTrang>>(Object.fromEntries(don.dong.map((d) => [d.ct_don_hang_id, 'nguyen_niem_phong' as TinhTrang])))
  const [loi, setLoi] = useState<string | null>(null)
  const gui = useMutation({
    mutationFn: async () => {
      const r = await goi(() =>
        api.POST('/api/v1/noi-bo/nhan-hang/hoan-ve/{don_id}', {
          params: { path: { don_id: don.id } },
          body: { dong: don.dong.map((d) => ({ ct_don_hang_id: d.ct_don_hang_id, tinh_trang: tt[d.ct_don_hang_id] })) },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return r.data
    },
    onSuccess: (kq) => {
      void message.success(kq?.cho_hoan_tien ? 'Đã kiểm hàng, đã tạo giao dịch hoàn tiền chờ Admin xác nhận' : 'Đã kiểm hàng hoàn')
      void lamMoi(qc)
      dong()
    },
    onError: (e: Error) => setLoi(e.message),
  })
  return (
    <Modal title={`Kiểm hàng hoàn đơn ${don.ma_don}`} open onCancel={dong} width={680} okText="Xác nhận và hủy đơn" cancelText="Đóng" confirmLoading={gui.isPending} onOk={() => gui.mutate()}>
      {loi && <Alert type="error" showIcon title={loi} style={{ marginBottom: 12 }} />}
      <Alert type="info" showIcon style={{ marginBottom: 12 }} title="Nguyên niêm phong: hoàn nhập đúng lô. Hư hỏng: đưa vào khu biệt trữ. Sau đó đơn chuyển Đã hủy." />
      <Table<Dong>
        size="small"
        pagination={false}
        rowKey="ct_don_hang_id"
        dataSource={don.dong}
        columns={[
          { title: 'Sản phẩm', render: (_, d) => `${d.ten_san_pham} (${d.ten_don_vi}) × ${d.so_luong}` },
          { title: 'Lô đã xuất', render: (_, d) => d.lo.map((l) => l.so_lo).join(', ') },
          {
            title: 'Tình trạng',
            render: (_, d) => (
              <Radio.Group
                value={tt[d.ct_don_hang_id]}
                onChange={(e) => setTt((s) => ({ ...s, [d.ct_don_hang_id]: e.target.value as TinhTrang }))}
                options={[{ value: 'nguyen_niem_phong', label: 'Nguyên niêm phong' }, { value: 'hu_hong', label: 'Hư hỏng' }]}
              />
            ),
          },
        ]}
      />
    </Modal>
  )
}

/** KHO10: nhận hàng khách trả về (đổi trả) và kiểm hàng hoàn do giao thất bại. */
export default function TrangHangTraVe() {
  const [chonDoiTra, setChonDoiTra] = useState<DoiTra | null>(null)
  const [chonHoan, setChonHoan] = useState<HoanVe | null>(null)
  const dt = useQuery({
    queryKey: ['noi-bo', 'nhan-hang', 'doi-tra'],
    gcTime: 0, // URL ảnh ký có hạn
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhan-hang/doi-tra')
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  const hv = useQuery({
    queryKey: ['noi-bo', 'nhan-hang', 'hoan-ve'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/nhan-hang/hoan-ve')
      if (error || !data) throw error ?? new Error('Không tải được danh sách')
      return data
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Nhận hàng trả về</Typography.Title>
      <Tabs
        items={[
          {
            key: 'doi-tra',
            label: `Hàng khách trả (${dt.data?.length ?? 0})`,
            children: (
              <Table<DoiTra>
                rowKey="id"
                loading={dt.isLoading}
                dataSource={dt.data ?? []}
                pagination={false}
                locale={{ emptyText: 'Không có hàng trả nào chờ nhận' }}
                columns={[
                  { title: 'Mã', dataIndex: 'ma_yeu_cau' },
                  { title: 'Đơn', dataIndex: 'ma_don' },
                  { title: 'Lý do', dataIndex: 'ly_do', render: (v: DoiTra['ly_do']) => <Tag>{NHAN_LY_DO_DOI_TRA[v]}</Tag> },
                  { title: 'Vận đơn', dataIndex: 'ma_van_don' },
                  { title: '', render: (_, r) => <Button type="link" onClick={() => setChonDoiTra(r)}>Nhận hàng</Button> },
                ]}
              />
            ),
          },
          {
            key: 'hoan-ve',
            label: `Đơn hoàn về kho (${hv.data?.length ?? 0})`,
            children: (
              <Table<HoanVe>
                rowKey="id"
                loading={hv.isLoading}
                dataSource={hv.data ?? []}
                pagination={false}
                locale={{ emptyText: 'Không có đơn hoàn nào chờ kiểm' }}
                columns={[
                  { title: 'Đơn', dataIndex: 'ma_don' },
                  { title: 'Đã thanh toán', dataIndex: 'da_thanh_toan', render: (v: boolean) => (v ? 'Có' : 'Chưa') },
                  { title: '', render: (_, r) => <Button type="link" onClick={() => setChonHoan(r)}>Kiểm hàng</Button> },
                ]}
              />
            ),
          },
        ]}
      />
      {chonDoiTra && <NhanDoiTra yc={chonDoiTra} dong={() => setChonDoiTra(null)} />}
      {chonHoan && <KiemHoanVe don={chonHoan} dong={() => setChonHoan(null)} />}
    </Space>
  )
}
