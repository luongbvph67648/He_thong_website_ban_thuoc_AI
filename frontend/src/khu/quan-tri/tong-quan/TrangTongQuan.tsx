import { CheckCircleFilled, DownloadOutlined, ReloadOutlined } from '@ant-design/icons'
import { useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Alert, Button, Card, Col, DatePicker, Empty, Progress, Row, Segmented, Space, Table, Tabs, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { api } from '../../../api/client'
import type { components } from '../../../api/schema'
import dayjs from '../../../lib/dayjs'
import { dinhDangNgay, dinhDangTien } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { nhanTrangThai } from '../../../lib/trangThai'
import { usePhien } from '../../../stores/phien'
import { BieuDoCotNgay } from './BieuDoCotNgay'
import { DongDaOn, TheChiSo, TheViec, ThanhChiaPhan } from './KhoiTongQuan'
import { MAU_KY, chia, congTien, dsViec, khoangMau, kyTruoc, mauCuaKhoang, phanTram, soNgay, thamSoKy, thayDoi, type Khoang, type MauKy } from './tongQuan'

type BaoCao = components['schemas']['BaoCaoTongHop']
type TrangThaiDon = components['schemas']['TrangThaiDon']
type LoCanhBao = components['schemas']['LoCanhBao']
type SanPhamThap = components['schemas']['SanPhamThap']

const KHOA = ['quan-tri', 'tong-quan'] as const
/** Đơn đang chạy trên đường đi, theo thứ tự luồng xử lý. */
const LUONG_DON: readonly TrangThaiDon[] = ['cho_xac_nhan', 'da_xac_nhan', 'dang_soan_hang', 'cho_lay_hang', 'dang_giao', 'giao_that_bai']
const LO: Record<string, { nhan: string; mau: string }> = {
  dang_ban: { nhan: 'Đang bán', mau: '#4096ff' },
  can_han: { nhan: 'Cận hạn', mau: '#faad14' },
  khoa: { nhan: 'Khóa', mau: '#8c8c8c' },
  thu_hoi: { nhan: 'Thu hồi', mau: '#9254de' },
  het_han: { nhan: 'Hết hạn', mau: '#ff4d4f' },
}

async function layBaoCao(k: Khoang): Promise<BaoCao> {
  const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/tong-hop', { params: { query: thamSoKy(k) } })
  if (error || !data) throw error ?? new Error('Không tải được báo cáo')
  return data
}

/**
 * AD14: trang đầu tiên Admin thấy. Trên cùng là việc cần xử lý (gấp lên trước, bấm là tới trang xử lý), tiếp theo là
 * chỉ số kinh doanh có so với kỳ liền trước, biểu đồ doanh thu, đơn đang chạy, rồi bán chạy, cảnh báo kho và AI.
 * Mỗi khối chỉ tải khi có quyền tương ứng; backend vẫn kiểm tra lại.
 */
export default function TrangTongQuan() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const quyen = usePhien((s) => s.quyen)
  const goc = useLocation().pathname.replace(/\/+$/, '')
  const [khoang, setKhoang] = useState<Khoang>(() => khoangMau('30_ngay'))
  const [dangXuat, setDangXuat] = useState(false)
  const truoc = kyTruoc(khoang)
  const co = (ma: string) => coQuyen(quyen, ma, 'xem')

  const bc = useQuery({ queryKey: [...KHOA, 'bao-cao', thamSoKy(khoang)], queryFn: () => layBaoCao(khoang), placeholderData: (cu) => cu })
  const bcTruoc = useQuery({ queryKey: [...KHOA, 'bao-cao', thamSoKy(truoc)], queryFn: () => layBaoCao(truoc), placeholderData: (cu) => cu })
  const canhBao = useQuery({
    queryKey: [...KHOA, 'canh-bao-kho'],
    enabled: co('stock.alert.view'),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/canh-bao-kho')
      if (error || !data) throw error ?? new Error('Không tải được cảnh báo kho')
      return data
    },
  })
  const phieu = useQuery({
    queryKey: [...KHOA, 'phieu-cho-duyet'],
    enabled: co('stock_doc.approve'),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/duyet-phieu', { params: { query: { trang_thai_duyet: 'cho_duyet', trang: 1, kich_thuoc: 1 } } })
      if (error || !data) throw error ?? new Error('Không tải được phiếu')
      return data
    },
  })
  const hoan = useQuery({
    queryKey: [...KHOA, 'hoan-tien'],
    enabled: co('refund.confirm'),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/hoan-tien', { params: { query: { trang_thai: 'khoi_tao' } } })
      if (error || !data) throw error ?? new Error('Không tải được hoàn tiền')
      return data
    },
  })
  const thuHoi = useQuery({
    queryKey: [...KHOA, 'thu-hoi'],
    enabled: co('recall.create'),
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/thu-hoi', { params: { query: { trang_thai: 'dang_thu_hoi', trang: 1, kich_thuoc: 50 } } })
      if (error || !data) throw error ?? new Error('Không tải được lệnh thu hồi')
      return data
    },
  })
  const don = useQueries({
    queries: LUONG_DON.map((tt) => ({
      queryKey: [...KHOA, 'don', tt],
      enabled: co('order.view'),
      queryFn: async () => {
        const { data, error } = await api.GET('/api/v1/noi-bo/don-hang', { params: { query: { trang_thai: tt, trang: 1, kich_thuoc: 1 } } })
        if (error || !data) throw error ?? new Error('Không tải được đơn')
        return data.tong
      },
    })),
  })
  const soDon = (tt: TrangThaiDon) => don[LUONG_DON.indexOf(tt)]?.data

  async function xuatExcel() {
    setDangXuat(true)
    try {
      const { data, error } = await api.GET('/api/v1/noi-bo/bao-cao/tong-hop/excel', { params: { query: thamSoKy(khoang) }, parseAs: 'blob' })
      if (error || !data) throw error ?? new Error('Xuất Excel thất bại')
      const url = URL.createObjectURL(data as Blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bao-cao-tong-hop_${thamSoKy(khoang).tu_ngay}_${thamSoKy(khoang).den_ngay}.xlsx`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      void message.error('Không xuất được file Excel')
    } finally {
      setDangXuat(false)
    }
  }

  const d = bc.data
  const t = bcTruoc.isError ? undefined : bcTruoc.data
  const viec = dsViec(
    {
      phieuChoDuyet: phieu.data?.tong,
      hoanTien: hoan.data && { so: hoan.data.length, tongTien: congTien(hoan.data.map((h) => h.so_tien)), thieuTaiKhoan: hoan.data.filter((h) => h.thieu_tai_khoan).length },
      thuHoi: thuHoi.data && { so: thuHoi.data.tong, khachChuaXuLy: thuHoi.data.du_lieu.reduce((s, l) => s + Math.max(0, l.so_khach - l.so_khach_da_xu_ly), 0) },
      loHetHan: canhBao.data?.het_han.tong,
      tonThap: canhBao.data?.ton_thap.tong,
      loCanHan: canhBao.data?.can_han.tong,
      donGiaoThatBai: soDon('giao_that_bai'),
      donChoXacNhan: soDon('cho_xac_nhan'),
      aiGanCo: d?.hieu_qua_ai.so_gan_co,
    },
    dinhDangTien,
  )
  const conViec = viec.filter((v) => v.so > 0)
  const soGap = conViec.filter((v) => v.mucDo === 'gap').length
  const dangTaiViec = [phieu, hoan, thuHoi, canhBao].some((q) => q.isLoading)
  const mau = mauCuaKhoang(khoang)
  const n = soNgay(khoang)
  const giaTriTb = d ? chia(d.doanh_thu, d.so_don_hoan_tat) : null
  const banChayMax = Math.max(1, ...(d?.ban_chay ?? []).map((s) => Number(s.doanh_thu)))
  const ai = d?.hieu_qua_ai
  const tongDanhGia = ai ? ai.danh_gia.khach_huu_ich + ai.danh_gia.khach_khong_huu_ich : 0

  return (
    <Space orientation="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <Typography.Title level={2} style={{ margin: 0 }}>Tổng quan</Typography.Title>
          <Typography.Text type="secondary">
            {dinhDangNgay(khoang[0].format('YYYY-MM-DD'), 'ngay')} – {dinhDangNgay(khoang[1].format('YYYY-MM-DD'), 'ngay')} ({n} ngày), so với {n} ngày liền trước
            {bc.dataUpdatedAt > 0 && ` · Cập nhật lúc ${dayjs(bc.dataUpdatedAt).tz().format('HH:mm')}`}
          </Typography.Text>
        </div>
        <Space wrap>
          <Segmented<MauKy | 'tuy_chon'>
            value={mau ?? 'tuy_chon'}
            onChange={(v) => v !== 'tuy_chon' && setKhoang(khoangMau(v))}
            options={[...MAU_KY, { value: 'tuy_chon', label: 'Tùy chọn', disabled: true }]}
          />
          <DatePicker.RangePicker allowClear={false} value={khoang} format="DD/MM/YYYY" disabledDate={(x) => x.isAfter(dayjs(), 'day')} onChange={(v) => v?.[0] && v[1] && setKhoang([v[0].startOf('day'), v[1].startOf('day')])} />
          <Button icon={<ReloadOutlined />} onClick={() => void qc.invalidateQueries({ queryKey: KHOA })}>Làm mới</Button>
          <Button icon={<DownloadOutlined />} loading={dangXuat} onClick={() => void xuatExcel()}>Xuất Excel</Button>
        </Space>
      </div>

      <Card
        title={<Space>Cần xử lý{conViec.length > 0 && <Tag color={soGap ? 'red' : 'gold'}>{conViec.length}</Tag>}</Space>}
        loading={dangTaiViec && viec.length === 0}
      >
        {conViec.length === 0 ? (
          <Space orientation="vertical" style={{ width: '100%' }}>
            <Alert type="success" showIcon icon={<CheckCircleFilled />} title="Không có việc nào đang chờ bạn" />
            <DongDaOn ds={viec} />
          </Space>
        ) : (
          <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
            {soGap > 0 && <Alert type="error" showIcon title={`Có ${soGap} nhóm việc cần bạn xử lý ngay`} />}
            <Row gutter={[12, 12]}>
              {conViec.map((v) => (
                <Col key={v.khoa} xs={24} md={12} xl={8} xxl={6}>
                  <TheViec viec={v} goc={goc} />
                </Col>
              ))}
            </Row>
            <DongDaOn ds={viec.filter((v) => v.so === 0)} />
          </Space>
        )}
      </Card>

      {bc.isError && <Alert type="error" showIcon title="Không tải được báo cáo (kỳ tối đa 366 ngày)" />}
      <Row gutter={[12, 12]}>
        <Col xs={24} md={12} xl={6}>
          <TheChiSo nhan="Doanh thu thuần" dangTai={bc.isLoading} giaTri={dinhDangTien(d?.doanh_thu_thuan)} ty={d ? thayDoi(d.doanh_thu_thuan, t?.doanh_thu_thuan) : null} phu={d && `Doanh thu ${dinhDangTien(d.doanh_thu)} · hoàn ${dinhDangTien(d.hoan_tien)}`} />
        </Col>
        <Col xs={24} md={12} xl={6}>
          <TheChiSo nhan="Lợi nhuận gộp" dangTai={bc.isLoading} giaTri={dinhDangTien(d?.loi_nhuan_gop)} ty={d ? thayDoi(d.loi_nhuan_gop, t?.loi_nhuan_gop) : null} phu={d && `Biên lợi nhuận ${phanTram(chia(d.loi_nhuan_gop, d.doanh_thu_thuan))}`} />
        </Col>
        <Col xs={24} md={12} xl={6}>
          <TheChiSo nhan="Đơn hoàn tất" dangTai={bc.isLoading} giaTri={d?.so_don_hoan_tat ?? '—'} ty={d ? thayDoi(d.so_don_hoan_tat, t?.so_don_hoan_tat) : null} phu={giaTriTb !== null ? `Trung bình ${dinhDangTien(Math.round(giaTriTb))}/đơn` : undefined} />
        </Col>
        <Col xs={24} md={12} xl={6}>
          <TheChiSo nhan="Tiền hoàn cho khách" nguoc dangTai={bc.isLoading} giaTri={dinhDangTien(d?.hoan_tien)} ty={d ? thayDoi(d.hoan_tien, t?.hoan_tien) : null} phu={d && `${phanTram(chia(d.hoan_tien, d.doanh_thu))} doanh thu`} />
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={16}>
          <Card size="small" title="Doanh thu theo ngày" extra={d && <Typography.Text type="secondary">{d.doanh_thu_theo_ngay.reduce((s, x) => s + x.so_don, 0)} đơn hoàn tất</Typography.Text>} style={{ height: '100%' }}>
            {d && d.doanh_thu_theo_ngay.some((x) => Number(x.doanh_thu) > 0) ? <BieuDoCotNgay diem={d.doanh_thu_theo_ngay} /> : <Empty description={bc.isLoading ? 'Đang tải' : 'Chưa có đơn hoàn tất trong kỳ'} />}
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card size="small" title="Đơn đang xử lý" extra={co('order.view') && <Link to={`${goc}/xem/don-hang`}>Tất cả đơn</Link>} style={{ height: '100%' }}>
            {co('order.view') ? (
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                {LUONG_DON.map((tt) => {
                  const nhan = nhanTrangThai('don_hang', tt)
                  const so = soDon(tt)
                  const canChu = tt === 'giao_that_bai' && (so ?? 0) > 0
                  return (
                    <Link key={tt} to={`${goc}/xem/don-hang?trang_thai=${tt}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 4px', borderBottom: '1px solid #f0f0f0', color: 'inherit' }}>
                      <span><Tag color={nhan.mau}>{nhan.nhan}</Tag></span>
                      <Typography.Text strong style={{ color: canChu ? '#cf1322' : undefined }}>{so ?? '…'}</Typography.Text>
                    </Link>
                  )
                })}
              </div>
            ) : (
              <Typography.Text type="secondary">Bạn chưa có quyền xem đơn hàng</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12}>
          <Card size="small" title="Sản phẩm bán chạy" style={{ height: '100%' }}>
            {d && d.ban_chay.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {d.ban_chay.slice(0, 5).map((s, i) => (
                  <div key={s.san_pham_id}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                      <Typography.Text ellipsis style={{ maxWidth: '65%' }}>{i + 1}. {s.ten} <Typography.Text type="secondary">({s.sku})</Typography.Text></Typography.Text>
                      <Typography.Text strong>{dinhDangTien(s.doanh_thu)}</Typography.Text>
                    </div>
                    <Progress percent={(Number(s.doanh_thu) / banChayMax) * 100} showInfo={false} size="small" status="normal" />
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>{s.so_luong_co_so.toLocaleString('vi-VN')} đơn vị cơ sở</Typography.Text>
                  </div>
                ))}
              </div>
            ) : (
              <Empty description="Chưa có đơn hoàn tất trong kỳ" />
            )}
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card size="small" title="Cảnh báo kho" style={{ height: '100%' }}>
            <Tabs
              size="small"
              items={[
                {
                  key: 'can-han',
                  label: `Cận hạn (${d?.so_lo_can_han ?? 0})`,
                  children: (
                    <Table size="small" pagination={false} rowKey="lo_id" dataSource={(d?.lo_can_han ?? []).slice(0, 6)} locale={{ emptyText: 'Không có lô cận hạn' }}
                      columns={[
                        { title: 'Sản phẩm', render: (_, r) => r.ten_san_pham, ellipsis: true },
                        { title: 'Lô', dataIndex: 'so_lo' },
                        { title: 'Còn', dataIndex: 'con_ngay', align: 'right', render: (v: number) => <Tag color={v <= 30 ? 'red' : 'orange'}>{v} ngày</Tag> },
                        { title: 'Giá trị', dataIndex: 'gia_tri', align: 'right', render: (v: string) => dinhDangTien(v) },
                      ]} />
                  ),
                },
                ...(canhBao.data
                  ? [
                      {
                        key: 'het-han',
                        label: `Hết hạn (${canhBao.data.het_han.tong})`,
                        children: (
                          <Table<LoCanhBao> size="small" pagination={false} rowKey="lo_id" dataSource={canhBao.data.het_han.du_lieu.slice(0, 6)} locale={{ emptyText: 'Không có lô hết hạn' }}
                            columns={[
                              { title: 'Sản phẩm', dataIndex: 'ten_san_pham', ellipsis: true },
                              { title: 'Lô', dataIndex: 'so_lo' },
                              { title: 'Hạn', dataIndex: 'han_su_dung', render: (v: string) => dinhDangNgay(v, 'ngay') },
                              { title: 'Tồn', dataIndex: 'so_luong_ton', align: 'right' },
                            ]} />
                        ),
                      },
                      {
                        key: 'ton-thap',
                        label: `Dưới tồn tối thiểu (${canhBao.data.ton_thap.tong})`,
                        children: (
                          <Table<SanPhamThap> size="small" pagination={false} rowKey="san_pham_id" dataSource={canhBao.data.ton_thap.du_lieu.slice(0, 6)} locale={{ emptyText: 'Không có sản phẩm dưới mức tối thiểu' }}
                            columns={[
                              { title: 'Sản phẩm', render: (_, r) => `${r.ten} (${r.sku})`, ellipsis: true },
                              { title: 'Khả dụng', dataIndex: 'ton_kha_dung', align: 'right', render: (v: number) => <Typography.Text type={v === 0 ? 'danger' : undefined}>{v}</Typography.Text> },
                              { title: 'Tối thiểu', dataIndex: 'ton_toi_thieu', align: 'right' },
                            ]} />
                        ),
                      },
                    ]
                  : []),
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[12, 12]}>
        <Col xs={24} xl={12}>
          <Card size="small" title="Tồn kho" extra={d && <Typography.Text strong>{dinhDangTien(d.gia_tri_ton_kho)}</Typography.Text>} style={{ height: '100%' }}>
            {d ? (
              <ThanhChiaPhan phan={d.ton_kho_theo_trang_thai.map((x) => ({ khoa: x.trang_thai, nhan: LO[x.trang_thai]?.nhan ?? x.trang_thai, mau: LO[x.trang_thai]?.mau ?? '#bfbfbf', giaTri: Number(x.gia_tri), chu: `${x.so_luong.toLocaleString('vi-VN')} · ${dinhDangTien(x.gia_tri)}` }))} />
            ) : (
              <Empty description={bc.isLoading ? 'Đang tải' : 'Không có dữ liệu'} />
            )}
            <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8, fontSize: 12 }}>Giá trị tồn kho tính theo giá nhập, không gồm lô hết hạn.</Typography.Text>
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card size="small" title="Hiệu quả trợ lý AI" extra={co('ai.monitor') && <Link to={`${goc}/giam-sat-ai`}>Giám sát AI</Link>} style={{ height: '100%' }}>
            {ai ? (
              <Row gutter={[12, 12]}>
                <Col span={12}><Typography.Text type="secondary">Hội thoại</Typography.Text><div style={{ fontSize: 20, fontWeight: 600 }}>{ai.tong_hoi_thoai}</div></Col>
                <Col span={12}><Typography.Text type="secondary">Chi phí</Typography.Text><div style={{ fontSize: 20, fontWeight: 600 }}>{Number(ai.tong_chi_phi_usd).toFixed(2)} USD</div></Col>
                <Col span={12}>
                  <Typography.Text type="secondary">Chuyển sang dược sĩ</Typography.Text>
                  <Progress percent={Number(ai.ty_le_chuyen_duoc_si ?? 0) * 100} format={() => phanTram(ai.ty_le_chuyen_duoc_si === null ? null : Number(ai.ty_le_chuyen_duoc_si))} size="small" />
                </Col>
                <Col span={12}>
                  <Typography.Text type="secondary">Khách thấy hữu ích</Typography.Text>
                  <Progress percent={tongDanhGia ? (ai.danh_gia.khach_huu_ich / tongDanhGia) * 100 : 0} format={() => (tongDanhGia ? phanTram(ai.danh_gia.khach_huu_ich / tongDanhGia) : '—')} size="small" strokeColor="#52c41a" />
                </Col>
                <Col span={24}>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    {ai.so_gan_co} câu trả lời bị gắn cờ · dược sĩ chấm đúng {ai.danh_gia.duoc_si_dung}, sai {ai.danh_gia.duoc_si_sai}
                  </Typography.Text>
                </Col>
              </Row>
            ) : (
              <Empty description={bc.isLoading ? 'Đang tải' : 'Không có dữ liệu'} />
            )}
          </Card>
        </Col>
      </Row>
    </Space>
  )
}
