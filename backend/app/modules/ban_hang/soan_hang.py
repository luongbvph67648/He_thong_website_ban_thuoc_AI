"""Soạn hàng, đóng gói và bàn giao vận chuyển (KHO03, KHO04, spec 04 dòng 16, 17, 18).

Chuyển trạng thái luôn qua `chuyen_trang_thai`; đổi lô qua `ton_kho.doi_lo`. Tạo vận đơn gọi đối tác bên ngoài nên làm
SAU khi đã khóa đơn và kiểm trạng thái, và hủy lại vận đơn nếu bước ghi sau đó lỗi.
"""

import logging
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import hom_nay_vn
from app.models.ban_hang import CtDonHang, DonHang, PhanBoLo, VanDon
from app.models.enums import HinhThucNhan, LoaiVanDon, TrangThaiDon, TrangThaiLo, TrangThaiPhanBo
from app.models.he_thong import NhanVien
from app.models.kho import LoThuoc
from app.models.san_pham import DonViQuyDoi
from app.modules.ban_hang import dat_hang
from app.modules.ban_hang.schemas_soan_hang import DoiLoVao, DongSoanRa, LoGoiY, PhanBoRa, SoanHangRa
from app.modules.ban_hang.trang_thai import NGUON_NGUOI_DUNG, TacNhan, chuyen_trang_thai
from app.modules.kho import ton_kho
from app.tich_hop.van_chuyen import lay_don_vi_van_chuyen

logger = logging.getLogger(__name__)
TT = TrangThaiDon
SO_LO_GOI_Y = 5
GRAM_MOI_DON_VI_CO_SO = dat_hang.GRAM_MOI_DON_VI_CO_SO


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")


def _sai_trang_thai(thong_diep: str) -> LoiNghiepVu:
    return LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", thong_diep)


async def _khoa_don(db: AsyncSession, don_id: int) -> DonHang:
    """Khóa dòng đơn (tuần tự hóa hai thao tác của kho trên cùng đơn) và nạp lại trạng thái mới nhất."""
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.id == don_id)
            .options(selectinload(DonHang.chi_tiet))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if don is None:
        raise _khong_tim_thay()
    return don


async def chi_tiet(db: AsyncSession, don_id: int) -> SoanHangRa:
    """Đơn kèm lô đang giữ/đã xuất theo từng dòng và các lô gợi ý FEFO (khi còn đổi lô được)."""
    don = (
        await db.execute(select(DonHang).where(DonHang.id == don_id).options(selectinload(DonHang.chi_tiet)))
    ).scalar_one_or_none()
    if don is None or don.trang_thai in (TT.cho_khach_xac_nhan, TT.cho_thanh_toan, TT.cho_xac_nhan):
        raise _khong_tim_thay()  # kho chỉ làm việc với đơn từ "Đã xác nhận" (spec 05 DS01)
    dong_ct = sorted(don.chi_tiet, key=lambda c: c.id)
    phan_bo = (
        await db.execute(
            select(PhanBoLo, LoThuoc.so_lo, LoThuoc.han_su_dung)
            .join(LoThuoc, LoThuoc.id == PhanBoLo.lo_id)
            .where(PhanBoLo.ct_don_hang_id.in_([c.id for c in dong_ct]), PhanBoLo.trang_thai != TrangThaiPhanBo.da_nha)
            .order_by(PhanBoLo.id)
        )
    ).all()
    ma_vach = {
        (r.id): r.ma_vach
        for r in (
            await db.execute(select(DonViQuyDoi).where(DonViQuyDoi.id.in_([c.don_vi_id for c in dong_ct])))
        ).scalars()
    }
    cho_doi = don.trang_thai == TT.da_xac_nhan
    goi_y = await _goi_y(db, {c.san_pham_id for c in dong_ct}) if cho_doi else {}
    dong = [
        DongSoanRa(
            ct_don_hang_id=c.id,
            san_pham_id=c.san_pham_id,
            ten_san_pham=c.ten_san_pham,
            ten_don_vi=c.ten_don_vi,
            he_so=c.he_so,
            so_luong=c.so_luong,
            ma_vach=ma_vach.get(c.don_vi_id),
            phan_bo=[
                PhanBoRa(
                    id=pb.id,
                    lo_id=pb.lo_id,
                    so_lo=so_lo,
                    han_su_dung=han,
                    so_luong_co_so=pb.so_luong_co_so,
                    trang_thai=pb.trang_thai,
                    ly_do_doi_lo=pb.ly_do_doi_lo,
                )
                for pb, so_lo, han in phan_bo
                if pb.ct_don_hang_id == c.id
            ],
            goi_y=goi_y.get(c.san_pham_id, []),
        )
        for c in dong_ct
    ]
    return SoanHangRa(
        id=don.id,
        ma_don=don.ma_don,
        trang_thai=don.trang_thai,
        hinh_thuc_nhan=don.hinh_thuc_nhan,
        ten_nguoi_nhan=don.ten_nguoi_nhan,
        sdt_nguoi_nhan=don.sdt_nguoi_nhan,
        dia_chi_giao=don.dia_chi_giao,
        ghi_chu=don.ghi_chu,
        created_at=don.created_at,
        dong=dong,
        van_don=await dat_hang.van_don_giao_hang(db, don.id),
        che_do_van_chuyen_gia=settings.VAN_CHUYEN_CHE_DO == "gia",
    )


async def _goi_y(db: AsyncSession, san_pham_ids: set[int]) -> dict[int, list[LoGoiY]]:
    """Lô còn bán được theo FEFO (HSD gần nhất trước) cho từng sản phẩm, tối đa `SO_LO_GOI_Y` lô."""
    hom_nay: date = hom_nay_vn()
    lo = (
        await db.execute(
            select(LoThuoc)
            .where(
                LoThuoc.san_pham_id.in_(san_pham_ids),
                LoThuoc.trang_thai == TrangThaiLo.dang_ban,
                LoThuoc.han_su_dung > hom_nay,
                LoThuoc.so_luong_ton - LoThuoc.so_luong_giu > 0,
            )
            .order_by(LoThuoc.han_su_dung, LoThuoc.id)
        )
    ).scalars()
    ket_qua: dict[int, list[LoGoiY]] = {}
    for x in lo:
        ds = ket_qua.setdefault(x.san_pham_id, [])
        if len(ds) < SO_LO_GOI_Y:
            ds.append(
                LoGoiY(lo_id=x.id, so_lo=x.so_lo, han_su_dung=x.han_su_dung, kha_dung=x.so_luong_ton - x.so_luong_giu)
            )
    return ket_qua


async def doi_lo(db: AsyncSession, don_id: int, vao: DoiLoVao) -> SoanHangRa:
    """KHO03: đổi lô của một phân bổ khi đơn còn "Đã xác nhận" (chưa chốt lô); bắt buộc lý do."""
    ly_do = vao.ly_do.strip()
    if not ly_do:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": "ly_do", "loi": "Bắt buộc nhập lý do"}]
        )
    don = await _khoa_don(db, don_id)
    if don.trang_thai != TT.da_xac_nhan:
        raise _sai_trang_thai("Chỉ đổi lô được khi đơn đang ở Đã xác nhận (chưa bắt đầu soạn hàng)")
    pb = (
        await db.execute(
            select(PhanBoLo)
            .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
            .where(PhanBoLo.id == vao.phan_bo_lo_id, CtDonHang.don_hang_id == don.id)
        )
    ).scalar_one_or_none()
    if pb is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy phân bổ lô của đơn này")
    await ton_kho.doi_lo(db, pb, vao.lo_id, ly_do)
    return await chi_tiet(db, don.id)


async def bat_dau_soan(db: AsyncSession, nv: NhanVien, don_id: int) -> SoanHangRa:
    """KHO03, dòng 16: chốt lô, trừ tồn thật, ghi thẻ kho (hook của máy trạng thái); lô giữ phải còn bán được."""
    don = await _khoa_don(db, don_id)
    if don.trang_thai == TT.da_xac_nhan:
        hom_nay = hom_nay_vn()
        lo = (
            await db.execute(
                select(LoThuoc.so_lo, LoThuoc.trang_thai, LoThuoc.han_su_dung)
                .join(PhanBoLo, PhanBoLo.lo_id == LoThuoc.id)
                .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
                .where(CtDonHang.don_hang_id == don.id, PhanBoLo.trang_thai == TrangThaiPhanBo.dang_giu)
            )
        ).all()
        for so_lo, trang_thai, han in lo:
            if trang_thai != TrangThaiLo.dang_ban or han <= hom_nay:
                raise _sai_trang_thai(f"Lô {so_lo} không còn bán được, hãy đổi lô trước khi soạn hàng")
    tac_nhan = TacNhan.kho(nv.id)
    await chuyen_trang_thai(db, don, TT.dang_soan_hang, tac_nhan, NGUON_NGUOI_DUNG)
    return await chi_tiet(db, don.id)


def _khoi_luong(don: DonHang) -> int:
    return max(sum(c.so_luong * c.he_so for c in don.chi_tiet) * GRAM_MOI_DON_VI_CO_SO, GRAM_MOI_DON_VI_CO_SO)


async def dong_goi(db: AsyncSession, nv: NhanVien, don_id: int) -> SoanHangRa:
    """KHO04: giao tận nơi thì tạo vận đơn qua adapter rồi chuyển "Chờ lấy hàng" (dòng 17); nhận tại nhà thuốc chỉ
    đóng gói (dòng 18, không có vận đơn)."""
    don = await _khoa_don(db, don_id)
    if don.trang_thai != TT.dang_soan_hang:
        raise _sai_trang_thai("Chỉ đóng gói được đơn đang soạn hàng")
    tac_nhan = TacNhan.kho(nv.id)
    if don.hinh_thuc_nhan == HinhThucNhan.nhan_tai_nha_thuoc:
        await chuyen_trang_thai(db, don, TT.cho_lay_hang, tac_nhan, NGUON_NGUOI_DUNG, "Đóng gói, chờ khách đến nhận")
        return await chi_tiet(db, don.id)
    don_vi = lay_don_vi_van_chuyen()
    khoi_luong = _khoi_luong(don)
    try:
        kq = await don_vi.tao_van_don(don, "giao_hang", khoi_luong)
    except Exception as e:  # noqa: BLE001  lỗi đối tác bất kỳ đều là 502, đơn giữ nguyên để kho thử lại
        logger.warning("Tạo vận đơn thất bại cho đơn %s", don.ma_don, exc_info=True)
        raise LoiNghiepVu("LOI_DOI_TAC", "Không tạo được vận đơn, vui lòng thử lại sau") from e
    try:
        db.add(
            VanDon(
                don_hang_id=don.id,
                loai=LoaiVanDon.giao_hang,
                don_vi_van_chuyen=don_vi.ten,
                ma_van_don=kq.ma_van_don,
                phi=Decimal(kq.phi),
                khoi_luong_gram=khoi_luong,
            )
        )
        await db.flush()
        await chuyen_trang_thai(db, don, TT.cho_lay_hang, tac_nhan, NGUON_NGUOI_DUNG, f"Vận đơn {kq.ma_van_don}")
    except Exception:
        try:
            await don_vi.huy_van_don(kq.ma_van_don)
        except Exception:  # noqa: BLE001  hủy là cố gắng tối đa, không che lỗi gốc
            logger.error("Không hủy được vận đơn %s sau lỗi ghi đơn", kq.ma_van_don, exc_info=True)
        raise
    return await chi_tiet(db, don.id)
