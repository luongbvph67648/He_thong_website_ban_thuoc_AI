"""Đổi trả phía khách (KTV09, T6.1). Không commit.

Điều kiện (spec 04 mục 1.3 dòng 1): đơn `da_giao`, còn trong `thoi_han_doi_tra_ngay` kể từ lúc giao, tổng số lượng
trả của mỗi dòng (cộng các yêu cầu chưa bị từ chối) không vượt số đã mua.
"""

import json
import secrets
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import luu_tru
from app.core.cau_hinh import doc_cau_hinh
from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.core.tien import lam_tron_vnd
from app.models.ban_hang import CtDonHang, CtYeuCauDoiTra, DonHang, LichSuTrangThai, ThanhToan, VanDon, YeuCauDoiTra
from app.models.enums import (
    LoaiGiaoDich,
    LoaiVanDon,
    LyDoDoiTra,
    PhuongThucThanhToan,
    TrangThaiDoiTra,
    TrangThaiDon,
    TrangThaiGiaoDich,
)
from app.models.khach_hang import KhachHang
from app.modules.doi_tra.schemas import DoiTraChiTietKhach, DoiTraTom, DongTraRa, DongTraVao, TaiKhoanNhanHoanVao

SO_TEP_TOI_DA = 8
CONG_HOAN_THU_CONG = (PhuongThucThanhToan.cod, PhuongThucThanhToan.tien_mat, PhuongThucThanhToan.chuyen_khoan)
"""Cổng của giao dịch gốc cần khách cung cấp tài khoản nhận hoàn (không gọi được API hoàn của cổng)."""


def _loi_du_lieu(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def kiem_tra_tep(ds_tep: list[bytes]) -> list[str]:
    """Kiểu thật của ảnh/video bằng chứng: 1-8 tệp, ảnh tối đa 5 MB, video mp4 tối đa 30 MB."""
    if not ds_tep:
        raise _loi_du_lieu("tep", "Cần ít nhất một ảnh hoặc video")
    if len(ds_tep) > SO_TEP_TOI_DA:
        raise _loi_du_lieu("tep", f"Tối đa {SO_TEP_TOI_DA} tệp")
    kieu = []
    for nd in ds_tep:
        k = luu_tru.nhan_dang_tep(nd)
        if k is None:
            raise _loi_du_lieu("tep", "Chỉ nhận ảnh jpeg, png, webp hoặc video mp4")
        gioi_han = luu_tru.TOI_DA_VIDEO_BYTE if k == "video/mp4" else luu_tru.TOI_DA_ANH_BYTE
        if len(nd) > gioi_han:
            raise _loi_du_lieu("tep", "Ảnh tối đa 5 MB, video tối đa 30 MB")
        kieu.append(k)
    return kieu


async def thoi_diem_giao(db: AsyncSession, don: DonHang):
    moc = await db.scalar(
        select(func.max(LichSuTrangThai.created_at)).where(
            LichSuTrangThai.don_hang_id == don.id, LichSuTrangThai.den_trang_thai == TrangThaiDon.da_giao
        )
    )
    return moc or don.created_at


async def da_yeu_cau_tra(db: AsyncSession, don_id: int) -> dict[int, int]:
    """Số lượng đã đưa vào yêu cầu (chưa bị từ chối) theo từng dòng đơn."""
    ds = (
        await db.execute(
            select(CtYeuCauDoiTra.ct_don_hang_id, func.sum(CtYeuCauDoiTra.so_luong))
            .join(YeuCauDoiTra, YeuCauDoiTra.id == CtYeuCauDoiTra.yeu_cau_id)
            .where(YeuCauDoiTra.don_hang_id == don_id, YeuCauDoiTra.trang_thai != TrangThaiDoiTra.tu_choi)
            .group_by(CtYeuCauDoiTra.ct_don_hang_id)
        )
    ).all()
    return {ct: int(n) for ct, n in ds}


async def tao_yeu_cau(
    db: AsyncSession,
    khach: KhachHang,
    ma_don: str,
    dong: list[DongTraVao],
    ly_do: LyDoDoiTra,
    mo_ta: str | None,
    ds_tep: list[bytes],
) -> DoiTraChiTietKhach:
    don = (
        await db.execute(
            select(DonHang)
            .where(DonHang.ma_don == ma_don, DonHang.khach_hang_id == khach.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if don is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")
    if don.trang_thai != TrangThaiDon.da_giao:
        raise LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chỉ đổi trả được đơn đã giao")
    ngay = int(await doc_cau_hinh(db, "thoi_han_doi_tra_ngay", 7))
    if bay_gio_utc() > await thoi_diem_giao(db, don) + timedelta(days=ngay):
        raise LoiNghiepVu("QUA_THOI_HAN_DOI_TRA", f"Đã quá thời hạn đổi trả ({ngay} ngày kể từ khi giao)")
    if not dong:
        raise _loi_du_lieu("dong", "Chọn ít nhất một sản phẩm cần trả")
    kieu = kiem_tra_tep(ds_tep)
    gop: dict[int, int] = {}
    for d in dong:
        gop[d.ct_don_hang_id] = gop.get(d.ct_don_hang_id, 0) + d.so_luong
    cts = {
        c.id: c
        for c in (
            await db.execute(
                select(CtDonHang).where(CtDonHang.don_hang_id == don.id).order_by(CtDonHang.id).with_for_update()
            )
        )
        .scalars()
        .all()
    }
    da_tra = await da_yeu_cau_tra(db, don.id)
    for ct_id, sl in gop.items():
        ct = cts.get(ct_id)
        if ct is None:
            raise _loi_du_lieu("dong", "Có dòng không thuộc đơn hàng này")
        con_lai = ct.so_luong - da_tra.get(ct_id, 0)
        if sl > con_lai:
            raise LoiNghiepVu(
                "HOAN_VUOT_SO_DA_TRA",
                f"Sản phẩm {ct.ten_san_pham} chỉ còn trả được tối đa {max(con_lai, 0)}",
                chi_tiet={"ct_don_hang_id": ct_id, "con_lai": max(con_lai, 0)},
            )
    khoa = []
    store = luu_tru.luu_tru()
    for nd, k in zip(ds_tep, kieu, strict=True):
        f = await store.luu("doi-tra", nd, k, vung="rieng_tu")
        luu_tru.xoa_neu_hoan_tac(db, f, "rieng_tu")
        khoa.append(f)
    yc = YeuCauDoiTra(
        ma_yeu_cau="DT" + secrets.token_hex(4).upper(),
        don_hang_id=don.id,
        khach_hang_id=khach.id,
        ly_do=ly_do,
        mo_ta=(mo_ta or "").strip() or None,
        anh=khoa,
        trang_thai=TrangThaiDoiTra.cho_duyet,
    )
    yc.chi_tiet = [CtYeuCauDoiTra(ct_don_hang_id=ct_id, so_luong=sl) for ct_id, sl in sorted(gop.items())]
    db.add(yc)
    await db.flush()
    return await chi_tiet_khach(db, khach, yc.ma_yeu_cau)


async def dong_tra(db: AsyncSession, yc_id: int) -> list[DongTraRa]:
    ds = (
        await db.execute(
            select(CtYeuCauDoiTra, CtDonHang)
            .join(CtDonHang, CtDonHang.id == CtYeuCauDoiTra.ct_don_hang_id)
            .where(CtYeuCauDoiTra.yeu_cau_id == yc_id)
            .order_by(CtYeuCauDoiTra.id)
        )
    ).all()
    return [
        DongTraRa(
            ct_don_hang_id=ct.id,
            ten_san_pham=ct.ten_san_pham,
            ten_don_vi=ct.ten_don_vi,
            so_luong_mua=ct.so_luong,
            so_luong_tra=r.so_luong,
            thanh_tien=lam_tron_vnd(ct.thanh_tien * r.so_luong / ct.so_luong),
            so_luong_nhan=r.so_luong_nhan,
        )
        for r, ct in ds
    ]


async def giao_dich_hoan(db: AsyncSession, yc_id: int) -> ThanhToan | None:
    return (
        (
            await db.execute(
                select(ThanhToan)
                .where(ThanhToan.yeu_cau_doi_tra_id == yc_id, ThanhToan.loai == LoaiGiaoDich.hoan_tien)
                .order_by(ThanhToan.id.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )


async def tom_tat(db: AsyncSession, yc: YeuCauDoiTra, ma_don: str) -> DoiTraTom:
    return DoiTraTom(
        ma_yeu_cau=yc.ma_yeu_cau,
        ma_don=ma_don,
        trang_thai=yc.trang_thai,
        ly_do=yc.ly_do,
        huong_xu_ly=yc.huong_xu_ly,
        so_tien_hoan=yc.so_tien_hoan,
        created_at=yc.created_at,
    )


async def _lay_cua_khach(db: AsyncSession, khach: KhachHang, ma_yeu_cau: str, *, khoa: bool = False):
    cau = (
        select(YeuCauDoiTra, DonHang.ma_don)
        .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
        .where(YeuCauDoiTra.ma_yeu_cau == ma_yeu_cau, YeuCauDoiTra.khach_hang_id == khach.id)
    )
    if khoa:
        cau = cau.with_for_update(of=YeuCauDoiTra).execution_options(populate_existing=True)
    dong = (await db.execute(cau)).first()
    if dong is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy yêu cầu đổi trả")
    return dong[0], dong[1]


async def chi_tiet_khach(db: AsyncSession, khach: KhachHang, ma_yeu_cau: str) -> DoiTraChiTietKhach:
    yc, ma_don = await _lay_cua_khach(db, khach, ma_yeu_cau[:20])
    return await dung_chi_tiet(db, yc, ma_don)


async def dung_chi_tiet(db: AsyncSession, yc: YeuCauDoiTra, ma_don: str) -> DoiTraChiTietKhach:
    van_don = await db.scalar(
        select(VanDon.ma_van_don)
        .where(VanDon.yeu_cau_doi_tra_id == yc.id, VanDon.loai == LoaiVanDon.tra_hang)
        .order_by(VanDon.id.desc())
        .limit(1)
    )
    hoan = await giao_dich_hoan(db, yc.id)
    can = (
        hoan is not None
        and hoan.trang_thai == TrangThaiGiaoDich.khoi_tao
        and hoan.cong_thanh_toan in CONG_HOAN_THU_CONG
    )
    return DoiTraChiTietKhach(
        **(await tom_tat(db, yc, ma_don)).model_dump(),
        mo_ta=yc.mo_ta,
        ly_do_tu_choi=yc.ly_do_tu_choi,
        ma_van_don=van_don,
        dong=await dong_tra(db, yc.id),
        anh=[luu_tru.url_ky(k) for k in yc.anh or []],
        can_nhap_tai_khoan_hoan=bool(can),
        da_nhap_tai_khoan_hoan=bool(can and hoan is not None and hoan.thong_tin_nhan_hoan),
    )


async def danh_sach_khach(db: AsyncSession, khach: KhachHang) -> list[DoiTraTom]:
    ds = (
        await db.execute(
            select(YeuCauDoiTra, DonHang.ma_don)
            .join(DonHang, DonHang.id == YeuCauDoiTra.don_hang_id)
            .where(YeuCauDoiTra.khach_hang_id == khach.id)
            .order_by(YeuCauDoiTra.created_at.desc(), YeuCauDoiTra.id.desc())
            .limit(100)
        )
    ).all()
    return [await tom_tat(db, yc, ma) for yc, ma in ds]


async def nhap_tai_khoan_hoan(
    db: AsyncSession, khach: KhachHang, ma_yeu_cau: str, vao: TaiKhoanNhanHoanVao
) -> DoiTraChiTietKhach:
    """Khách đơn COD/tiền mặt cung cấp tài khoản nhận hoàn; chỉ khi giao dịch hoàn đã tạo và chưa xử lý."""
    yc, ma_don = await _lay_cua_khach(db, khach, ma_yeu_cau[:20], khoa=True)
    hoan = await giao_dich_hoan(db, yc.id)
    if hoan is None or hoan.trang_thai != TrangThaiGiaoDich.khoi_tao or hoan.cong_thanh_toan not in CONG_HOAN_THU_CONG:
        raise LoiNghiepVu(
            "CHUYEN_TRANG_THAI_KHONG_HOP_LE", "Chưa đến bước hoàn tiền hoặc đơn không cần tài khoản nhận hoàn"
        )
    hoan.thong_tin_nhan_hoan = json.loads(vao.model_dump_json())  # Admin xem khi hoàn tiền; ẩn danh hóa sau khi xong
    hoan.updated_at = bay_gio_utc()
    await db.flush()
    return await dung_chi_tiet(db, yc, ma_don)


def tien_hoan(cts: list[tuple[CtDonHang, int]]) -> Decimal:
    """`Σ lam_tron(thanh_tien × so_luong_tra / so_luong)` (spec 04 mục 5)."""
    return sum((lam_tron_vnd(ct.thanh_tien * sl / ct.so_luong) for ct, sl in cts), Decimal(0))
