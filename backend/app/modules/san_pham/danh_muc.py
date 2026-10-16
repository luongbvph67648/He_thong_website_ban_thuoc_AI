"""Quản lý cây danh mục của Admin (AD03).

- Tối đa 3 cấp; tên không trùng giữa các danh mục cùng cha (không phân biệt hoa thường và dấu); `slug` tự sinh, duy
  nhất trên cả danh mục đã xóa mềm (giữ chỗ), và KHÔNG đổi khi đổi tên (đường dẫn công khai ổn định).
- Mọi thao tác ghi cây (tạo, chuyển, xóa) được tuần tự hóa bằng một khóa tư vấn PostgreSQL: kiểm tra cấp và vòng chỉ
  đúng khi thấy cây nhất quán (hai Admin cùng chuyển A vào B và B vào A sẽ tạo vòng nếu không tuần tự hóa).
- Xóa mềm: khóa dòng `FOR UPDATE` TRƯỚC khi đếm sản phẩm. Tạo sản phẩm giữ khóa FK `KEY SHARE` trên dòng danh mục nên
  bên xóa chờ rồi thấy sản phẩm vừa thêm, không để lại sản phẩm mồ côi.
- Thao tác ghi đòi người thực hiện là ADMIN (QĐ-13); ghi nhật ký cùng transaction.
"""

from collections import defaultdict

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.slug import tao_slug
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import NhanVien
from app.models.san_pham import DanhMuc, SanPham
from app.modules.san_pham.schemas_danh_muc import DanhMucNut, DanhMucSua, DanhMucTao

__all__ = ["DanhMucSua", "DanhMucTao", "cay", "dat_vi_tri", "sua", "tao", "xoa"]

BANG = "danh_muc"
SO_CAP_TOI_DA = 3
_KHOA_CAY = "nha_thuoc.danh_muc_cay"


def _loi_truong(truong: str, loi: str) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=[{"truong": truong, "loi": loi}])


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy danh mục")


def _trung_ten() -> LoiNghiepVu:
    return LoiNghiepVu("TRUNG_DU_LIEU", "Đã có danh mục cùng tên trong cùng danh mục cha", chi_tiet={"truong": "ten"})


async def _khoa_cay(db: AsyncSession) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:khoa))"), {"khoa": _KHOA_CAY})


async def _tai_tat_ca(db: AsyncSession) -> dict[int, DanhMuc]:
    dong = (await db.execute(select(DanhMuc).where(DanhMuc.deleted_at.is_(None)))).scalars()
    return {d.id: d for d in dong}


def _con(tat_ca: dict[int, DanhMuc]) -> dict[int | None, list[DanhMuc]]:
    theo_cha: dict[int | None, list[DanhMuc]] = defaultdict(list)
    for d in sorted(tat_ca.values(), key=lambda d: (d.thu_tu, d.id)):
        theo_cha[d.danh_muc_cha_id if d.danh_muc_cha_id in tat_ca else None].append(d)
    return theo_cha


def _cap(tat_ca: dict[int, DanhMuc], id_: int) -> int:
    cap, hien_tai, da_di = 1, tat_ca[id_], {id_}
    while hien_tai.danh_muc_cha_id in tat_ca:
        hien_tai = tat_ca[hien_tai.danh_muc_cha_id]
        if hien_tai.id in da_di:  # dữ liệu vòng (không thể xảy ra qua service): dừng thay vì lặp mãi
            break
        da_di.add(hien_tai.id)
        cap += 1
    return cap


def _chieu_cao(theo_cha: dict[int | None, list[DanhMuc]], id_: int) -> int:
    """Số cấp của cây con gốc `id_`, tính cả chính nó (lá là 1)."""
    return 1 + max((_chieu_cao(theo_cha, c.id) for c in theo_cha.get(id_, [])), default=0)


def _con_chau(theo_cha: dict[int | None, list[DanhMuc]], id_: int) -> set[int]:
    ket = {id_}
    for c in theo_cha.get(id_, []):
        ket |= _con_chau(theo_cha, c.id)
    return ket


async def _dem_san_pham(db: AsyncSession) -> dict[int, int]:
    dong = await db.execute(
        select(SanPham.danh_muc_id, func.count()).where(SanPham.deleted_at.is_(None)).group_by(SanPham.danh_muc_id)
    )
    return dict(dong.all())


def _nut(d: DanhMuc, cap: int, so_sp: dict[int, int], theo_cha: dict[int | None, list[DanhMuc]]) -> DanhMucNut:
    return DanhMucNut(
        id=d.id,
        ten=d.ten,
        slug=d.slug,
        danh_muc_cha_id=d.danh_muc_cha_id,
        anh_url=d.anh_url,
        thu_tu=d.thu_tu,
        dang_hien_thi=d.dang_hien_thi,
        cap=cap,
        so_san_pham=so_sp.get(d.id, 0),
        con=[_nut(c, cap + 1, so_sp, theo_cha) for c in theo_cha.get(d.id, [])],
    )


async def cay(db: AsyncSession) -> list[DanhMucNut]:
    """Cây đầy đủ (kể cả danh mục đang ẩn, không có danh mục đã xóa)."""
    tat_ca = await _tai_tat_ca(db)
    theo_cha = _con(tat_ca)
    so_sp = await _dem_san_pham(db)
    return [_nut(g, 1, so_sp, theo_cha) for g in theo_cha.get(None, [])]


def _tim(nut: list[DanhMucNut], id_: int) -> DanhMucNut | None:
    for n in nut:
        if n.id == id_:
            return n
        if (con := _tim(n.con, id_)) is not None:
            return con
    return None


async def _co_anh_em_trung_ten(db: AsyncSession, ten: str, cha_id: int | None, *, tru_id: int | None = None) -> bool:
    truy_van = select(DanhMuc.id).where(
        DanhMuc.deleted_at.is_(None),
        DanhMuc.danh_muc_cha_id.is_(None) if cha_id is None else DanhMuc.danh_muc_cha_id == cha_id,
        func.f_unaccent(func.lower(DanhMuc.ten)) == func.f_unaccent(func.lower(ten)),
    )
    if tru_id is not None:
        truy_van = truy_van.where(DanhMuc.id != tru_id)
    return (await db.execute(truy_van.limit(1))).first() is not None


async def _slug_chua_dung(db: AsyncSession, ten: str) -> str:
    """Slug theo tên, thêm `-2`, `-3`... nếu trùng với BẤT KỲ danh mục nào (kể cả đã xóa mềm: slug được giữ chỗ)."""
    goc = tao_slug(ten, 150)
    da_co = set(
        (await db.execute(select(DanhMuc.slug).where(DanhMuc.slug.regexp_match(f"^{goc}(-[0-9]+)?$")))).scalars()
    )
    ung_vien, n = goc, 1
    while ung_vien in da_co:
        n += 1
        ung_vien = f"{goc}-{n}"
    return ung_vien


# --- Ghi -------------------------------------------------------------------------------------------------------------


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: DanhMucTao, *, ip: str) -> DanhMucNut:
    await dam_bao_la_admin(db, actor)
    await _khoa_cay(db)
    tat_ca = await _tai_tat_ca(db)
    cha_id = du_lieu.danh_muc_cha_id
    if cha_id is not None:
        if cha_id not in tat_ca:
            raise _loi_truong("danh_muc_cha_id", "Danh mục cha không tồn tại")
        if _cap(tat_ca, cha_id) >= SO_CAP_TOI_DA:
            raise _loi_truong("danh_muc_cha_id", f"Danh mục chỉ có tối đa {SO_CAP_TOI_DA} cấp")
    if await _co_anh_em_trung_ten(db, du_lieu.ten, cha_id):
        raise _trung_ten()
    anh_em = _con(tat_ca).get(cha_id, [])
    moi = DanhMuc(
        ten=du_lieu.ten,
        slug=await _slug_chua_dung(db, du_lieu.ten),
        danh_muc_cha_id=cha_id,
        anh_url=du_lieu.anh_url,
        thu_tu=max((a.thu_tu for a in anh_em), default=-1) + 1,
        dang_hien_thi=du_lieu.dang_hien_thi,
    )
    db.add(moi)
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=moi.id,
        gia_tri_moi={
            "ten": moi.ten,
            "slug": moi.slug,
            "danh_muc_cha_id": cha_id,
            "anh_url": moi.anh_url,
            "dang_hien_thi": moi.dang_hien_thi,
        },
        ip=ip,
    )
    cap = 1 if cha_id is None else _cap(tat_ca, cha_id) + 1
    return DanhMucNut(
        id=moi.id, ten=moi.ten, slug=moi.slug, danh_muc_cha_id=cha_id, anh_url=moi.anh_url, thu_tu=moi.thu_tu,
        dang_hien_thi=moi.dang_hien_thi, cap=cap, so_san_pham=0, con=[],
    )  # fmt: skip


async def sua(db: AsyncSession, actor: NhanVien, danh_muc_id: int, du_lieu: DanhMucSua, *, ip: str) -> DanhMucNut:
    """Đổi tên, ảnh, hiển thị. Không đổi `slug` (đường dẫn công khai) và không đổi vị trí (xem `dat_vi_tri`)."""
    await dam_bao_la_admin(db, actor)
    await _khoa_cay(db)
    dong = (
        await db.execute(select(DanhMuc).where(DanhMuc.id == danh_muc_id, DanhMuc.deleted_at.is_(None)))
    ).scalar_one_or_none()
    if dong is None:
        raise _khong_tim_thay()
    gui = du_lieu.model_fields_set
    cu: dict[str, object] = {}
    moi: dict[str, object] = {}
    if "ten" in gui and du_lieu.ten != dong.ten:
        if await _co_anh_em_trung_ten(db, du_lieu.ten, dong.danh_muc_cha_id, tru_id=dong.id):  # type: ignore[arg-type]
            raise _trung_ten()
        cu["ten"], moi["ten"] = dong.ten, du_lieu.ten
        dong.ten = du_lieu.ten  # type: ignore[assignment]
    if "anh_url" in gui and du_lieu.anh_url != dong.anh_url:
        cu["anh_url"], moi["anh_url"] = dong.anh_url, du_lieu.anh_url
        dong.anh_url = du_lieu.anh_url
    if "dang_hien_thi" in gui and du_lieu.dang_hien_thi != dong.dang_hien_thi:
        cu["dang_hien_thi"], moi["dang_hien_thi"] = dong.dang_hien_thi, du_lieu.dang_hien_thi
        dong.dang_hien_thi = du_lieu.dang_hien_thi  # type: ignore[assignment]
    if moi:
        dong.updated_at = bay_gio_utc()
        await db.flush()
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=dong.id,
            gia_tri_cu=cu,
            gia_tri_moi=moi,
            ip=ip,
        )
    nut = _tim(await cay(db), dong.id)
    if nut is None:  # không thể xảy ra: vừa khóa và sửa dòng chưa xóa
        raise _khong_tim_thay()
    return nut


async def dat_vi_tri(
    db: AsyncSession, actor: NhanVien, danh_muc_id: int, cha_moi_id: int | None, vi_tri: int, *, ip: str
) -> list[DanhMucNut]:
    """Đặt danh mục dưới `cha_moi_id` tại chỉ số `vi_tri` (kéo thả); trả cây mới. Cha cũ và cha mới được đánh lại
    `thu_tu` liên tục từ 0. Đúng vị trí hiện tại thì không làm gì và không ghi nhật ký."""
    await dam_bao_la_admin(db, actor)
    await _khoa_cay(db)
    tat_ca = await _tai_tat_ca(db)
    if danh_muc_id not in tat_ca:
        raise _khong_tim_thay()
    dong = tat_ca[danh_muc_id]
    theo_cha = _con(tat_ca)
    if cha_moi_id is not None:
        if cha_moi_id not in tat_ca:
            raise _loi_truong("danh_muc_cha_id", "Danh mục cha không tồn tại")
        if cha_moi_id in _con_chau(theo_cha, danh_muc_id):
            raise _loi_truong("danh_muc_cha_id", "Không thể chuyển danh mục vào chính nó hoặc danh mục con của nó")
    cap_moi = 1 if cha_moi_id is None else _cap(tat_ca, cha_moi_id) + 1
    if cap_moi + _chieu_cao(theo_cha, danh_muc_id) - 1 > SO_CAP_TOI_DA:
        raise _loi_truong("danh_muc_cha_id", f"Danh mục chỉ có tối đa {SO_CAP_TOI_DA} cấp")
    cha_cu_id = dong.danh_muc_cha_id
    if await _co_anh_em_trung_ten(db, dong.ten, cha_moi_id, tru_id=dong.id) and cha_moi_id != cha_cu_id:
        raise _trung_ten()

    anh_em_moi = [a for a in theo_cha.get(cha_moi_id, []) if a.id != danh_muc_id]
    chi_so = min(vi_tri, len(anh_em_moi))
    vi_tri_cu = next(i for i, a in enumerate(theo_cha.get(cha_cu_id, [])) if a.id == danh_muc_id)
    if cha_cu_id == cha_moi_id and vi_tri_cu == chi_so:
        return await cay(db)
    anh_em_moi.insert(chi_so, dong)
    bay_gio = bay_gio_utc()
    dong.danh_muc_cha_id = cha_moi_id
    dong.updated_at = bay_gio
    doi_thu_tu: list[int] = []  # anh em bị đánh lại thứ tự theo (không tính chính danh mục được chuyển)
    danh_sach_dich = list(enumerate(anh_em_moi))
    if cha_cu_id != cha_moi_id:
        danh_sach_dich += list(enumerate(a for a in theo_cha.get(cha_cu_id, []) if a.id != danh_muc_id))
    for i, a in danh_sach_dich:
        if a.thu_tu != i:
            a.thu_tu = i
            if a.id != dong.id:
                a.updated_at = bay_gio
                doi_thu_tu.append(a.id)
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="sua",
        bang=BANG,
        ban_ghi_id=dong.id,
        gia_tri_cu={"danh_muc_cha_id": cha_cu_id, "vi_tri": vi_tri_cu},
        gia_tri_moi={"danh_muc_cha_id": cha_moi_id, "vi_tri": chi_so, "anh_em_doi_thu_tu": sorted(doi_thu_tu)},
        ip=ip,
    )
    return await cay(db)


async def xoa(db: AsyncSession, actor: NhanVien, danh_muc_id: int, *, ip: str) -> None:
    """Xóa mềm. Từ chối khi còn sản phẩm chưa xóa (`DANH_MUC_CON_SAN_PHAM`) hoặc danh mục con chưa xóa."""
    await dam_bao_la_admin(db, actor)
    await _khoa_cay(db)
    dong = (
        await db.execute(
            select(DanhMuc).where(DanhMuc.id == danh_muc_id, DanhMuc.deleted_at.is_(None)).with_for_update()
        )
    ).scalar_one_or_none()
    if dong is None:
        raise _khong_tim_thay()
    # Đã khóa dòng: giao dịch đang thêm sản phẩm vào danh mục này (giữ khóa FK) phải xong trước, nên số đếm dưới đây đủ.
    so_san_pham = await db.scalar(
        select(func.count()).select_from(SanPham).where(SanPham.danh_muc_id == dong.id, SanPham.deleted_at.is_(None))
    )
    if so_san_pham:
        raise LoiNghiepVu(
            "DANH_MUC_CON_SAN_PHAM", f"Danh mục còn {so_san_pham} sản phẩm, hãy chuyển hoặc xóa chúng trước"
        )
    so_con = await db.scalar(
        select(func.count())
        .select_from(DanhMuc)
        .where(DanhMuc.danh_muc_cha_id == dong.id, DanhMuc.deleted_at.is_(None))
    )
    if so_con:
        raise LoiNghiepVu(
            "DANH_MUC_CON_DANH_MUC",
            f"Danh mục còn {so_con} danh mục con, hãy xóa chúng trước (hoặc ẩn cả nhánh bằng cách tắt hiển thị)",
        )
    dong.deleted_at = bay_gio_utc()
    dong.updated_at = dong.deleted_at
    await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="xoa",
        bang=BANG,
        ban_ghi_id=dong.id,
        gia_tri_cu={"ten": dong.ten, "slug": dong.slug, "danh_muc_cha_id": dong.danh_muc_cha_id},
        ip=ip,
    )
