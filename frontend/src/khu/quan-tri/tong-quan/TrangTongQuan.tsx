import { DownloadOutlined } from '@ant-design/icons'
import { App, Alert, Button, Card, DatePicker, Descriptions, Space, Statistic, Table, Tag, Typography } from 'antd'
import { useQuery } from '@tanstack/react-query'
import type { Dayjs } from 'dayjs'
import { useState } from 'react'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import dayjs from '../../../lib/dayjs'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { BieuDoCotNgay } from './BieuDoCotNgay'

type Khoang = [Dayjs, Dayjs]
const macDinh = (): Khoang => [dayjs().subtract(29, 'day'), dayjs()]
const tham = (k: Khoang) => ({ tu_ngay: k[0].format('YYYY-MM-DD'), den_ngay: k[1].format('YYYY-MM-DD') })
const phanTram = (v: string | null) => (v === null ? '—' : `${(Number(v) * 100).toFixed(1)}%`)
type TonTheoTT = components['schemas']['GiaTriTonTheoTrangThai']
const NHAN_LO: Record<string, string> = { dang_ban: 'Đang bán', can_han: 'Cận hạn', khoa: 'Khóa', het_han: 'Hết hạn', thu_hoi: 'Thu hồi' }

/** AD14: tổng quan cho Admin: doanh thu (trừ hoàn tiền), lợi nhuận gộp, bán chạy, tồn kho, cận hạn, hiệu quả AI. */
export default function TrangTongQuan() {
  const { message } = App.useApp()
  const [khoang, setKhoang] = useState<Khoang>(macDinh)
  const [dangXuat, setDangXuat] = useState(false)
  const bc = useQuery({
    queryKey: ['noi-bo', 'bao-cao', 'tong-hop', tham(khoang)],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/tong-hop', { params: { query: tham(khoang) } })
      if (error || !data) throw error ?? new Error('Không tải được báo cáo')
      return data
    },
  })
  async function xuatExcel() {
    setDangXuat(true)
    try {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/tong-hop/excel', { params: { query: tham(khoang) }, parseAs: 'blob' })
      if (error || !data) throw error ?? new Error('Xuất Excel thất bại')
      const url = URL.createObjectURL(data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bao-cao-tong-hop_${tham(khoang).tu_ngay}_${tham(khoang).den_ngay}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      void message.error('Không xuất được file Excel')
    } finally {
      setDangXuat(false)
    }
  }
  const d = bc.data
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Tổng quan</Typography.Title>
      <Space wrap>
        <DatePicker.RangePicker allowClear={false} value={khoang} format="DD/MM/YYYY" disabledDate={(x) => x.isAfter(dayjs(), 'day')} onChange={(v) => v?.[0] && v[1] && setKhoang([v[0], v[1]])} />
        <Button icon={<DownloadOutlined />} loading={dangXuat} onClick={() => void xuatExcel()}>Xuất Excel</Button>
      </Space>
      {bc.isError && <Alert type="error" showIcon title="Không tải được báo cáo (kỳ tối đa 366 ngày)" />}
      <Space wrap size="large">
        <Statistic title="Doanh thu" value={d ? dinhDangTien(d.doanh_thu) : '—'} loading={bc.isLoading} />
        <Statistic title="Hoàn tiền" value={d ? dinhDangTien(d.hoan_tien) : '—'} loading={bc.isLoading} />
        <Statistic title="Doanh thu thuần" value={d ? dinhDangTien(d.doanh_thu_thuan) : '—'} loading={bc.isLoading} />
        <Statistic title="Lợi nhuận gộp" value={d ? dinhDangTien(d.loi_nhuan_gop) : '—'} loading={bc.isLoading} />
        <Statistic title="Đơn hoàn tất" value={d?.so_don_hoan_tat ?? '—'} loading={bc.isLoading} />
        <Statistic title="Giá trị tồn kho" value={d ? dinhDangTien(d.gia_tri_ton_kho) : '—'} loading={bc.isLoading} />
      </Space>
      {d && (
        <>
          <Card size="small" title="Doanh thu theo ngày"><BieuDoCotNgay diem={d.doanh_thu_theo_ngay} /></Card>
          <Card size="small" title="Sản phẩm bán chạy">
            <Table size="small" pagination={false} rowKey="san_pham_id" dataSource={d.ban_chay} locale={{ emptyText: 'Chưa có đơn hoàn tất trong kỳ' }}
              columns={[{ title: 'Sản phẩm', render: (_, r) => `${r.ten} (${r.sku})` }, { title: 'Số lượng (đơn vị cơ sở)', dataIndex: 'so_luong_co_so', align: 'right' }, { title: 'Doanh thu', dataIndex: 'doanh_thu', align: 'right', render: (v: string) => dinhDangTien(v) }]} />
          </Card>
          <Card size="small" title={`Thuốc cận hạn (${d.so_lo_can_han} lô)`}>
            <Table size="small" pagination={false} rowKey="lo_id" dataSource={d.lo_can_han} locale={{ emptyText: 'Không có lô cận hạn' }}
              columns={[{ title: 'Sản phẩm', render: (_, r) => `${r.ten_san_pham} (${r.sku})` }, { title: 'Số lô', dataIndex: 'so_lo' }, { title: 'Hạn', dataIndex: 'han_su_dung', render: (v: string) => dinhDangNgay(v, 'ngay') }, { title: 'Còn', dataIndex: 'con_ngay', align: 'right', render: (v: number) => <Tag color={v <= 30 ? 'red' : 'orange'}>{v} ngày</Tag> }, { title: 'Tồn', dataIndex: 'so_luong_ton', align: 'right' }, { title: 'Giá trị', dataIndex: 'gia_tri', align: 'right', render: (v: string) => dinhDangTien(v) }]} />
          </Card>
          <Descriptions bordered size="small" column={2} title="Tồn kho theo trạng thái lô">
            {d.ton_kho_theo_trang_thai.map((t: TonTheoTT) => <Descriptions.Item key={t.trang_thai} label={NHAN_LO[t.trang_thai] ?? t.trang_thai}>{t.so_luong} · {dinhDangTien(t.gia_tri)}</Descriptions.Item>)}
          </Descriptions>
          <Descriptions bordered size="small" column={2} title="Hiệu quả AI">
            <Descriptions.Item label="Hội thoại">{d.hieu_qua_ai.tong_hoi_thoai}</Descriptions.Item>
            <Descriptions.Item label="Tỉ lệ chuyển dược sĩ">{phanTram(d.hieu_qua_ai.ty_le_chuyen_duoc_si)}</Descriptions.Item>
            <Descriptions.Item label="Bị gắn cờ">{d.hieu_qua_ai.so_gan_co}</Descriptions.Item>
            <Descriptions.Item label="Chi phí (USD)">{d.hieu_qua_ai.tong_chi_phi_usd}</Descriptions.Item>
            <Descriptions.Item label="Khách đánh giá hữu ích / không">{d.hieu_qua_ai.danh_gia.khach_huu_ich} / {d.hieu_qua_ai.danh_gia.khach_khong_huu_ich}</Descriptions.Item>
            <Descriptions.Item label="Dược sĩ đúng / sai">{d.hieu_qua_ai.danh_gia.duoc_si_dung} / {d.hieu_qua_ai.danh_gia.duoc_si_sai}</Descriptions.Item>
          </Descriptions>
        </>
      )}
    </Space>
  )
}
