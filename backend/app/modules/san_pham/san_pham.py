"""Quản lý sản phẩm: thông tin thương mại (AD04, spec 06 mục 3.11).

- Mọi thao tác GHI vào một sản phẩm khóa dòng `san_pham` `FOR UPDATE` TRƯỚC (hai lần ghi vào cùng sản phẩm không chạy
  song song) rồi so `phien_ban` (dấu vân tay nội dung cả sản phẩm gồm đơn vị, thành phần, ảnh) với bản người dùng đã
  xem: lệch thì `409 DU_LIEU_DA_THAY_DOI`, không ghi đè ngầm thay đổi của Admin khác.
- Tạo sản phẩm tuần tự hóa việc sinh `slug`/kiểm tra SKU bằng một khóa tư vấn; mã vạch (DDL của ERD không có unique)
  bằng khóa tư vấn thứ hai, để quét một mã ở quầy chỉ ra đúng một đơn vị.
- Gắn danh mục cho sản phẩm giữ khóa dòng danh mục `FOR SHARE` và đòi nó chưa bị xóa mềm (QĐ-16): giao dịch xóa danh
  mục (khóa `FOR UPDATE` rồi đếm sản phẩm) và giao dịch gắn sản phẩm không lọt khe nhau.
- Thao tác ghi đòi người thực hiện là ADMIN (`dam_bao_la_admin`) và ghi nhật ký cùng giao dịch.
"""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.phan_trang import ThamSoPhanTrang, lay_trang, sap_xep_theo
from app.core.slug import tao_slug
from app.core.thoi_gian import bay_gio_utc
from app.core.tim_kiem import mau_tim_like
from app.models.enums import LoaiSanPham, TrangThaiKinhDoanh
from app.models.he_thong import NhanVien
from app.models.kho import LoThuoc
from app.models.san_pham import (
    AnhSanPham,
    DanhMuc,
    DonViQuyDoi,
    HoatChat,
    NhaSanXuat,
    SanPham,
    ThanhPhan,
    ThuongHieu,
)
from app.modules.san_pham.schemas_san_pham import (
    AnhDoc,
    DonViDoc,
    DonViVao,
    SanPhamChiTiet,
    SanPhamSua,
    SanPhamTao,
    SanPhamTomTat,
    ThanhPhanDoc,
    ThanhPhanVao,
    vi_pham_cheo,
)

BANG = "san_pham"
_KHOA_DINH_DANH = "nha_thuoc.san_pham.dinh_danh"
_KHOA_MA_VACH = "nha_thuoc.san_pham.ma_vach"

TRUONG_THUONG_MAI = (
    "sku",
    "ten",
    "loai_san_pham",
    "danh_muc_id",
    "thuong_hieu_id",
    "nha_san_xuat_id",
    "so_dang_ky",
    "dang_bao_che",
    "quy_cach",
    "doi_tuong_su_dung",
    "ton_toi_thieu",
    "dung_dinh_ky",
    "so_ngay_dung_moi_don_vi",
    "so_luong_toi_da_moi_don",
    "la_noi_bat",
    "trang_thai",
)


def loi_truong(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy sản phẩm")


async def khoa_tu_van(db: AsyncSession, ten: str) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:khoa))"), {"khoa": ten})


# --- Đọc --------------------------------------------------------------------------------------------------------------


async def chi_tiet(db: AsyncSession, sp: SanPham) -> SanPhamChiTiet:
    """Thông tin thương mại của một sản phẩm kèm `phien_ban` (đọc lại từ DB, không tin trạng thái trong bộ nhớ).

    Đọc lại cả dòng `san_pham`: thuộc tính vừa gán trong bộ nhớ (ví dụ `Decimal("7")`) khác dạng DB trả về (`7.00`), mà
    `phien_ban` là dấu vân tay của dạng DB; lệch dạng thì phản hồi lúc tạo không khớp với lần đọc sau đó.
    """
    await db.refresh(sp)
    don_vi = (
        (
            await db.execute(
                select(DonViQuyDoi)
                .where(DonViQuyDoi.san_pham_id == sp.id)
                .order_by(DonViQuyDoi.he_so, DonViQuyDoi.id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    thanh_phan = (
        await db.execute(
            select(ThanhPhan, HoatChat.ten)
            .join(HoatChat, HoatChat.id == ThanhPhan.hoat_chat_id)
            .where(ThanhPhan.san_pham_id == sp.id)
            .order_by(func.lower(HoatChat.ten), HoatChat.id)
            .execution_options(populate_existing=True)
        )
    ).all()
    anh = (
        (
            await db.execute(
                select(AnhSanPham)
                .where(AnhSanPham.san_pham_id == sp.id)
                .order_by(AnhSanPham.thu_tu, AnhSanPham.id)
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    ten_danh_muc = await db.scalar(select(DanhMuc.ten).where(DanhMuc.id == sp.danh_muc_id))
    ten_thuong_hieu = (
        None
        if sp.thuong_hieu_id is None
        else await db.scalar(select(ThuongHieu.ten).where(ThuongHieu.id == sp.thuong_hieu_id))
    )
    ten_nha_san_xuat = (
        None
        if sp.nha_san_xuat_id is None
        else await db.scalar(select(NhaSanXuat.ten).where(NhaSanXuat.id == sp.nha_san_xuat_id))
    )
    ban = SanPhamChiTiet(
        id=sp.id,
        sku=sp.sku,
        ten=sp.ten,
        slug=sp.slug,
        loai_san_pham=sp.loai_san_pham,
        danh_muc_id=sp.danh_muc_id,
        ten_danh_muc=ten_danh_muc or "",
        thuong_hieu_id=sp.thuong_hieu_id,
        ten_thuong_hieu=ten_thuong_hieu,
        nha_san_xuat_id=sp.nha_san_xuat_id,
        ten_nha_san_xuat=ten_nha_san_xuat,
        so_dang_ky=sp.so_dang_ky,
        dang_bao_che=sp.dang_bao_che,
        quy_cach=sp.quy_cach,
        doi_tuong_su_dung=sp.doi_tuong_su_dung,
        don_vi_co_so=sp.don_vi_co_so,
        ton_toi_thieu=sp.ton_toi_thieu,
        dung_dinh_ky=sp.dung_dinh_ky,
        so_ngay_dung_moi_don_vi=sp.so_ngay_dung_moi_don_vi,
        so_luong_toi_da_moi_don=sp.so_luong_toi_da_moi_don,
        la_noi_bat=sp.la_noi_bat,
        trang_thai=sp.trang_thai,
        created_at=sp.created_at,
        updated_at=sp.updated_at,
        don_vi=[DonViDoc.model_validate(d, from_attributes=True) for d in don_vi],
        thanh_phan=[
            ThanhPhanDoc(hoat_chat_id=t.hoat_chat_id, ten_hoat_chat=ten, ham_luong=t.ham_luong) for t, ten in thanh_phan
        ],
        anh=[AnhDoc.model_validate(a, from_attributes=True) for a in anh],
        phien_ban="0" * 16,
    )
    return ban.model_copy(update={"phien_ban": dau_van_tay(ban.model_dump(mode="json", exclude={"phien_ban"}))})


async def lay(db: AsyncSession, san_pham_id: int) -> SanPhamChiTiet:
    sp = (
        await db.execute(
            select(SanPham)
            .where(SanPham.id == san_pham_id, SanPham.deleted_at.is_(None))
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if sp is None:
        raise khong_tim_thay()
    return await chi_tiet(db, sp)


async def khoa_va_kiem_tra(db: AsyncSession, san_pham_id: int, phien_ban: str) -> tuple[SanPham, SanPhamChiTiet]:
    """Khóa dòng sản phẩm rồi đòi `phien_ban` khớp bản hiện tại. Mọi thao tác ghi bắt đầu từ đây."""
    sp = (
        await db.execute(
            select(SanPham)
            .where(SanPham.id == san_pham_id, SanPham.deleted_at.is_(None))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if sp is None:
        raise khong_tim_thay()
    hien_tai = await chi_tiet(db, sp)
    if hien_tai.phien_ban != phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Sản phẩm đã được người khác thay đổi, hãy tải lại rồi sửa tiếp",
            chi_tiet={"phien_ban_hien_tai": hien_tai.phien_ban},
        )
    return sp, hien_tai


def _gia_mac_dinh() -> ColumnElement[Any]:
    mac_dinh = (
        select(DonViQuyDoi.gia_ban)
        .where(DonViQuyDoi.san_pham_id == SanPham.id, DonViQuyDoi.la_mac_dinh)
        .correlate(SanPham)
        .scalar_subquery()
    )
    co_so = (
        select(DonViQuyDoi.gia_ban)
        .where(DonViQuyDoi.san_pham_id == SanPham.id, DonViQuyDoi.he_so == 1)
        .correlate(SanPham)
        .scalar_subquery()
    )
    return func.coalesce(mac_dinh, co_so)


def _anh_chinh() -> ColumnElement[Any]:
    return (
        select(AnhSanPham.url)
        .where(AnhSanPham.san_pham_id == SanPham.id, AnhSanPham.la_anh_chinh)
        .correlate(SanPham)
        .scalar_subquery()
    )


async def _id_danh_muc_con_chau(db: AsyncSession, goc_id: int) -> list[int]:
    cay = select(DanhMuc.id).where(DanhMuc.id == goc_id).cte("cay", recursive=True)
    cay = cay.union_all(select(DanhMuc.id).join(cay, DanhMuc.danh_muc_cha_id == cay.c.id))
    return list((await db.execute(select(cay.c.id))).scalars())


CAC_TRUONG_SAP_XEP = {
    "ten": func.f_unaccent(func.lower(SanPham.ten)),
    "sku": SanPham.sku,
    "created_at": SanPham.created_at,
}


async def danh_sach(
    db: AsyncSession,
    *,
    q: str | None,
    loai: LoaiSanPham | None,
    danh_muc_id: int | None,
    trang_thai: TrangThaiKinhDoanh | None,
    sap_xep: str | None,
    tp: ThamSoPhanTrang,
) -> tuple[Sequence[SanPhamTomTat], int]:
    """Sản phẩm chưa xóa. `q` tìm tên (không phân biệt dấu/hoa thường) hoặc SKU; `danh_muc_id` gồm cả danh mục con."""
    stmt: Select[Any] = (
        select(
            SanPham,
            DanhMuc.ten.label("ten_danh_muc"),
            ThuongHieu.ten.label("ten_thuong_hieu"),
            _gia_mac_dinh().label("gia_mac_dinh"),
            _anh_chinh().label("anh_chinh_url"),
        )
        .join(DanhMuc, DanhMuc.id == SanPham.danh_muc_id)
        .outerjoin(ThuongHieu, ThuongHieu.id == SanPham.thuong_hieu_id)
        .where(SanPham.deleted_at.is_(None))
    )
    if q and q.strip():
        mau = mau_tim_like(q)
        stmt = stmt.where(
            or_(
                func.f_unaccent(func.lower(SanPham.ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
                func.upper(SanPham.sku).like(func.upper(mau), escape="\\"),
            )
        )
    if loai is not None:
        stmt = stmt.where(SanPham.loai_san_pham == loai)
    if trang_thai is not None:
        stmt = stmt.where(SanPham.trang_thai == trang_thai)
    if danh_muc_id is not None:
        stmt = stmt.where(SanPham.danh_muc_id.in_(await _id_danh_muc_con_chau(db, danh_muc_id)))
    stmt = sap_xep_theo(stmt, sap_xep, CAC_TRUONG_SAP_XEP, mac_dinh="-created_at", khoa_phu=SanPham.id)
    dong, tong = await lay_trang(db, stmt, tp, nhieu_cot=True)
    return [
        SanPhamTomTat(
            id=sp.id,
            sku=sp.sku,
            ten=sp.ten,
            slug=sp.slug,
            loai_san_pham=sp.loai_san_pham,
            danh_muc_id=sp.danh_muc_id,
            ten_danh_muc=ten_dm,
            thuong_hieu_id=sp.thuong_hieu_id,
            ten_thuong_hieu=ten_th,
            trang_thai=sp.trang_thai,
            la_noi_bat=sp.la_noi_bat,
            don_vi_co_so=sp.don_vi_co_so,
            gia_mac_dinh=gia,
            anh_chinh_url=anh,
            created_at=sp.created_at,
        )
        for sp, ten_dm, ten_th, gia, anh in dong
    ], tong


# --- Kiểm tra tham chiếu và định danh ---------------------------------------------------------------------------------


async def _gan_danh_muc(db: AsyncSession, danh_muc_id: int) -> None:
    """Danh mục phải chưa xóa mềm; khóa dòng `FOR SHARE` để giao dịch xóa danh mục phải chờ (QĐ-16)."""
    co = (
        await db.execute(
            select(DanhMuc.id).where(DanhMuc.id == danh_muc_id, DanhMuc.deleted_at.is_(None)).with_for_update(read=True)
        )
    ).first()
    if co is None:
        raise loi_truong("danh_muc_id", "Danh mục không tồn tại hoặc đã bị xóa")


async def _kiem_tra_tham_chieu(db: AsyncSession, truong: str, mo_hinh: Any, gia_tri: int | None) -> None:
    if gia_tri is None:
        return
    # FOR SHARE: xóa thương hiệu/nhà sản xuất (AD05) phải chờ giao dịch này, nên không có sản phẩm nào trỏ vào bản ghi
    # vừa bị xóa.
    co = await db.execute(select(mo_hinh.id).where(mo_hinh.id == gia_tri).with_for_update(read=True))
    if co.first() is None:
        raise loi_truong(truong, "Không tồn tại")


async def kiem_tra_hoat_chat(db: AsyncSession, thanh_phan: Sequence[ThanhPhanVao]) -> None:
    ids = {t.hoat_chat_id for t in thanh_phan}
    if not ids:
        return
    co = set((await db.execute(select(HoatChat.id).where(HoatChat.id.in_(ids)))).scalars())
    for i, t in enumerate(thanh_phan):
        if t.hoat_chat_id not in co:
            raise loi_truong(f"thanh_phan.{i}.hoat_chat_id", "Hoạt chất không tồn tại")


async def kiem_tra_ma_vach(db: AsyncSession, don_vi: Sequence[DonViVao], san_pham_id: int | None) -> None:
    """Mã vạch không trùng với đơn vị của sản phẩm KHÁC (không phân biệt hoa thường)."""
    can = {i: d.ma_vach.upper() for i, d in enumerate(don_vi) if d.ma_vach}
    if not can:
        return
    await khoa_tu_van(db, _KHOA_MA_VACH)
    # Đơn vị của sản phẩm đã xóa mềm không giữ chỗ: xóa là cuối cùng (không có khôi phục) mà mã vạch in trên hộp thuốc.
    stmt = (
        select(func.upper(DonViQuyDoi.ma_vach))
        .join(SanPham, SanPham.id == DonViQuyDoi.san_pham_id)
        .where(SanPham.deleted_at.is_(None), func.upper(DonViQuyDoi.ma_vach).in_(set(can.values())))
    )
    if san_pham_id is not None:
        stmt = stmt.where(DonViQuyDoi.san_pham_id != san_pham_id)
    da_co = set((await db.execute(stmt)).scalars())
    for i, ma in can.items():
        if ma in da_co:
            raise LoiNghiepVu(
                "TRUNG_DU_LIEU",
                "Mã vạch này đã thuộc đơn vị của một sản phẩm khác",
                chi_tiet={"truong": f"don_vi.{i}.ma_vach"},
            )


async def _sku_chua_dung(db: AsyncSession, sku: str, *, tru_id: int | None = None) -> None:
    stmt = select(SanPham.id).where(func.upper(SanPham.sku) == sku)
    if tru_id is not None:
        stmt = stmt.where(SanPham.id != tru_id)
    if (await db.execute(stmt.limit(1))).first() is not None:
        raise LoiNghiepVu("TRUNG_DU_LIEU", "SKU này đã được dùng", chi_tiet={"truong": "sku"})


async def _slug_chua_dung(db: AsyncSession, ten: str) -> str:
    """Slug theo tên, thêm `-2`, `-3`... nếu trùng với BẤT KỲ sản phẩm nào (kể cả đã xóa: slug được giữ chỗ)."""
    goc = tao_slug(ten, 270)
    da_co = set(
        (await db.execute(select(SanPham.slug).where(SanPham.slug.regexp_match(f"^{goc}(-[0-9]+)?$")))).scalars()
    )
    ung_vien, n = goc, 1
    while ung_vien in da_co:
        n += 1
        ung_vien = f"{goc}-{n}"
    return ung_vien


def _du_lieu_nhat_ky(sp: SanPham) -> dict[str, Any]:
    return {truong: getattr(sp, truong) for truong in TRUONG_THUONG_MAI}


def _tom_tat_don_vi(don_vi: Sequence[DonViVao | DonViQuyDoi]) -> list[dict[str, Any]]:
    return [
        {
            "id": getattr(d, "id", None),
            "ten_don_vi": d.ten_don_vi,
            "he_so": d.he_so,
            "gia_ban": d.gia_ban,
            "ban_online": d.ban_online,
            "la_mac_dinh": d.la_mac_dinh,
            "ma_vach": d.ma_vach,
        }
        for d in don_vi
    ]


# --- Ghi --------------------------------------------------------------------------------------------------------------


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: SanPhamTao, *, ip: str) -> SanPhamChiTiet:
    await dam_bao_la_admin(db, actor)
    if vi_pham := vi_pham_cheo(
        du_lieu.dung_dinh_ky, du_lieu.so_ngay_dung_moi_don_vi, du_lieu.loai_san_pham, du_lieu.la_noi_bat
    ):
        raise loi_truong(*vi_pham)
    await khoa_tu_van(db, _KHOA_DINH_DANH)
    await _gan_danh_muc(db, du_lieu.danh_muc_id)
    await _kiem_tra_tham_chieu(db, "thuong_hieu_id", ThuongHieu, du_lieu.thuong_hieu_id)
    await _kiem_tra_tham_chieu(db, "nha_san_xuat_id", NhaSanXuat, du_lieu.nha_san_xuat_id)
    await kiem_tra_hoat_chat(db, du_lieu.thanh_phan)
    await _sku_chua_dung(db, du_lieu.sku)
    await kiem_tra_ma_vach(db, du_lieu.don_vi, None)
    if any(d.id is not None for d in du_lieu.don_vi):
        raise loi_truong("don_vi", "Sản phẩm mới chưa có đơn vị nào để sửa: bỏ `id`")
    co_so = next(d for d in du_lieu.don_vi if d.he_so == 1)
    sp = SanPham(
        sku=du_lieu.sku,
        ten=du_lieu.ten,
        slug=await _slug_chua_dung(db, du_lieu.ten),
        loai_san_pham=du_lieu.loai_san_pham,
        danh_muc_id=du_lieu.danh_muc_id,
        thuong_hieu_id=du_lieu.thuong_hieu_id,
        nha_san_xuat_id=du_lieu.nha_san_xuat_id,
        so_dang_ky=du_lieu.so_dang_ky,
        dang_bao_che=du_lieu.dang_bao_che,
        quy_cach=du_lieu.quy_cach,
        doi_tuong_su_dung=du_lieu.doi_tuong_su_dung,
        don_vi_co_so=co_so.ten_don_vi,
        ton_toi_thieu=du_lieu.ton_toi_thieu,
        dung_dinh_ky=du_lieu.dung_dinh_ky,
        so_ngay_dung_moi_don_vi=du_lieu.so_ngay_dung_moi_don_vi,
        so_luong_toi_da_moi_don=du_lieu.so_luong_toi_da_moi_don,
        la_noi_bat=du_lieu.la_noi_bat,
        trang_thai=du_lieu.trang_thai,
    )
    db.add(sp)
    await db.flush()
    for d in du_lieu.don_vi:
        db.add(
            DonViQuyDoi(
                san_pham_id=sp.id,
                ten_don_vi=d.ten_don_vi,
                he_so=d.he_so,
                gia_ban=d.gia_ban,
                ban_online=d.ban_online,
                la_mac_dinh=d.la_mac_dinh,
                ma_vach=d.ma_vach,
            )
        )
    for t in du_lieu.thanh_phan:
        db.add(ThanhPhan(san_pham_id=sp.id, hoat_chat_id=t.hoat_chat_id, ham_luong=t.ham_luong))
    await db.flush()
    ket_qua = await chi_tiet(db, sp)
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=sp.id,
        gia_tri_moi=_du_lieu_nhat_ky(sp)
        | {
            "don_vi": _tom_tat_don_vi(ket_qua.don_vi),  # dạng đã lưu: tiền "90000.00", không phải "90000"
            "thanh_phan": [{"hoat_chat_id": t.hoat_chat_id, "ham_luong": t.ham_luong} for t in ket_qua.thanh_phan],
        },
        ip=ip,
    )
    return ket_qua


async def sua(db: AsyncSession, actor: NhanVien, san_pham_id: int, du_lieu: SanPhamSua, *, ip: str) -> SanPhamChiTiet:
    """Đổi các trường thương mại đã gửi (đơn vị, thành phần, ảnh có thao tác riêng). Không đổi `slug`."""
    await dam_bao_la_admin(db, actor)
    sp, hien_tai = await khoa_va_kiem_tra(db, san_pham_id, du_lieu.phien_ban)
    gui = {t: getattr(du_lieu, t) for t in TRUONG_THUONG_MAI if t in du_lieu.model_fields_set}
    moi = {t: v for t, v in gui.items() if getattr(sp, t) != v}
    if not moi:
        return hien_tai
    gop = {
        t: moi.get(t, getattr(sp, t))
        for t in ("dung_dinh_ky", "so_ngay_dung_moi_don_vi", "loai_san_pham", "la_noi_bat")
    }
    if vi_pham := vi_pham_cheo(
        gop["dung_dinh_ky"], gop["so_ngay_dung_moi_don_vi"], gop["loai_san_pham"], gop["la_noi_bat"]
    ):
        raise loi_truong(*vi_pham)
    if "sku" in moi:
        await khoa_tu_van(db, _KHOA_DINH_DANH)
        await _sku_chua_dung(db, moi["sku"], tru_id=sp.id)
    if "danh_muc_id" in moi:
        await _gan_danh_muc(db, moi["danh_muc_id"])
    if "thuong_hieu_id" in moi:
        await _kiem_tra_tham_chieu(db, "thuong_hieu_id", ThuongHieu, moi["thuong_hieu_id"])
    if "nha_san_xuat_id" in moi:
        await _kiem_tra_tham_chieu(db, "nha_san_xuat_id", NhaSanXuat, moi["nha_san_xuat_id"])
    cu = {t: getattr(sp, t) for t in moi}
    for t, v in moi.items():
        setattr(sp, t, v)
    sp.updated_at = bay_gio_utc()
    await db.flush()
    await ghi_nhat_ky(
        db, nhan_vien_id=actor.id, hanh_dong="sua", bang=BANG, ban_ghi_id=sp.id, gia_tri_cu=cu, gia_tri_moi=moi, ip=ip
    )
    return await chi_tiet(db, sp)


async def xoa(db: AsyncSession, actor: NhanVien, san_pham_id: int, phien_ban: str, *, ip: str) -> None:
    """Xóa mềm. Từ chối khi còn lô có tồn, đang giữ hoặc biệt trữ (đưa về 0 qua kho trước)."""
    await dam_bao_la_admin(db, actor)
    sp, _ = await khoa_va_kiem_tra(db, san_pham_id, phien_ban)
    # Khóa mọi lô của sản phẩm (FOR UPDATE, id tăng dần) TRƯỚC khi xét tồn: nhập kho đang chạy trên một lô xong rồi mới
    # tới lượt ta (và ta thấy tồn mới); nhập kho đến sau phải chờ, rồi gặp `deleted_at`
    # (`ton_kho.kiem_tra_san_pham_chua_xoa`).
    cac_lo = (
        await db.execute(
            select(LoThuoc.so_luong_ton, LoThuoc.so_luong_giu, LoThuoc.so_luong_biet_tru)
            .where(LoThuoc.san_pham_id == sp.id)
            .order_by(LoThuoc.id)
            .with_for_update()
        )
    ).all()
    con_hang = sum(1 for ton, giu, biet_tru in cac_lo if ton > 0 or giu > 0 or biet_tru > 0)
    if con_hang:
        raise LoiNghiepVu(
            "SAN_PHAM_CON_TON_KHO",
            f"Sản phẩm còn {con_hang} lô có hàng, hãy xử lý tồn kho trước (hoặc chuyển sang ngừng kinh doanh)",
            chi_tiet={"so_lo": con_hang},
        )
    sp.deleted_at = bay_gio_utc()
    sp.updated_at = sp.deleted_at
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="xoa",
        bang=BANG,
        ban_ghi_id=sp.id,
        gia_tri_cu={"sku": sp.sku, "ten": sp.ten, "slug": sp.slug},
        ip=ip,
    )
