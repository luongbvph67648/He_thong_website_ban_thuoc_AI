"""Quản lý vai trò và phân quyền (AD18).

- Vai trò ADMIN bất biến: mọi thay đổi trả `PHAI_CON_ADMIN` (không ai còn quản trị được nếu Admin mất quyền).
- `profile.self` bắt buộc ở mức đầy đủ cho mọi vai trò, nếu không nhân viên không đổi được mật khẩu bắt buộc.
- `content.professional.edit` và `content.approve` chỉ PHARMACIST (spec 03 mục 7: Admin không sửa nội dung chuyên môn).
- Quyền mà ma trận spec 03 chỉ cấp cho ADMIN (`quyen_chi_cho_admin`) không gán được cho vai trò khác: nếu được thì người
  nhận tự tạo Admin/tự cấp quyền (`staff.manage`, `role.manage`) hoặc vừa lập vừa duyệt (`refund.confirm`).
- Khóa lạc quan: `phien_ban` (dấu vân tay của tập mã quyền + mức) phải khớp lúc lưu, nếu không một trang mở từ trước sẽ
  ngầm cấp lại quyền Admin khác vừa gỡ.
- Thay thế toàn bộ quyền của vai trò trong một transaction, khóa dòng vai trò (`FOR UPDATE`) để hai Admin sửa cùng lúc
  tuần tự; ghi nhật ký phần chênh lệch; xóa cache quyền sau commit.
"""

import hashlib

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.danh_muc_quyen import quyen_chi_cho_admin
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin, xoa_cache_quyen_sau_commit
from app.models.he_thong import NhanVien, Quyen, VaiTro, VaiTroQuyen
from app.modules.vai_tro.schemas import QuyenTrongVaiTro, VaiTroChiTiet, VaiTroTomTat

MA_VAI_TRO_ADMIN = "ADMIN"
QUYEN_BAT_BUOC = frozenset({"profile.self"})
QUYEN_CHI_CHO_VAI_TRO = {"content.professional.edit": "PHARMACIST", "content.approve": "PHARMACIST"}
BANG = "vai_tro_quyen"


def vai_tro_duoc_cap(ma_quyen: str) -> str | None:
    """Mã vai trò DUY NHẤT được giữ quyền này; `None` là gán được cho PHARMACIST và WAREHOUSE tùy ý."""
    if ma_quyen in QUYEN_CHI_CHO_VAI_TRO:
        return QUYEN_CHI_CHO_VAI_TRO[ma_quyen]
    return MA_VAI_TRO_ADMIN if ma_quyen in quyen_chi_cho_admin() else None


def tinh_phien_ban(muc_theo_ma: dict[str, str]) -> str:
    """Dấu vân tay chỉ phụ thuộc nội dung quyền (không phụ thuộc số lần lưu hay thời điểm): lưu lại bản cũ thì phiên bản
    cũ trở lại."""
    chuoi = "|".join(f"{ma}={muc}" for ma, muc in sorted(muc_theo_ma.items()))
    return hashlib.sha256(chuoi.encode()).hexdigest()[:16]


def _muc_tu_gioi_han(gioi_han: str | None) -> str:
    return "day_du" if gioi_han is None else "chi_xem"


def _gioi_han_tu_muc(muc: str) -> str | None:
    return None if muc == "day_du" else "chi_xem"


async def _lay_vai_tro(db: AsyncSession, ma: str, *, khoa: bool = False) -> VaiTro:
    truy_van = select(VaiTro).where(VaiTro.ma == ma)
    if khoa:
        truy_van = truy_van.with_for_update()
    vai_tro = (await db.execute(truy_van)).scalar_one_or_none()
    if vai_tro is None:
        raise LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy vai trò")
    return vai_tro


async def danh_sach(db: AsyncSession) -> list[VaiTroTomTat]:
    so_nv = dict(
        (
            await db.execute(
                select(NhanVien.vai_tro_id, func.count())
                .where(NhanVien.deleted_at.is_(None))
                .group_by(NhanVien.vai_tro_id)
            )
        ).all()
    )
    so_quyen = dict(
        (await db.execute(select(VaiTroQuyen.vai_tro_id, func.count()).group_by(VaiTroQuyen.vai_tro_id))).all()
    )
    vai_tro = (await db.execute(select(VaiTro).order_by(VaiTro.id))).scalars().all()
    return [
        VaiTroTomTat(
            ma=v.ma,
            ten=v.ten,
            mo_ta=v.mo_ta,
            so_nhan_vien=so_nv.get(v.id, 0),
            so_quyen=so_quyen.get(v.id, 0),
            chinh_sua_duoc=v.ma != MA_VAI_TRO_ADMIN,
        )
        for v in vai_tro
    ]


async def chi_tiet(db: AsyncSession, ma: str) -> VaiTroChiTiet:
    """Vai trò kèm TOÀN BỘ mã quyền của hệ thống và mức vai trò đang có, để màn hình dựng ma trận."""
    vai_tro = await _lay_vai_tro(db, ma)
    hien_co = {
        q_id: _muc_tu_gioi_han(g)
        for q_id, g in (
            await db.execute(
                select(VaiTroQuyen.quyen_id, VaiTroQuyen.gioi_han).where(VaiTroQuyen.vai_tro_id == vai_tro.id)
            )
        ).all()
    }
    so_nv = await db.scalar(
        select(func.count())
        .select_from(NhanVien)
        .where(NhanVien.vai_tro_id == vai_tro.id, NhanVien.deleted_at.is_(None))
    )
    quyen = (await db.execute(select(Quyen).order_by(Quyen.nhom, Quyen.ma))).scalars().all()
    return VaiTroChiTiet(
        ma=vai_tro.ma,
        ten=vai_tro.ten,
        mo_ta=vai_tro.mo_ta,
        so_nhan_vien=so_nv or 0,
        chinh_sua_duoc=vai_tro.ma != MA_VAI_TRO_ADMIN,
        phien_ban=tinh_phien_ban({q.ma: hien_co[q.id] for q in quyen if q.id in hien_co}),
        quyen=[
            QuyenTrongVaiTro(
                ma=q.ma,
                nhom=q.nhom,
                mo_ta=q.mo_ta,
                muc=hien_co.get(q.id),  # type: ignore[arg-type]
                bat_buoc=q.ma in QUYEN_BAT_BUOC,
                chi_cho_vai_tro=vai_tro_duoc_cap(q.ma),
            )
            for q in quyen
        ],
    )


def _loi_du_lieu(cac_loi: list[dict[str, str]]) -> LoiNghiepVu:
    return LoiNghiepVu("DU_LIEU_KHONG_HOP_LE", "Dữ liệu không hợp lệ", chi_tiet=cac_loi)


async def cap_nhat_quyen(
    db: AsyncSession, actor: NhanVien, ma: str, quyen_moi: dict[str, str], phien_ban: str, *, ip: str
) -> VaiTroChiTiet:
    """Đặt quyền của vai trò đúng bằng `quyen_moi`, với điều kiện `phien_ban` còn là bản hiện tại (nếu không:
    `DU_LIEU_DA_THAY_DOI`). Không có thay đổi thì không ghi gì."""
    await dam_bao_la_admin(db, actor)
    vai_tro = await _lay_vai_tro(db, ma, khoa=True)
    if vai_tro.ma == MA_VAI_TRO_ADMIN:
        raise LoiNghiepVu("PHAI_CON_ADMIN", "Không thể thay đổi quyền của vai trò Admin")

    danh_muc = {q.ma: q.id for q in (await db.execute(select(Quyen))).scalars()}
    loi: list[dict[str, str]] = []
    for ma_quyen in quyen_moi:
        if ma_quyen not in danh_muc:
            loi.append({"truong": f"quyen.{ma_quyen}", "loi": "Mã quyền không tồn tại"})
        elif (duoc_cap := vai_tro_duoc_cap(ma_quyen)) is not None and vai_tro.ma != duoc_cap:
            loi.append({"truong": f"quyen.{ma_quyen}", "loi": f"Quyền này chỉ dành cho vai trò {duoc_cap}"})
    for bat_buoc in QUYEN_BAT_BUOC:
        if quyen_moi.get(bat_buoc) != "day_du":
            loi.append({"truong": f"quyen.{bat_buoc}", "loi": "Quyền này bắt buộc ở mức đầy đủ cho mọi vai trò"})
    if loi:
        raise _loi_du_lieu(loi)

    hien_co = {
        q_id: g
        for q_id, g in (
            await db.execute(
                select(VaiTroQuyen.quyen_id, VaiTroQuyen.gioi_han).where(VaiTroQuyen.vai_tro_id == vai_tro.id)
            )
        ).all()
    }
    ma_theo_id = {v: k for k, v in danh_muc.items()}
    if tinh_phien_ban({ma_theo_id[q_id]: _muc_tu_gioi_han(g) for q_id, g in hien_co.items()}) != phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Phân quyền của vai trò này vừa được thay đổi, hãy tải lại rồi kiểm tra các thay đổi trước khi lưu",
        )
    them: list[str] = []
    bo: list[str] = []
    doi_muc: list[str] = []
    for ma_quyen, muc in sorted(quyen_moi.items()):
        q_id = danh_muc[ma_quyen]
        if q_id not in hien_co:
            them.append(f"{ma_quyen}:{muc}")
            db.add(VaiTroQuyen(vai_tro_id=vai_tro.id, quyen_id=q_id, gioi_han=_gioi_han_tu_muc(muc)))
        elif _muc_tu_gioi_han(hien_co[q_id]) != muc:
            doi_muc.append(f"{ma_quyen}:{_muc_tu_gioi_han(hien_co[q_id])}->{muc}")
            await db.execute(
                VaiTroQuyen.__table__.update()
                .where(VaiTroQuyen.vai_tro_id == vai_tro.id, VaiTroQuyen.quyen_id == q_id)
                .values(gioi_han=_gioi_han_tu_muc(muc))
            )
    muon_giu = {danh_muc[m] for m in quyen_moi}
    bo_id = sorted(q_id for q_id in hien_co if q_id not in muon_giu)
    for q_id in bo_id:
        bo.append(f"{ma_theo_id[q_id]}:{_muc_tu_gioi_han(hien_co[q_id])}")
    if bo_id:
        await db.execute(
            delete(VaiTroQuyen).where(VaiTroQuyen.vai_tro_id == vai_tro.id, VaiTroQuyen.quyen_id.in_(bo_id))
        )

    if them or bo or doi_muc:
        await db.flush()
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=vai_tro.ma,
            gia_tri_cu={"bo": bo, "doi_muc": doi_muc},
            gia_tri_moi={"them": them},
            ip=ip,
        )
        xoa_cache_quyen_sau_commit(db)
    return await chi_tiet(db, ma)
