"""Nghiệp vụ tài khoản nhân viên: đăng nhập, đổi mật khẩu, hồ sơ cá nhân (NV01, NV02).

Mọi lỗi cần giữ thay đổi ở DB (bộ đếm sai, khóa tạm) được trả bằng kết quả/enum; route TRẢ VỀ lỗi chứ không raise.
"""

from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import bam_mat_khau_async
from app.core.dien_thoai import che_sdt
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import quyen_cua_vai_tro
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import NhanVien, VaiTro
from app.modules.nhan_vien.schemas import CapNhatHoSoYeuCau, NhanVienToi, VaiTroDoc
from app.modules.tai_khoan import dang_nhap, phien
from app.modules.tai_khoan.dang_nhap import KetQuaDangNhap
from app.modules.tai_khoan.phien import CapToken


async def dung_ho_so(db: AsyncSession, nhan_vien: NhanVien) -> NhanVienToi:
    """Hồ sơ + quyền của nhân viên (quyền đọc từ DB, cache 60 giây)."""
    vai_tro = (await db.execute(select(VaiTro).where(VaiTro.id == nhan_vien.vai_tro_id))).scalar_one()
    return NhanVienToi(
        id=nhan_vien.id,
        ma_nhan_vien=nhan_vien.ma_nhan_vien,
        ho_ten=nhan_vien.ho_ten,
        email=nhan_vien.email,
        so_dien_thoai=nhan_vien.so_dien_thoai,
        vai_tro=VaiTroDoc(ma=vai_tro.ma, ten=vai_tro.ten),
        phai_doi_mat_khau=nhan_vien.phai_doi_mat_khau,
        quyen=dict(await quyen_cua_vai_tro(db, nhan_vien.vai_tro_id)),
    )


@dataclass(frozen=True)
class KetQuaDangNhapNhanVien:
    ket_qua: KetQuaDangNhap
    nhan_vien: NhanVien | None = None
    cap_token: CapToken | None = None
    thu_lai_sau_giay: int | None = None


async def dang_nhap_nhan_vien(
    db: AsyncSession, *, email: str, mat_khau: str, ip: str, thiet_bi: str | None
) -> KetQuaDangNhapNhanVien:
    """Kiểm tra email + mật khẩu, tạo phiên khi đúng và ghi nhật ký (đăng nhập thành công, bị khóa tạm)."""
    kq = await dang_nhap.kiem_tra_dang_nhap_nhan_vien(db, email=email, mat_khau=mat_khau)
    if kq.ket_qua is not KetQuaDangNhap.OK:
        if kq.vua_bi_khoa:
            await ghi_nhat_ky(
                db, nhan_vien_id=kq.tai_khoan.id, hanh_dong="khoa_tam_dang_nhap", bang="nhan_vien",
                ban_ghi_id=kq.tai_khoan.id, ip=ip,
            )  # fmt: skip
        return KetQuaDangNhapNhanVien(kq.ket_qua, thu_lai_sau_giay=kq.thu_lai_sau_giay)
    nhan_vien = kq.tai_khoan
    cap = await phien.tao_phien(db, loai="noi_bo", chu_id=nhan_vien.id, thiet_bi=thiet_bi, ip=ip)
    await ghi_nhat_ky(
        db, nhan_vien_id=nhan_vien.id, hanh_dong="dang_nhap", bang="nhan_vien", ban_ghi_id=nhan_vien.id, ip=ip
    )
    return KetQuaDangNhapNhanVien(KetQuaDangNhap.OK, nhan_vien, cap)


class KetQuaDoiMatKhau(StrEnum):
    OK = "ok"
    MAT_KHAU_CU_SAI = "mat_khau_cu_sai"
    KHOA_TAM = "khoa_tam"


@dataclass(frozen=True)
class KetQuaDoiMatKhauNhanVien:
    ket_qua: KetQuaDoiMatKhau
    nhan_vien: NhanVien | None = None
    cap_token: CapToken | None = None
    thu_lai_sau_giay: int | None = None


async def doi_mat_khau(
    db: AsyncSession, nhan_vien_id: int, *, mat_khau_cu: str, mat_khau_moi: str, ip: str, thiet_bi: str | None
) -> KetQuaDoiMatKhauNhanVien:
    """Đổi mật khẩu của chính mình (NV01).

    - Mật khẩu cũ sai bị đếm như đăng nhập sai: đủ số lần thì khóa tạm VÀ thu hồi mọi phiên (người đang gọi nhiều khả
      năng cầm một phiên bị đánh cắp), nên kẻ có access token cũng không dò được mật khẩu.
    - Thành công: mọi phiên cũ bị thu hồi, bỏ cờ `phai_doi_mat_khau`, cấp một phiên mới cho thiết bị đang đổi.
    """
    nhan_vien = (
        await db.execute(
            select(NhanVien)
            .where(NhanVien.id == nhan_vien_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    kq = await dang_nhap.kiem_tra_mat_khau_va_khoa(db, nhan_vien, mat_khau_cu)
    if kq.ket_qua is KetQuaDangNhap.KHOA_TAM:
        if kq.vua_bi_khoa:
            await phien.thu_hoi_tat_ca(db, "noi_bo", nhan_vien.id)
            await ghi_nhat_ky(
                db, nhan_vien_id=nhan_vien.id, hanh_dong="khoa_tam_doi_mat_khau", bang="nhan_vien",
                ban_ghi_id=nhan_vien.id, ip=ip,
            )  # fmt: skip
        return KetQuaDoiMatKhauNhanVien(KetQuaDoiMatKhau.KHOA_TAM, thu_lai_sau_giay=kq.thu_lai_sau_giay)
    if kq.ket_qua is not KetQuaDangNhap.OK:
        return KetQuaDoiMatKhauNhanVien(KetQuaDoiMatKhau.MAT_KHAU_CU_SAI)

    nhan_vien.mat_khau_hash = await bam_mat_khau_async(mat_khau_moi)
    nhan_vien.phai_doi_mat_khau = False
    nhan_vien.updated_at = bay_gio_utc()
    await phien.thu_hoi_tat_ca(db, "noi_bo", nhan_vien.id)
    cap = await phien.tao_phien(db, loai="noi_bo", chu_id=nhan_vien.id, thiet_bi=thiet_bi, ip=ip)
    await ghi_nhat_ky(
        db, nhan_vien_id=nhan_vien.id, hanh_dong="doi_mat_khau", bang="nhan_vien", ban_ghi_id=nhan_vien.id, ip=ip
    )
    return KetQuaDoiMatKhauNhanVien(KetQuaDoiMatKhau.OK, nhan_vien, cap)


async def cap_nhat_ho_so(db: AsyncSession, nhan_vien: NhanVien, du_lieu: CapNhatHoSoYeuCau, *, ip: str) -> NhanVien:
    """Cập nhật họ tên/số điện thoại của chính mình (NV02); chỉ đổi trường client có gửi, ghi nhật ký giá trị cũ/mới."""
    gui = du_lieu.model_fields_set
    cu: dict[str, str | None] = {}
    moi: dict[str, str | None] = {}
    if "ho_ten" in gui and du_lieu.ho_ten != nhan_vien.ho_ten:
        cu["ho_ten"], moi["ho_ten"] = nhan_vien.ho_ten, du_lieu.ho_ten
        nhan_vien.ho_ten = du_lieu.ho_ten  # type: ignore[assignment]
    if "so_dien_thoai" in gui and du_lieu.so_dien_thoai != nhan_vien.so_dien_thoai:
        # Chỉ ghi số đã che vào nhật ký, không ghi số đầy đủ.
        cu["so_dien_thoai"] = che_sdt(nhan_vien.so_dien_thoai) if nhan_vien.so_dien_thoai else None
        moi["so_dien_thoai"] = che_sdt(du_lieu.so_dien_thoai) if du_lieu.so_dien_thoai else None
        nhan_vien.so_dien_thoai = du_lieu.so_dien_thoai
    if moi:
        nhan_vien.updated_at = bay_gio_utc()
        await ghi_nhat_ky(
            db, nhan_vien_id=nhan_vien.id, hanh_dong="sua", bang="nhan_vien", ban_ghi_id=nhan_vien.id,
            gia_tri_cu=cu, gia_tri_moi=moi, ip=ip,
        )  # fmt: skip
    return nhan_vien
