"""Admin xác nhận hoàn tiền (AD17, T6.3). Không commit.

VNPay/MoMo: gọi API hoàn của cổng theo giao dịch gốc. COD/tiền mặt/chuyển khoản: Admin chuyển tay rồi đính kèm chứng từ.
Người xác nhận phải khác dược sĩ đã duyệt yêu cầu đổi trả (spec 03 mục 7).
"""

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.loi import LoiNghiepVu
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import DonHang, ThanhToan, YeuCauDoiTra
from app.models.enums import (
    LoaiGiaoDich,
    TrangThaiDoiTra,
    TrangThaiGiaoDich,
    TrangThaiThanhToan,
)
from app.models.he_thong import NhanVien
from app.models.khach_hang import KhachHang
from app.modules.doi_tra.dich_vu import CONG_HOAN_THU_CONG
from app.modules.hoan_tien.schemas import HoanTienRa
from app.modules.thong_bao import service as thong_bao
from app.tich_hop.thanh_toan import lay_cong

logger = logging.getLogger(__name__)
TG = TrangThaiGiaoDich


def _che_tai_khoan(tt: dict | None) -> dict | None:
    """Ẩn danh hóa sau khi hoàn: giữ ngân hàng và 4 số cuối, bỏ tên chủ tài khoản."""
    if not tt:
        return None
    so = str(tt.get("so_tai_khoan", ""))
    return {"ngan_hang": tt.get("ngan_hang"), "so_tai_khoan": "****" + so[-4:] if so else None, "da_an_danh": True}


async def _tong(db: AsyncSession, don_id: int, loai: LoaiGiaoDich, trang_thai: tuple[TG, ...]) -> Decimal:
    return await db.scalar(
        select(func.coalesce(func.sum(ThanhToan.so_tien), 0)).where(
            ThanhToan.don_hang_id == don_id, ThanhToan.loai == loai, ThanhToan.trang_thai.in_(trang_thai)
        )
    ) or Decimal(0)


async def _ra(
    db: AsyncSession, gd: ThanhToan, don: DonHang, khach: KhachHang | None, yc: YeuCauDoiTra | None
) -> HoanTienRa:
    thu_cong = gd.cong_thanh_toan in CONG_HOAN_THU_CONG
    return HoanTienRa(
        id=gd.id,
        ma_don=don.ma_don,
        ten_khach=khach.ho_ten if khach else None,
        so_tien=gd.so_tien,
        cong_thanh_toan=gd.cong_thanh_toan,
        trang_thai=gd.trang_thai,
        nguon="doi_tra" if yc else "huy_don",
        ma_yeu_cau=yc.ma_yeu_cau if yc else None,
        tong_da_thanh_toan=await _tong(db, don.id, LoaiGiaoDich.thanh_toan, (TG.thanh_cong,)),
        tu_dong_qua_cong=not thu_cong,
        thong_tin_nhan_hoan=gd.thong_tin_nhan_hoan,
        thieu_tai_khoan=bool(
            thu_cong and yc is not None and gd.trang_thai == TG.khoi_tao and not gd.thong_tin_nhan_hoan
        ),
        chung_tu=luu_tru.url_ky(gd.chung_tu_url) if gd.chung_tu_url else None,
        ghi_chu=gd.ghi_chu,
        created_at=gd.created_at,
        xu_ly_luc=gd.updated_at if gd.trang_thai != TG.khoi_tao else None,
    )


def _truy_van():
    return (
        select(ThanhToan, DonHang, KhachHang, YeuCauDoiTra)
        .join(DonHang, DonHang.id == ThanhToan.don_hang_id)
        .outerjoin(KhachHang, KhachHang.id == DonHang.khach_hang_id)
        .outerjoin(YeuCauDoiTra, YeuCauDoiTra.id == ThanhToan.yeu_cau_doi_tra_id)
        .where(ThanhToan.loai == LoaiGiaoDich.hoan_tien)
    )


async def danh_sach(db: AsyncSession, nv: NhanVien, trang_thai: TG | None) -> list[HoanTienRa]:
    await dam_bao_la_admin(db, nv)
    cau = _truy_van().where(ThanhToan.trang_thai == (trang_thai or TG.khoi_tao))
    cau = cau.order_by(ThanhToan.created_at, ThanhToan.id).limit(200)
    return [await _ra(db, *dong) for dong in (await db.execute(cau)).all()]


async def xac_nhan(db: AsyncSession, nv: NhanVien, gd_id: int, chung_tu: tuple[bytes, str] | None) -> HoanTienRa:
    """`chung_tu` = (nội dung, kiểu mime đã nhận dạng) bắt buộc với hoàn thủ công."""
    await dam_bao_la_admin(db, nv)
    gd = (
        await db.execute(
            select(ThanhToan)
            .where(ThanhToan.id == gd_id, ThanhToan.loai == LoaiGiaoDich.hoan_tien)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if gd is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy giao dịch hoàn tiền")
    if gd.trang_thai != TG.khoi_tao:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Giao dịch hoàn tiền này đã được xử lý")
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.id == gd.don_hang_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    yc = None
    if gd.yeu_cau_doi_tra_id is not None:
        yc = (
            await db.execute(
                select(YeuCauDoiTra)
                .where(YeuCauDoiTra.id == gd.yeu_cau_doi_tra_id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        if yc.duoc_si_id == nv.id:
            raise LoiNghiepVu(
                "TU_DUYET_KHONG_DUOC", "Người duyệt đổi trả không được tự xác nhận chuyển tiền hoàn cho yêu cầu đó"
            )
    da_thanh_toan = await _tong(db, don.id, LoaiGiaoDich.thanh_toan, (TG.thanh_cong,))
    da_hoan = await _tong(db, don.id, LoaiGiaoDich.hoan_tien, (TG.thanh_cong,))
    if da_hoan + gd.so_tien > da_thanh_toan:
        raise LoiNghiepVu("HOAN_VUOT_SO_DA_TRA", "Tổng tiền hoàn vượt số tiền khách đã thanh toán")
    thu_cong = gd.cong_thanh_toan in CONG_HOAN_THU_CONG
    if thu_cong:
        if chung_tu is None:
            raise LoiNghiepVu(
                "DU_LIEU_KHONG_HOP_LE",
                "Dữ liệu không hợp lệ",
                chi_tiet=[{"truong": "chung_tu", "loi": "Cần ảnh chứng từ chuyển khoản"}],
            )
        if yc is not None and not gd.thong_tin_nhan_hoan:
            raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Khách chưa cung cấp tài khoản nhận hoàn")
        noi_dung, kieu = chung_tu
        gd.chung_tu_url = await luu_tru.luu_tru().luu("hoan-tien", noi_dung, kieu, "rieng_tu")
    else:
        goc = await db.get(ThanhToan, gd.thanh_toan_goc_id) if gd.thanh_toan_goc_id else None
        if goc is None or not goc.ma_giao_dich_cong:
            raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Không có giao dịch gốc trên cổng để hoàn tiền")
        try:
            kq = await lay_cong(gd.cong_thanh_toan).hoan_tien(goc, gd.so_tien, f"Hoàn tiền đơn {don.ma_don}")
        except Exception as e:  # noqa: BLE001  lỗi đối tác bất kỳ đều là 502, giao dịch giữ khởi tạo để thử lại
            logger.warning("Gọi API hoàn tiền thất bại cho giao dịch %s", gd.id, exc_info=True)
            raise LoiNghiepVu("LOI_DOI_TAC", "Không gọi được cổng thanh toán để hoàn tiền, vui lòng thử lại") from e
        if not kq.thanh_cong:
            raise LoiNghiepVu("LOI_DOI_TAC", f"Cổng thanh toán từ chối hoàn tiền: {kq.thong_diep or 'không rõ lý do'}")
        gd.ma_giao_dich_cong = kq.ma_giao_dich_cong
    bay_gio = bay_gio_utc()
    gd.trang_thai, gd.nhan_vien_xu_ly_id, gd.updated_at = TG.thanh_cong, nv.id, bay_gio
    gd.thong_tin_nhan_hoan = _che_tai_khoan(gd.thong_tin_nhan_hoan)
    await db.flush()
    con_cho = await db.scalar(
        select(func.count()).where(
            ThanhToan.don_hang_id == don.id,
            ThanhToan.loai == LoaiGiaoDich.hoan_tien,
            ThanhToan.trang_thai == TG.khoi_tao,
        )
    )
    if con_cho:
        don.trang_thai_tt = TrangThaiThanhToan.cho_hoan_tien
    else:
        tong_hoan = da_hoan + gd.so_tien
        don.trang_thai_tt = (
            TrangThaiThanhToan.da_hoan_tien if tong_hoan >= da_thanh_toan else TrangThaiThanhToan.hoan_tien_mot_phan
        )
    don.updated_at = bay_gio
    if yc is not None and yc.trang_thai == TrangThaiDoiTra.kho_da_nhan:
        yc.trang_thai, yc.updated_at = TrangThaiDoiTra.hoan_tat, bay_gio  # dòng 7 của vòng đời đổi trả
    if don.khach_hang_id is not None:
        await thong_bao.gui_cho_khach(
            db,
            don.khach_hang_id,
            loai="hoan_tien",
            tieu_de=f"Đã hoàn tiền cho đơn {don.ma_don}",
            noi_dung="Nhà thuốc đã hoàn tiền; tiền về tài khoản trong vài ngày làm việc tùy ngân hàng.",
            lien_ket="/tai-khoan/don-hang/" + don.ma_don,
        )
    khach = await db.get(KhachHang, don.khach_hang_id) if don.khach_hang_id else None
    return await _ra(db, gd, don, khach, yc)
