import { useQuery } from '@tanstack/react-query'
import { Alert, App, Button, Input, InputNumber, Select, Space, Table, Typography } from 'antd'
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { loiTheoTruong } from '../../../api/loi'
import type { components } from '../../../api/schema'
import { dinhDangTien } from '../../../lib/dinhDang'
import { chonDonVi, type DongForm, type SanPham, tongTienPhieu } from './phieuNhap'

type CanhBao = components['schemas']['CanhBao']

/** KHO02: lập phiếu nhập nhiều dòng; máy quét mã vạch gõ mã rồi Enter vào ô tìm. */
export default function TrangTaoPhieuNhap() {
  const { message, modal } = App.useApp()
  const dieuHuong = useNavigate()
  const [nccId, setNccId] = useState<number | undefined>()
  const [hoaDon, setHoaDon] = useState('')
  const [ghiChu, setGhiChu] = useState('')
  const [dong, setDong] = useState<DongForm[]>([])
  const [tim, setTim] = useState('')
  const [ketQua, setKetQua] = useState<SanPham[]>([])
  const [loi, setLoi] = useState<string | null>(null)
  const [loiDong, setLoiDong] = useState<Record<string, string>>({})
  const [dangGui, setDangGui] = useState(false)
  const dem = useRef(1)

  const ncc = useQuery({
    queryKey: ['nhan-vien', 'nha-cung-cap', 'dang-hop-tac'],
    queryFn: async () => (await api.GET('/api/v1/noi-bo/nha-cung-cap', { params: { query: { kich_thuoc: 100 } } })).data?.du_lieu ?? [],
  })

  const them = (sp: SanPham, maVach = '') => {
    setDong((d) => [...d, { khoa: dem.current++, sp, donViId: chonDonVi(sp, maVach), soLo: '', nsx: '', hsd: '', soLuong: 1, giaNhap: null }])
    setKetQua([])
    setTim('')
  }
  const timSanPham = async () => {
    const ma = tim.trim()
    if (!ma) return
    const kq = await goi(() => api.GET('/api/v1/noi-bo/phieu-nhap/tra-cuu-san-pham', { params: { query: { q: ma } } }))
    if (!kq.ok) return void message.error(thongDiepChung(kq.loi))
    if (kq.data.length === 1) return them(kq.data[0], ma)
    setKetQua(kq.data)
    if (kq.data.length === 0) void message.warning('Không tìm thấy sản phẩm')
  }
  const sua = (khoa: number, thayDoi: Partial<DongForm>) => setDong((d) => d.map((x) => (x.khoa === khoa ? { ...x, ...thayDoi } : x)))

  const gui = async (xacNhan: boolean) => {
    setLoi(null)
    setLoiDong({})
    setDangGui(true)
    const kq = await goi(() =>
      api.POST('/api/v1/noi-bo/phieu-nhap', {
        body: {
          nha_cung_cap_id: nccId as number,
          so_hoa_don_ncc: hoaDon.trim() || null,
          ghi_chu: ghiChu.trim() || null,
          xac_nhan_canh_bao: xacNhan,
          dong: dong.map((d) => ({
            san_pham_id: d.sp.id,
            don_vi_id: d.donViId,
            so_lo: d.soLo,
            ngay_san_xuat: d.nsx || null,
            han_su_dung: d.hsd,
            so_luong: d.soLuong as number,
            gia_nhap: String(d.giaNhap ?? 0),
          })),
        },
      }),
    )
    setDangGui(false)
    if (kq.ok) {
      void message.success(`Đã lập phiếu ${kq.data.ma_phieu}`)
      dieuHuong('/nhan-vien/phieu-nhap')
      return
    }
    if (kq.loi?.ma_loi === 'CAN_XAC_NHAN_CANH_BAO') {
      const canhBao = ((kq.loi.chi_tiet as { canh_bao?: CanhBao[] } | null)?.canh_bao ?? []) as CanhBao[]
      modal.confirm({
        title: 'Có dòng hạn sử dụng ngắn',
        content: (
          <ul>
            {canhBao.map((c) => (
              <li key={c.dong}>
                Dòng {c.dong + 1}: còn {c.so_ngay_con_lai} ngày (tối thiểu nên là {c.toi_thieu} ngày)
              </li>
            ))}
          </ul>
        ),
        okText: 'Vẫn nhập',
        cancelText: 'Xem lại',
        onOk: () => gui(true),
      })
      return
    }
    setLoi(thongDiepChung(kq.loi))
    setLoiDong(kq.loi ? loiTheoTruong(kq.loi) : {})
  }

  const hopLe = nccId !== undefined && dong.length > 0 && dong.every((d) => d.soLo.trim() && d.hsd && d.soLuong && d.soLuong >= 1 && d.giaNhap !== null)
  const loiO = (i: number, truong: string) => loiDong[`dong.${i}.${truong}`]

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={4}>Lập phiếu nhập kho</Typography.Title>
      <Space wrap>
        <Select showSearch optionFilterProp="label" placeholder="Nhà cung cấp" style={{ width: 280 }} value={nccId} onChange={setNccId} options={(ncc.data ?? []).map((n) => ({ value: n.id, label: n.ten }))} />
        <Input placeholder="Số hóa đơn NCC" style={{ width: 200 }} value={hoaDon} onChange={(e) => setHoaDon(e.target.value)} maxLength={50} />
        <Input placeholder="Ghi chú" style={{ width: 280 }} value={ghiChu} onChange={(e) => setGhiChu(e.target.value)} maxLength={2000} />
      </Space>
      <Input autoFocus placeholder="Quét mã vạch hoặc gõ tên/SKU rồi Enter" value={tim} onChange={(e) => setTim(e.target.value)} onPressEnter={() => void timSanPham()} allowClear />
      {ketQua.length > 1 && (
        <Space wrap>
          {ketQua.map((s) => (
            <Button key={s.id} onClick={() => them(s)}>
              {s.ten} ({s.sku})
            </Button>
          ))}
        </Space>
      )}
      {loi && <Alert type="error" showIcon message={loi} />}
      <Table<DongForm>
        rowKey="khoa"
        pagination={false}
        dataSource={dong}
        scroll={{ x: 1100 }}
        columns={[
          { title: 'Sản phẩm', key: 'sp', width: 220, render: (_, d, i) => <span>{d.sp.ten}<br /><Typography.Text type="secondary">{d.sp.sku}</Typography.Text>{loiO(i, 'san_pham_id') && <Typography.Text type="danger"> {loiO(i, 'san_pham_id')}</Typography.Text>}</span> },
          { title: 'Đơn vị', key: 'dv', width: 110, render: (_, d, i) => <Select value={d.donViId} style={{ width: 100 }} status={loiO(i, 'don_vi_id') ? 'error' : undefined} onChange={(v) => sua(d.khoa, { donViId: v })} options={d.sp.don_vi.map((u) => ({ value: u.id, label: u.ten_don_vi }))} /> },
          { title: 'Số lô', key: 'lo', width: 130, render: (_, d, i) => <Input aria-label="Số lô" value={d.soLo} status={loiO(i, 'so_lo') ? 'error' : undefined} onChange={(e) => sua(d.khoa, { soLo: e.target.value })} maxLength={50} /> },
          { title: 'NSX', key: 'nsx', width: 150, render: (_, d) => <Input aria-label="Ngày sản xuất" type="date" value={d.nsx} onChange={(e) => sua(d.khoa, { nsx: e.target.value })} /> },
          { title: 'HSD', key: 'hsd', width: 150, render: (_, d, i) => <Input aria-label="Hạn sử dụng" type="date" value={d.hsd} status={loiO(i, 'han_su_dung') ? 'error' : undefined} onChange={(e) => sua(d.khoa, { hsd: e.target.value })} /> },
          { title: 'Số lượng', key: 'sl', width: 110, render: (_, d) => <InputNumber aria-label="Số lượng" value={d.soLuong} precision={0} onChange={(v) => sua(d.khoa, { soLuong: v })} /> },
          { title: 'Giá nhập', key: 'gia', width: 140, render: (_, d) => <InputNumber aria-label="Giá nhập" value={d.giaNhap} precision={0} style={{ width: 130 }} onChange={(v) => sua(d.khoa, { giaNhap: v })} /> },
          { title: 'Thành tiền', key: 'tt', width: 120, align: 'right', render: (_, d) => dinhDangTien((d.soLuong ?? 0) * (d.giaNhap ?? 0)) },
          { title: '', key: 'xoa', width: 70, render: (_, d) => <Button size="small" onClick={() => setDong((x) => x.filter((y) => y.khoa !== d.khoa))}>Bỏ</Button> },
        ]}
      />
      {Object.entries(loiDong).filter(([k]) => k.startsWith('dong.')).map(([k, v]) => <Alert key={k} type="error" showIcon message={`Dòng ${Number(k.split('.')[1]) + 1}: ${v}`} />)}
      <Space>
        <Typography.Text strong>Tổng tiền: {dinhDangTien(tongTienPhieu(dong))}</Typography.Text>
        <Button type="primary" disabled={!hopLe} loading={dangGui} onClick={() => void gui(false)}>
          Lưu phiếu nhập
        </Button>
        <Button onClick={() => dieuHuong('/nhan-vien/phieu-nhap')}>Hủy</Button>
      </Space>
    </Space>
  )
}
