"""Seed cơ bản, cần cho mọi môi trường kể cả test: vai trò, quyền, cấu hình mặc định và Admin đầu tiên (spec 02 mục 6).

Chạy lại nhiều lần không nhân bản và KHÔNG ghi đè thứ người dùng đã chỉnh lúc chạy:
- `quyen`: danh mục do code định nghĩa nên luôn đồng bộ theo `docs/spec/data/quyen.yaml`; quyền đã bỏ khỏi yaml bị gỡ.
- `vai_tro_quyen`: chỉ cấp mặc định cho quyền MỚI (lần đầu, hoặc quyền mới thêm vào yaml ở bản phát hành sau). Quyền đã
  có thì giữ nguyên cách gán hiện tại vì Admin được gán/bỏ quyền cho vai trò lúc chạy (AD18).
- `vai_tro`: chỉ thêm vai trò còn thiếu, không đổi tên.
- `cau_hinh`: chỉ thêm khóa còn thiếu, giữ nguyên giá trị Admin đã sửa.
- Admin: chỉ tạo khi chưa có tài khoản cùng email, không đặt lại mật khẩu.
Hai tiến trình seed chạy cùng lúc được tuần tự hóa bằng khóa tư vấn của PostgreSQL.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bao_mat import TIEN_TO_GIA_TRI_MAU, bam_mat_khau, mat_khau_du_manh
from app.core.config import BACKEND_DIR
from app.core.ma_chung_tu import ma_nhan_vien
from app.models.he_thong import CauHinh, NhanVien, Quyen, VaiTro, VaiTroQuyen

QUYEN_YAML = BACKEND_DIR.parent / "docs" / "spec" / "data" / "quyen.yaml"

_MUC_QUYEN = {"day_du": None, "chi_xem": "chi_xem"}  # giá trị lưu ở vai_tro_quyen.gioi_han
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
MAT_KHAU_ADMIN_TOI_THIEU = 12
KHOA_SEED = 7306001  # khóa tư vấn pg_advisory_xact_lock cho seed (job nền dùng dải số khác)

DAU_HIEU_NGUY_HIEM = [
    "đau ngực",
    "khó thở",
    "co giật",
    "ngất",
    "nôn ra máu",
    "đi ngoài ra máu",
    "yếu liệt nửa người",
    "méo miệng",
    "sốc phản vệ",
    "sưng mặt môi lưỡi",
    "uống quá liều",
    "muốn tự tử",
    "tự làm hại bản thân",
]

# (khóa, giá trị mặc định, mô tả). Khớp bảng ở docs/spec/02-database.md mục 6 (test đối chiếu từng khóa).
CAU_HINH_MAC_DINH: list[tuple[str, Any, str]] = [
    ("nguong_can_han_ngay", 90, "Lô còn dưới số ngày này là cận hạn (ngừng bán online)"),
    ("han_su_dung_toi_thieu_nhap_ngay", 180, "Cảnh báo khi nhập lô có HSD còn dưới số ngày này"),
    ("thoi_han_thanh_toan_phut", 15, "Quá số phút này chưa thanh toán thì hủy đơn"),
    ("thoi_han_khach_xac_nhan_gio", 24, "Khách phải xác nhận đơn dược sĩ tạo trong số giờ này"),
    ("thoi_han_doi_tra_ngay", 7, "Số ngày được yêu cầu đổi trả sau khi nhận hàng"),
    ("thoi_han_nhan_tai_quay_ngay", 3, "Số ngày giữ hàng chờ khách nhận tại quầy"),
    ("thoi_gian_khoa_don_thuoc_phut", 30, "Dược sĩ nhận xử lý yêu cầu đơn thuốc được khóa trong số phút này"),
    ("hieu_luc_don_thuoc_ngay", 5, "Số ngày hiệu lực của đơn thuốc (checklist; kiểm tra lại theo quy định hiện hành)"),
    ("phi_ship_mac_dinh", 30000, "Phí ship khi adapter vận chuyển lỗi (đồng)"),
    ("mien_phi_ship_tu", 300000, "Đơn từ mức này được miễn phí ship (đồng)"),
    ("so_lan_dang_nhap_sai_toi_da", 5, "Số lần đăng nhập sai trước khi khóa tạm"),
    ("thoi_gian_khoa_dang_nhap_phut", 15, "Số phút khóa tạm sau khi đăng nhập sai quá số lần"),
    ("gioi_han_otp", {"moi_sdt_moi_gio": 5, "moi_ip_moi_gio": 20}, "Giới hạn gửi OTP"),
    (
        "gioi_han_ai",
        {"chat_moi_phien": 30, "chat_moi_ip_moi_ngay": 100, "tra_anh_moi_ip_moi_ngay": 20},
        "Giới hạn dùng AI cho khách",
    ),
    (
        "gio_lam_viec_duoc_si",
        {"bat_dau": "08:00", "ket_thuc": "21:00", "ngay_trong_tuan": [1, 2, 3, 4, 5, 6, 7]},
        "Giờ dược sĩ trực (ngoài giờ AI báo hẹn lại)",
    ),
    (
        "ai_module",
        {"tim_kiem": True, "chat": True, "tra_anh": True, "doc_don_thuoc": True, "goi_y": True, "du_bao": True},
        "Bật/tắt từng module AI",
    ),
    ("ai_dau_hieu_nguy_hiem", DAU_HIEU_NGUY_HIEM, "Cụm từ khiến chatbot chuyển ngay sang cảnh báo cấp cứu"),
    ("ai_nguong_chuyen_duoc_si", 0.6, "Độ tin cậy dưới ngưỡng này thì chatbot chuyển dược sĩ"),
    ("ai_loi_nhac_bo_sung", "", "Nối vào cuối system prompt khi mở phiên chat mới"),
]


@dataclass(frozen=True)
class TaiKhoanAdmin:
    email: str
    mat_khau: str
    ho_ten: str = "Quản trị viên"

    def __repr__(self) -> str:  # không để mật khẩu lọt vào log/traceback
        return f"TaiKhoanAdmin(email={self.email!r}, mat_khau='***')"


def _doc_quyen_yaml(duong_dan: Path) -> dict:
    du_lieu = yaml.safe_load(duong_dan.read_text(encoding="utf-8"))
    vai_tro_hop_le = {v["ma"] for v in du_lieu["vai_tro"]}
    for q in du_lieu["quyen"]:
        for vai_tro, muc in q["vai_tro"].items():
            if vai_tro not in vai_tro_hop_le or muc not in _MUC_QUYEN:
                raise ValueError(f"quyen.yaml: {q['ma']} có cấp quyền không hợp lệ ({vai_tro}: {muc})")
    return du_lieu


async def khoa_seed(db: AsyncSession) -> None:
    """Tuần tự hóa các tiến trình seed; khóa tự nhả khi transaction kết thúc."""
    await db.execute(text("SELECT pg_advisory_xact_lock(:khoa)"), {"khoa": KHOA_SEED})


async def _dong_bo_vai_tro_va_quyen(db: AsyncSession, du_lieu: dict) -> dict[str, int]:
    await db.execute(
        pg_insert(VaiTro)
        .values([{"ma": v["ma"], "ten": v["ten"]} for v in du_lieu["vai_tro"]])
        .on_conflict_do_nothing(index_elements=[VaiTro.ma])
    )
    ma_quyen = [q["ma"] for q in du_lieu["quyen"]]
    quyen_da_co = set((await db.execute(select(Quyen.ma))).scalars())
    quyen_moi = {ma for ma in ma_quyen if ma not in quyen_da_co}

    insert_quyen = pg_insert(Quyen)
    await db.execute(
        insert_quyen.values(
            [{"ma": q["ma"], "nhom": q.get("nhom"), "mo_ta": q.get("mo_ta")} for q in du_lieu["quyen"]]
        ).on_conflict_do_update(
            index_elements=[Quyen.ma], set_={"nhom": insert_quyen.excluded.nhom, "mo_ta": insert_quyen.excluded.mo_ta}
        )
    )
    id_vai_tro = {ma: id_ for id_, ma in (await db.execute(select(VaiTro.id, VaiTro.ma))).all()}
    id_quyen = {ma: id_ for id_, ma in (await db.execute(select(Quyen.id, Quyen.ma))).all()}

    # Quyền không còn trong yaml: gỡ khỏi mọi vai trò rồi xóa.
    thua = [id_ for ma, id_ in id_quyen.items() if ma not in ma_quyen]
    if thua:
        await db.execute(delete(VaiTroQuyen).where(VaiTroQuyen.quyen_id.in_(thua)))
        await db.execute(delete(Quyen).where(Quyen.id.in_(thua)))

    mac_dinh = [
        {"vai_tro_id": id_vai_tro[vai_tro], "quyen_id": id_quyen[q["ma"]], "gioi_han": _MUC_QUYEN[muc]}
        for q in du_lieu["quyen"]
        if q["ma"] in quyen_moi
        for vai_tro, muc in q["vai_tro"].items()
    ]
    if mac_dinh:
        await db.execute(pg_insert(VaiTroQuyen).values(mac_dinh).on_conflict_do_nothing())
    so_cap = (await db.execute(select(func.count()).select_from(VaiTroQuyen))).scalar_one()
    return {
        "vai_tro": len(id_vai_tro),
        "quyen": len(ma_quyen),
        "quyen_moi": len(quyen_moi),
        "vai_tro_quyen": so_cap,
    }


async def _them_cau_hinh_con_thieu(db: AsyncSession) -> int:
    """Chỉ chèn khóa chưa có; trả số khóa mới thêm."""
    ket_qua = await db.execute(
        pg_insert(CauHinh)
        .values([{"khoa": k, "gia_tri": v, "mo_ta": mo_ta} for k, v, mo_ta in CAU_HINH_MAC_DINH])
        .on_conflict_do_nothing(index_elements=[CauHinh.khoa])
        .returning(CauHinh.khoa)
    )
    return len(ket_qua.all())


def kiem_tra_admin(admin: TaiKhoanAdmin) -> str:
    """Kiểm tra email và mật khẩu, trả email đã chuẩn hóa. Sai thì raise ValueError (thông điệp không chứa mật khẩu).

    Mật khẩu Admin đầu tiên chặt hơn mật khẩu thường (spec 06: 8 ký tự): tối thiểu 12 ký tự và không được là giá trị
    mẫu công khai trong `.env.example`, vì tài khoản này giữ toàn quyền và được tạo từ file cấu hình.
    """
    email = admin.email.strip().lower()
    if not _EMAIL.fullmatch(email):
        raise ValueError(f"Admin: email không hợp lệ: {admin.email!r}")
    if admin.mat_khau.startswith(TIEN_TO_GIA_TRI_MAU):
        raise ValueError("Admin: mật khẩu vẫn là giá trị mẫu của .env.example, hãy đặt mật khẩu riêng")
    if len(admin.mat_khau) < MAT_KHAU_ADMIN_TOI_THIEU or not mat_khau_du_manh(admin.mat_khau):
        raise ValueError(f"Admin: mật khẩu cần tối thiểu {MAT_KHAU_ADMIN_TOI_THIEU} ký tự, gồm cả chữ và số")
    return email


async def co_admin_hoat_dong(db: AsyncSession) -> bool:
    """Đã có ít nhất một Admin hoạt động chưa (để CLI biết lần chạy đầu bắt buộc phải có ADMIN_EMAIL)."""
    dem = await db.execute(
        select(func.count())
        .select_from(NhanVien)
        .join(VaiTro, VaiTro.id == NhanVien.vai_tro_id)
        .where(VaiTro.ma == "ADMIN", NhanVien.trang_thai == "hoat_dong", NhanVien.deleted_at.is_(None))
    )
    return dem.scalar_one() > 0


async def _tao_admin(db: AsyncSession, admin: TaiKhoanAdmin) -> str:
    email = kiem_tra_admin(admin)  # kiểm tra trước khi đụng DB để lỗi cấu hình không để lại dữ liệu dở dang
    da_co = (
        await db.execute(
            select(VaiTro.ma).join(NhanVien, NhanVien.vai_tro_id == VaiTro.id).where(NhanVien.email == email)
        )
    ).first()
    if da_co:
        if da_co[0] != "ADMIN":
            raise ValueError(f"Admin: email {email} đã thuộc nhân viên vai trò {da_co[0]}, không phải Admin")
        return "da_co"
    vai_tro_id = (await db.execute(select(VaiTro.id).where(VaiTro.ma == "ADMIN"))).scalar_one()
    db.add(
        NhanVien(
            ma_nhan_vien=await ma_nhan_vien(db),
            ho_ten=admin.ho_ten,
            email=email,
            mat_khau_hash=bam_mat_khau(admin.mat_khau),
            vai_tro_id=vai_tro_id,
            phai_doi_mat_khau=True,
        )
    )
    await db.flush()
    return "da_tao"


async def seed_co_ban(
    db: AsyncSession, *, admin: TaiKhoanAdmin | None = None, duong_dan_quyen: Path = QUYEN_YAML
) -> dict[str, Any]:
    """Seed vai trò, quyền, cấu hình mặc định và (nếu có `admin`) Admin đầu tiên. Không commit: người gọi quản lý."""
    if admin is not None:
        kiem_tra_admin(admin)
    await khoa_seed(db)
    ket_qua: dict[str, Any] = await _dong_bo_vai_tro_va_quyen(db, _doc_quyen_yaml(duong_dan_quyen))
    ket_qua["cau_hinh_moi"] = await _them_cau_hinh_con_thieu(db)
    ket_qua["admin"] = await _tao_admin(db, admin) if admin is not None else "bo_qua"
    return ket_qua
