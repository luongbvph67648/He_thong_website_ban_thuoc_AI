import { Button, Checkbox, Collapse, InputNumber, Select, Space, Switch, Typography } from 'antd'
import { useState } from 'react'
import { dinhDangTien } from '../../lib/dinhDang'
import { LOAI_SAN_PHAM, soBoLocDangDung, type BoLocApi, type BoLocUrl, type ThayDoiLoc } from './cuaHang'

interface Props {
  boLoc: BoLocUrl
  tuyChon: BoLocApi | undefined
  onDoi: (thayDoi: ThayDoiLoc) => void
  onXoa: () => void
}

/** Khoảng giá nhập tay, chỉ áp dụng khi bấm nút (gõ từng chữ số không gọi API liên tục). */
function KhoangGia({ boLoc, onDoi }: Pick<Props, 'boLoc' | 'onDoi'>) {
  const [tu, datTu] = useState<number | null>(boLoc.giaTu ?? null)
  const [den, datDen] = useState<number | null>(boLoc.giaDen ?? null)
  return (
    <Space orientation="vertical" size={8} style={{ width: '100%' }}>
      <Space.Compact style={{ width: '100%' }}>
        <InputNumber<number> aria-label="Giá từ" placeholder="Từ" value={tu} onChange={datTu} controls={false} changeOnWheel={false} style={{ width: '50%' }} />
        <InputNumber<number> aria-label="Giá đến" placeholder="Đến" value={den} onChange={datDen} controls={false} changeOnWheel={false} style={{ width: '50%' }} />
      </Space.Compact>
      <Button
        block
        onClick={() => onDoi({ giaTu: tu === null ? undefined : Math.max(0, Math.trunc(tu)), giaDen: den === null ? undefined : Math.max(0, Math.trunc(den)) })}
      >
        Áp dụng giá (₫)
      </Button>
    </Space>
  )
}

/** Bộ lọc của trang danh mục (KVL02). Mọi giá trị nằm trên URL, component này chỉ hiển thị và báo thay đổi. */
export function BoLocSanPham({ boLoc, tuyChon, onDoi, onXoa }: Props) {
  const dangDung = soBoLocDangDung(boLoc)
  return (
    <Collapse
      defaultActiveKey={['loc']}
      items={[
        {
          key: 'loc',
          label: dangDung ? `Bộ lọc (${dangDung})` : 'Bộ lọc',
          children: (
            <Space orientation="vertical" size={16} style={{ width: '100%' }}>
              <div>
                <Typography.Text strong id="loc-loai">
                  Loại sản phẩm
                </Typography.Text>
                <Select
                  aria-labelledby="loc-loai"
                  allowClear
                  placeholder="Tất cả"
                  style={{ width: '100%', marginTop: 4 }}
                  value={boLoc.loai}
                  options={[...LOAI_SAN_PHAM]}
                  onChange={(x) => onDoi({ loai: x ?? undefined })}
                />
              </div>
              {!!tuyChon?.thuong_hieu.length && (
                <div>
                  <Typography.Text strong>Thương hiệu</Typography.Text>
                  <Checkbox.Group
                    style={{ display: 'flex', flexDirection: 'column', marginTop: 4 }}
                    value={boLoc.thuongHieu}
                    options={tuyChon.thuong_hieu.map((t) => ({ value: t.id, label: t.ten }))}
                    onChange={(ids) => onDoi({ thuongHieu: ids as number[] })}
                  />
                </div>
              )}
              {!!tuyChon?.doi_tuong.length && (
                <div>
                  <Typography.Text strong id="loc-doi-tuong">
                    Đối tượng sử dụng
                  </Typography.Text>
                  <Select
                    aria-labelledby="loc-doi-tuong"
                    allowClear
                    placeholder="Tất cả"
                    style={{ width: '100%', marginTop: 4 }}
                    value={boLoc.doiTuong}
                    options={tuyChon.doi_tuong.map((d) => ({ value: d, label: d }))}
                    onChange={(x) => onDoi({ doiTuong: x ?? undefined })}
                  />
                </div>
              )}
              <div>
                <Typography.Text strong>Khoảng giá</Typography.Text>
                {tuyChon?.gia_thap_nhat && tuyChon.gia_cao_nhat && (
                  <Typography.Paragraph type="secondary" style={{ fontSize: 12, marginBottom: 4 }}>
                    Từ {dinhDangTien(tuyChon.gia_thap_nhat)} đến {dinhDangTien(tuyChon.gia_cao_nhat)}
                  </Typography.Paragraph>
                )}
                <KhoangGia key={`${boLoc.giaTu ?? ''}-${boLoc.giaDen ?? ''}`} boLoc={boLoc} onDoi={onDoi} />
              </div>
              <Space>
                <Switch id="loc-con-hang" checked={boLoc.conHang} onChange={(x) => onDoi({ conHang: x })} />
                <label htmlFor="loc-con-hang">Chỉ sản phẩm còn hàng</label>
              </Space>
              {dangDung > 0 && (
                <Button block onClick={onXoa}>
                  Xóa bộ lọc
                </Button>
              )}
            </Space>
          ),
        },
      ]}
    />
  )
}
