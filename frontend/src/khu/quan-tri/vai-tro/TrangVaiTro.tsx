import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Modal, Radio, Segmented, Space, Table, Tag, Typography } from 'antd'
import { useMemo, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { nhanMuc, thanCapNhatQuyen, tinhThayDoiQuyen, type MucHoacKhong } from '../../../lib/quyenVaiTro'

type Quyen = components['schemas']['QuyenTrongVaiTro']
type Muc = MucHoacKhong

const TEN_VAI_TRO: Record<string, string> = { ADMIN: 'Quản trị', PHARMACIST: 'Dược sĩ bán hàng', WAREHOUSE: 'Nhân viên kho' }
const KHOA_QUERY = ['noi-bo', 'vai-tro'] as const
const KHONG = 'khong'

/**
 * Ma trận vai trò - quyền (AD18): chọn vai trò, đặt mức cho từng mã quyền (không có / chỉ xem / đầy đủ), xem tóm tắt thay
 * đổi rồi lưu. Vai trò Admin chỉ xem; `profile.self` luôn đầy đủ; quyền nội dung chuyên môn chỉ cấp cho dược sĩ.
 */
export default function TrangVaiTro() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const [maVaiTro, setMaVaiTro] = useState<string>('PHARMACIST')
  // Chỉ lưu các mã quyền người dùng đã đổi so với bản máy chủ; bản đang sửa = bản máy chủ + các thay đổi này.
  const [daDoi, setDaDoi] = useState<Record<string, Muc>>({})
  const [xacNhan, setXacNhan] = useState(false)

  const danhSach = useQuery({
    queryKey: [...KHOA_QUERY, 'danh-sach'],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/vai-tro')
      if (error) throw error
      return data
    },
  })
  const chiTiet = useQuery({
    queryKey: [...KHOA_QUERY, maVaiTro],
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/vai-tro/{ma}', { params: { path: { ma: maVaiTro } } })
      if (error) throw error
      return data
    },
  })

  const goc = useMemo<Record<string, Muc>>(
    () => Object.fromEntries((chiTiet.data?.quyen ?? []).map((q) => [q.ma, q.muc])),
    [chiTiet.data],
  )
  const sua = useMemo(() => ({ ...goc, ...daDoi }), [goc, daDoi])

  const thayDoi = useMemo(() => tinhThayDoiQuyen(goc, sua), [goc, sua])
  const chinhSuaDuoc = chiTiet.data?.chinh_sua_duoc ?? false

  const luu = useMutation({
    mutationFn: () =>
      goi(() =>
        api.PUT('/api/v1/noi-bo/vai-tro/{ma}/quyen', {
          params: { path: { ma: maVaiTro } },
          body: { quyen: thanCapNhatQuyen(sua), phien_ban: chiTiet.data?.phien_ban ?? '' },
        }),
      ),
    onSuccess: async (kq) => {
      setXacNhan(false)
      if (!kq.ok && kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
        await queryClient.invalidateQueries({ queryKey: KHOA_QUERY }) // bản mới về, `daDoi` giữ nguyên
        return void message.warning('Phân quyền của vai trò này vừa được người khác thay đổi. Đã tải bản mới, hãy kiểm tra các thay đổi của bạn rồi lưu lại.')
      }
      if (!kq.ok) {
        const chiTietLoi = Array.isArray(kq.loi?.chi_tiet) ? (kq.loi.chi_tiet as { loi?: string }[]).map((c) => c.loi).join('; ') : ''
        return void message.error(chiTietLoi || thongDiepChung(kq.loi))
      }
      await queryClient.invalidateQueries({ queryKey: KHOA_QUERY })
      setDaDoi({})
      void message.success('Đã lưu phân quyền. Nhân viên đang đăng nhập nhận quyền mới trong vài phút hoặc khi quay lại cửa sổ.')
    },
  })

  const quyenNhom = useMemo(() => {
    const theoNhom = new Map<string, Quyen[]>()
    for (const q of chiTiet.data?.quyen ?? []) theoNhom.set(q.nhom ?? 'Khác', [...(theoNhom.get(q.nhom ?? 'Khác') ?? []), q])
    return [...theoNhom.entries()]
  }, [chiTiet.data])

  function khoaTuyChon(q: Quyen, muc: 'day_du' | 'chi_xem' | null): boolean {
    if (!chinhSuaDuoc) return true
    if (q.bat_buoc) return muc !== 'day_du' // `profile.self` chỉ được ở mức đầy đủ
    if (q.chi_cho_vai_tro && q.chi_cho_vai_tro !== maVaiTro) return muc !== null // chỉ dược sĩ có
    return false
  }

  return (
    <div>
      <Typography.Title level={3}>Vai trò và phân quyền</Typography.Title>
      <Segmented
        value={maVaiTro}
        onChange={(v) => {
          setMaVaiTro(String(v))
          setDaDoi({}) // bỏ các thay đổi chưa lưu của vai trò trước
        }}
        options={(danhSach.data ?? []).map((v) => ({ value: v.ma, label: `${TEN_VAI_TRO[v.ma] ?? v.ten} (${v.so_nhan_vien})` }))}
        style={{ marginBottom: 16 }}
      />
      {!chinhSuaDuoc && chiTiet.data && (
        <Alert type="info" showIcon style={{ marginBottom: 16 }} title="Quyền của vai trò Quản trị không thay đổi được" description="Để luôn còn người quản trị hệ thống, vai trò này chỉ xem." />
      )}
      {chiTiet.isError && <Alert type="error" showIcon title="Không tải được phân quyền" style={{ marginBottom: 16 }} />}

      {quyenNhom.map(([nhom, quyen]) => (
        <div key={nhom} style={{ marginBottom: 16 }}>
          <Typography.Title level={5}>{nhom}</Typography.Title>
          <Table<Quyen>
            size="small"
            rowKey="ma"
            pagination={false}
            dataSource={quyen}
            columns={[
              {
                title: 'Quyền',
                render: (_, q) => (
                  <>
                    <code>{q.ma}</code> {q.bat_buoc && <Tag>Bắt buộc</Tag>}
                    {q.chi_cho_vai_tro && <Tag color="blue">Chỉ {TEN_VAI_TRO[q.chi_cho_vai_tro] ?? q.chi_cho_vai_tro}</Tag>}
                    <div style={{ color: '#8c8c8c' }}>{q.mo_ta}</div>
                  </>
                ),
              },
              {
                title: 'Mức',
                width: 330,
                render: (_, q) => (
                  <Radio.Group
                    aria-label={`Mức của ${q.ma}`}
                    name={`muc-${q.ma}`} // mỗi nhóm một tên: nếu trùng tên, trình duyệt coi mọi nhóm là MỘT nhóm radio
                    // Ô radio không nhận giá trị null nên dùng chuỗi `khong` cho "không có quyền".
                    value={sua[q.ma] ?? KHONG}
                    onChange={(e) => setDaDoi((s) => ({ ...s, [q.ma]: e.target.value === KHONG ? null : (e.target.value as Muc) }))}
                    optionType="button"
                    size="small"
                    options={([null, 'chi_xem', 'day_du'] as const).map((m) => ({ value: m ?? KHONG, label: nhanMuc(m), disabled: khoaTuyChon(q, m) }))}
                  />
                ),
              },
            ]}
          />
        </div>
      ))}

      <YeuCauQuyen ma="role.manage" kieu="nut">
        <Space style={{ position: 'sticky', bottom: 0, background: '#fff', padding: '12px 0' }}>
          <Button type="primary" disabled={!chinhSuaDuoc || thayDoi.length === 0} onClick={() => setXacNhan(true)}>
            Lưu phân quyền {thayDoi.length > 0 && `(${thayDoi.length} thay đổi)`}
          </Button>
          <Button disabled={thayDoi.length === 0} onClick={() => setDaDoi({})}>
            Hoàn tác
          </Button>
        </Space>
      </YeuCauQuyen>

      <Modal
        title={`Lưu phân quyền cho ${TEN_VAI_TRO[maVaiTro] ?? maVaiTro}?`}
        open={xacNhan}
        okText="Lưu"
        cancelText="Hủy"
        confirmLoading={luu.isPending}
        onOk={() => luu.mutate()}
        onCancel={() => setXacNhan(false)}
        destroyOnHidden
      >
        <ul aria-label="Các thay đổi quyền">
          {thayDoi.map((d) => (
            <li key={d.ma}>
              <code>{d.ma}</code>: {nhanMuc(d.tu)} → <strong>{nhanMuc(d.den)}</strong>
            </li>
          ))}
        </ul>
      </Modal>
    </div>
  )
}
