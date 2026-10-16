import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Input, Modal, Result, Select, Space, Spin, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { nhanTrangThai } from '../../../lib/trangThai'
import { usePhien } from '../../../stores/phien'
import { type DaQuet, type DongSoan, SU_KIEN_GIA, dongXong, quetMa, tatCaXong, xacNhanTay } from './soanHang'

const CSS_IN = '@media print { body * { visibility: hidden } .phieu-in, .phieu-in * { visibility: visible } .phieu-in { position: absolute; left: 0; top: 0; width: 100% } }'

/** KHO03, KHO04: phiếu soạn hàng. Quét mã vạch xác nhận từng dòng, đổi lô (có lý do), bắt đầu soạn, đóng gói, in phiếu. */
export default function TrangPhieuSoan() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const { id = '' } = useParams()
  const idSo = Number(id)
  const quyen = usePhien((s) => s.quyen)
  const [daQuet, setDaQuet] = useState<DaQuet>({})
  const [ma, setMa] = useState('')
  const [doi, setDoi] = useState<{ dong: DongSoan; pbId: number } | null>(null)
  const [loMoi, setLoMoi] = useState<number | undefined>()
  const [lyDo, setLyDo] = useState('')
  const [dangGui, setDangGui] = useState(false)
  const q = useQuery({
    queryKey: ['nhan-vien', 'soan-hang', 'ct', idSo],
    enabled: Number.isInteger(idSo) && idSo > 0,
    retry: false,
    queryFn: async () => (await api.GET('/api/v1/noi-bo/soan-hang/{don_id}', { params: { path: { don_id: idSo } } })).data ?? null,
  })
  if (q.isLoading) return <Spin />
  const don = q.data
  if (!don) return <Result status="404" title="Không tìm thấy đơn hàng" extra={<Link to=".." relative="path"><Button type="primary">Về hàng đợi</Button></Link>} />
  const tt = nhanTrangThai('don_hang', don.trang_thai)
  const coSoan = coQuyen(quyen, 'order.pick')
  const coDongGoi = coQuyen(quyen, 'shipment.create')

  async function chay<T>(thaoTac: () => Promise<{ ok: true; data: T } | { ok: false; loi: Parameters<typeof thongDiepChung>[0] }>, thanhCong: string) {
    setDangGui(true)
    const r = await thaoTac()
    setDangGui(false)
    if (!r.ok) return void message.error(thongDiepChung(r.loi))
    void message.success(thanhCong)
    setDoi(null)
    setLyDo('')
    setLoMoi(undefined)
    void queryClient.invalidateQueries({ queryKey: ['nhan-vien', 'soan-hang'] })
    void queryClient.invalidateQueries({ queryKey: ['nhan-vien', 'don-hang'] })
  }
  const path = { params: { path: { don_id: idSo } } }

  function quet() {
    const moi = quetMa(don!.dong, daQuet, ma)
    if (!moi) void message.error('Mã vạch không thuộc đơn này hoặc dòng đó đã đủ số lượng')
    else setDaQuet(moi)
    setMa('')
  }

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <style>{CSS_IN}</style>
      <Link to=".." relative="path">← Hàng đợi soạn hàng</Link>
      <Space wrap>
        <Typography.Title level={3} style={{ margin: 0 }}>Phiếu soạn hàng {don.ma_don}</Typography.Title>
        <Tag color={tt.mau}>{tt.nhan}</Tag>
        {coSoan && don.trang_thai === 'da_xac_nhan' && (
          <Button type="primary" loading={dangGui} onClick={() => void chay(() => goi(() => api.POST('/api/v1/noi-bo/soan-hang/{don_id}/bat-dau', path)), 'Đã chốt lô và trừ tồn, bắt đầu soạn hàng')}>Bắt đầu soạn hàng</Button>
        )}
        {coDongGoi && don.trang_thai === 'dang_soan_hang' && (
          <Button
            type="primary"
            loading={dangGui}
            disabled={!tatCaXong(don.dong, daQuet)}
            onClick={() => void chay(() => goi(() => api.POST('/api/v1/noi-bo/soan-hang/{don_id}/dong-goi', path)), don.hinh_thuc_nhan === 'giao_tan_noi' ? 'Đã tạo vận đơn, chờ đơn vị vận chuyển lấy hàng' : 'Đã đóng gói, chờ khách đến nhận')}
          >
            {don.hinh_thuc_nhan === 'giao_tan_noi' ? 'Đóng gói & tạo vận đơn' : 'Đóng gói để khách nhận'}
          </Button>
        )}
        <Button onClick={() => window.print()}>In phiếu</Button>
      </Space>
      {don.trang_thai === 'dang_soan_hang' && (
        <Input
          autoFocus
          allowClear
          value={ma}
          onChange={(e) => setMa(e.target.value)}
          onPressEnter={quet}
          placeholder="Quét mã vạch sản phẩm rồi nhấn Enter để xác nhận từng đơn vị"
        />
      )}
      <div className="phieu-in">
        <Descriptions bordered size="small" column={2} style={{ marginBottom: 12 }}>
          <Descriptions.Item label="Mã đơn">{don.ma_don}</Descriptions.Item>
          <Descriptions.Item label="Ngày đặt">{dinhDangNgay(don.created_at, 'ngayGio')}</Descriptions.Item>
          <Descriptions.Item label="Người nhận">{[don.ten_nguoi_nhan, don.sdt_nguoi_nhan].filter(Boolean).join(' · ') || '—'}</Descriptions.Item>
          <Descriptions.Item label="Nhận hàng">{don.hinh_thuc_nhan === 'giao_tan_noi' ? (don.dia_chi_giao ?? '—') : 'Tại nhà thuốc'}</Descriptions.Item>
          {don.ghi_chu && <Descriptions.Item label="Ghi chú" span={2}>{don.ghi_chu}</Descriptions.Item>}
          {don.van_don.length > 0 && <Descriptions.Item label="Mã vận đơn" span={2}>{don.van_don.map((v) => `${v.don_vi_van_chuyen} ${v.ma_van_don}`).join(', ')}</Descriptions.Item>}
        </Descriptions>
        <Table<DongSoan>
          size="small"
          rowKey="ct_don_hang_id"
          pagination={false}
          dataSource={don.dong}
          columns={[
            { title: 'Sản phẩm', key: 'ten', render: (_, d) => `${d.ten_san_pham} (${d.ten_don_vi})` },
            { title: 'Mã vạch', key: 'mv', render: (_, d) => d.ma_vach ?? '—' },
            { title: 'SL', dataIndex: 'so_luong', key: 'sl', align: 'right' },
            {
              title: 'Lô (FEFO)',
              key: 'lo',
              render: (_, d) => (
                <Space orientation="vertical" size={2}>
                  {d.phan_bo.map((p) => (
                    <span key={p.id}>
                      {p.so_lo} · HSD {dinhDangNgay(p.han_su_dung)} · {p.so_luong_co_so}
                      {p.ly_do_doi_lo && <Typography.Text type="secondary"> (đã đổi lô: {p.ly_do_doi_lo})</Typography.Text>}
                      {coSoan && don.trang_thai === 'da_xac_nhan' && <Button type="link" size="small" onClick={() => setDoi({ dong: d, pbId: p.id })}>Đổi lô</Button>}
                    </span>
                  ))}
                </Space>
              ),
            },
            {
              title: 'Đã quét',
              key: 'quet',
              className: 'khong-in',
              render: (_, d) =>
                don.trang_thai !== 'dang_soan_hang' ? '—' : (
                  <Space>
                    <Tag color={dongXong(d, daQuet) ? 'success' : 'default'}>{daQuet[d.ct_don_hang_id] ?? 0}/{d.so_luong}</Tag>
                    {!d.ma_vach && !dongXong(d, daQuet) && <Button size="small" onClick={() => setDaQuet(xacNhanTay(d, daQuet))}>Xác nhận tay</Button>}
                  </Space>
                ),
            },
          ]}
        />
      </div>
      {don.che_do_van_chuyen_gia && don.van_don.length > 0 && (
        <Alert
          type="info"
          showIcon
          message="Giả lập vận chuyển (chỉ khi chạy chế độ giả)"
          description={
            <Space wrap>
              {SU_KIEN_GIA.map((s) => (
                <Button
                  key={s.trangThai}
                  size="small"
                  onClick={() => void chay(() => goi(() => api.POST('/api/v1/webhook/gia-van-chuyen', { body: { ma_van_don: don.van_don[0].ma_van_don ?? '', trang_thai_doi_tac: s.trangThai } })), `Đã gửi sự kiện: ${s.nhan}`)}
                >
                  {s.nhan}
                </Button>
              ))}
            </Space>
          }
        />
      )}
      <Modal
        title={doi ? `Đổi lô: ${doi.dong.ten_san_pham}` : ''}
        open={doi !== null}
        okText="Đổi lô"
        cancelText="Đóng"
        okButtonProps={{ loading: dangGui, disabled: loMoi === undefined || !lyDo.trim() }}
        onCancel={() => setDoi(null)}
        onOk={() => doi && loMoi !== undefined && void chay(() => goi(() => api.POST('/api/v1/noi-bo/soan-hang/{don_id}/doi-lo', { ...path, body: { phan_bo_lo_id: doi.pbId, lo_id: loMoi, ly_do: lyDo.trim() } })), 'Đã đổi lô')}
        destroyOnHidden
      >
        <Space orientation="vertical" style={{ width: '100%' }}>
          <Select<number>
            style={{ width: '100%' }}
            placeholder="Chọn lô thay thế"
            value={loMoi}
            onChange={setLoMoi}
            options={(doi?.dong.goi_y ?? []).filter((l) => !doi?.dong.phan_bo.some((p) => p.lo_id === l.lo_id)).map((l) => ({ value: l.lo_id, label: `${l.so_lo} · HSD ${dinhDangNgay(l.han_su_dung)} · khả dụng ${l.kha_dung}` }))}
          />
          <Input.TextArea rows={2} maxLength={500} placeholder="Lý do đổi lô (bắt buộc)" value={lyDo} onChange={(e) => setLyDo(e.target.value)} />
        </Space>
      </Modal>
    </Space>
  )
}
