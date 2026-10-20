"""Máy trạng thái đơn hàng (HT06, spec 04 mục 1.1). ĐÂY LÀ NƠI DUY NHẤT được gán `don_hang.trang_thai`
(CLAUDE.md quy tắc 1; có test quét mã nguồn).

Bảng chuyển trạng thái là DỮ LIỆU (`BANG_CHUYEN`, số dòng theo spec 04). Chuyển không có trong bảng, tác nhân không
được phép hoặc điều kiện không thỏa đều bị từ chối. Lịch sử và các tác động kho đi cùng một transaction: lỗi ở bất kỳ
bước nào thì cả lần chuyển bị hoàn tác (hàm này không commit; `Db` commit cuối request).
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc
from app.models.ban_hang import CtDonHang, DonHang, LichSuTrangThai, PhanBoLo, ThanhToan, VanDon, YeuCauDonThuoc
from app.models.enums import (
    HinhThucNhan,
    KenhBan,
    LoaiGiaoDich,
    LoaiSanPham,
    LoaiVanDon,
    PhuongThucThanhToan,
    TrangThaiDon,
    TrangThaiGiaoDich,
    TrangThaiPhanBo,
    TrangThaiThanhToan,
    TrangThaiYeuCauDonThuoc,
)
from app.models.he_thong import NhanVien
from app.models.san_pham import SanPham
from app.modules.ban_hang.so_tien_da_thu import tinh_so_tien, trang_thai_thanh_toan
from app.modules.kho import ton_kho
from app.modules.khuyen_mai.ap_dung import tra_luot_khi_huy
from app.modules.thong_bao import service as thong_bao
from app.tich_hop.van_chuyen import lay_don_vi_van_chuyen

logger = logging.getLogger(__name__)
TT = TrangThaiDon


class LoaiTacNhan(StrEnum):
    khach = "khach"
    duoc_si = "duoc_si"
    kho = "kho"
    he_thong = "he_thong"


NGUON_NGUOI_DUNG = "nguoi_dung"
NGUON_HE_THONG = "he_thong"
NGUON_VAN_CHUYEN = "webhook_van_chuyen"
NGUON_THANH_TOAN = "ipn_thanh_toan"
NGUON_HE_THONG_HOP_LE = frozenset({NGUON_HE_THONG, NGUON_VAN_CHUYEN, NGUON_THANH_TOAN})
VAI_TRO_THEO_TAC_NHAN = {"PHARMACIST": LoaiTacNhan.duoc_si, "WAREHOUSE": LoaiTacNhan.kho}


@dataclass(frozen=True)
class TacNhan:
    """Người/hệ thống gây ra chuyển trạng thái. Khách qua link mã truy cập (vãng lai) có `khach_hang_id = None`."""

    loai: LoaiTacNhan
    khach_hang_id: int | None = None
    nhan_vien_id: int | None = None
    qua_link: bool = False

    @classmethod
    def khach(cls, khach_hang_id: int) -> "TacNhan":
        return cls(LoaiTacNhan.khach, khach_hang_id=khach_hang_id)

    @classmethod
    def khach_qua_link(cls) -> "TacNhan":
        """Khách vãng lai bấm link có mã truy cập đã xác thực ở nơi gọi (KTV07)."""
        return cls(LoaiTacNhan.khach, qua_link=True)

    @classmethod
    def duoc_si(cls, nhan_vien_id: int) -> "TacNhan":
        return cls(LoaiTacNhan.duoc_si, nhan_vien_id=nhan_vien_id)

    @classmethod
    def kho(cls, nhan_vien_id: int) -> "TacNhan":
        return cls(LoaiTacNhan.kho, nhan_vien_id=nhan_vien_id)

    @classmethod
    def he_thong(cls) -> "TacNhan":
        return cls(LoaiTacNhan.he_thong)


async def tac_nhan_tu_nhan_vien(db: AsyncSession, nhan_vien: NhanVien) -> TacNhan:
    """Dược sĩ hoặc nhân viên kho theo mã vai trò; vai trò khác (kể cả Admin) không có dòng nào trong bảng chuyển."""
    from app.models.he_thong import VaiTro

    ma = await db.scalar(select(VaiTro.ma).where(VaiTro.id == nhan_vien.vai_tro_id))
    loai = VAI_TRO_THEO_TAC_NHAN.get(ma or "")
    if loai is None:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Vai trò này không được đổi trạng thái đơn hàng")
    return TacNhan(loai, nhan_vien_id=nhan_vien.id)


@dataclass(frozen=True)
class Chuyen:
    """Một dòng của bảng chuyển trạng thái. `tu = None` là tạo mới."""

    so: tuple[int, ...]
    tu: frozenset[TT] | None
    den: TT
    tac_nhan: frozenset[LoaiTacNhan]
    nguon_he_thong: frozenset[str] = frozenset({NGUON_HE_THONG})
    khach_qua_link: bool = False
    can_ly_do: bool = False
    dieu_kien: tuple[str, ...] = ()


def _t(*trang_thai: TT) -> frozenset[TT]:
    return frozenset(trang_thai)


K, D, N, H = LoaiTacNhan.khach, LoaiTacNhan.duoc_si, LoaiTacNhan.kho, LoaiTacNhan.he_thong
TD = frozenset

BANG_CHUYEN: tuple[Chuyen, ...] = (
    Chuyen((1,), None, TT.cho_xac_nhan, TD({K}), dieu_kien=("online", "cod", "khong_ke_don")),
    Chuyen((2,), None, TT.cho_thanh_toan, TD({K}), dieu_kien=("online", "tt_online", "khong_ke_don")),
    Chuyen((3,), None, TT.cho_khach_xac_nhan, TD({D}), dieu_kien=("co_nhan_vien_tao",)),
    Chuyen((4,), None, TT.da_xac_nhan, TD({D}), dieu_kien=("dien_thoai", "cod", "khong_ke_don")),
    Chuyen((5,), None, TT.cho_thanh_toan, TD({D}), dieu_kien=("dien_thoai", "tt_online", "khong_ke_don")),
    Chuyen((6,), None, TT.hoan_tat, TD({D}), dieu_kien=("tai_quay", "da_thanh_toan")),
    Chuyen(
        (7,),
        _t(TT.cho_khach_xac_nhan),
        TT.da_xac_nhan,
        TD({K}),
        khach_qua_link=True,
        dieu_kien=("truoc_han_xac_nhan", "cod"),
    ),
    Chuyen(
        (8,),
        _t(TT.cho_khach_xac_nhan),
        TT.cho_thanh_toan,
        TD({K}),
        khach_qua_link=True,
        dieu_kien=("truoc_han_xac_nhan", "tt_online"),
    ),
    Chuyen(
        (9,),
        _t(TT.cho_khach_xac_nhan),
        TT.da_huy,
        TD({K, H}),
        khach_qua_link=True,
        dieu_kien=("he_thong_qua_han_xac_nhan",),
    ),
    Chuyen(
        (10,),
        _t(TT.cho_thanh_toan),
        TT.cho_xac_nhan,
        TD({H}),
        frozenset({NGUON_THANH_TOAN}),
        dieu_kien=("khach_tu_dat",),
    ),
    Chuyen(
        (11,), _t(TT.cho_thanh_toan), TT.da_xac_nhan, TD({H}), frozenset({NGUON_THANH_TOAN}), dieu_kien=("duoc_si_tao",)
    ),
    Chuyen(
        (12,),
        _t(TT.cho_thanh_toan),
        TT.da_huy,
        TD({K, H}),
        dieu_kien=("chua_thanh_toan", "he_thong_qua_han_thanh_toan"),
    ),
    Chuyen((13,), _t(TT.cho_xac_nhan), TT.da_xac_nhan, TD({D})),
    Chuyen((14,), _t(TT.cho_xac_nhan, TT.da_xac_nhan), TT.da_huy, TD({K})),
    Chuyen((15,), _t(TT.cho_xac_nhan, TT.da_xac_nhan), TT.da_huy, TD({D}), can_ly_do=True),
    Chuyen((16,), _t(TT.da_xac_nhan), TT.dang_soan_hang, TD({N})),
    Chuyen((17, 18), _t(TT.dang_soan_hang), TT.cho_lay_hang, TD({N})),
    Chuyen((19,), _t(TT.dang_soan_hang, TT.cho_lay_hang), TT.da_huy, TD({D}), can_ly_do=True),
    Chuyen((20,), _t(TT.cho_lay_hang), TT.da_giao, TD({D}), dieu_kien=("nhan_tai_nha_thuoc",)),
    Chuyen((21,), _t(TT.cho_lay_hang), TT.da_huy, TD({H}), dieu_kien=("nhan_tai_nha_thuoc",)),
    Chuyen((22,), _t(TT.cho_lay_hang), TT.dang_giao, TD({H}), frozenset({NGUON_VAN_CHUYEN})),
    Chuyen((23,), _t(TT.dang_giao), TT.da_giao, TD({H}), frozenset({NGUON_VAN_CHUYEN})),
    Chuyen((24,), _t(TT.dang_giao), TT.giao_that_bai, TD({H}), frozenset({NGUON_VAN_CHUYEN})),
    Chuyen((25,), _t(TT.giao_that_bai), TT.dang_giao, TD({H, N}), frozenset({NGUON_VAN_CHUYEN})),
    Chuyen((26,), _t(TT.giao_that_bai), TT.hoan_ve_kho, TD({H}), frozenset({NGUON_VAN_CHUYEN})),
    Chuyen((27,), _t(TT.hoan_ve_kho), TT.da_huy, TD({N})),
    Chuyen((29,), _t(TT.da_giao), TT.hoan_tat, TD({H})),
    Chuyen((30,), None, TT.da_xac_nhan, TD({D}), dieu_kien=("co_nhan_vien_tao", "don_thay_the")),
)
"""Spec 04 mục 1.1. Dòng 28 (yêu cầu đổi trả) không đổi trạng thái đơn nên không có ở đây."""


def cac_cap_hop_le() -> set[tuple[TT | None, TT]]:
    """Mọi cặp (từ, đến) có trong bảng (None = tạo mới), để test và giao diện dùng chung."""
    return {(tu, c.den) for c in BANG_CHUYEN for tu in (c.tu or {None})}


def _loi_trang_thai(thong_diep: str, **chi_tiet) -> LoiNghiepVu:
    return LoiNghiepVu("CHUYEN_TRANG_THAI_KHONG_HOP_LE", thong_diep, chi_tiet=chi_tiet or None)


# --- Điều kiện kèm theo (cột "Điều kiện" của bảng chuyển) ---


async def _co_thuoc_ke_don(db: AsyncSession, don: DonHang) -> bool:
    return bool(
        await db.scalar(
            select(
                exists().where(
                    CtDonHang.don_hang_id == don.id,
                    CtDonHang.san_pham_id == SanPham.id,
                    SanPham.loai_san_pham == LoaiSanPham.thuoc_ke_don,
                )
            )
        )
    )


async def _kiem_tra_dieu_kien(
    db: AsyncSession, don: DonHang, chuyen: Chuyen, tac_nhan: TacNhan, bay_gio: datetime
) -> None:
    he_thong = tac_nhan.loai == LoaiTacNhan.he_thong
    for dk in chuyen.dieu_kien:
        loi: str | None = None
        match dk:
            case "online":
                loi = None if don.kenh_ban == KenhBan.online else "Đơn không thuộc kênh online"
            case "dien_thoai":
                loi = None if don.kenh_ban == KenhBan.dien_thoai else "Đơn không thuộc kênh điện thoại"
            case "tai_quay":
                loi = None if don.kenh_ban == KenhBan.tai_quay else "Đơn không thuộc kênh tại quầy"
            case "cod":
                loi = None if don.phuong_thuc_tt == PhuongThucThanhToan.cod else "Chỉ áp dụng cho đơn thanh toán COD"
            case "tt_online":
                ok = don.phuong_thuc_tt in (PhuongThucThanhToan.vnpay, PhuongThucThanhToan.momo)
                loi = None if ok else "Chỉ áp dụng cho đơn thanh toán online (VNPay/MoMo)"
            case "khong_ke_don":
                if await _co_thuoc_ke_don(db, don):
                    loi = "Đơn có thuốc kê đơn không đi kênh này"
            case "co_nhan_vien_tao":
                loi = None if don.nhan_vien_tao_id == tac_nhan.nhan_vien_id else "Đơn phải ghi nhận dược sĩ tạo"
            case "da_thanh_toan":
                ok = don.trang_thai_tt == TrangThaiThanhToan.da_thanh_toan
                loi = None if ok else "Bán tại quầy phải thanh toán đủ trước khi hoàn tất"
            case "truoc_han_xac_nhan":
                if don.han_xac_nhan is not None and bay_gio > don.han_xac_nhan:
                    loi = "Đã quá hạn xác nhận"
            case "he_thong_qua_han_xac_nhan":
                if he_thong and (don.han_xac_nhan is None or bay_gio <= don.han_xac_nhan):
                    loi = "Chưa quá hạn xác nhận"
            case "chua_thanh_toan":
                if don.trang_thai_tt == TrangThaiThanhToan.da_thanh_toan:
                    loi = "Đơn đã có thanh toán thành công"
            case "he_thong_qua_han_thanh_toan":
                if he_thong and (don.han_thanh_toan is None or bay_gio <= don.han_thanh_toan):
                    loi = "Chưa quá hạn thanh toán"
            case "khach_tu_dat":
                loi = None if don.nhan_vien_tao_id is None else "Đơn do dược sĩ tạo"
            case "duoc_si_tao":
                loi = None if don.nhan_vien_tao_id is not None else "Đơn do khách tự đặt"
            case "don_thay_the":
                ok = don.don_hang_goc_id is not None and don.tong_tien == 0
                loi = None if ok else "Đơn thay thế phải trỏ về đơn gốc và có tổng tiền 0"
            case "nhan_tai_nha_thuoc":
                ok = don.hinh_thuc_nhan == HinhThucNhan.nhan_tai_nha_thuoc
                loi = None if ok else "Chỉ áp dụng cho đơn nhận tại nhà thuốc"
            case _:
                raise AssertionError(f"Điều kiện chưa cài: {dk}")
        if loi:
            raise _loi_trang_thai(loi, dieu_kien=dk)


# --- Tác động (hook) trong cùng transaction ---

Hook = Callable[[AsyncSession, DonHang, TacNhan], Awaitable[None]]
HOOK_THEO_DONG: dict[int, list[Hook]] = {}


def dang_ky_hook(so_dong: int, hook: Hook) -> None:
    """Task sau (thanh toán, vận chuyển, thông báo, mã giảm giá...) gắn tác động vào một dòng của bảng chuyển."""
    HOOK_THEO_DONG.setdefault(so_dong, []).append(hook)


async def _phan_bo(db: AsyncSession, don: DonHang, trang_thai: TrangThaiPhanBo) -> list[PhanBoLo]:
    return list(
        (
            await db.execute(
                select(PhanBoLo)
                .join(CtDonHang, CtDonHang.id == PhanBoLo.ct_don_hang_id)
                .where(CtDonHang.don_hang_id == don.id, PhanBoLo.trang_thai == trang_thai)
                .order_by(PhanBoLo.id)
            )
        ).scalars()
    )


def _chung_tu(don: DonHang, tac_nhan: TacNhan) -> ton_kho.ChungTu:
    return ton_kho.ChungTu("don_hang", don.id, tac_nhan.nhan_vien_id)


async def _nha_hang_giu(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Hủy khi hàng mới chỉ được giữ: nhả giữ, giảm `so_luong_giu`."""
    await ton_kho.nha_giu(db, await _phan_bo(db, don, TrangThaiPhanBo.dang_giu))


async def _hoan_nhap_hang_da_xuat(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Hủy khi hàng đã trừ kho nhưng chưa rời kho: hoàn nhập đúng lô, thẻ kho `hoan_nhap`."""
    await ton_kho.hoan_nhap(db, await _phan_bo(db, don, TrangThaiPhanBo.da_xuat), _chung_tu(don, tac_nhan))


async def _xuat_kho(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Bắt đầu soạn hàng: chốt lô, trừ tồn và giữ, thẻ kho `xuat_ban`.

    Mỗi dòng phải còn giữ ĐỦ hàng: lô hết hạn/thu hồi mà không phân bổ lại được sẽ nhả phân bổ (HT01, thu hồi), khi đó
    xuất kho rỗng sẽ giao hàng mà không trừ tồn, không ghi thẻ kho (bất biến 5, spec 04 mục 3.2)."""
    giu = await _phan_bo(db, don, TrangThaiPhanBo.dang_giu)
    da_giu: dict[int, int] = {}
    for p in giu:
        da_giu[p.ct_don_hang_id] = da_giu.get(p.ct_don_hang_id, 0) + p.so_luong_co_so
    thieu = [
        c.id
        for c in (await db.execute(select(CtDonHang).where(CtDonHang.don_hang_id == don.id))).scalars()
        if da_giu.get(c.id, 0) != c.so_luong * c.he_so
    ]
    if thieu:
        raise _loi_trang_thai(
            "Đơn chưa giữ đủ hàng (lô đã hết hạn hoặc bị thu hồi), không thể soạn hàng; hãy hủy đơn hoặc liên hệ khách",
            dieu_kien="du_hang_giu",
            dong_thieu=thieu,
        )
    await ton_kho.xuat_theo_phan_bo(db, giu, _chung_tu(don, tac_nhan))


async def _danh_dau_da_thanh_toan(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Dòng 10, 11: IPN thành công thì đơn đã thanh toán (giao dịch `thanh_toan` do HT04 ghi cùng transaction)."""
    don.trang_thai_tt = TrangThaiThanhToan.da_thanh_toan


async def _tao_hoan_tien_khi_huy(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Hủy đơn đã thu tiền (dòng 14, 15, 19, 21, 27): tạo giao dịch `hoan_tien` `khoi_tao` cho phần tiền đã thu mà chưa
    có giao dịch hoàn nào bao phủ (tính từ sổ tiền, không dựa vào `trang_thai_tt`: khách có thể đã trả hai lần và một
    khoản thừa đang chờ hoàn). Mỗi giao dịch hoàn trỏ về MỘT giao dịch thanh toán gốc và không vượt phần còn hoàn
    được của giao dịch đó (cổng chỉ cho hoàn tối đa số đã trả). Admin xác nhận ở AD17."""
    if don.phuong_thuc_tt is None or don.tong_tien <= 0:  # đơn thay thế 0đ (dòng 30): không có tiền để hoàn
        return
    so = await tinh_so_tien(db, don.id)
    con = so.con_phai_hoan
    if con > 0:
        goc_ds = (
            (
                await db.execute(
                    select(ThanhToan)
                    .where(
                        ThanhToan.don_hang_id == don.id,
                        ThanhToan.loai == LoaiGiaoDich.thanh_toan,
                        ThanhToan.trang_thai == TrangThaiGiaoDich.thanh_cong,
                    )
                    .order_by(ThanhToan.id)
                )
            )
            .scalars()
            .all()
        )
        da_hoan_theo_goc = dict(
            (
                await db.execute(
                    select(ThanhToan.thanh_toan_goc_id, func.sum(ThanhToan.so_tien))
                    .where(
                        ThanhToan.don_hang_id == don.id,
                        ThanhToan.loai == LoaiGiaoDich.hoan_tien,
                        ThanhToan.trang_thai.in_((TrangThaiGiaoDich.khoi_tao, TrangThaiGiaoDich.thanh_cong)),
                        ThanhToan.thanh_toan_goc_id.is_not(None),
                    )
                    .group_by(ThanhToan.thanh_toan_goc_id)
                )
            ).all()
        )
        for goc in goc_ds:
            if con <= 0:
                break
            duoc = goc.so_tien - Decimal(da_hoan_theo_goc.get(goc.id) or 0)
            if duoc <= 0:
                continue
            so_hoan = min(con, duoc)
            db.add(
                ThanhToan(
                    don_hang_id=don.id,
                    loai=LoaiGiaoDich.hoan_tien,
                    cong_thanh_toan=goc.cong_thanh_toan,
                    so_tien=so_hoan,
                    trang_thai=TrangThaiGiaoDich.khoi_tao,
                    thanh_toan_goc_id=goc.id,
                    ghi_chu=f"Hoàn tiền do hủy đơn {don.ma_don}",
                )
            )
            con -= so_hoan
        await db.flush()
    don.trang_thai_tt = trang_thai_thanh_toan(don, await tinh_so_tien(db, don.id))


async def _huy_van_don_khi_huy(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Dòng 19 (hủy khi hàng chưa rời kho): hủy vận đơn giao hàng còn hiệu lực ở đơn vị vận chuyển, nếu không
    shipper vẫn tới lấy hàng đã hoàn nhập vào kho. Đơn vị vận chuyển từ chối (đã lấy hàng) hoặc không phản hồi thì
    KHÔNG hủy đơn: ném lỗi để cả giao dịch hoàn tác (hàng đã thực sự rời kho thì đi theo luồng giao thất bại/hoàn
    hàng). Chạy SAU các hook kho để lỗi DB không để lại vận đơn đã hủy mà đơn còn sống."""
    van_don = (
        await db.execute(
            select(VanDon)
            .where(
                VanDon.don_hang_id == don.id,
                VanDon.loai == LoaiVanDon.giao_hang,
                VanDon.ma_van_don.is_not(None),
                VanDon.trang_thai_doi_tac.is_distinct_from("cancel"),
            )
            .order_by(VanDon.id.desc())
            .limit(1)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if van_don is None or van_don.ma_van_don is None:
        return
    don_vi = lay_don_vi_van_chuyen()
    if van_don.don_vi_van_chuyen != don_vi.ten:
        logger.warning(
            "Vận đơn %s của %s, adapter hiện tại là %s", van_don.ma_van_don, van_don.don_vi_van_chuyen, don_vi.ten
        )
        return
    try:
        await don_vi.huy_van_don(van_don.ma_van_don)
    except Exception as e:  # noqa: BLE001  lỗi đối tác bất kỳ: không hủy đơn khi chưa chắc vận đơn đã hủy
        logger.warning("Hủy vận đơn %s thất bại cho đơn %s", van_don.ma_van_don, don.ma_don, exc_info=True)
        raise LoiNghiepVu(
            "LOI_DOI_TAC",
            "Không hủy được vận đơn ở đơn vị vận chuyển (có thể shipper đã lấy hàng), đơn chưa bị hủy",
        ) from e
    van_don.trang_thai_doi_tac = "cancel"
    van_don.updated_at = bay_gio_utc()


async def _ghi_nhan_cod(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Dòng 23: COD giao thành công thì ghi giao dịch `thanh_toan` cod thành công và đơn `da_thanh_toan`."""
    if don.phuong_thuc_tt != PhuongThucThanhToan.cod or don.trang_thai_tt != TrangThaiThanhToan.chua_thanh_toan:
        return
    db.add(
        ThanhToan(
            don_hang_id=don.id,
            loai=LoaiGiaoDich.thanh_toan,
            cong_thanh_toan=PhuongThucThanhToan.cod,
            so_tien=don.tong_tien,
            trang_thai=TrangThaiGiaoDich.thanh_cong,
            ghi_chu="Thu tiền khi giao hàng",
        )
    )
    don.trang_thai_tt = TrangThaiThanhToan.da_thanh_toan


async def _danh_dau_don_thuoc_da_su_dung(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Dòng 16: thuốc thực sự xuất kho thì yêu cầu đơn thuốc liên kết hết dùng lại được (spec 04 mục 1.2 dòng 9)."""
    if don.yeu_cau_don_thuoc_id is not None:
        yc = await db.get(YeuCauDonThuoc, don.yeu_cau_don_thuoc_id, with_for_update=True, populate_existing=True)
        if yc is not None:
            yc.da_su_dung = True


async def _tra_yeu_cau_don_thuoc(db: AsyncSession, don: DonHang, tac_nhan: TacNhan) -> None:
    """Đơn từ đơn thuốc bị hủy/hết hạn TRƯỚC khi xuất kho: yêu cầu quay lại `dang_tu_van` để tạo lại đơn (dòng 8)."""
    if don.yeu_cau_don_thuoc_id is None:
        return
    yc = await db.get(YeuCauDonThuoc, don.yeu_cau_don_thuoc_id, with_for_update=True, populate_existing=True)
    if yc is not None and not yc.da_su_dung and yc.trang_thai == TrangThaiYeuCauDonThuoc.da_tao_don:
        yc.trang_thai = TrangThaiYeuCauDonThuoc.dang_tu_van
        yc.khoa_luc = bay_gio_utc()  # tính lại thời gian khóa từ lúc đơn hủy
        yc.updated_at = yc.khoa_luc


dang_ky_hook(23, _ghi_nhan_cod)
for _so in (10, 11):
    dang_ky_hook(_so, _danh_dau_da_thanh_toan)
# Khóa mã giảm giá TRƯỚC khóa lô: đặt đơn khóa theo thứ tự này, hủy đơn khóa ngược lại sẽ deadlock
for _so in (9, 12, 14, 15, 19, 21, 27):
    dang_ky_hook(_so, tra_luot_khi_huy)
for _so in (9, 12, 14, 15):
    dang_ky_hook(_so, _nha_hang_giu)
dang_ky_hook(16, _xuat_kho)
dang_ky_hook(16, _danh_dau_don_thuoc_da_su_dung)
for _so in (9, 12, 14, 15, 19, 21, 27):
    dang_ky_hook(_so, _tra_yeu_cau_don_thuoc)
for _so in (14, 15, 19, 21, 27):
    dang_ky_hook(_so, _tao_hoan_tien_khi_huy)
for _so in (19, 21):
    dang_ky_hook(_so, _nha_hang_giu)
    dang_ky_hook(_so, _hoan_nhap_hang_da_xuat)
dang_ky_hook(19, _huy_van_don_khi_huy)


# --- Điểm vào duy nhất ---


def _tim_dong(tu: TT | None, den: TT, tac_nhan: TacNhan, nguon: str, so_dong: int | None = None) -> Chuyen:
    ung_vien = [
        c
        for c in BANG_CHUYEN
        if c.den == den and (tu is None if c.tu is None else tu in c.tu) and (so_dong is None or so_dong in c.so)
    ]
    if not ung_vien:
        tu_ten = "tạo mới" if tu is None else tu.value
        raise _loi_trang_thai(f"Không thể chuyển đơn từ {tu_ten} sang {den.value}", tu=tu and tu.value, den=den.value)
    if tac_nhan.loai == LoaiTacNhan.he_thong:
        if nguon not in NGUON_HE_THONG_HOP_LE:
            raise _loi_trang_thai("Nguồn của hệ thống không hợp lệ", nguon=nguon)
    elif nguon != NGUON_NGUOI_DUNG:
        raise _loi_trang_thai("Tác nhân là người dùng thì nguồn phải là nguoi_dung", nguon=nguon)
    cho_phep = [c for c in ung_vien if tac_nhan.loai in c.tac_nhan]
    if not cho_phep:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Bạn không được thực hiện chuyển trạng thái này")
    if tac_nhan.loai == LoaiTacNhan.he_thong:
        cho_phep = [c for c in cho_phep if nguon in c.nguon_he_thong]
        if not cho_phep:
            raise _loi_trang_thai("Nguồn này không được thực hiện chuyển trạng thái này", nguon=nguon)
    return cho_phep[0]


def _kiem_tra_tac_nhan_khach(don: DonHang | None, chuyen: Chuyen, tac_nhan: TacNhan) -> None:
    if tac_nhan.loai != LoaiTacNhan.khach:
        return
    if tac_nhan.qua_link:
        if not chuyen.khach_qua_link:
            raise LoiNghiepVu("KHONG_CO_QUYEN", "Link mã truy cập không dùng được cho thao tác này")
        return
    if tac_nhan.khach_hang_id is None:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Cần đăng nhập")
    if don is not None and don.khach_hang_id != tac_nhan.khach_hang_id:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy đơn hàng")  # đơn của người khác là 404 (quy tắc 3)


async def _ghi(
    db: AsyncSession,
    don: DonHang,
    chuyen: Chuyen,
    tu: TT | None,
    tac_nhan: TacNhan,
    nguon: str,
    ghi_chu: str | None,
) -> LichSuTrangThai:
    bay_gio = bay_gio_utc()
    don.trang_thai = chuyen.den  # nơi duy nhất trong mã nguồn được gán trạng thái đơn
    don.updated_at = bay_gio
    if chuyen.den == TT.da_huy and ghi_chu:
        don.ly_do_huy = ghi_chu
    if chuyen.den == TT.da_xac_nhan and tu == TT.cho_xac_nhan:
        don.nhan_vien_xac_nhan_id = tac_nhan.nhan_vien_id
    ls = LichSuTrangThai(
        don_hang_id=don.id,
        tu_trang_thai=tu,
        den_trang_thai=chuyen.den,
        nhan_vien_id=tac_nhan.nhan_vien_id,
        khach_hang_id=tac_nhan.khach_hang_id,
        nguon=nguon,
        ghi_chu=ghi_chu,
    )
    db.add(ls)
    await db.flush()
    for so in chuyen.so:
        for hook in HOOK_THEO_DONG.get(so, []):
            await hook(db, don, tac_nhan)
    if tu is not None:  # đơn mới tạo đã có thông báo riêng ở nơi tạo
        await _bao_khach_trang_thai_don(db, don, chuyen.den, tac_nhan)
    await db.flush()
    return ls


TIN_NHAN_TRANG_THAI: dict[TT, str] = {
    TT.da_xac_nhan: "đã được nhà thuốc xác nhận",
    TT.cho_lay_hang: "đã sẵn sàng để bạn đến nhận",
    TT.dang_giao: "đang được giao",
    TT.da_giao: "đã giao thành công",
    TT.giao_that_bai: "giao không thành công",
    TT.da_huy: "đã bị hủy",
}


async def _bao_khach_trang_thai_don(db: AsyncSession, don: DonHang, den: TT, tac_nhan: TacNhan) -> None:
    """KTV13: báo khách có tài khoản khi đơn đổi trạng thái đáng chú ý (trừ thay đổi do chính khách làm)."""
    if don.khach_hang_id is None or tac_nhan.loai == LoaiTacNhan.khach or den not in TIN_NHAN_TRANG_THAI:
        return
    await thong_bao.gui_cho_khach(
        db,
        don.khach_hang_id,
        loai="don_hang",
        tieu_de=f"Đơn {don.ma_don} {TIN_NHAN_TRANG_THAI[den]}",
        lien_ket=f"/tai-khoan/don-hang/{don.ma_don}",
    )


def _chuan_ghi_chu(chuyen: Chuyen, ghi_chu: str | None) -> str | None:
    ghi_chu = (ghi_chu or "").strip() or None
    if chuyen.can_ly_do and ghi_chu is None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "ghi_chu", "loi": "Bắt buộc nhập lý do"}],
        )
    return ghi_chu


async def chuyen_trang_thai(
    db: AsyncSession,
    don: DonHang,
    den: TrangThaiDon,
    tac_nhan: TacNhan,
    nguon: str,
    ghi_chu: str | None = None,
) -> LichSuTrangThai:
    """Chuyển đơn đã có sang `den`. Khóa dòng đơn rồi đọc lại trạng thái mới nhất (hai người cùng bấm thì người sau
    nhận `CHUYEN_TRANG_THAI_KHONG_HOP_LE`, tác động kho không chạy hai lần)."""
    await db.execute(
        select(DonHang.id).where(DonHang.id == don.id).with_for_update().execution_options(populate_existing=True)
    )
    await db.refresh(don)
    tu = don.trang_thai
    chuyen = _tim_dong(tu, den, tac_nhan, nguon)
    _kiem_tra_tac_nhan_khach(don, chuyen, tac_nhan)
    ghi_chu = _chuan_ghi_chu(chuyen, ghi_chu)
    await _kiem_tra_dieu_kien(db, don, chuyen, tac_nhan, bay_gio_utc())
    return await _ghi(db, don, chuyen, tu, tac_nhan, nguon, ghi_chu)


async def khoi_tao_trang_thai(
    db: AsyncSession,
    don: DonHang,
    den: TrangThaiDon,
    tac_nhan: TacNhan,
    nguon: str,
    ghi_chu: str | None = None,
    so_dong: int | None = None,
) -> LichSuTrangThai:
    """Tạo đơn mới (dòng "tạo mới" 1 đến 6 và 30; `so_dong` chọn dòng khi nhiều dòng cùng đích, như 4 và 30).
    `don` là `DonHang` chưa có `trang_thai` và chưa add vào phiên, các dòng hàng gắn qua `don.chi_tiet`;
    hàm lưu đơn cùng dòng hàng rồi kiểm tra "không thuốc kê đơn" bằng SQL."""
    chuyen = _tim_dong(None, den, tac_nhan, nguon, so_dong)
    _kiem_tra_tac_nhan_khach(None, chuyen, tac_nhan)
    if tac_nhan.loai == LoaiTacNhan.khach and don.khach_hang_id != tac_nhan.khach_hang_id:
        raise LoiNghiepVu("KHONG_CO_QUYEN", "Đơn phải thuộc về chính khách đặt hàng")
    ghi_chu = _chuan_ghi_chu(chuyen, ghi_chu)
    if tac_nhan.nhan_vien_id is not None:
        don.nhan_vien_tao_id = tac_nhan.nhan_vien_id
    don.trang_thai = den  # tạo mới: cần để lưu được dòng đơn, kiểm tra điều kiện ngay sau đó
    db.add(don)
    await db.flush()
    await _kiem_tra_dieu_kien(db, don, chuyen, tac_nhan, bay_gio_utc())
    return await _ghi(db, don, chuyen, None, tac_nhan, nguon, ghi_chu)
