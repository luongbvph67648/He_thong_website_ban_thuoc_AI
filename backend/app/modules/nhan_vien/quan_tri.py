"""Quản lý tài khoản nhân viên của Admin (AD01).

Quy tắc (spec 03 mục 7, 05 AD01):
- Không tự khóa, tự xóa, tự đổi vai trò hay tự đặt lại mật khẩu (`TU_THAY_DOI_KHONG_DUOC`).
- Luôn còn ít nhất một Admin hoạt động (`PHAI_CON_ADMIN`). Mọi thao tác có thể làm mất một Admin hoạt động khóa dòng
  của TẤT CẢ tài khoản Admin (cùng dòng đích) theo id tăng dần trước khi đếm, nên hai Admin khóa nhau cùng lúc không
  thể cùng thành công và để lại hệ thống không còn Admin nào.
- Khóa, xóa mềm, đổi vai trò, đặt lại mật khẩu đều thu hồi mọi phiên đăng nhập của người đó. Khóa dòng tài khoản
  TRƯỚC, phiên SAU (QĐ-12).
- Mật khẩu tạm sinh ngẫu nhiên, hiện một lần, bắt đổi ngay (`phai_doi_mat_khau`); không bao giờ vào nhật ký.
Mọi thay đổi ghi `nhat_ky_he_thong` cùng transaction.
"""

import re
from dataclasses import dataclass

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.bao_mat import bam_mat_khau_async, tao_mat_khau_tam
from app.core.dien_thoai import che_sdt
from app.core.loi import LoiNghiepVu
from app.core.ma_chung_tu import ma_nhan_vien
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.phan_trang import ThamSoPhanTrang, lay_trang, sap_xep_theo
from app.core.thoi_gian import bay_gio_utc
from app.models.enums import TrangThaiTaiKhoan
from app.models.he_thong import NhanVien, VaiTro
from app.modules.nhan_vien.schemas_quan_tri import NhanVienSua, NhanVienTao
from app.modules.tai_khoan import phien

MA_VAI_TRO_ADMIN = "ADMIN"
BANG = "nhan_vien"


@dataclass(frozen=True)
class KetQuaCoMatKhauTam:
    nhan_vien: NhanVien
    mat_khau_tam: str


def _khong_tim_thay() -> LoiNghiepVu:
    return LoiNghiepVu("KHONG_TIM_THAY", "Không tìm thấy nhân viên")


def _tu_thay_doi(viec: str) -> LoiNghiepVu:
    return LoiNghiepVu("TU_THAY_DOI_KHONG_DUOC", f"Bạn không thể tự {viec} chính mình, hãy nhờ một Admin khác")


def _phai_con_admin() -> LoiNghiepVu:
    return LoiNghiepVu("PHAI_CON_ADMIN", "Hệ thống phải luôn còn ít nhất một Admin đang hoạt động")


async def _vai_tro_theo_ma(db: AsyncSession, ma: str) -> VaiTro:
    vai_tro = (await db.execute(select(VaiTro).where(VaiTro.ma == ma))).scalar_one_or_none()
    if vai_tro is None:
        raise LoiNghiepVu(
            "DU_LIEU_KHONG_HOP_LE",
            "Dữ liệu không hợp lệ",
            chi_tiet=[{"truong": "vai_tro", "loi": "Vai trò không tồn tại"}],
        )
    return vai_tro


async def _tai_nhan_vien(db: AsyncSession, nhan_vien_id: int) -> NhanVien:
    nv = (
        await db.execute(
            select(NhanVien)
            .options(selectinload(NhanVien.vai_tro))
            .where(NhanVien.id == nhan_vien_id, NhanVien.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if nv is None:
        raise _khong_tim_thay()
    return nv


async def _khoa_dich_va_cac_admin(db: AsyncSession, nhan_vien_id: int) -> tuple[NhanVien, int]:
    """Khóa dòng của nhân viên đích cùng mọi tài khoản Admin (một câu `ORDER BY id FOR UPDATE`, nên mọi tiến trình khóa
    theo cùng thứ tự, không deadlock). Trả (nhân viên đích, số Admin hoạt động KHÁC nhân viên đích)."""
    admin_id = select(VaiTro.id).where(VaiTro.ma == MA_VAI_TRO_ADMIN).scalar_subquery()
    dong = list(
        (
            await db.execute(
                select(NhanVien)
                .options(selectinload(NhanVien.vai_tro))
                .where(
                    or_(
                        NhanVien.id == nhan_vien_id,
                        and_(NhanVien.vai_tro_id == admin_id, NhanVien.deleted_at.is_(None)),
                    )
                )
                .order_by(NhanVien.id)
                .with_for_update(of=NhanVien)
                .execution_options(populate_existing=True)
            )
        ).scalars()
    )
    dich = next((d for d in dong if d.id == nhan_vien_id), None)
    if dich is None or dich.deleted_at is not None:
        raise _khong_tim_thay()
    admin_khac_hoat_dong = [
        d
        for d in dong
        if d.id != dich.id
        and d.vai_tro.ma == MA_VAI_TRO_ADMIN
        and d.trang_thai == TrangThaiTaiKhoan.hoat_dong
        and d.deleted_at is None
    ]
    return dich, len(admin_khac_hoat_dong)


def _la_admin_hoat_dong(nv: NhanVien) -> bool:
    return nv.vai_tro.ma == MA_VAI_TRO_ADMIN and nv.trang_thai == TrangThaiTaiKhoan.hoat_dong and nv.deleted_at is None


async def _dam_bao_email_chua_dung(db: AsyncSession, email: str, *, tru_id: int | None = None) -> None:
    truy_van = select(NhanVien.id).where(
        func.lower(NhanVien.email) == email
    )  # tính cả tài khoản đã xóa mềm (ràng buộc unique)
    if tru_id is not None:
        truy_van = truy_van.where(NhanVien.id != tru_id)
    if (await db.execute(truy_van)).first() is not None:
        raise LoiNghiepVu(
            "TRUNG_DU_LIEU", "Email này đã được dùng cho một tài khoản nhân viên", chi_tiet={"truong": "email"}
        )


# --- Đọc -------------------------------------------------------------------------------------------------------------


def _mau_tim(q: str) -> str:
    # Thoát ký tự đặc biệt của LIKE để người dùng gõ % hoặc _ không biến thành ký tự thay thế.
    return "%" + re.sub(r"([\\%_])", r"\\\1", q.strip()) + "%"


CAC_TRUONG_SAP_XEP = {
    "created_at": NhanVien.created_at,
    "ma_nhan_vien": NhanVien.ma_nhan_vien,
    "ho_ten": func.f_unaccent(func.lower(NhanVien.ho_ten)),  # không phân biệt dấu và hoa thường, như ô tìm kiếm
    "email": func.lower(NhanVien.email),
}


async def danh_sach(
    db: AsyncSession,
    *,
    q: str | None,
    vai_tro: str | None,
    trang_thai: TrangThaiTaiKhoan | None,
    sap_xep: str | None = None,
    tp: ThamSoPhanTrang,
):
    """Danh sách nhân viên chưa xóa, mặc định mới tạo trước (`sap_xep`, xem `CAC_TRUONG_SAP_XEP`).

    `q` tìm theo tên (không phân biệt dấu), email, mã nhân viên."""
    stmt = select(NhanVien).options(selectinload(NhanVien.vai_tro)).where(NhanVien.deleted_at.is_(None))
    if q and q.strip():
        mau = _mau_tim(q)
        stmt = stmt.where(
            or_(
                func.f_unaccent(func.lower(NhanVien.ho_ten)).like(func.f_unaccent(func.lower(mau)), escape="\\"),
                func.lower(NhanVien.email).like(func.lower(mau), escape="\\"),
                func.lower(NhanVien.ma_nhan_vien).like(func.lower(mau), escape="\\"),
            )
        )
    if vai_tro:
        stmt = stmt.where(NhanVien.vai_tro_id == select(VaiTro.id).where(VaiTro.ma == vai_tro).scalar_subquery())
    if trang_thai is not None:
        stmt = stmt.where(NhanVien.trang_thai == trang_thai)
    stmt = sap_xep_theo(stmt, sap_xep, CAC_TRUONG_SAP_XEP, mac_dinh="-created_at", khoa_phu=NhanVien.id)
    return await lay_trang(db, stmt, tp)


async def chi_tiet(db: AsyncSession, nhan_vien_id: int) -> NhanVien:
    return await _tai_nhan_vien(db, nhan_vien_id)


# --- Ghi -------------------------------------------------------------------------------------------------------------


async def tao(db: AsyncSession, actor: NhanVien, du_lieu: NhanVienTao, *, ip: str) -> KetQuaCoMatKhauTam:
    """Tạo tài khoản với mật khẩu tạm ngẫu nhiên, bắt đổi ở lần đăng nhập đầu."""
    await dam_bao_la_admin(db, actor)
    vai_tro = await _vai_tro_theo_ma(db, du_lieu.vai_tro)
    await _dam_bao_email_chua_dung(db, du_lieu.email)
    mat_khau_tam = tao_mat_khau_tam()
    nv = NhanVien(
        ma_nhan_vien=await ma_nhan_vien(db),
        ho_ten=du_lieu.ho_ten,
        email=du_lieu.email,
        so_dien_thoai=du_lieu.so_dien_thoai,
        mat_khau_hash=await bam_mat_khau_async(mat_khau_tam),
        vai_tro_id=vai_tro.id,
        phai_doi_mat_khau=True,
    )
    try:
        async with db.begin_nested():  # hai Admin tạo cùng email cùng lúc: bên thua nhận TRUNG_DU_LIEU thay vì 500
            db.add(nv)
            await db.flush()
    except IntegrityError as loi:
        raise LoiNghiepVu(
            "TRUNG_DU_LIEU", "Email này đã được dùng cho một tài khoản nhân viên", chi_tiet={"truong": "email"}
        ) from loi
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao",
        bang=BANG,
        ban_ghi_id=nv.id,
        gia_tri_moi={"ma_nhan_vien": nv.ma_nhan_vien, "email": nv.email, "vai_tro": vai_tro.ma},
        ip=ip,
    )
    return KetQuaCoMatKhauTam(await _tai_nhan_vien(db, nv.id), mat_khau_tam)


async def sua(db: AsyncSession, actor: NhanVien, nhan_vien_id: int, du_lieu: NhanVienSua, *, ip: str) -> NhanVien:
    """Sửa họ tên, email, số điện thoại, vai trò. Đổi vai trò thu hồi mọi phiên (giao diện nạp lại quyền)."""
    await dam_bao_la_admin(db, actor)
    dich, admin_khac = await _khoa_dich_va_cac_admin(db, nhan_vien_id)
    gui = du_lieu.model_fields_set
    cu: dict[str, str | None] = {}
    moi: dict[str, str | None] = {}

    if "vai_tro" in gui and du_lieu.vai_tro != dich.vai_tro.ma:
        vai_tro_moi = await _vai_tro_theo_ma(db, du_lieu.vai_tro)  # type: ignore[arg-type]
        if dich.id == actor.id:
            raise _tu_thay_doi("đổi vai trò")
        if _la_admin_hoat_dong(dich) and admin_khac == 0:
            raise _phai_con_admin()
        cu["vai_tro"], moi["vai_tro"] = dich.vai_tro.ma, vai_tro_moi.ma
        dich.vai_tro_id = vai_tro_moi.id
        dich.vai_tro = vai_tro_moi
    if "email" in gui and du_lieu.email != dich.email.lower():
        await _dam_bao_email_chua_dung(db, du_lieu.email, tru_id=dich.id)  # type: ignore[arg-type]
        cu["email"], moi["email"] = dich.email, du_lieu.email
        dich.email = du_lieu.email  # type: ignore[assignment]
    if "ho_ten" in gui and du_lieu.ho_ten != dich.ho_ten:
        cu["ho_ten"], moi["ho_ten"] = dich.ho_ten, du_lieu.ho_ten
        dich.ho_ten = du_lieu.ho_ten  # type: ignore[assignment]
    if "so_dien_thoai" in gui and du_lieu.so_dien_thoai != dich.so_dien_thoai:
        cu["so_dien_thoai"] = che_sdt(dich.so_dien_thoai) if dich.so_dien_thoai else None
        moi["so_dien_thoai"] = che_sdt(du_lieu.so_dien_thoai) if du_lieu.so_dien_thoai else None
        dich.so_dien_thoai = du_lieu.so_dien_thoai

    if moi:
        dich.updated_at = bay_gio_utc()
        if "vai_tro" in moi:
            await phien.thu_hoi_tat_ca(db, "noi_bo", dich.id)
        await ghi_nhat_ky(
            db,
            nhan_vien_id=actor.id,
            hanh_dong="sua",
            bang=BANG,
            ban_ghi_id=dich.id,
            gia_tri_cu=cu,
            gia_tri_moi=moi,
            ip=ip,
        )
    return dich


async def khoa(db: AsyncSession, actor: NhanVien, nhan_vien_id: int, *, ip: str) -> NhanVien:
    """Khóa tài khoản: không đăng nhập/làm mới được nữa và mọi phiên bị thu hồi ngay."""
    await dam_bao_la_admin(db, actor)
    dich, admin_khac = await _khoa_dich_va_cac_admin(db, nhan_vien_id)
    if dich.id == actor.id:
        raise _tu_thay_doi("khóa")
    if dich.trang_thai == TrangThaiTaiKhoan.bi_khoa:
        return dich  # đã khóa: gọi lại vẫn thành công
    if _la_admin_hoat_dong(dich) and admin_khac == 0:
        raise _phai_con_admin()
    dich.trang_thai = TrangThaiTaiKhoan.bi_khoa
    dich.updated_at = bay_gio_utc()
    await phien.thu_hoi_tat_ca(db, "noi_bo", dich.id)
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="khoa", bang=BANG, ban_ghi_id=dich.id, ip=ip)
    return dich


async def mo_khoa(db: AsyncSession, actor: NhanVien, nhan_vien_id: int, *, ip: str) -> NhanVien:
    """Mở khóa tài khoản (cả khóa của Admin lẫn khóa tạm do đoán mật khẩu), xóa bộ đếm sai."""
    await dam_bao_la_admin(db, actor)
    dich, _ = await _khoa_dich_va_cac_admin(db, nhan_vien_id)
    if dich.trang_thai == TrangThaiTaiKhoan.hoat_dong and dich.khoa_den is None and dich.so_lan_dang_nhap_sai == 0:
        return dich
    dich.trang_thai = TrangThaiTaiKhoan.hoat_dong
    dich.khoa_den = None
    dich.so_lan_dang_nhap_sai = 0
    dich.updated_at = bay_gio_utc()
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="mo_khoa", bang=BANG, ban_ghi_id=dich.id, ip=ip)
    return dich


async def dat_lai_mat_khau(db: AsyncSession, actor: NhanVien, nhan_vien_id: int, *, ip: str) -> KetQuaCoMatKhauTam:
    """Đặt mật khẩu tạm mới, bắt đổi ở lần đăng nhập kế, xóa khóa tạm và thu hồi mọi phiên. Không mở khóa của Admin."""
    await dam_bao_la_admin(db, actor)
    dich, _ = await _khoa_dich_va_cac_admin(db, nhan_vien_id)
    if dich.id == actor.id:
        raise _tu_thay_doi("đặt lại mật khẩu của")
    mat_khau_tam = tao_mat_khau_tam()
    dich.mat_khau_hash = await bam_mat_khau_async(mat_khau_tam)
    dich.phai_doi_mat_khau = True
    dich.khoa_den = None
    dich.so_lan_dang_nhap_sai = 0
    dich.updated_at = bay_gio_utc()
    await phien.thu_hoi_tat_ca(db, "noi_bo", dich.id)
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="dat_lai_mat_khau", bang=BANG, ban_ghi_id=dich.id, ip=ip)
    return KetQuaCoMatKhauTam(dich, mat_khau_tam)


async def xoa_mem(db: AsyncSession, actor: NhanVien, nhan_vien_id: int, *, ip: str) -> None:
    """Xóa mềm (không xóa cứng: chứng từ cũ vẫn trỏ tới người lập). Thu hồi mọi phiên."""
    await dam_bao_la_admin(db, actor)
    dich, admin_khac = await _khoa_dich_va_cac_admin(db, nhan_vien_id)
    if dich.id == actor.id:
        raise _tu_thay_doi("xóa")
    if _la_admin_hoat_dong(dich) and admin_khac == 0:
        raise _phai_con_admin()
    dich.deleted_at = bay_gio_utc()
    dich.updated_at = dich.deleted_at
    await phien.thu_hoi_tat_ca(db, "noi_bo", dich.id)
    await ghi_nhat_ky(db, nhan_vien_id=actor.id, hanh_dong="xoa", bang=BANG, ban_ghi_id=dich.id, ip=ip)
