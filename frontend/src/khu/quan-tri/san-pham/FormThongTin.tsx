import { Alert, Col, Form, Input, InputNumber, Row, Select, Switch, TreeSelect } from 'antd'
import type { ReactNode } from 'react'
import { ChonDuLieuChung } from './ChonDuLieuChung'
import { TUY_CHON_KINH_DOANH, TUY_CHON_LOAI, type TuyChonDanhMuc } from './sanPham'
import { GIOI_HAN, type GiaTriThongTin } from './thongTin'

type Loi = Partial<Record<keyof GiaTriThongTin, string>>

interface Props {
  value: GiaTriThongTin
  onChange: (v: GiaTriThongTin) => void
  /** Lỗi theo ô (từ `kiemTraThongTin` hoặc từ máy chủ); ô nào có lỗi thì hiện đỏ kèm thông điệp. */
  loi: Loi
  cay: TuyChonDanhMuc[]
  disabled?: boolean
}

function O({ nhan, id, loi, batBuoc, ghiChu, children }: { nhan: string; id: string; loi?: string; batBuoc?: boolean; ghiChu?: string; children: ReactNode }) {
  return (
    <Form.Item label={nhan} htmlFor={id} required={batBuoc} validateStatus={loi ? 'error' : undefined} help={loi} extra={loi ? undefined : ghiChu}>
      {children}
    </Form.Item>
  )
}

/** Các ô thông tin thương mại của sản phẩm (AD04). Chỉ hiển thị; trạng thái và lưu do trang cha giữ. */
export function FormThongTin({ value: v, onChange, loi, cay, disabled }: Props) {
  const dat = (thayDoi: Partial<GiaTriThongTin>) => onChange({ ...v, ...thayDoi })
  const keDon = v.loai_san_pham === 'thuoc_ke_don'

  return (
    <Form layout="vertical" component="div" disabled={disabled}>
      {keDon && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="Thuốc kê đơn không vào giỏ hàng, không giảm giá, không bán qua điện thoại và không được AI gợi ý; sản phẩm chỉ hiện để khách xem thông tin và gửi đơn thuốc."
        />
      )}
      <Row gutter={16}>
        <Col xs={24} md={8}>
          <O nhan="SKU" id="sp-sku" loi={loi.sku} batBuoc ghiChu="Tự chuyển thành chữ hoa; chữ, số, . _ -">
            <Input id="sp-sku" value={v.sku} maxLength={50} autoComplete="off" status={loi.sku ? 'error' : undefined} onChange={(e) => dat({ sku: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={16}>
          <O nhan="Tên sản phẩm" id="sp-ten" loi={loi.ten} batBuoc>
            <Input id="sp-ten" value={v.ten} maxLength={GIOI_HAN.ten * 2} autoComplete="off" status={loi.ten ? 'error' : undefined} onChange={(e) => dat({ ten: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Loại sản phẩm" id="sp-loai" loi={loi.loai_san_pham} batBuoc>
            <Select id="sp-loai" value={v.loai_san_pham} options={TUY_CHON_LOAI} placeholder="Chọn loại" status={loi.loai_san_pham ? 'error' : undefined} onChange={(x) => dat({ loai_san_pham: x, ...(x === 'thuoc_ke_don' ? { la_noi_bat: false } : {}) })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Danh mục" id="sp-danh-muc" loi={loi.danh_muc_id} batBuoc>
            <TreeSelect
              id="sp-danh-muc"
              showSearch
              treeNodeFilterProp="title"
              treeDefaultExpandAll
              placeholder="Chọn danh mục"
              value={v.danh_muc_id}
              treeData={cay}
              status={loi.danh_muc_id ? 'error' : undefined}
              onChange={(x: number | undefined) => dat({ danh_muc_id: x })}
            />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Trạng thái kinh doanh" id="sp-trang-thai" loi={loi.trang_thai} batBuoc ghiChu="Ngừng kinh doanh: khách không đặt được, lịch sử vẫn giữ.">
            <Select id="sp-trang-thai" value={v.trang_thai} options={TUY_CHON_KINH_DOANH} onChange={(x) => dat({ trang_thai: x })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Thương hiệu" id="sp-thuong-hieu" loi={loi.thuong_hieu}>
            <ChonDuLieuChung ma="thuong-hieu" id="sp-thuong-hieu" placeholder="Chọn thương hiệu" value={v.thuong_hieu} onChange={(x) => dat({ thuong_hieu: x })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Nhà sản xuất" id="sp-nsx" loi={loi.nha_san_xuat}>
            <ChonDuLieuChung ma="nha-san-xuat" id="sp-nsx" placeholder="Chọn nhà sản xuất" value={v.nha_san_xuat} onChange={(x) => dat({ nha_san_xuat: x })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Số đăng ký" id="sp-so-dang-ky" loi={loi.so_dang_ky}>
            <Input id="sp-so-dang-ky" value={v.so_dang_ky} autoComplete="off" status={loi.so_dang_ky ? 'error' : undefined} onChange={(e) => dat({ so_dang_ky: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Dạng bào chế" id="sp-dang-bao-che" loi={loi.dang_bao_che}>
            <Input id="sp-dang-bao-che" value={v.dang_bao_che} autoComplete="off" status={loi.dang_bao_che ? 'error' : undefined} onChange={(e) => dat({ dang_bao_che: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Quy cách đóng gói" id="sp-quy-cach" loi={loi.quy_cach}>
            <Input id="sp-quy-cach" value={v.quy_cach} autoComplete="off" status={loi.quy_cach ? 'error' : undefined} onChange={(e) => dat({ quy_cach: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Đối tượng sử dụng" id="sp-doi-tuong" loi={loi.doi_tuong_su_dung}>
            <Input id="sp-doi-tuong" value={v.doi_tuong_su_dung} autoComplete="off" status={loi.doi_tuong_su_dung ? 'error' : undefined} onChange={(e) => dat({ doi_tuong_su_dung: e.target.value })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Tồn tối thiểu (đơn vị cơ sở)" id="sp-ton-toi-thieu" loi={loi.ton_toi_thieu} batBuoc ghiChu="Dưới mức này thì cảnh báo sắp hết hàng.">
            <InputNumber<number> id="sp-ton-toi-thieu" style={{ width: '100%' }} value={v.ton_toi_thieu} status={loi.ton_toi_thieu ? 'error' : undefined} changeOnWheel={false} onChange={(x) => dat({ ton_toi_thieu: x })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Số lượng tối đa mỗi đơn" id="sp-toi-da" loi={loi.so_luong_toi_da_moi_don} ghiChu="Để trống là không giới hạn.">
            <InputNumber<number> id="sp-toi-da" style={{ width: '100%' }} value={v.so_luong_toi_da_moi_don} status={loi.so_luong_toi_da_moi_don ? 'error' : undefined} changeOnWheel={false} onChange={(x) => dat({ so_luong_toi_da_moi_don: x })} />
          </O>
        </Col>
        <Col xs={24} md={8}>
          <O nhan="Sản phẩm dùng định kỳ" id="sp-dinh-ky" loi={loi.dung_dinh_ky} ghiChu="Bật để hệ thống nhắc khách mua lại khi gần hết.">
            <Switch id="sp-dinh-ky" checked={v.dung_dinh_ky} onChange={(x) => dat({ dung_dinh_ky: x, ...(x ? {} : { so_ngay_dung_moi_don_vi: null }) })} />
          </O>
        </Col>
        {v.dung_dinh_ky && (
          <Col xs={24} md={8}>
            <O nhan="Số ngày dùng cho mỗi đơn vị" id="sp-so-ngay" loi={loi.so_ngay_dung_moi_don_vi} batBuoc ghiChu="Ví dụ 30 nếu một hộp dùng đủ 30 ngày.">
              <InputNumber<number> id="sp-so-ngay" style={{ width: '100%' }} value={v.so_ngay_dung_moi_don_vi} status={loi.so_ngay_dung_moi_don_vi ? 'error' : undefined} changeOnWheel={false} stringMode={false} onChange={(x) => dat({ so_ngay_dung_moi_don_vi: x })} />
            </O>
          </Col>
        )}
        <Col xs={24} md={8}>
          <O nhan="Sản phẩm nổi bật" id="sp-noi-bat" loi={loi.la_noi_bat} ghiChu={keDon ? 'Thuốc kê đơn không đặt nổi bật được.' : 'Hiện ở khu nổi bật của trang chủ.'}>
            <Switch id="sp-noi-bat" checked={v.la_noi_bat} disabled={keDon} onChange={(x) => dat({ la_noi_bat: x })} />
          </O>
        </Col>
      </Row>
    </Form>
  )
}
