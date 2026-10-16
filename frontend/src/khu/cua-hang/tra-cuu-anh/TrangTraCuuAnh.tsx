import { CameraOutlined } from '@ant-design/icons'
import { useMutation } from '@tanstack/react-query'
import { Alert, Button, Card, Descriptions, Space, Tag, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { api } from '../../../api/client'
import { goi, thongDiepChung } from '../../../api/goi'
import type { components } from '../../../api/schema'
import { layMaPhien } from '../../../lib/maPhien'
import { TheSanPham } from '../TheSanPham'
import { loiAnhTraCuu } from './traCuuAnh'

type KetQua = components['schemas']['TraCuuAnhRa']

/** KVL06: chụp hoặc chọn ảnh hộp thuốc, hệ thống đọc thông tin và đối chiếu với sản phẩm của nhà thuốc. */
export default function TrangTraCuuAnh() {
  const o = useRef<HTMLInputElement>(null)
  const [tep, setTep] = useState<File | null>(null)
  const [xem, setXem] = useState<string | null>(null)
  const [loi, setLoi] = useState<string | null>(null)
  useEffect(() => () => { if (xem) URL.revokeObjectURL(xem) }, [xem])

  const tra = useMutation({
    mutationFn: async (f: File) => {
      const maPhien = layMaPhien()
      const r = await goi(() =>
        api.POST('/api/v1/tra-cuu-anh', {
          params: { header: { 'X-Ma-Phien': maPhien } },
          body: { anh: '' },
          bodySerializer: () => {
            const fd = new FormData()
            fd.append('anh', f)
            return fd
          },
        }),
      )
      if (!r.ok) throw new Error(thongDiepChung(r.loi))
      return r.data as KetQua
    },
  })

  function chon(f: File | undefined) {
    tra.reset()
    const l = f ? loiAnhTraCuu(f) : null
    setLoi(l)
    const hopLe = f && !l ? f : null
    setTep(hopLe)
    setXem(hopLe ? URL.createObjectURL(hopLe) : null)
  }
  const kq = tra.data

  return (
    <Space orientation="vertical" size="middle" style={{ width: '100%', maxWidth: 720 }}>
      <Typography.Title level={2} style={{ margin: 0 }}>Tra cứu thuốc bằng ảnh</Typography.Title>
      <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
        Chụp rõ mặt hộp có tên thuốc và số đăng ký. Kết quả chỉ mang tính tham khảo, không thay thế tư vấn của dược sĩ.
      </Typography.Paragraph>
      <input ref={o} type="file" hidden data-testid="chon-anh" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={(e) => { chon(e.target.files?.[0]); e.target.value = '' }} />
      <Space wrap>
        <Button icon={<CameraOutlined />} onClick={() => o.current?.click()}>{tep ? 'Chọn ảnh khác' : 'Chụp hoặc chọn ảnh'}</Button>
        <Button type="primary" disabled={!tep} loading={tra.isPending} onClick={() => tep && tra.mutate(tep)}>Tra cứu</Button>
      </Space>
      {loi && <Alert type="error" showIcon title={loi} />}
      {xem && <img src={xem} alt="Ảnh hộp thuốc đã chọn" style={{ maxWidth: '100%', maxHeight: 280, objectFit: 'contain', border: '1px solid #f0f0f0', borderRadius: 6 }} />}
      {tra.isError && <Alert type="error" showIcon title={tra.error.message} />}
      {kq && (
        <Space orientation="vertical" size="middle" style={{ width: '100%' }}>
          {kq.canh_bao && <Alert type={kq.khop ? 'warning' : 'info'} showIcon title={kq.canh_bao} />}
          {kq.khop && (
            <Card size="small" title={<>Sản phẩm trong nhà thuốc <Tag color="green">Đã xác minh</Tag></>}>
              <div style={{ maxWidth: 260 }}><TheSanPham sp={kq.khop.san_pham} /></div>
              {kq.khop.tom_tat && (
                <Descriptions size="small" column={1} style={{ marginTop: 12 }}>
                  {kq.khop.tom_tat.chi_dinh && <Descriptions.Item label="Chỉ định">{kq.khop.tom_tat.chi_dinh}</Descriptions.Item>}
                  {kq.khop.tom_tat.chong_chi_dinh && <Descriptions.Item label="Chống chỉ định">{kq.khop.tom_tat.chong_chi_dinh}</Descriptions.Item>}
                  {kq.khop.tom_tat.than_trong && <Descriptions.Item label="Thận trọng">{kq.khop.tom_tat.than_trong}</Descriptions.Item>}
                </Descriptions>
              )}
            </Card>
          )}
          {(kq.doc_duoc.ten_san_pham || kq.doc_duoc.so_dang_ky || (kq.doc_duoc.hoat_chat ?? []).length > 0) && (
            <Card size="small" title={<>Thông tin đọc được từ ảnh {!kq.da_xac_minh && <Tag color="orange">Chưa xác minh</Tag>}</>}>
              <Descriptions size="small" column={1}>
                <Descriptions.Item label="Tên">{kq.doc_duoc.ten_san_pham ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="Hoạt chất">{(kq.doc_duoc.hoat_chat ?? []).length ? (kq.doc_duoc.hoat_chat ?? []).map((h) => (h.ham_luong ? `${h.ten} ${h.ham_luong}` : h.ten)).join(', ') : '—'}</Descriptions.Item>
                <Descriptions.Item label="Số đăng ký">{kq.doc_duoc.so_dang_ky ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="Nhà sản xuất">{kq.doc_duoc.nha_san_xuat ?? '—'}</Descriptions.Item>
                <Descriptions.Item label="Dạng bào chế">{kq.doc_duoc.dang_bao_che ?? '—'}</Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </Space>
      )}
    </Space>
  )
}
