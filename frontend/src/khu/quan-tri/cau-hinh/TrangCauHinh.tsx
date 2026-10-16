import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, App, Button, Card, Checkbox, Input, InputNumber, Skeleton, Space, Tag, Typography } from 'antd'
import { useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import { YeuCauQuyen } from '../../../components/YeuCauQuyen'
import { bangNhau, kiemTraGiaTri, loiTheoTruongCauHinh, nhomTheoChuDe, type MucCauHinh } from '../../../lib/cauHinh'
import { dinhDangNgay } from '../../../lib/dinhDang'
import { coQuyen } from '../../../lib/quyen'
import { usePhien } from '../../../stores/phien'

const KHOA_QUERY = ['noi-bo', 'cau-hinh'] as const
const NGAY_TRONG_TUAN = ['Thứ hai', 'Thứ ba', 'Thứ tư', 'Thứ năm', 'Thứ sáu', 'Thứ bảy', 'Chủ nhật'].map((label, i) => ({ label, value: i + 1 }))
const GIO_RONG = { bat_dau: '', ket_thuc: '', ngay_trong_tuan: [] as number[] }

const laDoiTuong = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v)
const nhomTien = (v: number | string | undefined) => String(v ?? '').replace(/\B(?=(\d{3})+(?!\d))/g, '.')

function hienThiGiaTri(gia: unknown): string {
  return laDoiTuong(gia) || Array.isArray(gia) ? JSON.stringify(gia) : String(gia)
}

interface BoNhapProps {
  muc: MucCauHinh
  giaTri: unknown
  doi: (gia: unknown) => void
  khoa: boolean
  loi: Record<string, string>
}

const ChuLoi = ({ noiDung }: { noiDung?: string }) =>
  noiDung ? (
    <Typography.Text type="danger" role="alert" style={{ display: 'block' }}>
      {noiDung}
    </Typography.Text>
  ) : null

/** Ô nhập một số nguyên (số thường hoặc tiền: có dấu chấm ngăn nghìn). */
function OSo({ nhan, gia, doi, khoa, don_vi, tien }: { nhan: string; gia: unknown; doi: (v: number | null) => void; khoa: boolean; don_vi: string | null; tien: boolean }) {
  return (
    <InputNumber
      aria-label={nhan}
      value={typeof gia === 'number' ? gia : null}
      precision={0} // không đặt min/max: antd sẽ âm thầm ép giá trị về khoảng, người dùng không biết mình nhập sai
      controls={false}
      disabled={khoa}
      addonAfter={don_vi ?? undefined}
      formatter={tien ? nhomTien : undefined}
      // Chuỗi rỗng phải giữ là rỗng: `Number('')` là 0 nên xóa trắng ô tiền sẽ âm thầm thành 0 (miễn phí vận chuyển).
      parser={tien ? (v) => String(v ?? '').replace(/\./g, '') : undefined}
      onChange={(v) => doi(typeof v === 'number' ? v : null)}
      style={{ width: 240 }}
    />
  )
}

function BoNhap({ muc, giaTri, doi, khoa, loi }: BoNhapProps) {
  if (muc.kieu === 'so' || muc.kieu === 'tien') {
    return (
      <>
        <OSo nhan={muc.nhan} gia={giaTri} doi={doi} khoa={khoa} don_vi={muc.don_vi} tien={muc.kieu === 'tien'} />
        <ChuLoi noiDung={loi.gia_tri} />
      </>
    )
  }
  if (muc.kieu === 'nhom_so') {
    const hienTai = laDoiTuong(giaTri) ? giaTri : {}
    return (
      <Space direction="vertical" size={8}>
        {muc.truong.map((t) => (
          <div key={t.ten}>
            <div>{t.nhan}</div>
            <OSo
              nhan={`${muc.nhan}: ${t.nhan}`}
              gia={hienTai[t.ten]}
              doi={(v) => doi({ ...hienTai, [t.ten]: v })}
              khoa={khoa}
              don_vi={t.don_vi}
              tien={false}
            />
            <Typography.Text type="secondary"> {t.toi_thieu}–{t.toi_da}</Typography.Text>
            <ChuLoi noiDung={loi[t.ten]} />
          </div>
        ))}
        <ChuLoi noiDung={loi.gia_tri} />
      </Space>
    )
  }
  const gio = laDoiTuong(giaTri) ? { ...GIO_RONG, ...giaTri } : GIO_RONG
  const ngay = Array.isArray(gio.ngay_trong_tuan) ? (gio.ngay_trong_tuan as number[]) : []
  return (
    <Space direction="vertical" size={8}>
      <Space wrap>
        <label>
          Từ{' '}
          <Input type="time" aria-label="Giờ bắt đầu" value={String(gio.bat_dau)} disabled={khoa} onChange={(e) => doi({ ...gio, bat_dau: e.target.value })} style={{ width: 130 }} />
        </label>
        <label>
          đến{' '}
          <Input type="time" aria-label="Giờ kết thúc" value={String(gio.ket_thuc)} disabled={khoa} onChange={(e) => doi({ ...gio, ket_thuc: e.target.value })} style={{ width: 130 }} />
        </label>
      </Space>
      <ChuLoi noiDung={loi.bat_dau} />
      <ChuLoi noiDung={loi.ket_thuc} />
      <Checkbox.Group
        options={NGAY_TRONG_TUAN}
        value={ngay}
        disabled={khoa}
        onChange={(v) => doi({ ...gio, ngay_trong_tuan: [...(v as number[])].sort((a, b) => a - b) })}
      />
      <ChuLoi noiDung={loi.ngay_trong_tuan} />
      <ChuLoi noiDung={loi.gia_tri} />
    </Space>
  )
}

/**
 * Cấu hình hệ thống (AD08): các khóa nhóm theo chủ đề, mỗi khóa một ô nhập đúng kiểu dựng từ metadata của API. Sửa xong mới có
 * nút Lưu (từng khóa riêng); lưu gửi kèm `phien_ban` nên nếu Admin khác vừa sửa khóa đó (409) thì tải lại bản mới nhưng GIỮ
 * giá trị đang gõ để người dùng quyết định, không ghi đè ngầm.
 */
export default function TrangCauHinh() {
  const { message } = App.useApp()
  const queryClient = useQueryClient()
  const quyen = usePhien((s) => s.quyen)
  const duocSua = coQuyen(quyen, 'config.manage')
  // Bản nháp theo khóa; `goc` ghi phiên bản máy chủ lúc bắt đầu sửa để báo khi máy chủ đã đổi giữa chừng.
  const [ban, setBan] = useState<Record<string, unknown>>({})
  const [goc, setGoc] = useState<Record<string, string>>({})
  const [loiMayChu, setLoiMayChu] = useState<Record<string, Record<string, string>>>({})

  const danhSach = useQuery({
    queryKey: KHOA_QUERY,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/noi-bo/cau-hinh')
      if (error) throw error
      return data
    },
  })

  const luu = useMutation({
    mutationFn: ({ muc, giaTri }: { muc: MucCauHinh; giaTri: unknown }) =>
      goi(() => api.PUT('/api/v1/noi-bo/cau-hinh/{khoa}', { params: { path: { khoa: muc.khoa } }, body: { gia_tri: giaTri, phien_ban: muc.phien_ban } })),
    onSuccess: async (kq, { muc }) => {
      if (!kq.ok) {
        if (kq.loi?.ma_loi === 'DU_LIEU_DA_THAY_DOI') {
          await queryClient.invalidateQueries({ queryKey: KHOA_QUERY }) // bản mới về, bản nháp giữ nguyên
          return void message.warning(`${kq.loi.thong_diep}. Đã tải bản mới, hãy kiểm tra rồi lưu lại.`)
        }
        const theoTruong = loiTheoTruongCauHinh(kq.loi?.chi_tiet)
        if (Object.keys(theoTruong).length > 0) setLoiMayChu((s) => ({ ...s, [muc.khoa]: theoTruong }))
        else void message.error(thongDiepChung(kq.loi))
        return
      }
      bo(muc.khoa)
      await queryClient.invalidateQueries({ queryKey: KHOA_QUERY })
      void message.success(`Đã lưu: ${muc.nhan}`)
    },
  })

  function bo(khoa: string) {
    const boKhoa = <T,>(s: Record<string, T>) => Object.fromEntries(Object.entries(s).filter(([k]) => k !== khoa))
    setBan(boKhoa)
    setGoc(boKhoa)
    setLoiMayChu(boKhoa)
  }

  function sua(muc: MucCauHinh, gia: unknown) {
    setGoc((s) => (muc.khoa in s ? s : { ...s, [muc.khoa]: muc.phien_ban }))
    setBan((s) => ({ ...s, [muc.khoa]: gia }))
    setLoiMayChu((s) => Object.fromEntries(Object.entries(s).filter(([k]) => k !== muc.khoa)))
  }

  if (danhSach.isError) return <Alert type="error" showIcon title="Không tải được cấu hình hệ thống" />
  if (!danhSach.data) return <Skeleton active />

  return (
    <div>
      <Typography.Title level={3}>Cấu hình hệ thống</Typography.Title>
      <Typography.Paragraph type="secondary">
        Thay đổi có hiệu lực ngay và được ghi vào nhật ký hệ thống. Mỗi khóa có khoảng giá trị cho phép để tránh cài đặt làm hệ thống lỗi.
      </Typography.Paragraph>
      {nhomTheoChuDe(danhSach.data).map(([nhom, danh]) => (
        <Card key={nhom} title={nhom} style={{ marginBottom: 16 }}>
          {danh.map((muc) => {
            const gia = muc.khoa in ban ? ban[muc.khoa] : muc.gia_tri
            const daDoi = muc.khoa in ban && !bangNhau(ban[muc.khoa], muc.gia_tri)
            const loiClient = daDoi ? kiemTraGiaTri(muc, gia) : {}
            const loi = { ...loiClient, ...(loiMayChu[muc.khoa] ?? {}) }
            const mayChuDaDoi = daDoi && muc.khoa in goc && goc[muc.khoa] !== muc.phien_ban
            return (
              <div key={muc.khoa} data-khoa={muc.khoa} style={{ display: 'flex', gap: 24, flexWrap: 'wrap', padding: '12px 0', borderBottom: '1px solid #f0f0f0' }}>
                <div style={{ flex: '1 1 280px', minWidth: 240 }}>
                  <Typography.Text strong>{muc.nhan}</Typography.Text> {muc.gia_tri === null && <Tag color="orange">Chưa thiết lập</Tag>}
                  <div>
                    <Typography.Text type="secondary">{muc.mo_ta}</Typography.Text>
                  </div>
                  {(muc.kieu === 'so' || muc.kieu === 'tien') && (
                    <div>
                      <Typography.Text type="secondary">
                        Giá trị từ {muc.toi_thieu?.toLocaleString('vi-VN')} đến {muc.toi_da?.toLocaleString('vi-VN')} {muc.don_vi}
                      </Typography.Text>
                    </div>
                  )}
                </div>
                <div style={{ flex: '1 1 360px' }}>
                  <BoNhap muc={muc} giaTri={gia} doi={(v) => sua(muc, v)} khoa={!duocSua} loi={loi} />
                  {mayChuDaDoi && (
                    <Alert type="warning" showIcon style={{ marginTop: 8 }} title={`Giá trị hiện tại trên máy chủ: ${hienThiGiaTri(muc.gia_tri)}. Người khác vừa đổi khóa này.`} />
                  )}
                  <YeuCauQuyen ma="config.manage" kieu="nut">
                    <Space style={{ marginTop: 8 }}>
                      <Button type="primary" disabled={!daDoi || Object.keys(loi).length > 0} loading={luu.isPending && luu.variables?.muc.khoa === muc.khoa} onClick={() => luu.mutate({ muc, giaTri: gia })}>
                        Lưu
                      </Button>
                      <Button disabled={!daDoi} onClick={() => bo(muc.khoa)}>
                        Hoàn tác
                      </Button>
                    </Space>
                  </YeuCauQuyen>
                  <div>
                    <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                      {muc.nhan_vien_cap_nhat
                        ? `Cập nhật bởi ${muc.nhan_vien_cap_nhat.ho_ten} (${muc.nhan_vien_cap_nhat.ma_nhan_vien}) lúc ${dinhDangNgay(muc.updated_at, 'ngayGio')}`
                        : 'Chưa có ai chỉnh, đang dùng giá trị mặc định'}
                    </Typography.Text>
                  </div>
                </div>
              </div>
            )
          })}
        </Card>
      ))}
    </div>
  )
}
