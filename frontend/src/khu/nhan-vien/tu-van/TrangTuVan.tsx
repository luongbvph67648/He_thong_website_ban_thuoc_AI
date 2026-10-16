import { SendOutlined } from '@ant-design/icons'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Descriptions, Empty, Input, Space, Table, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { usePhongChat, type TinTrucTiep } from '../../../lib/phongChat'
import { usePhien } from '../../../stores/phien'

type Hang = components['schemas']['ChatTomTat']
type ChiTiet = components['schemas']['ChatChiTiet']

const NHAN_VAI_TRO: Record<TinTrucTiep['vaiTro'], string> = { khach: 'Khách', ai: 'Trợ lý AI', duoc_si: 'Dược sĩ', he_thong: 'Hệ thống' }

function KhungChat({ ct, onDong }: { ct: ChiTiet; onDong: () => void }) {
  const token = usePhien((s) => s.accessToken)
  const [nhap, setNhap] = useState('')
  const dangXuLy = ct.trang_thai === 'duoc_si_dang_xu_ly' && ct.duoc_si_cua_toi
  const phong = usePhongChat({ maPhien: dangXuLy ? ct.ma_phien : null, vaiTro: 'duoc_si', token })
  const daCo = new Set(ct.tin_nhan.map((t) => `s${t.id}`))
  const tatCa: TinTrucTiep[] = [
    ...ct.tin_nhan.map((t) => ({ khoa: `s${t.id}`, vaiTro: t.vai_tro, noiDung: t.noi_dung })),
    ...phong.tin.filter((t) => !daCo.has(t.khoa)),
  ]
  function gui() {
    if (phong.gui(nhap)) setNhap('')
  }
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Descriptions size="small" column={2} bordered>
        <Descriptions.Item label="Khách">{ct.ten_khach ?? 'Khách vãng lai'}</Descriptions.Item>
        <Descriptions.Item label="Bắt đầu">{dinhDangNgay(ct.created_at, 'ngayGio')}</Descriptions.Item>
        {ct.so_dien_thoai_goi_lai && <Descriptions.Item label="Gọi lại số">{ct.so_dien_thoai_goi_lai}</Descriptions.Item>}
        {ct.tom_tat && <Descriptions.Item label="Tóm tắt AI" span={2}>{ct.tom_tat}</Descriptions.Item>}
        {ct.ho_so_suc_khoe && (
          <Descriptions.Item label="Hồ sơ sức khỏe (đã được khách đồng ý)" span={2}>
            Năm sinh: {ct.ho_so_suc_khoe.nam_sinh ?? 'không rõ'}
            {ct.ho_so_suc_khoe.dang_mang_thai ? ' · Đang mang thai' : ''}
            {ct.ho_so_suc_khoe.dang_cho_con_bu ? ' · Đang cho con bú' : ''}
            {ct.ho_so_suc_khoe.di_ung.length > 0 ? ` · Dị ứng: ${ct.ho_so_suc_khoe.di_ung.join(', ')}` : ''}
          </Descriptions.Item>
        )}
      </Descriptions>
      {ct.bi_gan_co && <Alert type="warning" showIcon title="Cuộc trò chuyện có dấu hiệu nguy hiểm, ưu tiên khuyên khách đi cấp cứu hoặc đến cơ sở y tế." />}
      <div role="log" aria-label="Nội dung trò chuyện" style={{ maxHeight: 360, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 6, padding: 8 }}>
        {tatCa.map((t) => (
          <div key={t.khoa} style={{ marginBottom: 6, textAlign: t.vaiTro === 'duoc_si' ? 'right' : 'left' }}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>{NHAN_VAI_TRO[t.vaiTro]}</Typography.Text>
            <div style={{ whiteSpace: 'pre-wrap' }}>{t.noiDung}</div>
          </div>
        ))}
        {phong.doiPhuongDangGo && <Typography.Text type="secondary">Khách đang nhập…</Typography.Text>}
      </div>
      {phong.trangThai === 'mat_ket_noi' && dangXuLy && <Alert type="error" showIcon title="Mất kết nối, tải lại trang để nối lại." />}
      {dangXuLy && (
        <YeuCauQuyen ma="chat.handle" kieu="nut">
          <Space.Compact style={{ width: '100%' }}>
            <Input aria-label="Tin nhắn cho khách" value={nhap} maxLength={1000} onChange={(e) => { setNhap(e.target.value); phong.baoDangGo() }} onPressEnter={gui} disabled={phong.trangThai !== 'da_noi'} />
            <Button type="primary" icon={<SendOutlined />} aria-label="Gửi" onClick={gui} disabled={phong.trangThai !== 'da_noi' || !nhap.trim()} />
          </Space.Compact>
        </YeuCauQuyen>
      )}
      {(dangXuLy || ct.trang_thai === 'cho_goi_lai') && (
        <YeuCauQuyen ma="chat.handle" kieu="nut">
          <Button danger onClick={onDong}>{ct.trang_thai === 'cho_goi_lai' ? 'Đã gọi lại, đóng phiên' : 'Kết thúc tư vấn'}</Button>
        </YeuCauQuyen>
      )}
    </Space>
  )
}

/** DS06: hàng chờ tư vấn trực tiếp và cửa sổ chat của dược sĩ (WebSocket, AI04 tóm tắt sẵn). */
export default function TrangTuVan() {
  const { message } = App.useApp()
  const qc = useQueryClient()
  const [chon, setChon] = useState<number | null>(null)
  const ds = useQuery({
    queryKey: ['noi-bo', 'tu-van'],
    refetchInterval: 15_000,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/tu-van')
      if (error || !data) throw error ?? new Error('Không tải được hàng chờ')
      return data
    },
  })
  const ct = useQuery({
    queryKey: ['noi-bo', 'tu-van', chon],
    enabled: chon !== null,
    staleTime: Infinity,
    gcTime: 0,
    refetchOnWindowFocus: false,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/tu-van/{hoi_thoai_id}', { params: { path: { hoi_thoai_id: chon! } } })
      if (error || !data) throw error ?? new Error('Không tải được phiên')
      return data
    },
  })
  const hanhDong = useMutation({
    mutationFn: async ({ id, viec }: { id: number; viec: 'nhan' | 'dong' }) => {
      const r = await goi(() =>
        viec === 'nhan'
          ? api.POST('/api/v1/noi-bo/tu-van/{hoi_thoai_id}/nhan', { params: { path: { hoi_thoai_id: id } } })
          : api.POST('/api/v1/noi-bo/tu-van/{hoi_thoai_id}/dong', { params: { path: { hoi_thoai_id: id } } }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return { id, viec, ct: r.data as ChiTiet }
    },
    onSuccess: ({ id, viec, ct: moi }) => {
      qc.setQueryData(['noi-bo', 'tu-van', id], moi)
      if (viec === 'dong') setChon(null)
      void qc.invalidateQueries({ queryKey: ['noi-bo', 'tu-van'], exact: true })
    },
    onError: (e: Error) => {
      void message.error(e.message)
      void ds.refetch()
    },
  })
  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Tư vấn khách</Typography.Title>
      {ds.isError && <Alert type="error" showIcon title="Không tải được hàng chờ" />}
      <Table<Hang>
        rowKey="id"
        size="small"
        loading={ds.isLoading}
        dataSource={ds.data ?? []}
        pagination={false}
        locale={{ emptyText: 'Không có khách nào đang chờ' }}
        columns={[
          { title: 'Khách', dataIndex: 'ten_khach', render: (v: string | null) => v ?? 'Khách vãng lai' },
          { title: 'Tóm tắt', dataIndex: 'tom_tat', ellipsis: true },
          { title: 'Gửi lúc', dataIndex: 'created_at', render: (v: string) => dinhDangNgay(v, 'ngayGio') },
          {
            title: 'Trạng thái',
            dataIndex: 'trang_thai',
            render: (t: string, r) => (
              <>
                {t === 'cho_duoc_si' && <Tag color="gold">Chờ dược sĩ</Tag>}
                {t === 'cho_goi_lai' && <Tag color="purple">Chờ gọi lại</Tag>}
                {t === 'duoc_si_dang_xu_ly' && <Tag color="green">Tôi đang xử lý</Tag>}
                {r.bi_gan_co && <Tag color="red">Nguy hiểm</Tag>}
              </>
            ),
          },
          {
            title: '',
            render: (_, r) =>
              r.trang_thai === 'cho_duoc_si' ? (
                <YeuCauQuyen ma="chat.handle" kieu="nut">
                  <Button type="primary" size="small" loading={hanhDong.isPending && hanhDong.variables?.id === r.id} onClick={() => { setChon(r.id); hanhDong.mutate({ id: r.id, viec: 'nhan' }) }}>Nhận tư vấn</Button>
                </YeuCauQuyen>
              ) : (
                <Button size="small" onClick={() => setChon(r.id)}>{r.trang_thai === 'cho_goi_lai' ? 'Xem' : 'Tiếp tục'}</Button>
              ),
          },
        ]}
      />
      {chon === null ? (
        <Empty description="Chọn một phiên để xem" />
      ) : ct.isError ? (
        <Alert type="error" showIcon title="Không mở được phiên này" />
      ) : ct.data ? (
        <KhungChat key={ct.data.id} ct={ct.data} onDong={() => hanhDong.mutate({ id: ct.data.id, viec: 'dong' })} />
      ) : null}
    </Space>
  )
}
