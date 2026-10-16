import { DeleteOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import { useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Input, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { mauDoTinCay } from './thuocTrenDon'

type YeuCau = components['schemas']['YeuCauDuyetRa']
type Dong = components['schemas']['ThuocTrenDonRa']

interface DongSua {
  khoa: string
  id: number | null
  ten: string
  hamLuong: string
  soLuong: string
  sanPhamId: number | null
  tenSanPham: string | null
  doTinCay: string | null
  duocSiNhap: boolean
}

let dem = 0
const tuApi = (d: Dong): DongSua => ({ khoa: `d${d.id}`, id: d.id, ten: d.ten_thuoc_tren_don, hamLuong: d.ham_luong ?? '', soLuong: d.so_luong_ke ?? '', sanPhamId: d.san_pham_id, tenSanPham: d.ten_san_pham, doTinCay: d.do_tin_cay_ai, duocSiNhap: d.do_duoc_si_nhap })
const dongMoi = (): DongSua => ({ khoa: `m${++dem}`, id: null, ten: '', hamLuong: '', soLuong: '', sanPhamId: null, tenSanPham: null, doTinCay: null, duocSiNhap: true })

/** T7.6 (DS04): thuốc trên đơn do AI06 đọc kèm độ tin cậy; dược sĩ sửa, thêm, xóa rồi bấm lưu để chốt. AI không tự duyệt. */
export default function ThuocTrenDon({ yc, onTim }: { yc: YeuCau; onTim: (tuKhoa: string) => void }) {
  const { message } = App.useApp()
  const qc = useQueryClient()
  // `sua` = null: chưa sửa gì, hiển thị thẳng dữ liệu máy chủ (kết quả AI đến muộn vẫn hiện); có giá trị: bản đang sửa.
  const [sua, setSua] = useState<DongSua[] | null>(null)
  const [dang, setDang] = useState(false)
  const [loi, setLoi] = useState<string | null>(null)
  const ds = sua ?? yc.thuoc_tren_don.map(tuApi)
  const daSua = sua !== null
  const capNhat = (f: (x: DongSua[]) => DongSua[]) => setSua((cu) => f(cu ?? yc.thuoc_tren_don.map(tuApi)))
  const doi = (khoa: string, f: Partial<DongSua>) => capNhat((x) => x.map((d) => (d.khoa === khoa ? { ...d, ...f } : d)))
  const ai = yc.ket_qua_ai as { trang_thai?: string; ngay_ke?: string | null; co_chu_ky_bac_si?: boolean } | null

  async function luu() {
    if (ds.some((d) => !d.ten.trim())) return setLoi('Tên thuốc không được để trống')
    setDang(true)
    setLoi(null)
    const r = await goi(() =>
      api.PUT('/api/v1/noi-bo/don-thuoc/{yc_id}/thuoc-tren-don', {
        params: { path: { yc_id: yc.id } },
        body: { dong: ds.map((d) => ({ id: d.id, ten_thuoc_tren_don: d.ten.trim(), ham_luong: d.hamLuong.trim() || null, so_luong_ke: d.soLuong.trim() || null, san_pham_id: d.sanPhamId })) },
      }),
    )
    setDang(false)
    if (!r.ok) return setLoi(thongDiepChung(r.loi))
    qc.setQueryData(['noi-bo', 'don-thuoc', yc.id], r.data)
    setSua(null)
    void message.success('Đã lưu danh sách thuốc trên đơn')
  }

  return (
    <Card size="small" title="Thuốc trên đơn (AI đọc, dược sĩ xác nhận)">
      <Space orientation="vertical" style={{ width: '100%' }}>
        {ai?.trang_thai === 'loi' && <Alert type="info" showIcon title="AI chưa đọc được ảnh đơn này, hãy nhập thuốc từ ảnh." />}
        {ai?.trang_thai === 'xong' && (
          <Typography.Text type="secondary">
            AI đọc: ngày kê {ai.ngay_ke ?? 'không rõ'}, {ai.co_chu_ky_bac_si ? 'có' : 'không thấy'} chữ ký bác sĩ. Gợi ý chỉ để tham khảo, hãy đối chiếu với ảnh.
          </Typography.Text>
        )}
        <Table<DongSua>
          size="small"
          pagination={false}
          rowKey="khoa"
          dataSource={ds}
          locale={{ emptyText: 'Chưa có thuốc nào, bấm "Thêm thuốc" để nhập từ ảnh đơn' }}
          columns={[
            { title: 'Thuốc trên đơn', render: (_, d) => <Input aria-label="Tên thuốc trên đơn" value={d.ten} maxLength={255} onChange={(e) => doi(d.khoa, { ten: e.target.value, doTinCay: null, duocSiNhap: true })} /> },
            { title: 'Hàm lượng', width: 120, render: (_, d) => <Input aria-label="Hàm lượng" value={d.hamLuong} maxLength={50} onChange={(e) => doi(d.khoa, { hamLuong: e.target.value, doTinCay: null, duocSiNhap: true })} /> },
            { title: 'SL kê', width: 110, render: (_, d) => <Input aria-label="Số lượng kê" value={d.soLuong} maxLength={50} onChange={(e) => doi(d.khoa, { soLuong: e.target.value, doTinCay: null, duocSiNhap: true })} /> },
            {
              title: 'Nguồn',
              width: 130,
              render: (_, d) =>
                d.doTinCay !== null ? <Tag color={mauDoTinCay(Number(d.doTinCay))}>AI {Math.round(Number(d.doTinCay) * 100)}%</Tag> : <Tag>Dược sĩ nhập</Tag>,
            },
            {
              title: 'Gợi ý sản phẩm',
              render: (_, d) => (
                <Space size={4} wrap>
                  {d.tenSanPham ? <Tag color="blue">{d.tenSanPham}</Tag> : <Typography.Text type="secondary">Chưa khớp</Typography.Text>}
                  <Button size="small" icon={<SearchOutlined />} aria-label={`Tìm sản phẩm cho ${d.ten || 'dòng này'}`} disabled={!d.ten.trim()} onClick={() => onTim(d.ten.trim())} />
                </Space>
              ),
            },
            { title: '', width: 50, render: (_, d) => <Button type="text" danger aria-label={`Xóa dòng ${d.ten || 'trống'}`} icon={<DeleteOutlined />} onClick={() => capNhat((x) => x.filter((k) => k.khoa !== d.khoa))} /> },
          ]}
        />
        {loi && <Alert type="error" showIcon title={loi} />}
        <YeuCauQuyen ma="rx_request.review" kieu="nut">
          <Space>
            <Button icon={<PlusOutlined />} onClick={() => capNhat((x) => [...x, dongMoi()])}>Thêm thuốc</Button>
            <Button type="primary" loading={dang} disabled={!daSua} onClick={() => void luu()}>Lưu danh sách thuốc</Button>
          </Space>
        </YeuCauQuyen>
      </Space>
    </Card>
  )
}
