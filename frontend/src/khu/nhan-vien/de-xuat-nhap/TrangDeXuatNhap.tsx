import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Checkbox, Drawer, Input, Select, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { BieuDoTuan } from './BieuDoTuan'

type Dong = components['schemas']['DeXuatRa']

const KICH_THUOC = 20
const KHOA = ['noi-bo', 'de-xuat-nhap'] as const
const NHAN_MO_HINH: Record<string, string> = { holt_winters: 'Holt-Winters', trung_binh_truot: 'Trung bình trượt', khong_co_lich_su: 'Chưa có lịch sử bán' }

/** KHO14: đề xuất nhập hàng từ dự báo AI09. Kho xem biểu đồ lịch sử/dự báo và đánh dấu đã xử lý khi đã lập phiếu nhập. */
export default function TrangDeXuatNhap() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [trang, setTrang] = useState(1)
  const [ky, setKy] = useState<string | undefined>()
  const [q, setQ] = useState('')
  const [chiCanNhap, setChiCanNhap] = useState(true)
  const [chuaXuLy, setChuaXuLy] = useState(false)
  const [mo, setMo] = useState<Dong | null>(null)

  const cacKy = useQuery({
    queryKey: [...KHOA, 'ky'],
    queryFn: async () => (await api.GET('/api/v1/noi-bo/de-xuat-nhap/ky')).data ?? [],
  })
  const ds = useQuery({
    queryKey: [...KHOA, 'ds', ky, q, chiCanNhap, chuaXuLy, trang],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/de-xuat-nhap', {
        params: { query: { ky, q: q.trim() || undefined, chi_can_nhap: chiCanNhap, da_xu_ly: chuaXuLy ? false : undefined, trang, kich_thuoc: KICH_THUOC } },
      })
      if (error || !data) throw error ?? new Error('Không tải được đề xuất')
      return data
    },
  })
  const bieuDo = useQuery({
    queryKey: [...KHOA, 'bieu-do', mo?.id],
    enabled: mo !== null,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/de-xuat-nhap/{de_xuat_id}/bieu-do', { params: { path: { de_xuat_id: mo!.id } } })
      if (error || !data) throw error ?? new Error('Không tải được biểu đồ')
      return data
    },
  })
  const danhDau = useMutation({
    mutationFn: async ({ id, daXuLy }: { id: number; daXuLy: boolean }) => {
      const r = await goi(() => api.PUT('/api/v1/noi-bo/de-xuat-nhap/{de_xuat_id}/da-xu-ly', { params: { path: { de_xuat_id: id } }, body: { da_xu_ly: daXuLy } }))
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return r.data as Dong
    },
    onSuccess: (d) => {
      void qc.invalidateQueries({ queryKey: [...KHOA, 'ds'] })
      setMo((cu) => (cu && cu.id === d.id ? d : cu))
    },
    onError: (e: Error) => void message.error(e.message),
  })

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Đề xuất nhập từ AI</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Dự báo nhu cầu 30 ngày từ lượng đã xuất kho mỗi tuần. Đề xuất = dự báo + tồn tối thiểu − tồn khả dụng; chỉ để tham khảo, kho quyết định số lượng nhập.
      </Typography.Paragraph>
      <Space wrap>
        <Select aria-label="Kỳ đề xuất" style={{ width: 240 }} placeholder="Kỳ mới nhất" allowClear value={ky} onChange={(v) => { setKy(v); setTrang(1) }}
          options={(cacKy.data ?? []).map((k) => ({ value: k.ky_bat_dau, label: `${dinhDangNgay(k.ky_bat_dau, 'ngay')} – ${dinhDangNgay(k.ky_ket_thuc, 'ngay')} (${k.so_san_pham})` }))} />
        <Input.Search allowClear placeholder="Tìm theo tên hoặc SKU" style={{ width: 260 }} maxLength={100} onSearch={(v) => { setQ(v); setTrang(1) }} />
        <Checkbox checked={chiCanNhap} onChange={(e) => { setChiCanNhap(e.target.checked); setTrang(1) }}>Chỉ sản phẩm cần nhập</Checkbox>
        <Checkbox checked={chuaXuLy} onChange={(e) => { setChuaXuLy(e.target.checked); setTrang(1) }}>Chưa xử lý</Checkbox>
      </Space>
      {ds.isError && <Alert type="error" showIcon title="Không tải được đề xuất" />}
      <Table<Dong>
        rowKey="id"
        size="small"
        loading={ds.isLoading}
        dataSource={ds.data?.du_lieu ?? []}
        locale={{ emptyText: 'Chưa có đề xuất nào (job dự báo chạy mỗi thứ Hai)' }}
        pagination={{ current: trang, pageSize: KICH_THUOC, total: ds.data?.tong ?? 0, showSizeChanger: false, onChange: setTrang }}
        columns={[
          { title: 'Sản phẩm', render: (_, r) => <><div>{r.ten_san_pham}</div><Typography.Text type="secondary">{r.sku}</Typography.Text></> },
          { title: 'Dự báo 30 ngày', dataIndex: 'so_luong_du_bao', align: 'right' },
          { title: 'Tồn khả dụng', dataIndex: 'ton_kha_dung', align: 'right' },
          { title: 'Tồn tối thiểu', dataIndex: 'ton_toi_thieu', align: 'right' },
          { title: 'Đề xuất nhập', dataIndex: 'so_luong_de_xuat', align: 'right', render: (v: number, r) => <strong>{v} {r.don_vi_co_so}</strong> },
          { title: 'Mô hình', render: (_, r) => <>{NHAN_MO_HINH[r.mo_hinh ?? ''] ?? r.mo_hinh}{r.sai_so_mape !== null && <div><Typography.Text type="secondary">MAPE {Number(r.sai_so_mape).toFixed(1)}%</Typography.Text></div>}</> },
          { title: 'Trạng thái', render: (_, r) => (r.da_xu_ly ? <Tag color="green">Đã xử lý</Tag> : <Tag color="gold">Chưa xử lý</Tag>) },
          { title: '', render: (_, r) => <Button size="small" onClick={() => setMo(r)}>Biểu đồ</Button> },
        ]}
      />
      <Drawer title={mo?.ten_san_pham} size={720} open={mo !== null} onClose={() => setMo(null)} destroyOnHidden>
        {bieuDo.isError && <Alert type="error" showIcon title="Không tải được biểu đồ" />}
        {bieuDo.data && (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            <BieuDoTuan lichSu={bieuDo.data.lich_su} duBao={bieuDo.data.du_bao} donVi={bieuDo.data.don_vi_co_so} />
            <Typography.Text type="secondary">26 tuần gần nhất đã xuất (xanh đậm) và 5 tuần dự báo (xanh nhạt). Đơn vị: {bieuDo.data.don_vi_co_so}.</Typography.Text>
          </Space>
        )}
        {mo && (
          <YeuCauQuyen ma="forecast.view" kieu="nut">
            <Button style={{ marginTop: 16 }} type={mo.da_xu_ly ? 'default' : 'primary'} loading={danhDau.isPending} onClick={() => danhDau.mutate({ id: mo.id, daXuLy: !mo.da_xu_ly })}>
              {mo.da_xu_ly ? 'Bỏ đánh dấu đã xử lý' : 'Đánh dấu đã xử lý (đã lập phiếu nhập)'}
            </Button>
          </YeuCauQuyen>
        )}
      </Drawer>
    </Space>
  )
}
