"""Dịch vụ tồn kho: nơi DUY NHẤT được đổi `so_luong_ton`, `so_luong_giu`, `so_luong_biet_tru` (CLAUDE.md quy tắc 2).

Mọi hàm nhận `db` đang trong transaction, tự khóa các lô liên quan bằng `SELECT ... FOR UPDATE` theo id tăng dần rồi mới
tính toán, và ghi `bien_dong_kho` trong cùng transaction (spec 04 mục 3).

Hàm lỗi nghiệp vụ (`LoiNghiepVu`) ném TRƯỚC khi đổi bất cứ số liệu nào; người gọi vẫn phải để transaction rollback.
Lỗi lập trình (số lượng không phải số nguyên dương...) là `TypeError`/`ValueError`.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.thoi_gian import bay_gio_utc, hom_nay_vn
from app.models.ban_hang import CtDonHang, PhanBoLo
from app.models.enums import KhuTon, LoaiBienDong, TrangThaiLo, TrangThaiPhanBo
from app.models.kho import BienDongKho, LoThuoc
from app.models.san_pham import SanPham


@dataclass(frozen=True)
class ChungTu:
    """Chứng từ gây ra biến động: `loai` là tên bảng (`phieu_nhap`, `don_hang`...). `nhan_vien_id` None = hệ thống."""

    loai: str
    id: int
    nhan_vien_id: int | None = None


async def khoa_cac_lo(db: AsyncSession, lo_ids: Iterable[int]) -> list[LoThuoc]:
    """Khóa các lô (FOR UPDATE) theo id tăng dần và trả về theo thứ tự đó.

    Thứ tự cố định giữa mọi giao dịch để hai giao dịch khóa chung nhiều lô không bao giờ chờ vòng tròn (deadlock).
    Các đối tượng đã nạp từ trước được làm mới theo dòng vừa khóa, nên số liệu tồn luôn là bản đã commit mới nhất.
    """
    ids = sorted(set(lo_ids))
    if not ids:
        return []
    truy_van = (
        select(LoThuoc)
        .where(LoThuoc.id.in_(ids))
        .order_by(LoThuoc.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    lo_thuoc = list((await db.execute(truy_van)).scalars())
    thieu = set(ids) - {lo.id for lo in lo_thuoc}
    if thieu:
        raise LookupError(f"Không tìm thấy lô: {sorted(thieu)}")
    return lo_thuoc


async def kiem_tra_san_pham_chua_xoa(db: AsyncSession, lo: LoThuoc) -> None:
    """Từ chối TĂNG tồn của lô thuộc sản phẩm đã xóa mềm. Gọi SAU khi đã khóa lô (`khoa_cac_lo`).

    Xóa sản phẩm khóa mọi lô của nó `FOR UPDATE` rồi mới kiểm tra "không còn hàng". Nhập kho đã khóa lô thì hoặc thắng
    (xóa chờ rồi thấy tồn > 0 và bị từ chối), hoặc chờ xóa commit rồi đọc được `deleted_at` ở đây và bị từ chối; không
    có đường thứ ba để tồn mắc kẹt dưới sản phẩm đã xóa. Mọi hàm tăng tồn từ 0 (nhập kho, hoàn nhập đổi trả, điều chỉnh
    tăng, ra khỏi biệt trữ) phải gọi hàm này; hàm chỉ giảm hay chuyển khu thì không cần vì lô đang có hàng chặn xóa.
    """
    da_xoa = await db.scalar(select(SanPham.deleted_at).where(SanPham.id == lo.san_pham_id))
    if da_xoa is not None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Sản phẩm của lô này đã bị xóa")


def _kiem_tra_so_luong(so_luong: int) -> None:
    if isinstance(so_luong, bool) or not isinstance(so_luong, int):
        raise TypeError(f"so_luong phải là số nguyên, nhận {type(so_luong).__name__}")
    if so_luong <= 0:
        raise ValueError("so_luong phải lớn hơn 0")


async def nhap_kho(
    db: AsyncSession, lo: LoThuoc, so_luong: int, chung_tu: ChungTu, luc: datetime | None = None
) -> BienDongKho:
    """Cộng `so_luong` (đơn vị cơ sở) vào tồn kho bán của lô và ghi thẻ kho `nhap_kho`.

    `luc`: thời điểm ghi thẻ kho, mặc định là bây giờ; chỉ truyền khi nhập lại dữ liệu cũ (seed, chuyển đổi) để thẻ
    kho mang ngày của chứng từ gốc, báo cáo nhập - xuất - tồn theo kỳ mới khớp.

    Hàm khóa MỘT lô. Phiếu nhập nhiều dòng phải gọi `khoa_cac_lo` với TẤT CẢ id lô trước (khóa theo id tăng dần) rồi mới
    gọi `nhap_kho` từng dòng, nếu không hai phiếu khóa các lô theo thứ tự ngược nhau có thể deadlock. Tính lại giá nhập
    bình quân gia quyền (KHO02) và kiểm tra trạng thái lô (khóa, thu hồi) thuộc dịch vụ phiếu nhập ở T3.1.
    """
    _kiem_tra_so_luong(so_luong)
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    await kiem_tra_san_pham_chua_xoa(db, lo_khoa)
    lo_khoa.so_luong_ton += so_luong
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = BienDongKho(
        lo_id=lo_khoa.id,
        loai=LoaiBienDong.nhap_kho,
        khu=KhuTon.kho_ban,
        so_luong=so_luong,
        ton_sau=lo_khoa.so_luong_ton,
        chung_tu_loai=chung_tu.loai,
        chung_tu_id=chung_tu.id,
        nhan_vien_id=chung_tu.nhan_vien_id,
        **({"created_at": luc} if luc is not None else {}),
    )
    db.add(bien_dong)
    await db.flush()
    return bien_dong


def _the_kho(
    lo: LoThuoc, loai: LoaiBienDong, khu: KhuTon, so_luong: int, ton_sau: int, chung_tu: ChungTu
) -> BienDongKho:
    return BienDongKho(
        lo_id=lo.id,
        loai=loai,
        khu=khu,
        so_luong=so_luong,
        ton_sau=ton_sau,
        chung_tu_loai=chung_tu.loai,
        chung_tu_id=chung_tu.id,
        nhan_vien_id=chung_tu.nhan_vien_id,
    )


def _het_hang(lo: LoThuoc, con_lai: int, viec: str) -> LoiNghiepVu:
    return LoiNghiepVu(
        "HET_HANG",
        f"Lô {lo.so_lo} chỉ còn {con_lai} khả dụng, không đủ để {viec}",
        chi_tiet={"lo_id": lo.id, "con_lai": con_lai},
    )


# --- Giữ hàng theo FEFO (spec 04 mục 3.1) -----------------------------------------------------------------------------


@dataclass(frozen=True)
class YeuCauGiu:
    """Một dòng cần giữ: `so_luong_co_so` theo đơn vị cơ sở của `san_pham_id`."""

    ct_don_hang_id: int
    san_pham_id: int
    so_luong_co_so: int


def _duoc_ban(lo: LoThuoc, hom_nay, cho_phep_can_han: bool) -> bool:
    cho_phep = {TrangThaiLo.dang_ban, TrangThaiLo.can_han} if cho_phep_can_han else {TrangThaiLo.dang_ban}
    # So hạn với hôm nay (giờ VN) chứ không tin nhãn: job HT01 chỉ chạy 00:05 mỗi ngày.
    return lo.trang_thai in cho_phep and lo.han_su_dung > hom_nay and lo.so_luong_ton - lo.so_luong_giu > 0


async def giu_hang_nhieu(
    db: AsyncSession, yeu_cau: Sequence[YeuCauGiu], *, cho_phep_can_han: bool = False
) -> dict[int, list[PhanBoLo]]:
    """Giữ hàng cho nhiều dòng đơn trong MỘT lần khóa: tạo `phan_bo_lo` `dang_giu` và tăng `so_luong_giu`, KHÔNG ghi
    thẻ kho (chưa đổi tồn thật). Kết quả: `ct_don_hang_id` -> các phân bổ theo thứ tự FEFO.

    Lô ứng viên của MỌI dòng được khóa cùng lúc theo id tăng dần (không theo thứ tự FEFO), nên hai đơn có các dòng
    khác thứ tự nhau không thể chờ vòng tròn; FEFO chỉ quyết định lô nào được lấy trước SAU khi đã khóa. Việc chia lô
    được tính trọn trong bộ nhớ trước, thiếu hàng ở bất kỳ dòng nào thì ném `HET_HANG` mà chưa đổi gì.
    `cho_phep_can_han`: bán tại quầy dùng thêm lô `can_han` (spec 04 mục 1.4).
    """
    for y in yeu_cau:
        _kiem_tra_so_luong(y.so_luong_co_so)
    if not yeu_cau:
        return {}
    hom_nay = hom_nay_vn()
    san_pham_ids = sorted({y.san_pham_id for y in yeu_cau})
    ung_vien = (await db.execute(select(LoThuoc.id).where(LoThuoc.san_pham_id.in_(san_pham_ids)))).scalars().all()
    lo_thuoc = await khoa_cac_lo(db, ung_vien)
    theo_san_pham: dict[int, list[LoThuoc]] = {sp: [] for sp in san_pham_ids}
    for lo in lo_thuoc:
        if _duoc_ban(lo, hom_nay, cho_phep_can_han):
            theo_san_pham[lo.san_pham_id].append(lo)
    for danh_sach in theo_san_pham.values():
        danh_sach.sort(key=lambda lo: (lo.han_su_dung, lo.id))

    kha_dung = {lo.id: lo.so_luong_ton - lo.so_luong_giu for lo in lo_thuoc}
    ke_hoach: list[tuple[YeuCauGiu, list[tuple[LoThuoc, int]]]] = []
    for y in yeu_cau:
        can, chia = y.so_luong_co_so, []
        for lo in theo_san_pham[y.san_pham_id]:
            if can == 0:
                break
            lay = min(can, kha_dung[lo.id])
            if lay > 0:
                chia.append((lo, lay))
                kha_dung[lo.id] -= lay
                can -= lay
        if can > 0:
            con_lai = _con_lai_san_pham(theo_san_pham[y.san_pham_id], yeu_cau, y)
            ten = await db.scalar(select(SanPham.ten).where(SanPham.id == y.san_pham_id)) or f"#{y.san_pham_id}"
            raise LoiNghiepVu(
                "HET_HANG",
                f"Sản phẩm {ten} chỉ còn {con_lai}",
                chi_tiet={"san_pham_id": y.san_pham_id, "con_lai": con_lai},
            )
        ke_hoach.append((y, chia))

    ket_qua: dict[int, list[PhanBoLo]] = {}
    bay_gio = bay_gio_utc()
    for y, chia in ke_hoach:
        phan_bo = ket_qua.setdefault(y.ct_don_hang_id, [])
        for lo, so_luong in chia:
            lo.so_luong_giu += so_luong
            lo.updated_at = bay_gio
            pb = PhanBoLo(
                ct_don_hang_id=y.ct_don_hang_id,
                lo_id=lo.id,
                so_luong_co_so=so_luong,
                gia_von=lo.gia_nhap,
                trang_thai=TrangThaiPhanBo.dang_giu,
            )
            db.add(pb)
            phan_bo.append(pb)
    await db.flush()
    return ket_qua


def _con_lai_san_pham(lo_thuoc: list[LoThuoc], yeu_cau: Sequence[YeuCauGiu], dong_loi: YeuCauGiu) -> int:
    """Số lượng khả dụng của sản phẩm ở thời điểm dòng lỗi (đã trừ phần các dòng đứng trước trong cùng yêu cầu)."""
    tong = sum(lo.so_luong_ton - lo.so_luong_giu for lo in lo_thuoc)
    da_lay = 0
    for y in yeu_cau:
        if y is dong_loi:
            break
        if y.san_pham_id == dong_loi.san_pham_id:
            da_lay += y.so_luong_co_so
    return max(tong - da_lay, 0)


async def giu_hang(
    db: AsyncSession, ct_don_hang: CtDonHang, so_luong_co_so: int, cho_phep_can_han: bool = False
) -> list[PhanBoLo]:
    """Giữ hàng cho MỘT dòng đơn (xem `giu_hang_nhieu`; đơn nhiều dòng phải dùng hàm đó để khóa một lượt)."""
    ket_qua = await giu_hang_nhieu(
        db,
        [YeuCauGiu(ct_don_hang.id, ct_don_hang.san_pham_id, so_luong_co_so)],
        cho_phep_can_han=cho_phep_can_han,
    )
    return ket_qua[ct_don_hang.id]


# --- Nhả, xuất, hoàn nhập theo phân bổ ---


async def _khoa_phan_bo(
    db: AsyncSession, phan_bo: PhanBoLo | Sequence[PhanBoLo], trang_thai_can: TrangThaiPhanBo, viec: str
) -> tuple[list[PhanBoLo], dict[int, LoThuoc]]:
    """Khóa các lô của phân bổ (id tăng dần), nạp lại trạng thái MỚI NHẤT của từng phân bổ rồi kiểm tra phải đang ở
    `trang_thai_can`. Mọi thay đổi phân bổ đều khóa lô trước nên đọc lại sau khóa là đọc đúng bản đã commit."""
    ds = [phan_bo] if isinstance(phan_bo, PhanBoLo) else list(phan_bo)
    lo_thuoc = {lo.id: lo for lo in await khoa_cac_lo(db, [p.lo_id for p in ds])}
    if ds:
        await db.execute(
            select(PhanBoLo).where(PhanBoLo.id.in_([p.id for p in ds])).execution_options(populate_existing=True)
        )
    for p in ds:
        if p.trang_thai != trang_thai_can:
            raise LoiNghiepVu(
                "CHUYEN_TRANG_THAI_KHONG_HOP_LE",
                f"Không thể {viec}: phân bổ lô đang ở trạng thái {p.trang_thai.value}, cần {trang_thai_can.value}",
                chi_tiet={"phan_bo_lo_id": p.id},
            )
    if len({p.id for p in ds}) != len(ds):
        raise ValueError("Danh sách phân bổ có phần tử trùng")
    return ds, lo_thuoc


async def nha_giu(db: AsyncSession, phan_bo: PhanBoLo | Sequence[PhanBoLo]) -> None:
    """`dang_giu -> da_nha`, `so_luong_giu -= n`. Không ghi thẻ kho (giữ hàng chưa đổi tồn thật)."""
    ds, lo_thuoc = await _khoa_phan_bo(db, phan_bo, TrangThaiPhanBo.dang_giu, "nhả hàng giữ")
    bay_gio = bay_gio_utc()
    for p in ds:
        lo = lo_thuoc[p.lo_id]
        lo.so_luong_giu -= p.so_luong_co_so
        lo.updated_at = bay_gio
        p.trang_thai = TrangThaiPhanBo.da_nha
        p.updated_at = bay_gio
    await db.flush()


async def xuat_theo_phan_bo(
    db: AsyncSession, phan_bo: PhanBoLo | Sequence[PhanBoLo], chung_tu: ChungTu
) -> list[BienDongKho]:
    """`dang_giu -> da_xuat`, `so_luong_ton -= n` và `so_luong_giu -= n`; thẻ kho `xuat_ban` âm."""
    ds, lo_thuoc = await _khoa_phan_bo(db, phan_bo, TrangThaiPhanBo.dang_giu, "xuất kho")
    bay_gio = bay_gio_utc()
    the: list[BienDongKho] = []
    for p in ds:
        lo = lo_thuoc[p.lo_id]
        lo.so_luong_ton -= p.so_luong_co_so
        lo.so_luong_giu -= p.so_luong_co_so
        lo.updated_at = bay_gio
        p.trang_thai = TrangThaiPhanBo.da_xuat
        p.updated_at = bay_gio
        the.append(_the_kho(lo, LoaiBienDong.xuat_ban, KhuTon.kho_ban, -p.so_luong_co_so, lo.so_luong_ton, chung_tu))
    db.add_all(the)
    await db.flush()
    return the


async def hoan_nhap(db: AsyncSession, phan_bo: PhanBoLo | Sequence[PhanBoLo], chung_tu: ChungTu) -> list[BienDongKho]:
    """`da_xuat -> da_hoan_nhap`, `so_luong_ton += n` đúng lô cũ; thẻ kho `hoan_nhap` dương."""
    ds, lo_thuoc = await _khoa_phan_bo(db, phan_bo, TrangThaiPhanBo.da_xuat, "hoàn nhập")
    bay_gio = bay_gio_utc()
    the: list[BienDongKho] = []
    for p in ds:
        lo = lo_thuoc[p.lo_id]
        await kiem_tra_san_pham_chua_xoa(db, lo)
        lo.so_luong_ton += p.so_luong_co_so
        lo.updated_at = bay_gio
        p.trang_thai = TrangThaiPhanBo.da_hoan_nhap
        p.updated_at = bay_gio
        the.append(_the_kho(lo, LoaiBienDong.hoan_nhap, KhuTon.kho_ban, p.so_luong_co_so, lo.so_luong_ton, chung_tu))
    db.add_all(the)
    await db.flush()
    return the


# --- Biệt trữ, trừ tồn, điều chỉnh ---


async def vao_biet_tru(db: AsyncSession, lo: LoThuoc, so_luong: int, chung_tu: ChungTu) -> BienDongKho:
    """Hàng khách trả hoặc hư hỏng vào khu biệt trữ: `so_luong_biet_tru += n`, thẻ kho `nhan_tra_ve` khu `biet_tru`."""
    _kiem_tra_so_luong(so_luong)
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    await kiem_tra_san_pham_chua_xoa(db, lo_khoa)
    lo_khoa.so_luong_biet_tru += so_luong
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = _the_kho(
        lo_khoa, LoaiBienDong.nhan_tra_ve, KhuTon.biet_tru, so_luong, lo_khoa.so_luong_biet_tru, chung_tu
    )
    db.add(bien_dong)
    await db.flush()
    return bien_dong


_LOAI_TRU_TON = frozenset({LoaiBienDong.huy_hang, LoaiBienDong.xuat_tra_ncc})


async def tru_ton(
    db: AsyncSession, lo: LoThuoc, so_luong: int, khu: KhuTon, loai: LoaiBienDong, chung_tu: ChungTu
) -> BienDongKho:
    """Trừ hàng khỏi khu `khu` của lô (phiếu hủy, phiếu xuất trả NCC đã duyệt); thẻ kho `-n`.

    Khu `kho_ban` không được làm tồn khả dụng (`ton - giu`) âm: hàng đang giữ cho đơn không bị hủy hay trả đi.
    Khu `biet_tru` không được âm. Thiếu thì ném `HET_HANG` kèm `{lo_id, con_lai}`.
    """
    _kiem_tra_so_luong(so_luong)
    if loai not in _LOAI_TRU_TON:
        raise ValueError(f"tru_ton chỉ nhận loại {sorted(x.value for x in _LOAI_TRU_TON)}, nhận {loai}")
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    viec = "hủy hoặc xuất trả"
    if khu == KhuTon.kho_ban:
        con_lai = lo_khoa.so_luong_ton - lo_khoa.so_luong_giu
        if so_luong > con_lai:
            raise _het_hang(lo_khoa, con_lai, viec)
        lo_khoa.so_luong_ton -= so_luong
        ton_sau = lo_khoa.so_luong_ton
    else:
        if so_luong > lo_khoa.so_luong_biet_tru:
            raise _het_hang(lo_khoa, lo_khoa.so_luong_biet_tru, viec)
        lo_khoa.so_luong_biet_tru -= so_luong
        ton_sau = lo_khoa.so_luong_biet_tru
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = _the_kho(lo_khoa, loai, khu, -so_luong, ton_sau, chung_tu)
    db.add(bien_dong)
    await db.flush()
    return bien_dong


async def dieu_chinh(db: AsyncSession, lo: LoThuoc, delta: int, chung_tu: ChungTu) -> BienDongKho:
    """Điều chỉnh tồn kho bán của lô theo kết quả kiểm kê: `so_luong_ton += delta` (khác 0), thẻ kho `dieu_chinh ±n`.

    Tồn sau điều chỉnh không âm và không nhỏ hơn `so_luong_giu`; vi phạm thì `HET_HANG` kèm `con_lai` là mức giảm tối
    đa cho phép. Tăng tồn phải qua `kiem_tra_san_pham_chua_xoa` (sản phẩm đã xóa không được có thêm hàng).
    """
    if isinstance(delta, bool) or not isinstance(delta, int):
        raise TypeError(f"delta phải là số nguyên, nhận {type(delta).__name__}")
    if delta == 0:
        raise ValueError("delta không được bằng 0")
    (lo_khoa,) = await khoa_cac_lo(db, [lo.id])
    if delta > 0:
        await kiem_tra_san_pham_chua_xoa(db, lo_khoa)
    giam_toi_da = lo_khoa.so_luong_ton - lo_khoa.so_luong_giu
    if delta < 0 and -delta > giam_toi_da:
        raise _het_hang(lo_khoa, giam_toi_da, "điều chỉnh giảm")
    lo_khoa.so_luong_ton += delta
    lo_khoa.updated_at = bay_gio_utc()
    bien_dong = _the_kho(lo_khoa, LoaiBienDong.dieu_chinh, KhuTon.kho_ban, delta, lo_khoa.so_luong_ton, chung_tu)
    db.add(bien_dong)
    await db.flush()
    return bien_dong
