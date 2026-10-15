"""Migration nền: extension, 33 enum và 65 bảng theo docs/database/ERD_da_chinh_sua.dbml.

Sinh bằng `alembic revision --autogenerate` rồi chỉnh tay: enum được tạo tường minh một lần (autogenerate sinh
`sa.Enum` inline nên CREATE TYPE bị lặp với enum dùng chung); thêm extension; DROP TYPE ở downgrade.
Ràng buộc bổ sung (CHECK, partial unique, GIN/HNSW, sequence) nằm ở migration 0002.

Revision ID: 0001
Revises:
Create Date: 2026-10-15
"""

from typing import Sequence, Union

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        "CREATE TYPE loai_san_pham AS ENUM ('thuoc_ke_don', 'thuoc_khong_ke_don', 'thuc_pham_chuc_nang', 'duoc_my_pham', 'thiet_bi_y_te')"
    )
    op.execute("CREATE TYPE trang_thai_kinh_doanh AS ENUM ('dang_kinh_doanh', 'ngung_kinh_doanh')")
    op.execute("CREATE TYPE trang_thai_noi_dung AS ENUM ('nhap', 'da_duyet', 'luu_tru')")
    op.execute("CREATE TYPE trang_thai_lo AS ENUM ('dang_ban', 'can_han', 'khoa', 'het_han', 'thu_hoi')")
    op.execute(
        "CREATE TYPE trang_thai_don AS ENUM ('cho_khach_xac_nhan', 'cho_thanh_toan', 'cho_xac_nhan', 'da_xac_nhan', 'dang_soan_hang', 'cho_lay_hang', 'dang_giao', 'da_giao', 'hoan_tat', 'giao_that_bai', 'hoan_ve_kho', 'da_huy')"
    )
    op.execute("CREATE TYPE kenh_ban AS ENUM ('online', 'dien_thoai', 'tai_quay')")
    op.execute("CREATE TYPE hinh_thuc_nhan AS ENUM ('giao_tan_noi', 'nhan_tai_nha_thuoc')")
    op.execute("CREATE TYPE phuong_thuc_thanh_toan AS ENUM ('cod', 'vnpay', 'momo', 'tien_mat', 'chuyen_khoan')")
    op.execute(
        "CREATE TYPE trang_thai_thanh_toan AS ENUM ('chua_thanh_toan', 'da_thanh_toan', 'cho_hoan_tien', 'hoan_tien_mot_phan', 'da_hoan_tien')"
    )
    op.execute("CREATE TYPE loai_giao_dich AS ENUM ('thanh_toan', 'hoan_tien')")
    op.execute("CREATE TYPE trang_thai_giao_dich AS ENUM ('khoi_tao', 'thanh_cong', 'that_bai')")
    op.execute("CREATE TYPE trang_thai_phan_bo AS ENUM ('dang_giu', 'da_xuat', 'da_nha', 'da_hoan_nhap')")
    op.execute("CREATE TYPE khu_ton AS ENUM ('kho_ban', 'biet_tru')")
    op.execute(
        "CREATE TYPE loai_bien_dong AS ENUM ('nhap_kho', 'xuat_ban', 'hoan_nhap', 'nhan_tra_ve', 'dieu_chinh', 'huy_hang', 'xuat_tra_ncc')"
    )
    op.execute("CREATE TYPE loai_van_don AS ENUM ('giao_hang', 'tra_hang')")
    op.execute("CREATE TYPE muc_do_tuong_tac AS ENUM ('nhe', 'trung_binh', 'nghiem_trong', 'chong_chi_dinh')")
    op.execute("CREATE TYPE loai_bai_viet AS ENUM ('bai_viet', 'chinh_sach', 'faq')")
    op.execute(
        "CREATE TYPE trang_thai_yeu_cau_don_thuoc AS ENUM ('cho_duyet', 'dang_tu_van', 'da_tao_don', 'tu_choi', 'khach_huy')"
    )
    op.execute("CREATE TYPE trang_thai_duyet AS ENUM ('cho_duyet', 'da_duyet', 'tu_choi')")
    op.execute("CREATE TYPE ly_do_huy_hang AS ENUM ('het_han', 'hu_hong', 'hang_tra_ve', 'thu_hoi', 'khac')")
    op.execute(
        "CREATE TYPE ly_do_doi_tra AS ENUM ('giao_sai_san_pham', 'sai_so_luong', 'hu_hong', 'het_han_can_han', 'khac')"
    )
    op.execute("CREATE TYPE trang_thai_doi_tra AS ENUM ('cho_duyet', 'da_duyet', 'tu_choi', 'kho_da_nhan', 'hoan_tat')")
    op.execute("CREATE TYPE huong_xu_ly_doi_tra AS ENUM ('hoan_tien', 'gui_hang_thay_the')")
    op.execute("CREATE TYPE loai_giam_gia AS ENUM ('phan_tram', 'so_tien')")
    op.execute("CREATE TYPE pham_vi_khuyen_mai AS ENUM ('toan_bo', 'danh_muc', 'san_pham')")
    op.execute("CREATE TYPE trang_thai_tai_khoan AS ENUM ('hoat_dong', 'bi_khoa')")
    op.execute("CREATE TYPE trang_thai_kiem_ke AS ENUM ('dang_kiem', 'da_chot')")
    op.execute("CREATE TYPE trang_thai_thu_hoi AS ENUM ('dang_thu_hoi', 'hoan_tat')")
    op.execute(
        "CREATE TYPE ket_qua_lien_he_thu_hoi AS ENUM ('chua_lien_he', 'da_lien_he', 'da_hen_tra_hang', 'da_thu_ve', 'khong_lien_lac_duoc')"
    )
    op.execute("CREATE TYPE loai_hoi_thoai AS ENUM ('ai', 'duoc_si')")
    op.execute(
        "CREATE TYPE trang_thai_hoi_thoai AS ENUM ('dang_mo', 'cho_duoc_si', 'duoc_si_dang_xu_ly', 'cho_goi_lai', 'da_dong')"
    )
    op.execute("CREATE TYPE vai_tro_tin_nhan AS ENUM ('khach', 'ai', 'duoc_si', 'he_thong')")
    op.execute("CREATE TYPE nguon_tri_thuc AS ENUM ('san_pham', 'bai_viet', 'chinh_sach', 'faq')")

    op.create_table(
        "banner",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("tieu_de", sa.String(length=200), nullable=True),
        sa.Column("anh_url", sa.String(length=500), nullable=False),
        sa.Column("lien_ket", sa.String(length=500), nullable=True),
        sa.Column("vi_tri", sa.String(length=30), nullable=False),
        sa.Column("thu_tu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("bat_dau", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ket_thuc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dang_hien", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_banner")),
    )
    op.create_table(
        "danh_muc",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("danh_muc_cha_id", sa.Integer(), nullable=True),
        sa.Column("anh_url", sa.String(length=500), nullable=True),
        sa.Column("thu_tu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dang_hien_thi", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["danh_muc_cha_id"], ["danh_muc.id"], name=op.f("fk_danh_muc_danh_muc_cha_id_danh_muc")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_danh_muc")),
        sa.UniqueConstraint("slug", name=op.f("uq_danh_muc_slug")),
    )
    op.create_index("ix_danh_muc__danh_muc_cha_id", "danh_muc", ["danh_muc_cha_id"], unique=False)
    op.create_table(
        "hoat_chat",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("ten_khac", sa.Text(), nullable=True),
        sa.Column("mo_ta", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hoat_chat")),
        sa.UniqueConstraint("ten", name=op.f("uq_hoat_chat_ten")),
    )
    op.create_table(
        "khach_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ho_ten", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("so_dien_thoai", sa.String(length=20), nullable=False),
        sa.Column("mat_khau_hash", sa.String(length=255), nullable=False),
        sa.Column("gioi_tinh", sa.String(length=10), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("hoat_dong", "bi_khoa", name="trang_thai_tai_khoan", create_type=False),
            server_default="hoat_dong",
            nullable=False,
        ),
        sa.Column("so_lan_dang_nhap_sai", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("khoa_den", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dong_y_chinh_sach_luc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_khach_hang")),
        sa.UniqueConstraint("email", name=op.f("uq_khach_hang_email")),
        sa.UniqueConstraint("so_dien_thoai", name=op.f("uq_khach_hang_so_dien_thoai")),
    )
    op.create_table(
        "khuyen_mai",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column(
            "loai_giam",
            postgresql.ENUM("phan_tram", "so_tien", name="loai_giam_gia", create_type=False),
            nullable=False,
        ),
        sa.Column("gia_tri", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("giam_toi_da", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("don_toi_thieu", sa.Numeric(precision=14, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("bat_dau", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ket_thuc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tong_luot", sa.Integer(), nullable=True),
        sa.Column("luot_moi_khach", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "pham_vi",
            postgresql.ENUM("toan_bo", "danh_muc", "san_pham", name="pham_vi_khuyen_mai", create_type=False),
            server_default="toan_bo",
            nullable=False,
        ),
        sa.Column("dang_hoat_dong", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_khuyen_mai")),
    )
    op.create_table(
        "ma_otp",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("dich_den", sa.String(length=150), nullable=False),
        sa.Column("ma_hash", sa.String(length=255), nullable=False),
        sa.Column("muc_dich", sa.String(length=30), nullable=False),
        sa.Column("het_han", sa.DateTime(timezone=True), nullable=False),
        sa.Column("so_lan_thu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("da_dung", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ma_otp")),
    )
    op.create_index(
        "ix_ma_otp__dich_den_muc_dich_created_at", "ma_otp", ["dich_den", "muc_dich", "created_at"], unique=False
    )
    op.create_table(
        "nha_cung_cap",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("ma_so_thue", sa.String(length=20), nullable=True),
        sa.Column("dia_chi", sa.String(length=500), nullable=True),
        sa.Column("nguoi_lien_he", sa.String(length=150), nullable=True),
        sa.Column("so_dien_thoai", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=150), nullable=True),
        sa.Column("dang_hop_tac", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nha_cung_cap")),
        sa.UniqueConstraint("ma_so_thue", name=op.f("uq_nha_cung_cap_ma_so_thue")),
    )
    op.create_table(
        "nha_san_xuat",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=200), nullable=False),
        sa.Column("quoc_gia", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nha_san_xuat")),
    )
    op.create_index("uq_nha_san_xuat__ten_quoc_gia", "nha_san_xuat", ["ten", "quoc_gia"], unique=True)
    op.create_table(
        "quyen",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma", sa.String(length=60), nullable=False),
        sa.Column("nhom", sa.String(length=50), nullable=True),
        sa.Column("mo_ta", sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_quyen")),
        sa.UniqueConstraint("ma", name=op.f("uq_quyen_ma")),
    )
    op.create_table(
        "thuong_hieu",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ten", sa.String(length=150), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thuong_hieu")),
        sa.UniqueConstraint("ten", name=op.f("uq_thuong_hieu_ten")),
    )
    op.create_table(
        "vai_tro",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma", sa.String(length=30), nullable=False),
        sa.Column("ten", sa.String(length=100), nullable=False),
        sa.Column("mo_ta", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vai_tro")),
        sa.UniqueConstraint("ma", name=op.f("uq_vai_tro_ma")),
    )
    op.create_table(
        "di_ung",
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("hoat_chat_id", sa.Integer(), nullable=False),
        sa.Column("ghi_chu", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["hoat_chat_id"], ["hoat_chat.id"], name=op.f("fk_di_ung_hoat_chat_id_hoat_chat")),
        sa.ForeignKeyConstraint(["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_di_ung_khach_hang_id_khach_hang")),
        sa.PrimaryKeyConstraint("khach_hang_id", "hoat_chat_id", name=op.f("pk_di_ung")),
    )
    op.create_table(
        "dia_chi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("ten_nguoi_nhan", sa.String(length=150), nullable=False),
        sa.Column("so_dien_thoai", sa.String(length=20), nullable=False),
        sa.Column("dia_chi_chi_tiet", sa.String(length=300), nullable=False),
        sa.Column("ma_tinh", sa.String(length=20), nullable=False),
        sa.Column("ten_tinh", sa.String(length=100), nullable=True),
        sa.Column("ma_quan_huyen", sa.String(length=20), nullable=True),
        sa.Column("ma_phuong_xa", sa.String(length=20), nullable=False),
        sa.Column("ten_phuong_xa", sa.String(length=100), nullable=True),
        sa.Column("la_mac_dinh", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_dia_chi_khach_hang_id_khach_hang")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_dia_chi")),
    )
    op.create_index("ix_dia_chi__khach_hang_id", "dia_chi", ["khach_hang_id"], unique=False)
    op.create_table(
        "gio_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_gio_hang_khach_hang_id_khach_hang")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gio_hang")),
        sa.UniqueConstraint("khach_hang_id", name=op.f("uq_gio_hang_khach_hang_id")),
    )
    op.create_table(
        "ho_so_suc_khoe",
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("nam_sinh", sa.Integer(), nullable=True),
        sa.Column("benh_nen", sa.Text(), nullable=True),
        sa.Column("dang_mang_thai", sa.Boolean(), nullable=True),
        sa.Column("dang_cho_con_bu", sa.Boolean(), nullable=True),
        sa.Column("dong_y_su_dung", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("dong_y_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_ho_so_suc_khoe_khach_hang_id_khach_hang")
        ),
        sa.PrimaryKeyConstraint("khach_hang_id", name=op.f("pk_ho_so_suc_khoe")),
    )
    op.create_table(
        "lich_su_tim_kiem",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("ma_phien", sa.String(length=64), nullable=True),
        sa.Column("tu_khoa", sa.String(length=255), nullable=False),
        sa.Column("che_do", sa.String(length=20), nullable=True),
        sa.Column("so_ket_qua", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_lich_su_tim_kiem_khach_hang_id_khach_hang")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lich_su_tim_kiem")),
    )
    op.create_index("ix_lich_su_tim_kiem__created_at", "lich_su_tim_kiem", ["created_at"], unique=False)
    op.create_index("ix_lich_su_tim_kiem__so_ket_qua", "lich_su_tim_kiem", ["so_ket_qua"], unique=False)
    op.create_table(
        "ma_giam_gia",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("khuyen_mai_id", sa.Integer(), nullable=False),
        sa.Column("ma", sa.String(length=30), nullable=False),
        sa.Column("so_luot_da_dung", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khuyen_mai_id"], ["khuyen_mai.id"], name=op.f("fk_ma_giam_gia_khuyen_mai_id_khuyen_mai")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ma_giam_gia")),
        sa.UniqueConstraint("ma", name=op.f("uq_ma_giam_gia_ma")),
    )
    op.create_index("ix_ma_giam_gia__khuyen_mai_id", "ma_giam_gia", ["khuyen_mai_id"], unique=False)
    op.create_table(
        "nhan_vien",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_nhan_vien", sa.String(length=20), nullable=False),
        sa.Column("ho_ten", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=150), nullable=False),
        sa.Column("so_dien_thoai", sa.String(length=20), nullable=True),
        sa.Column("mat_khau_hash", sa.String(length=255), nullable=False),
        sa.Column("vai_tro_id", sa.Integer(), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("hoat_dong", "bi_khoa", name="trang_thai_tai_khoan", create_type=False),
            server_default="hoat_dong",
            nullable=False,
        ),
        sa.Column("phai_doi_mat_khau", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("so_lan_dang_nhap_sai", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("khoa_den", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["vai_tro_id"], ["vai_tro.id"], name=op.f("fk_nhan_vien_vai_tro_id_vai_tro")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nhan_vien")),
        sa.UniqueConstraint("email", name=op.f("uq_nhan_vien_email")),
        sa.UniqueConstraint("ma_nhan_vien", name=op.f("uq_nhan_vien_ma_nhan_vien")),
    )
    op.create_table(
        "san_pham",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("ten", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=280), nullable=False),
        sa.Column(
            "loai_san_pham",
            postgresql.ENUM(
                "thuoc_ke_don",
                "thuoc_khong_ke_don",
                "thuc_pham_chuc_nang",
                "duoc_my_pham",
                "thiet_bi_y_te",
                name="loai_san_pham",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("danh_muc_id", sa.Integer(), nullable=False),
        sa.Column("thuong_hieu_id", sa.Integer(), nullable=True),
        sa.Column("nha_san_xuat_id", sa.Integer(), nullable=True),
        sa.Column("so_dang_ky", sa.String(length=50), nullable=True),
        sa.Column("dang_bao_che", sa.String(length=100), nullable=True),
        sa.Column("quy_cach", sa.String(length=150), nullable=True),
        sa.Column("doi_tuong_su_dung", sa.String(length=150), nullable=True),
        sa.Column("don_vi_co_so", sa.String(length=30), nullable=False),
        sa.Column("ton_toi_thieu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("dung_dinh_ky", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("so_ngay_dung_moi_don_vi", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("so_luong_toi_da_moi_don", sa.Integer(), nullable=True),
        sa.Column("la_noi_bat", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("dang_kinh_doanh", "ngung_kinh_doanh", name="trang_thai_kinh_doanh", create_type=False),
            server_default="dang_kinh_doanh",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["danh_muc_id"], ["danh_muc.id"], name=op.f("fk_san_pham_danh_muc_id_danh_muc")),
        sa.ForeignKeyConstraint(
            ["nha_san_xuat_id"], ["nha_san_xuat.id"], name=op.f("fk_san_pham_nha_san_xuat_id_nha_san_xuat")
        ),
        sa.ForeignKeyConstraint(
            ["thuong_hieu_id"], ["thuong_hieu.id"], name=op.f("fk_san_pham_thuong_hieu_id_thuong_hieu")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_san_pham")),
        sa.UniqueConstraint("sku", name=op.f("uq_san_pham_sku")),
        sa.UniqueConstraint("slug", name=op.f("uq_san_pham_slug")),
    )
    op.create_index("ix_san_pham__danh_muc_id_trang_thai", "san_pham", ["danh_muc_id", "trang_thai"], unique=False)
    op.create_index("ix_san_pham__loai_san_pham", "san_pham", ["loai_san_pham"], unique=False)
    op.create_index("ix_san_pham__so_dang_ky", "san_pham", ["so_dang_ky"], unique=False)
    op.create_table(
        "vai_tro_quyen",
        sa.Column("vai_tro_id", sa.Integer(), nullable=False),
        sa.Column("quyen_id", sa.Integer(), nullable=False),
        sa.Column("gioi_han", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["quyen_id"], ["quyen.id"], name=op.f("fk_vai_tro_quyen_quyen_id_quyen")),
        sa.ForeignKeyConstraint(["vai_tro_id"], ["vai_tro.id"], name=op.f("fk_vai_tro_quyen_vai_tro_id_vai_tro")),
        sa.PrimaryKeyConstraint("vai_tro_id", "quyen_id", name=op.f("pk_vai_tro_quyen")),
    )
    op.create_table(
        "anh_san_pham",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("thu_tu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("la_anh_chinh", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_anh_san_pham_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anh_san_pham")),
    )
    op.create_index("ix_anh_san_pham__san_pham_id", "anh_san_pham", ["san_pham_id"], unique=False)
    op.create_table(
        "bai_viet",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("tieu_de", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=280), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("anh_bia_url", sa.String(length=500), nullable=True),
        sa.Column(
            "loai",
            postgresql.ENUM("bai_viet", "chinh_sach", "faq", name="loai_bai_viet", create_type=False),
            server_default="bai_viet",
            nullable=False,
        ),
        sa.Column("tac_gia_id", sa.Integer(), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("nhap", "da_duyet", "luu_tru", name="trang_thai_noi_dung", create_type=False),
            server_default="nhap",
            nullable=False,
        ),
        sa.Column("dua_vao_ai", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("duoc_si_duyet_id", sa.Integer(), nullable=True),
        sa.Column("ngay_duyet", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["duoc_si_duyet_id"], ["nhan_vien.id"], name=op.f("fk_bai_viet_duoc_si_duyet_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(["tac_gia_id"], ["nhan_vien.id"], name=op.f("fk_bai_viet_tac_gia_id_nhan_vien")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bai_viet")),
        sa.UniqueConstraint("slug", name=op.f("uq_bai_viet_slug")),
    )
    op.create_table(
        "cau_hinh",
        sa.Column("khoa", sa.String(length=80), nullable=False),
        sa.Column("gia_tri", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("mo_ta", sa.String(length=255), nullable=True),
        sa.Column("nhan_vien_cap_nhat_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["nhan_vien_cap_nhat_id"], ["nhan_vien.id"], name=op.f("fk_cau_hinh_nhan_vien_cap_nhat_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("khoa", name=op.f("pk_cau_hinh")),
    )
    op.create_table(
        "de_xuat_nhap_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("ky_bat_dau", sa.Date(), nullable=False),
        sa.Column("ky_ket_thuc", sa.Date(), nullable=False),
        sa.Column("so_luong_du_bao", sa.Integer(), nullable=False),
        sa.Column("ton_kha_dung", sa.Integer(), nullable=False),
        sa.Column("so_luong_de_xuat", sa.Integer(), nullable=False),
        sa.Column("mo_hinh", sa.String(length=50), nullable=True),
        sa.Column("sai_so_mape", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("da_xu_ly", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["san_pham_id"], ["san_pham.id"], name=op.f("fk_de_xuat_nhap_hang_san_pham_id_san_pham")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_de_xuat_nhap_hang")),
    )
    op.create_index(
        "uq_de_xuat_nhap_hang__ky_bat_dau_san_pham_id", "de_xuat_nhap_hang", ["ky_bat_dau", "san_pham_id"], unique=True
    )
    op.create_table(
        "don_vi_quy_doi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("ten_don_vi", sa.String(length=30), nullable=False),
        sa.Column("he_so", sa.Integer(), nullable=False),
        sa.Column("gia_ban", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("ban_online", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("la_mac_dinh", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ma_vach", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_don_vi_quy_doi_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_don_vi_quy_doi")),
    )
    op.create_index("ix_don_vi_quy_doi__ma_vach", "don_vi_quy_doi", ["ma_vach"], unique=False)
    op.create_index("uq_don_vi_quy_doi__id_san_pham_id", "don_vi_quy_doi", ["id", "san_pham_id"], unique=True)
    op.create_index(
        "uq_don_vi_quy_doi__san_pham_id_ten_don_vi", "don_vi_quy_doi", ["san_pham_id", "ten_don_vi"], unique=True
    )
    op.create_table(
        "hoi_dap",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("cau_hoi", sa.Text(), nullable=False),
        sa.Column("tra_loi", sa.Text(), nullable=True),
        sa.Column("nhan_vien_tra_loi_id", sa.Integer(), nullable=True),
        sa.Column("tra_loi_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dang_hien", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_hoi_dap_khach_hang_id_khach_hang")),
        sa.ForeignKeyConstraint(
            ["nhan_vien_tra_loi_id"], ["nhan_vien.id"], name=op.f("fk_hoi_dap_nhan_vien_tra_loi_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_hoi_dap_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hoi_dap")),
    )
    op.create_index(
        "ix_hoi_dap__san_pham_id_dang_hien_created_at",
        "hoi_dap",
        ["san_pham_id", "dang_hien", "created_at"],
        unique=False,
    )
    op.create_index("ix_hoi_dap__tra_loi_luc", "hoi_dap", ["tra_loi_luc"], unique=False)
    op.create_table(
        "hoi_thoai",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phien", sa.Uuid(), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column(
            "loai",
            postgresql.ENUM("ai", "duoc_si", name="loai_hoi_thoai", create_type=False),
            server_default="ai",
            nullable=False,
        ),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "dang_mo",
                "cho_duoc_si",
                "duoc_si_dang_xu_ly",
                "cho_goi_lai",
                "da_dong",
                name="trang_thai_hoi_thoai",
                create_type=False,
            ),
            server_default="dang_mo",
            nullable=False,
        ),
        sa.Column("duoc_si_id", sa.Integer(), nullable=True),
        sa.Column("tom_tat", sa.Text(), nullable=True),
        sa.Column("so_dien_thoai_goi_lai", sa.String(length=20), nullable=True),
        sa.Column("bi_gan_co", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("ly_do_gan_co", sa.String(length=100), nullable=True),
        sa.Column("ip_hash", sa.String(length=128), nullable=True),
        sa.Column("tong_token", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chi_phi", sa.Numeric(precision=12, scale=6), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dong_luc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["duoc_si_id"], ["nhan_vien.id"], name=op.f("fk_hoi_thoai_duoc_si_id_nhan_vien")),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_hoi_thoai_khach_hang_id_khach_hang")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_hoi_thoai")),
        sa.UniqueConstraint("ma_phien", name=op.f("uq_hoi_thoai_ma_phien")),
    )
    op.create_index("ix_hoi_thoai__bi_gan_co", "hoi_thoai", ["bi_gan_co"], unique=False)
    op.create_index("ix_hoi_thoai__duoc_si_id_trang_thai", "hoi_thoai", ["duoc_si_id", "trang_thai"], unique=False)
    op.create_index("ix_hoi_thoai__khach_hang_id", "hoi_thoai", ["khach_hang_id"], unique=False)
    op.create_index("ix_hoi_thoai__trang_thai_created_at", "hoi_thoai", ["trang_thai", "created_at"], unique=False)
    op.create_table(
        "khuyen_mai_pham_vi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("khuyen_mai_id", sa.Integer(), nullable=False),
        sa.Column("danh_muc_id", sa.Integer(), nullable=True),
        sa.Column("san_pham_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["danh_muc_id"], ["danh_muc.id"], name=op.f("fk_khuyen_mai_pham_vi_danh_muc_id_danh_muc")
        ),
        sa.ForeignKeyConstraint(
            ["khuyen_mai_id"], ["khuyen_mai.id"], name=op.f("fk_khuyen_mai_pham_vi_khuyen_mai_id_khuyen_mai")
        ),
        sa.ForeignKeyConstraint(
            ["san_pham_id"], ["san_pham.id"], name=op.f("fk_khuyen_mai_pham_vi_san_pham_id_san_pham")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_khuyen_mai_pham_vi")),
    )
    op.create_index("ix_khuyen_mai_pham_vi__khuyen_mai_id", "khuyen_mai_pham_vi", ["khuyen_mai_id"], unique=False)
    op.create_table(
        "lich_su_xem",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("ma_phien", sa.String(length=64), nullable=True),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("nguon", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_lich_su_xem_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_lich_su_xem_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lich_su_xem")),
    )
    op.create_index(
        "ix_lich_su_xem__khach_hang_id_created_at", "lich_su_xem", ["khach_hang_id", "created_at"], unique=False
    )
    op.create_index("ix_lich_su_xem__san_pham_id", "lich_su_xem", ["san_pham_id"], unique=False)
    op.create_table(
        "lo_thuoc",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("so_lo", sa.String(length=50), nullable=False),
        sa.Column("ngay_san_xuat", sa.Date(), nullable=True),
        sa.Column("han_su_dung", sa.Date(), nullable=False),
        sa.Column("gia_nhap", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("so_luong_ton", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("so_luong_giu", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("so_luong_biet_tru", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "dang_ban", "can_han", "khoa", "het_han", "thu_hoi", name="trang_thai_lo", create_type=False
            ),
            server_default="dang_ban",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_lo_thuoc_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lo_thuoc")),
    )
    op.create_index("ix_lo_thuoc__han_su_dung", "lo_thuoc", ["han_su_dung"], unique=False)
    op.create_index(
        "ix_lo_thuoc__san_pham_id_trang_thai_han_su_dung",
        "lo_thuoc",
        ["san_pham_id", "trang_thai", "han_su_dung"],
        unique=False,
    )
    op.create_index(
        "uq_lo_thuoc__san_pham_id_so_lo_han_su_dung", "lo_thuoc", ["san_pham_id", "so_lo", "han_su_dung"], unique=True
    )
    op.create_table(
        "luat_mua_kem",
        sa.Column("san_pham_a_id", sa.Integer(), nullable=False),
        sa.Column("san_pham_b_id", sa.Integer(), nullable=False),
        sa.Column("support", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("confidence", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("lift", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["san_pham_a_id"], ["san_pham.id"], name=op.f("fk_luat_mua_kem_san_pham_a_id_san_pham")
        ),
        sa.ForeignKeyConstraint(
            ["san_pham_b_id"], ["san_pham.id"], name=op.f("fk_luat_mua_kem_san_pham_b_id_san_pham")
        ),
        sa.PrimaryKeyConstraint("san_pham_a_id", "san_pham_b_id", name=op.f("pk_luat_mua_kem")),
    )
    op.create_table(
        "nhat_ky_he_thong",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("hanh_dong", sa.String(length=30), nullable=False),
        sa.Column("bang", sa.String(length=60), nullable=False),
        sa.Column("ban_ghi_id", sa.String(length=60), nullable=True),
        sa.Column("gia_tri_cu", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("gia_tri_moi", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_nhat_ky_he_thong_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_nhat_ky_he_thong")),
    )
    op.create_index("ix_nhat_ky_he_thong__bang_ban_ghi_id", "nhat_ky_he_thong", ["bang", "ban_ghi_id"], unique=False)
    op.create_index(
        "ix_nhat_ky_he_thong__nhan_vien_id_created_at", "nhat_ky_he_thong", ["nhan_vien_id", "created_at"], unique=False
    )
    op.create_table(
        "phien_dang_nhap",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("refresh_token_hash", sa.String(length=128), nullable=False),
        sa.Column("thiet_bi", sa.String(length=255), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("het_han", sa.DateTime(timezone=True), nullable=False),
        sa.Column("thu_hoi_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_phien_dang_nhap_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_phien_dang_nhap_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phien_dang_nhap")),
        sa.UniqueConstraint("refresh_token_hash", name=op.f("uq_phien_dang_nhap_refresh_token_hash")),
    )
    op.create_index("ix_phien_dang_nhap__khach_hang_id", "phien_dang_nhap", ["khach_hang_id"], unique=False)
    op.create_index("ix_phien_dang_nhap__nhan_vien_id", "phien_dang_nhap", ["nhan_vien_id"], unique=False)
    op.create_table(
        "phieu_huy",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column(
            "ly_do",
            postgresql.ENUM(
                "het_han", "hu_hong", "hang_tra_ve", "thu_hoi", "khac", name="ly_do_huy_hang", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("mo_ta", sa.Text(), nullable=True),
        sa.Column("bien_ban_url", sa.String(length=500), nullable=True),
        sa.Column(
            "trang_thai_duyet",
            postgresql.ENUM("cho_duyet", "da_duyet", "tu_choi", name="trang_thai_duyet", create_type=False),
            server_default="cho_duyet",
            nullable=False,
        ),
        sa.Column("nguoi_lap_id", sa.Integer(), nullable=False),
        sa.Column("nguoi_duyet_id", sa.Integer(), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=True),
        sa.Column("duyet_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["nguoi_duyet_id"], ["nhan_vien.id"], name=op.f("fk_phieu_huy_nguoi_duyet_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(["nguoi_lap_id"], ["nhan_vien.id"], name=op.f("fk_phieu_huy_nguoi_lap_id_nhan_vien")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phieu_huy")),
        sa.UniqueConstraint("ma_phieu", name=op.f("uq_phieu_huy_ma_phieu")),
    )
    op.create_table(
        "phieu_kiem_ke",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column("danh_muc_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("dang_kiem", "da_chot", name="trang_thai_kiem_ke", create_type=False),
            server_default="dang_kiem",
            nullable=False,
        ),
        sa.Column("thoi_diem_chup_ton", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("chot_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["danh_muc_id"], ["danh_muc.id"], name=op.f("fk_phieu_kiem_ke_danh_muc_id_danh_muc")),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_phieu_kiem_ke_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phieu_kiem_ke")),
        sa.UniqueConstraint("ma_phieu", name=op.f("uq_phieu_kiem_ke_ma_phieu")),
    )
    op.create_table(
        "phieu_nhap",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column("nha_cung_cap_id", sa.Integer(), nullable=False),
        sa.Column("so_hoa_don_ncc", sa.String(length=50), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=False),
        sa.Column("ngay_nhap", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("tong_tien", sa.Numeric(precision=16, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["nha_cung_cap_id"], ["nha_cung_cap.id"], name=op.f("fk_phieu_nhap_nha_cung_cap_id_nha_cung_cap")
        ),
        sa.ForeignKeyConstraint(["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_phieu_nhap_nhan_vien_id_nhan_vien")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phieu_nhap")),
        sa.UniqueConstraint("ma_phieu", name=op.f("uq_phieu_nhap_ma_phieu")),
    )
    op.create_index(
        "ix_phieu_nhap__nha_cung_cap_id_ngay_nhap", "phieu_nhap", ["nha_cung_cap_id", "ngay_nhap"], unique=False
    )
    op.create_table(
        "tai_lieu_tri_thuc",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column(
            "nguon_loai",
            postgresql.ENUM("san_pham", "bai_viet", "chinh_sach", "faq", name="nguon_tri_thuc", create_type=False),
            nullable=False,
        ),
        sa.Column("nguon_id", sa.Integer(), nullable=True),
        sa.Column("san_pham_id", sa.Integer(), nullable=True),
        sa.Column("truong", sa.String(length=50), nullable=True),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", pgvector.sqlalchemy.vector.VECTOR(dim=1024), nullable=True),
        sa.Column("mo_hinh_embedding", sa.String(length=100), nullable=True),
        sa.Column("hash_noi_dung", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["san_pham_id"], ["san_pham.id"], name=op.f("fk_tai_lieu_tri_thuc_san_pham_id_san_pham")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tai_lieu_tri_thuc")),
    )
    op.create_index(
        "ix_tai_lieu_tri_thuc__nguon_loai_nguon_id", "tai_lieu_tri_thuc", ["nguon_loai", "nguon_id"], unique=False
    )
    op.create_index("ix_tai_lieu_tri_thuc__san_pham_id", "tai_lieu_tri_thuc", ["san_pham_id"], unique=False)
    op.create_table(
        "thanh_phan",
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("hoat_chat_id", sa.Integer(), nullable=False),
        sa.Column("ham_luong", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["hoat_chat_id"], ["hoat_chat.id"], name=op.f("fk_thanh_phan_hoat_chat_id_hoat_chat")),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_thanh_phan_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("san_pham_id", "hoat_chat_id", name=op.f("pk_thanh_phan")),
    )
    op.create_index("ix_thanh_phan__hoat_chat_id", "thanh_phan", ["hoat_chat_id"], unique=False)
    op.create_table(
        "thong_bao",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("loai", sa.String(length=50), nullable=False),
        sa.Column("tieu_de", sa.String(length=255), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=True),
        sa.Column("lien_ket", sa.String(length=500), nullable=True),
        sa.Column("da_doc", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_thong_bao_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_thong_bao_nhan_vien_id_nhan_vien")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thong_bao")),
    )
    op.create_index("ix_thong_bao__khach_hang_id_da_doc", "thong_bao", ["khach_hang_id", "da_doc"], unique=False)
    op.create_index("ix_thong_bao__nhan_vien_id_da_doc", "thong_bao", ["nhan_vien_id", "da_doc"], unique=False)
    op.create_table(
        "thong_tin_chuyen_mon",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("phien_ban", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("chi_dinh", sa.Text(), nullable=True),
        sa.Column("chong_chi_dinh", sa.Text(), nullable=True),
        sa.Column("lieu_dung_tham_khao", sa.Text(), nullable=True),
        sa.Column("tac_dung_phu", sa.Text(), nullable=True),
        sa.Column("than_trong", sa.Text(), nullable=True),
        sa.Column("tuong_tac_thuoc", sa.Text(), nullable=True),
        sa.Column("phu_nu_co_thai_cho_con_bu", sa.Text(), nullable=True),
        sa.Column("tre_em", sa.Text(), nullable=True),
        sa.Column("qua_lieu_xu_tri", sa.Text(), nullable=True),
        sa.Column("bao_quan", sa.Text(), nullable=True),
        sa.Column("file_hdsd_url", sa.String(length=500), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("nhap", "da_duyet", "luu_tru", name="trang_thai_noi_dung", create_type=False),
            server_default="nhap",
            nullable=False,
        ),
        sa.Column("nguoi_soan_id", sa.Integer(), nullable=True),
        sa.Column("duoc_si_duyet_id", sa.Integer(), nullable=True),
        sa.Column("ngay_duyet", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["duoc_si_duyet_id"], ["nhan_vien.id"], name=op.f("fk_thong_tin_chuyen_mon_duoc_si_duyet_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["nguoi_soan_id"], ["nhan_vien.id"], name=op.f("fk_thong_tin_chuyen_mon_nguoi_soan_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["san_pham_id"], ["san_pham.id"], name=op.f("fk_thong_tin_chuyen_mon_san_pham_id_san_pham")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thong_tin_chuyen_mon")),
    )
    op.create_index(
        "ix_thong_tin_chuyen_mon__san_pham_id_trang_thai",
        "thong_tin_chuyen_mon",
        ["san_pham_id", "trang_thai"],
        unique=False,
    )
    op.create_index(
        "uq_thong_tin_chuyen_mon__san_pham_id_phien_ban",
        "thong_tin_chuyen_mon",
        ["san_pham_id", "phien_ban"],
        unique=True,
    )
    op.create_table(
        "tuong_tac_hoat_chat",
        sa.Column("hoat_chat_a_id", sa.Integer(), nullable=False),
        sa.Column("hoat_chat_b_id", sa.Integer(), nullable=False),
        sa.Column(
            "muc_do",
            postgresql.ENUM(
                "nhe", "trung_binh", "nghiem_trong", "chong_chi_dinh", name="muc_do_tuong_tac", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("co_che", sa.Text(), nullable=True),
        sa.Column("khuyen_cao", sa.Text(), nullable=False),
        sa.Column("nguon_tham_khao", sa.String(length=255), nullable=True),
        sa.Column("nhan_vien_cap_nhat_id", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["hoat_chat_a_id"], ["hoat_chat.id"], name=op.f("fk_tuong_tac_hoat_chat_hoat_chat_a_id_hoat_chat")
        ),
        sa.ForeignKeyConstraint(
            ["hoat_chat_b_id"], ["hoat_chat.id"], name=op.f("fk_tuong_tac_hoat_chat_hoat_chat_b_id_hoat_chat")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_cap_nhat_id"],
            ["nhan_vien.id"],
            name=op.f("fk_tuong_tac_hoat_chat_nhan_vien_cap_nhat_id_nhan_vien"),
        ),
        sa.PrimaryKeyConstraint("hoat_chat_a_id", "hoat_chat_b_id", name=op.f("pk_tuong_tac_hoat_chat")),
    )
    op.create_index("ix_tuong_tac_hoat_chat__hoat_chat_b_id", "tuong_tac_hoat_chat", ["hoat_chat_b_id"], unique=False)
    op.create_table(
        "yeu_cau_don_thuoc",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_yeu_cau", sa.String(length=20), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column(
            "kenh",
            postgresql.ENUM("online", "dien_thoai", "tai_quay", name="kenh_ban", create_type=False),
            server_default="online",
            nullable=False,
        ),
        sa.Column("ho_ten", sa.String(length=150), nullable=False),
        sa.Column("so_dien_thoai", sa.String(length=20), nullable=False),
        sa.Column("anh_don_thuoc", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("hash_anh", sa.String(length=128), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("ket_qua_ai", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "cho_duyet",
                "dang_tu_van",
                "da_tao_don",
                "tu_choi",
                "khach_huy",
                name="trang_thai_yeu_cau_don_thuoc",
                create_type=False,
            ),
            server_default="cho_duyet",
            nullable=False,
        ),
        sa.Column("duoc_si_id", sa.Integer(), nullable=True),
        sa.Column("khoa_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checklist", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=True),
        sa.Column("da_su_dung", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["duoc_si_id"], ["nhan_vien.id"], name=op.f("fk_yeu_cau_don_thuoc_duoc_si_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_yeu_cau_don_thuoc_khach_hang_id_khach_hang")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_yeu_cau_don_thuoc")),
        sa.UniqueConstraint("ma_yeu_cau", name=op.f("uq_yeu_cau_don_thuoc_ma_yeu_cau")),
    )
    op.create_index("ix_yeu_cau_don_thuoc__hash_anh", "yeu_cau_don_thuoc", ["hash_anh"], unique=False)
    op.create_index("ix_yeu_cau_don_thuoc__khach_hang_id", "yeu_cau_don_thuoc", ["khach_hang_id"], unique=False)
    op.create_index(
        "ix_yeu_cau_don_thuoc__trang_thai_created_at", "yeu_cau_don_thuoc", ["trang_thai", "created_at"], unique=False
    )
    op.create_table(
        "bien_dong_kho",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column(
            "loai",
            postgresql.ENUM(
                "nhap_kho",
                "xuat_ban",
                "hoan_nhap",
                "nhan_tra_ve",
                "dieu_chinh",
                "huy_hang",
                "xuat_tra_ncc",
                name="loai_bien_dong",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "khu",
            postgresql.ENUM("kho_ban", "biet_tru", name="khu_ton", create_type=False),
            server_default="kho_ban",
            nullable=False,
        ),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.Column("ton_sau", sa.Integer(), nullable=False),
        sa.Column("chung_tu_loai", sa.String(length=30), nullable=False),
        sa.Column("chung_tu_id", sa.Integer(), nullable=False),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_bien_dong_kho_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_bien_dong_kho_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bien_dong_kho")),
    )
    op.create_index(
        "ix_bien_dong_kho__chung_tu_loai_chung_tu_id", "bien_dong_kho", ["chung_tu_loai", "chung_tu_id"], unique=False
    )
    op.create_index("ix_bien_dong_kho__created_at", "bien_dong_kho", ["created_at"], unique=False)
    op.create_index("ix_bien_dong_kho__lo_id_created_at", "bien_dong_kho", ["lo_id", "created_at"], unique=False)
    op.create_table(
        "ct_gio_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("gio_hang_id", sa.Integer(), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("don_vi_id", sa.Integer(), nullable=False),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["don_vi_id", "san_pham_id"],
            ["don_vi_quy_doi.id", "don_vi_quy_doi.san_pham_id"],
            name=op.f("fk_ct_gio_hang_don_vi_id_don_vi_quy_doi"),
        ),
        sa.ForeignKeyConstraint(["gio_hang_id"], ["gio_hang.id"], name=op.f("fk_ct_gio_hang_gio_hang_id_gio_hang")),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_ct_gio_hang_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_gio_hang")),
    )
    op.create_index(
        "uq_ct_gio_hang__gio_hang_id_san_pham_id_don_vi_id",
        "ct_gio_hang",
        ["gio_hang_id", "san_pham_id", "don_vi_id"],
        unique=True,
    )
    op.create_table(
        "ct_kiem_ke",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("phieu_kiem_ke_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column("so_luong_so_sach", sa.Integer(), nullable=False),
        sa.Column("so_luong_thuc_te", sa.Integer(), nullable=True),
        sa.Column("chenh_lech", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_kiem_ke_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["phieu_kiem_ke_id"], ["phieu_kiem_ke.id"], name=op.f("fk_ct_kiem_ke_phieu_kiem_ke_id_phieu_kiem_ke")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_kiem_ke")),
    )
    op.create_index("ix_ct_kiem_ke__lo_id", "ct_kiem_ke", ["lo_id"], unique=False)
    op.create_index("uq_ct_kiem_ke__phieu_kiem_ke_id_lo_id", "ct_kiem_ke", ["phieu_kiem_ke_id", "lo_id"], unique=True)
    op.create_table(
        "ct_phieu_huy",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("phieu_huy_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column(
            "tu_khu",
            postgresql.ENUM("kho_ban", "biet_tru", name="khu_ton", create_type=False),
            server_default="kho_ban",
            nullable=False,
        ),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_phieu_huy_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["phieu_huy_id"], ["phieu_huy.id"], name=op.f("fk_ct_phieu_huy_phieu_huy_id_phieu_huy")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_phieu_huy")),
    )
    op.create_index("ix_ct_phieu_huy__phieu_huy_id", "ct_phieu_huy", ["phieu_huy_id"], unique=False)
    op.create_table(
        "ct_phieu_nhap",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("phieu_nhap_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column("don_vi_id", sa.Integer(), nullable=False),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.Column("so_luong_co_so", sa.Integer(), nullable=False),
        sa.Column("gia_nhap", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ["don_vi_id"], ["don_vi_quy_doi.id"], name=op.f("fk_ct_phieu_nhap_don_vi_id_don_vi_quy_doi")
        ),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_phieu_nhap_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["phieu_nhap_id"], ["phieu_nhap.id"], name=op.f("fk_ct_phieu_nhap_phieu_nhap_id_phieu_nhap")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_phieu_nhap")),
    )
    op.create_index("ix_ct_phieu_nhap__lo_id", "ct_phieu_nhap", ["lo_id"], unique=False)
    op.create_index("ix_ct_phieu_nhap__phieu_nhap_id", "ct_phieu_nhap", ["phieu_nhap_id"], unique=False)
    op.create_table(
        "ct_yeu_cau_don_thuoc",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("yeu_cau_id", sa.Integer(), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=True),
        sa.Column("ten_thuoc_tren_don", sa.String(length=255), nullable=False),
        sa.Column("ham_luong", sa.String(length=50), nullable=True),
        sa.Column("so_luong_ke", sa.String(length=50), nullable=True),
        sa.Column("do_tin_cay_ai", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("do_duoc_si_nhap", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.ForeignKeyConstraint(
            ["san_pham_id"], ["san_pham.id"], name=op.f("fk_ct_yeu_cau_don_thuoc_san_pham_id_san_pham")
        ),
        sa.ForeignKeyConstraint(
            ["yeu_cau_id"], ["yeu_cau_don_thuoc.id"], name=op.f("fk_ct_yeu_cau_don_thuoc_yeu_cau_id_yeu_cau_don_thuoc")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_yeu_cau_don_thuoc")),
    )
    op.create_index("ix_ct_yeu_cau_don_thuoc__yeu_cau_id", "ct_yeu_cau_don_thuoc", ["yeu_cau_id"], unique=False)
    op.create_table(
        "don_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_don", sa.String(length=20), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column(
            "kenh_ban",
            postgresql.ENUM("online", "dien_thoai", "tai_quay", name="kenh_ban", create_type=False),
            server_default="online",
            nullable=False,
        ),
        sa.Column(
            "hinh_thuc_nhan",
            postgresql.ENUM("giao_tan_noi", "nhan_tai_nha_thuoc", name="hinh_thuc_nhan", create_type=False),
            server_default="giao_tan_noi",
            nullable=False,
        ),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "cho_khach_xac_nhan",
                "cho_thanh_toan",
                "cho_xac_nhan",
                "da_xac_nhan",
                "dang_soan_hang",
                "cho_lay_hang",
                "dang_giao",
                "da_giao",
                "hoan_tat",
                "giao_that_bai",
                "hoan_ve_kho",
                "da_huy",
                name="trang_thai_don",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "phuong_thuc_tt",
            postgresql.ENUM(
                "cod", "vnpay", "momo", "tien_mat", "chuyen_khoan", name="phuong_thuc_thanh_toan", create_type=False
            ),
            nullable=True,
        ),
        sa.Column(
            "trang_thai_tt",
            postgresql.ENUM(
                "chua_thanh_toan",
                "da_thanh_toan",
                "cho_hoan_tien",
                "hoan_tien_mot_phan",
                "da_hoan_tien",
                name="trang_thai_thanh_toan",
                create_type=False,
            ),
            server_default="chua_thanh_toan",
            nullable=False,
        ),
        sa.Column("yeu_cau_don_thuoc_id", sa.Integer(), nullable=True),
        sa.Column("don_hang_goc_id", sa.Integer(), nullable=True),
        sa.Column("token_truy_cap_hash", sa.String(length=128), nullable=True),
        sa.Column("ma_giam_gia_id", sa.Integer(), nullable=True),
        sa.Column("tam_tinh", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("giam_gia", sa.Numeric(precision=16, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("phi_van_chuyen", sa.Numeric(precision=14, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("tong_tien", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("ten_nguoi_nhan", sa.String(length=150), nullable=True),
        sa.Column("sdt_nguoi_nhan", sa.String(length=20), nullable=True),
        sa.Column("dia_chi_giao", sa.String(length=500), nullable=True),
        sa.Column("ma_tinh", sa.String(length=20), nullable=True),
        sa.Column("ma_quan_huyen", sa.String(length=20), nullable=True),
        sa.Column("ma_phuong_xa", sa.String(length=20), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("ly_do_huy", sa.Text(), nullable=True),
        sa.Column("nhan_vien_tao_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_xac_nhan_id", sa.Integer(), nullable=True),
        sa.Column("han_thanh_toan", sa.DateTime(timezone=True), nullable=True),
        sa.Column("han_xac_nhan", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["don_hang_goc_id"], ["don_hang.id"], name=op.f("fk_don_hang_don_hang_goc_id_don_hang")
        ),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_don_hang_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["ma_giam_gia_id"], ["ma_giam_gia.id"], name=op.f("fk_don_hang_ma_giam_gia_id_ma_giam_gia")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_tao_id"], ["nhan_vien.id"], name=op.f("fk_don_hang_nhan_vien_tao_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_xac_nhan_id"], ["nhan_vien.id"], name=op.f("fk_don_hang_nhan_vien_xac_nhan_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["yeu_cau_don_thuoc_id"],
            ["yeu_cau_don_thuoc.id"],
            name=op.f("fk_don_hang_yeu_cau_don_thuoc_id_yeu_cau_don_thuoc"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_don_hang")),
        sa.UniqueConstraint("ma_don", name=op.f("uq_don_hang_ma_don")),
    )
    op.create_index("ix_don_hang__khach_hang_id_created_at", "don_hang", ["khach_hang_id", "created_at"], unique=False)
    op.create_index("ix_don_hang__sdt_nguoi_nhan", "don_hang", ["sdt_nguoi_nhan"], unique=False)
    op.create_index("ix_don_hang__trang_thai_created_at", "don_hang", ["trang_thai", "created_at"], unique=False)
    op.create_index("ix_don_hang__yeu_cau_don_thuoc_id", "don_hang", ["yeu_cau_don_thuoc_id"], unique=False)
    op.create_table(
        "lenh_thu_hoi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_lenh", sa.String(length=30), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=True),
        sa.Column("can_cu", sa.String(length=255), nullable=False),
        sa.Column("muc_do", sa.String(length=50), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("dang_thu_hoi", "hoan_tat", name="trang_thai_thu_hoi", create_type=False),
            server_default="dang_thu_hoi",
            nullable=False,
        ),
        sa.Column("nguoi_tao_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dong_luc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_lenh_thu_hoi_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["nguoi_tao_id"], ["nhan_vien.id"], name=op.f("fk_lenh_thu_hoi_nguoi_tao_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_lenh_thu_hoi_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lenh_thu_hoi")),
        sa.UniqueConstraint("ma_lenh", name=op.f("uq_lenh_thu_hoi_ma_lenh")),
    )
    op.create_index("ix_lenh_thu_hoi__lo_id", "lenh_thu_hoi", ["lo_id"], unique=False)
    op.create_table(
        "phieu_dieu_chinh",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column("phieu_kiem_ke_id", sa.Integer(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False),
        sa.Column(
            "trang_thai_duyet",
            postgresql.ENUM("cho_duyet", "da_duyet", "tu_choi", name="trang_thai_duyet", create_type=False),
            server_default="cho_duyet",
            nullable=False,
        ),
        sa.Column("nguoi_lap_id", sa.Integer(), nullable=False),
        sa.Column("nguoi_duyet_id", sa.Integer(), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=True),
        sa.Column("duyet_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["nguoi_duyet_id"], ["nhan_vien.id"], name=op.f("fk_phieu_dieu_chinh_nguoi_duyet_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["nguoi_lap_id"], ["nhan_vien.id"], name=op.f("fk_phieu_dieu_chinh_nguoi_lap_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["phieu_kiem_ke_id"], ["phieu_kiem_ke.id"], name=op.f("fk_phieu_dieu_chinh_phieu_kiem_ke_id_phieu_kiem_ke")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phieu_dieu_chinh")),
        sa.UniqueConstraint("ma_phieu", name=op.f("uq_phieu_dieu_chinh_ma_phieu")),
    )
    op.create_table(
        "tin_nhan",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("hoi_thoai_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "vai_tro",
            postgresql.ENUM("khach", "ai", "duoc_si", "he_thong", name="vai_tro_tin_nhan", create_type=False),
            nullable=False,
        ),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("noi_dung", sa.Text(), nullable=False),
        sa.Column("y_dinh", sa.String(length=50), nullable=True),
        sa.Column("san_pham_goi_y", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dau_hieu_nguy_hiem", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("so_token", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["hoi_thoai_id"], ["hoi_thoai.id"], name=op.f("fk_tin_nhan_hoi_thoai_id_hoi_thoai")),
        sa.ForeignKeyConstraint(["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_tin_nhan_nhan_vien_id_nhan_vien")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tin_nhan")),
    )
    op.create_index("ix_tin_nhan__hoi_thoai_id_created_at", "tin_nhan", ["hoi_thoai_id", "created_at"], unique=False)
    op.create_table(
        "ct_don_hang",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("don_vi_id", sa.Integer(), nullable=False),
        sa.Column("ten_san_pham", sa.String(length=255), nullable=False),
        sa.Column("ten_don_vi", sa.String(length=30), nullable=False),
        sa.Column("he_so", sa.Integer(), nullable=False),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.Column("don_gia", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("giam_gia_phan_bo", sa.Numeric(precision=14, scale=2), server_default=sa.text("0"), nullable=False),
        sa.Column("thanh_tien", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["don_hang_id"], ["don_hang.id"], name=op.f("fk_ct_don_hang_don_hang_id_don_hang")),
        sa.ForeignKeyConstraint(
            ["don_vi_id", "san_pham_id"],
            ["don_vi_quy_doi.id", "don_vi_quy_doi.san_pham_id"],
            name=op.f("fk_ct_don_hang_don_vi_id_don_vi_quy_doi"),
        ),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_ct_don_hang_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_don_hang")),
    )
    op.create_index("ix_ct_don_hang__don_hang_id", "ct_don_hang", ["don_hang_id"], unique=False)
    op.create_index("ix_ct_don_hang__san_pham_id", "ct_don_hang", ["san_pham_id"], unique=False)
    op.create_table(
        "ct_lenh_thu_hoi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("lenh_thu_hoi_id", sa.Integer(), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("so_luong_da_ban", sa.Integer(), nullable=False),
        sa.Column("so_luong_da_thu_ve", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "ket_qua_lien_he",
            postgresql.ENUM(
                "chua_lien_he",
                "da_lien_he",
                "da_hen_tra_hang",
                "da_thu_ve",
                "khong_lien_lac_duoc",
                name="ket_qua_lien_he_thu_hoi",
                create_type=False,
            ),
            server_default="chua_lien_he",
            nullable=False,
        ),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("cap_nhat_luc", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["don_hang_id"], ["don_hang.id"], name=op.f("fk_ct_lenh_thu_hoi_don_hang_id_don_hang")),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_ct_lenh_thu_hoi_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["lenh_thu_hoi_id"], ["lenh_thu_hoi.id"], name=op.f("fk_ct_lenh_thu_hoi_lenh_thu_hoi_id_lenh_thu_hoi")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_ct_lenh_thu_hoi_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_lenh_thu_hoi")),
    )
    op.create_index("ix_ct_lenh_thu_hoi__don_hang_id", "ct_lenh_thu_hoi", ["don_hang_id"], unique=False)
    op.create_index(
        "uq_ct_lenh_thu_hoi__lenh_thu_hoi_id_don_hang_id",
        "ct_lenh_thu_hoi",
        ["lenh_thu_hoi_id", "don_hang_id"],
        unique=True,
    )
    op.create_table(
        "ct_phieu_dieu_chinh",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("phieu_dieu_chinh_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column("so_luong_thay_doi", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_phieu_dieu_chinh_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["phieu_dieu_chinh_id"],
            ["phieu_dieu_chinh.id"],
            name=op.f("fk_ct_phieu_dieu_chinh_phieu_dieu_chinh_id_phieu_dieu_chinh"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_phieu_dieu_chinh")),
    )
    op.create_index(
        "ix_ct_phieu_dieu_chinh__phieu_dieu_chinh_id", "ct_phieu_dieu_chinh", ["phieu_dieu_chinh_id"], unique=False
    )
    op.create_table(
        "danh_gia_cau_tra_loi",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("tin_nhan_id", sa.BigInteger(), nullable=False),
        sa.Column("nguon", sa.String(length=20), nullable=False),
        sa.Column("ket_qua", sa.String(length=20), nullable=False),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_danh_gia_cau_tra_loi_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_danh_gia_cau_tra_loi_nhan_vien_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["tin_nhan_id"], ["tin_nhan.id"], name=op.f("fk_danh_gia_cau_tra_loi_tin_nhan_id_tin_nhan")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_danh_gia_cau_tra_loi")),
    )
    op.create_index("ix_danh_gia_cau_tra_loi__tin_nhan_id", "danh_gia_cau_tra_loi", ["tin_nhan_id"], unique=False)
    op.create_table(
        "lich_su_trang_thai",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column(
            "tu_trang_thai",
            postgresql.ENUM(
                "cho_khach_xac_nhan",
                "cho_thanh_toan",
                "cho_xac_nhan",
                "da_xac_nhan",
                "dang_soan_hang",
                "cho_lay_hang",
                "dang_giao",
                "da_giao",
                "hoan_tat",
                "giao_that_bai",
                "hoan_ve_kho",
                "da_huy",
                name="trang_thai_don",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column(
            "den_trang_thai",
            postgresql.ENUM(
                "cho_khach_xac_nhan",
                "cho_thanh_toan",
                "cho_xac_nhan",
                "da_xac_nhan",
                "dang_soan_hang",
                "cho_lay_hang",
                "dang_giao",
                "da_giao",
                "hoan_tat",
                "giao_that_bai",
                "hoan_ve_kho",
                "da_huy",
                name="trang_thai_don",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=True),
        sa.Column("khach_hang_id", sa.Integer(), nullable=True),
        sa.Column("nguon", sa.String(length=30), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["don_hang_id"], ["don_hang.id"], name=op.f("fk_lich_su_trang_thai_don_hang_id_don_hang")
        ),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_lich_su_trang_thai_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_lich_su_trang_thai_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lich_su_trang_thai")),
    )
    op.create_index(
        "ix_lich_su_trang_thai__don_hang_id_created_at",
        "lich_su_trang_thai",
        ["don_hang_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "phieu_xuat_tra",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_phieu", sa.String(length=30), nullable=False),
        sa.Column("nha_cung_cap_id", sa.Integer(), nullable=False),
        sa.Column("lenh_thu_hoi_id", sa.Integer(), nullable=True),
        sa.Column("ly_do", sa.Text(), nullable=False),
        sa.Column("nhan_vien_id", sa.Integer(), nullable=False),
        sa.Column(
            "trang_thai_duyet",
            postgresql.ENUM("cho_duyet", "da_duyet", "tu_choi", name="trang_thai_duyet", create_type=False),
            server_default="cho_duyet",
            nullable=False,
        ),
        sa.Column("nguoi_duyet_id", sa.Integer(), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=True),
        sa.Column("duyet_luc", sa.DateTime(timezone=True), nullable=True),
        sa.Column("da_xac_nhan", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["lenh_thu_hoi_id"], ["lenh_thu_hoi.id"], name=op.f("fk_phieu_xuat_tra_lenh_thu_hoi_id_lenh_thu_hoi")
        ),
        sa.ForeignKeyConstraint(
            ["nguoi_duyet_id"], ["nhan_vien.id"], name=op.f("fk_phieu_xuat_tra_nguoi_duyet_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["nha_cung_cap_id"], ["nha_cung_cap.id"], name=op.f("fk_phieu_xuat_tra_nha_cung_cap_id_nha_cung_cap")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_id"], ["nhan_vien.id"], name=op.f("fk_phieu_xuat_tra_nhan_vien_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phieu_xuat_tra")),
        sa.UniqueConstraint("ma_phieu", name=op.f("uq_phieu_xuat_tra_ma_phieu")),
    )
    op.create_table(
        "yeu_cau_doi_tra",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ma_yeu_cau", sa.String(length=20), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column(
            "ly_do",
            postgresql.ENUM(
                "giao_sai_san_pham",
                "sai_so_luong",
                "hu_hong",
                "het_han_can_han",
                "khac",
                name="ly_do_doi_tra",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("mo_ta", sa.Text(), nullable=True),
        sa.Column("anh", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "cho_duyet",
                "da_duyet",
                "tu_choi",
                "kho_da_nhan",
                "hoan_tat",
                name="trang_thai_doi_tra",
                create_type=False,
            ),
            server_default="cho_duyet",
            nullable=False,
        ),
        sa.Column(
            "huong_xu_ly",
            postgresql.ENUM("hoan_tien", "gui_hang_thay_the", name="huong_xu_ly_doi_tra", create_type=False),
            nullable=True,
        ),
        sa.Column("duoc_si_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_kho_id", sa.Integer(), nullable=True),
        sa.Column("so_tien_hoan", sa.Numeric(precision=16, scale=2), nullable=True),
        sa.Column("ly_do_tu_choi", sa.Text(), nullable=True),
        sa.Column("ket_qua_kiem_hang", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["don_hang_id"], ["don_hang.id"], name=op.f("fk_yeu_cau_doi_tra_don_hang_id_don_hang")),
        sa.ForeignKeyConstraint(["duoc_si_id"], ["nhan_vien.id"], name=op.f("fk_yeu_cau_doi_tra_duoc_si_id_nhan_vien")),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_yeu_cau_doi_tra_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_kho_id"], ["nhan_vien.id"], name=op.f("fk_yeu_cau_doi_tra_nhan_vien_kho_id_nhan_vien")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_yeu_cau_doi_tra")),
        sa.UniqueConstraint("ma_yeu_cau", name=op.f("uq_yeu_cau_doi_tra_ma_yeu_cau")),
    )
    op.create_index("ix_yeu_cau_doi_tra__don_hang_id", "yeu_cau_doi_tra", ["don_hang_id"], unique=False)
    op.create_index(
        "ix_yeu_cau_doi_tra__khach_hang_id_created_at", "yeu_cau_doi_tra", ["khach_hang_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_yeu_cau_doi_tra__trang_thai_created_at", "yeu_cau_doi_tra", ["trang_thai", "created_at"], unique=False
    )
    op.create_table(
        "ct_phieu_xuat_tra",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("phieu_xuat_tra_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column(
            "tu_khu",
            postgresql.ENUM("kho_ban", "biet_tru", name="khu_ton", create_type=False),
            server_default="kho_ban",
            nullable=False,
        ),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.Column("don_gia", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_phieu_xuat_tra_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["phieu_xuat_tra_id"],
            ["phieu_xuat_tra.id"],
            name=op.f("fk_ct_phieu_xuat_tra_phieu_xuat_tra_id_phieu_xuat_tra"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_phieu_xuat_tra")),
    )
    op.create_index("ix_ct_phieu_xuat_tra__phieu_xuat_tra_id", "ct_phieu_xuat_tra", ["phieu_xuat_tra_id"], unique=False)
    op.create_table(
        "ct_yeu_cau_doi_tra",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("yeu_cau_id", sa.Integer(), nullable=False),
        sa.Column("ct_don_hang_id", sa.Integer(), nullable=False),
        sa.Column("so_luong", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=True),
        sa.Column("so_luong_nhan", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["ct_don_hang_id"], ["ct_don_hang.id"], name=op.f("fk_ct_yeu_cau_doi_tra_ct_don_hang_id_ct_don_hang")
        ),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_ct_yeu_cau_doi_tra_lo_id_lo_thuoc")),
        sa.ForeignKeyConstraint(
            ["yeu_cau_id"], ["yeu_cau_doi_tra.id"], name=op.f("fk_ct_yeu_cau_doi_tra_yeu_cau_id_yeu_cau_doi_tra")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ct_yeu_cau_doi_tra")),
    )
    op.create_index("ix_ct_yeu_cau_doi_tra__ct_don_hang_id", "ct_yeu_cau_doi_tra", ["ct_don_hang_id"], unique=False)
    op.create_index(
        "uq_ct_yeu_cau_doi_tra__yeu_cau_id_ct_don_hang_id",
        "ct_yeu_cau_doi_tra",
        ["yeu_cau_id", "ct_don_hang_id"],
        unique=True,
    )
    op.create_table(
        "danh_gia",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("san_pham_id", sa.Integer(), nullable=False),
        sa.Column("khach_hang_id", sa.Integer(), nullable=False),
        sa.Column("ct_don_hang_id", sa.Integer(), nullable=False),
        sa.Column("so_sao", sa.SmallInteger(), nullable=False),
        sa.Column("noi_dung", sa.Text(), nullable=True),
        sa.Column("anh", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("dang_hien", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("phan_hoi", sa.Text(), nullable=True),
        sa.Column("nhan_vien_phan_hoi_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["ct_don_hang_id"], ["ct_don_hang.id"], name=op.f("fk_danh_gia_ct_don_hang_id_ct_don_hang")
        ),
        sa.ForeignKeyConstraint(
            ["khach_hang_id"], ["khach_hang.id"], name=op.f("fk_danh_gia_khach_hang_id_khach_hang")
        ),
        sa.ForeignKeyConstraint(
            ["nhan_vien_phan_hoi_id"], ["nhan_vien.id"], name=op.f("fk_danh_gia_nhan_vien_phan_hoi_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(["san_pham_id"], ["san_pham.id"], name=op.f("fk_danh_gia_san_pham_id_san_pham")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_danh_gia")),
        sa.UniqueConstraint("ct_don_hang_id", name=op.f("uq_danh_gia_ct_don_hang_id")),
    )
    op.create_index(
        "ix_danh_gia__san_pham_id_dang_hien_created_at",
        "danh_gia",
        ["san_pham_id", "dang_hien", "created_at"],
        unique=False,
    )
    op.create_table(
        "phan_bo_lo",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("ct_don_hang_id", sa.Integer(), nullable=False),
        sa.Column("lo_id", sa.Integer(), nullable=False),
        sa.Column("so_luong_co_so", sa.Integer(), nullable=False),
        sa.Column("gia_von", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column(
            "trang_thai",
            postgresql.ENUM(
                "dang_giu", "da_xuat", "da_nha", "da_hoan_nhap", name="trang_thai_phan_bo", create_type=False
            ),
            server_default="dang_giu",
            nullable=False,
        ),
        sa.Column("ly_do_doi_lo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["ct_don_hang_id"], ["ct_don_hang.id"], name=op.f("fk_phan_bo_lo_ct_don_hang_id_ct_don_hang")
        ),
        sa.ForeignKeyConstraint(["lo_id"], ["lo_thuoc.id"], name=op.f("fk_phan_bo_lo_lo_id_lo_thuoc")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_phan_bo_lo")),
    )
    op.create_index("ix_phan_bo_lo__ct_don_hang_id", "phan_bo_lo", ["ct_don_hang_id"], unique=False)
    op.create_index("ix_phan_bo_lo__lo_id", "phan_bo_lo", ["lo_id"], unique=False)
    op.create_table(
        "thanh_toan",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column(
            "loai",
            postgresql.ENUM("thanh_toan", "hoan_tien", name="loai_giao_dich", create_type=False),
            server_default="thanh_toan",
            nullable=False,
        ),
        sa.Column(
            "cong_thanh_toan",
            postgresql.ENUM(
                "cod", "vnpay", "momo", "tien_mat", "chuyen_khoan", name="phuong_thuc_thanh_toan", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("so_tien", sa.Numeric(precision=16, scale=2), nullable=False),
        sa.Column("ma_giao_dich_cong", sa.String(length=100), nullable=True),
        sa.Column(
            "trang_thai",
            postgresql.ENUM("khoi_tao", "thanh_cong", "that_bai", name="trang_thai_giao_dich", create_type=False),
            server_default="khoi_tao",
            nullable=False,
        ),
        sa.Column("du_lieu_ipn", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("thanh_toan_goc_id", sa.Integer(), nullable=True),
        sa.Column("yeu_cau_doi_tra_id", sa.Integer(), nullable=True),
        sa.Column("nhan_vien_xu_ly_id", sa.Integer(), nullable=True),
        sa.Column("thong_tin_nhan_hoan", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("chung_tu_url", sa.String(length=500), nullable=True),
        sa.Column("ghi_chu", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["don_hang_id"], ["don_hang.id"], name=op.f("fk_thanh_toan_don_hang_id_don_hang")),
        sa.ForeignKeyConstraint(
            ["nhan_vien_xu_ly_id"], ["nhan_vien.id"], name=op.f("fk_thanh_toan_nhan_vien_xu_ly_id_nhan_vien")
        ),
        sa.ForeignKeyConstraint(
            ["thanh_toan_goc_id"], ["thanh_toan.id"], name=op.f("fk_thanh_toan_thanh_toan_goc_id_thanh_toan")
        ),
        sa.ForeignKeyConstraint(
            ["yeu_cau_doi_tra_id"],
            ["yeu_cau_doi_tra.id"],
            name=op.f("fk_thanh_toan_yeu_cau_doi_tra_id_yeu_cau_doi_tra"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_thanh_toan")),
        sa.UniqueConstraint("ma_giao_dich_cong", name=op.f("uq_thanh_toan_ma_giao_dich_cong")),
    )
    op.create_index("ix_thanh_toan__don_hang_id", "thanh_toan", ["don_hang_id"], unique=False)
    op.create_table(
        "van_don",
        sa.Column("id", sa.Integer(), sa.Identity(always=False), nullable=False),
        sa.Column("don_hang_id", sa.Integer(), nullable=False),
        sa.Column(
            "loai",
            postgresql.ENUM("giao_hang", "tra_hang", name="loai_van_don", create_type=False),
            server_default="giao_hang",
            nullable=False,
        ),
        sa.Column("yeu_cau_doi_tra_id", sa.Integer(), nullable=True),
        sa.Column("don_vi_van_chuyen", sa.String(length=30), nullable=False),
        sa.Column("ma_van_don", sa.String(length=50), nullable=True),
        sa.Column("phi", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("khoi_luong_gram", sa.Integer(), nullable=True),
        sa.Column("trang_thai_doi_tac", sa.String(length=50), nullable=True),
        sa.Column("du_lieu_webhook", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["don_hang_id"], ["don_hang.id"], name=op.f("fk_van_don_don_hang_id_don_hang")),
        sa.ForeignKeyConstraint(
            ["yeu_cau_doi_tra_id"], ["yeu_cau_doi_tra.id"], name=op.f("fk_van_don_yeu_cau_doi_tra_id_yeu_cau_doi_tra")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_van_don")),
        sa.UniqueConstraint("ma_van_don", name=op.f("uq_van_don_ma_van_don")),
    )
    op.create_index("ix_van_don__don_hang_id", "van_don", ["don_hang_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_van_don__don_hang_id", table_name="van_don")
    op.drop_table("van_don")
    op.drop_index("ix_thanh_toan__don_hang_id", table_name="thanh_toan")
    op.drop_table("thanh_toan")
    op.drop_index("ix_phan_bo_lo__lo_id", table_name="phan_bo_lo")
    op.drop_index("ix_phan_bo_lo__ct_don_hang_id", table_name="phan_bo_lo")
    op.drop_table("phan_bo_lo")
    op.drop_index("ix_danh_gia__san_pham_id_dang_hien_created_at", table_name="danh_gia")
    op.drop_table("danh_gia")
    op.drop_index("uq_ct_yeu_cau_doi_tra__yeu_cau_id_ct_don_hang_id", table_name="ct_yeu_cau_doi_tra")
    op.drop_index("ix_ct_yeu_cau_doi_tra__ct_don_hang_id", table_name="ct_yeu_cau_doi_tra")
    op.drop_table("ct_yeu_cau_doi_tra")
    op.drop_index("ix_ct_phieu_xuat_tra__phieu_xuat_tra_id", table_name="ct_phieu_xuat_tra")
    op.drop_table("ct_phieu_xuat_tra")
    op.drop_index("ix_yeu_cau_doi_tra__trang_thai_created_at", table_name="yeu_cau_doi_tra")
    op.drop_index("ix_yeu_cau_doi_tra__khach_hang_id_created_at", table_name="yeu_cau_doi_tra")
    op.drop_index("ix_yeu_cau_doi_tra__don_hang_id", table_name="yeu_cau_doi_tra")
    op.drop_table("yeu_cau_doi_tra")
    op.drop_table("phieu_xuat_tra")
    op.drop_index("ix_lich_su_trang_thai__don_hang_id_created_at", table_name="lich_su_trang_thai")
    op.drop_table("lich_su_trang_thai")
    op.drop_index("ix_danh_gia_cau_tra_loi__tin_nhan_id", table_name="danh_gia_cau_tra_loi")
    op.drop_table("danh_gia_cau_tra_loi")
    op.drop_index("ix_ct_phieu_dieu_chinh__phieu_dieu_chinh_id", table_name="ct_phieu_dieu_chinh")
    op.drop_table("ct_phieu_dieu_chinh")
    op.drop_index("uq_ct_lenh_thu_hoi__lenh_thu_hoi_id_don_hang_id", table_name="ct_lenh_thu_hoi")
    op.drop_index("ix_ct_lenh_thu_hoi__don_hang_id", table_name="ct_lenh_thu_hoi")
    op.drop_table("ct_lenh_thu_hoi")
    op.drop_index("ix_ct_don_hang__san_pham_id", table_name="ct_don_hang")
    op.drop_index("ix_ct_don_hang__don_hang_id", table_name="ct_don_hang")
    op.drop_table("ct_don_hang")
    op.drop_index("ix_tin_nhan__hoi_thoai_id_created_at", table_name="tin_nhan")
    op.drop_table("tin_nhan")
    op.drop_table("phieu_dieu_chinh")
    op.drop_index("ix_lenh_thu_hoi__lo_id", table_name="lenh_thu_hoi")
    op.drop_table("lenh_thu_hoi")
    op.drop_index("ix_don_hang__yeu_cau_don_thuoc_id", table_name="don_hang")
    op.drop_index("ix_don_hang__trang_thai_created_at", table_name="don_hang")
    op.drop_index("ix_don_hang__sdt_nguoi_nhan", table_name="don_hang")
    op.drop_index("ix_don_hang__khach_hang_id_created_at", table_name="don_hang")
    op.drop_table("don_hang")
    op.drop_index("ix_ct_yeu_cau_don_thuoc__yeu_cau_id", table_name="ct_yeu_cau_don_thuoc")
    op.drop_table("ct_yeu_cau_don_thuoc")
    op.drop_index("ix_ct_phieu_nhap__phieu_nhap_id", table_name="ct_phieu_nhap")
    op.drop_index("ix_ct_phieu_nhap__lo_id", table_name="ct_phieu_nhap")
    op.drop_table("ct_phieu_nhap")
    op.drop_index("ix_ct_phieu_huy__phieu_huy_id", table_name="ct_phieu_huy")
    op.drop_table("ct_phieu_huy")
    op.drop_index("uq_ct_kiem_ke__phieu_kiem_ke_id_lo_id", table_name="ct_kiem_ke")
    op.drop_index("ix_ct_kiem_ke__lo_id", table_name="ct_kiem_ke")
    op.drop_table("ct_kiem_ke")
    op.drop_index("uq_ct_gio_hang__gio_hang_id_san_pham_id_don_vi_id", table_name="ct_gio_hang")
    op.drop_table("ct_gio_hang")
    op.drop_index("ix_bien_dong_kho__lo_id_created_at", table_name="bien_dong_kho")
    op.drop_index("ix_bien_dong_kho__created_at", table_name="bien_dong_kho")
    op.drop_index("ix_bien_dong_kho__chung_tu_loai_chung_tu_id", table_name="bien_dong_kho")
    op.drop_table("bien_dong_kho")
    op.drop_index("ix_yeu_cau_don_thuoc__trang_thai_created_at", table_name="yeu_cau_don_thuoc")
    op.drop_index("ix_yeu_cau_don_thuoc__khach_hang_id", table_name="yeu_cau_don_thuoc")
    op.drop_index("ix_yeu_cau_don_thuoc__hash_anh", table_name="yeu_cau_don_thuoc")
    op.drop_table("yeu_cau_don_thuoc")
    op.drop_index("ix_tuong_tac_hoat_chat__hoat_chat_b_id", table_name="tuong_tac_hoat_chat")
    op.drop_table("tuong_tac_hoat_chat")
    op.drop_index("uq_thong_tin_chuyen_mon__san_pham_id_phien_ban", table_name="thong_tin_chuyen_mon")
    op.drop_index("ix_thong_tin_chuyen_mon__san_pham_id_trang_thai", table_name="thong_tin_chuyen_mon")
    op.drop_table("thong_tin_chuyen_mon")
    op.drop_index("ix_thong_bao__nhan_vien_id_da_doc", table_name="thong_bao")
    op.drop_index("ix_thong_bao__khach_hang_id_da_doc", table_name="thong_bao")
    op.drop_table("thong_bao")
    op.drop_index("ix_thanh_phan__hoat_chat_id", table_name="thanh_phan")
    op.drop_table("thanh_phan")
    op.drop_index("ix_tai_lieu_tri_thuc__san_pham_id", table_name="tai_lieu_tri_thuc")
    op.drop_index("ix_tai_lieu_tri_thuc__nguon_loai_nguon_id", table_name="tai_lieu_tri_thuc")
    op.drop_table("tai_lieu_tri_thuc")
    op.drop_index("ix_phieu_nhap__nha_cung_cap_id_ngay_nhap", table_name="phieu_nhap")
    op.drop_table("phieu_nhap")
    op.drop_table("phieu_kiem_ke")
    op.drop_table("phieu_huy")
    op.drop_index("ix_phien_dang_nhap__nhan_vien_id", table_name="phien_dang_nhap")
    op.drop_index("ix_phien_dang_nhap__khach_hang_id", table_name="phien_dang_nhap")
    op.drop_table("phien_dang_nhap")
    op.drop_index("ix_nhat_ky_he_thong__nhan_vien_id_created_at", table_name="nhat_ky_he_thong")
    op.drop_index("ix_nhat_ky_he_thong__bang_ban_ghi_id", table_name="nhat_ky_he_thong")
    op.drop_table("nhat_ky_he_thong")
    op.drop_table("luat_mua_kem")
    op.drop_index("uq_lo_thuoc__san_pham_id_so_lo_han_su_dung", table_name="lo_thuoc")
    op.drop_index("ix_lo_thuoc__san_pham_id_trang_thai_han_su_dung", table_name="lo_thuoc")
    op.drop_index("ix_lo_thuoc__han_su_dung", table_name="lo_thuoc")
    op.drop_table("lo_thuoc")
    op.drop_index("ix_lich_su_xem__san_pham_id", table_name="lich_su_xem")
    op.drop_index("ix_lich_su_xem__khach_hang_id_created_at", table_name="lich_su_xem")
    op.drop_table("lich_su_xem")
    op.drop_index("ix_khuyen_mai_pham_vi__khuyen_mai_id", table_name="khuyen_mai_pham_vi")
    op.drop_table("khuyen_mai_pham_vi")
    op.drop_index("ix_hoi_thoai__trang_thai_created_at", table_name="hoi_thoai")
    op.drop_index("ix_hoi_thoai__khach_hang_id", table_name="hoi_thoai")
    op.drop_index("ix_hoi_thoai__duoc_si_id_trang_thai", table_name="hoi_thoai")
    op.drop_index("ix_hoi_thoai__bi_gan_co", table_name="hoi_thoai")
    op.drop_table("hoi_thoai")
    op.drop_index("ix_hoi_dap__tra_loi_luc", table_name="hoi_dap")
    op.drop_index("ix_hoi_dap__san_pham_id_dang_hien_created_at", table_name="hoi_dap")
    op.drop_table("hoi_dap")
    op.drop_index("uq_don_vi_quy_doi__san_pham_id_ten_don_vi", table_name="don_vi_quy_doi")
    op.drop_index("uq_don_vi_quy_doi__id_san_pham_id", table_name="don_vi_quy_doi")
    op.drop_index("ix_don_vi_quy_doi__ma_vach", table_name="don_vi_quy_doi")
    op.drop_table("don_vi_quy_doi")
    op.drop_index("uq_de_xuat_nhap_hang__ky_bat_dau_san_pham_id", table_name="de_xuat_nhap_hang")
    op.drop_table("de_xuat_nhap_hang")
    op.drop_table("cau_hinh")
    op.drop_table("bai_viet")
    op.drop_index("ix_anh_san_pham__san_pham_id", table_name="anh_san_pham")
    op.drop_table("anh_san_pham")
    op.drop_table("vai_tro_quyen")
    op.drop_index("ix_san_pham__so_dang_ky", table_name="san_pham")
    op.drop_index("ix_san_pham__loai_san_pham", table_name="san_pham")
    op.drop_index("ix_san_pham__danh_muc_id_trang_thai", table_name="san_pham")
    op.drop_table("san_pham")
    op.drop_table("nhan_vien")
    op.drop_index("ix_ma_giam_gia__khuyen_mai_id", table_name="ma_giam_gia")
    op.drop_table("ma_giam_gia")
    op.drop_index("ix_lich_su_tim_kiem__so_ket_qua", table_name="lich_su_tim_kiem")
    op.drop_index("ix_lich_su_tim_kiem__created_at", table_name="lich_su_tim_kiem")
    op.drop_table("lich_su_tim_kiem")
    op.drop_table("ho_so_suc_khoe")
    op.drop_table("gio_hang")
    op.drop_index("ix_dia_chi__khach_hang_id", table_name="dia_chi")
    op.drop_table("dia_chi")
    op.drop_table("di_ung")
    op.drop_table("vai_tro")
    op.drop_table("thuong_hieu")
    op.drop_table("quyen")
    op.drop_index("uq_nha_san_xuat__ten_quoc_gia", table_name="nha_san_xuat")
    op.drop_table("nha_san_xuat")
    op.drop_table("nha_cung_cap")
    op.drop_index("ix_ma_otp__dich_den_muc_dich_created_at", table_name="ma_otp")
    op.drop_table("ma_otp")
    op.drop_table("khuyen_mai")
    op.drop_table("khach_hang")
    op.drop_table("hoat_chat")
    op.drop_index("ix_danh_muc__danh_muc_cha_id", table_name="danh_muc")
    op.drop_table("danh_muc")
    op.drop_table("banner")
    op.execute("DROP TYPE nguon_tri_thuc")
    op.execute("DROP TYPE vai_tro_tin_nhan")
    op.execute("DROP TYPE trang_thai_hoi_thoai")
    op.execute("DROP TYPE loai_hoi_thoai")
    op.execute("DROP TYPE ket_qua_lien_he_thu_hoi")
    op.execute("DROP TYPE trang_thai_thu_hoi")
    op.execute("DROP TYPE trang_thai_kiem_ke")
    op.execute("DROP TYPE trang_thai_tai_khoan")
    op.execute("DROP TYPE pham_vi_khuyen_mai")
    op.execute("DROP TYPE loai_giam_gia")
    op.execute("DROP TYPE huong_xu_ly_doi_tra")
    op.execute("DROP TYPE trang_thai_doi_tra")
    op.execute("DROP TYPE ly_do_doi_tra")
    op.execute("DROP TYPE ly_do_huy_hang")
    op.execute("DROP TYPE trang_thai_duyet")
    op.execute("DROP TYPE trang_thai_yeu_cau_don_thuoc")
    op.execute("DROP TYPE loai_bai_viet")
    op.execute("DROP TYPE muc_do_tuong_tac")
    op.execute("DROP TYPE loai_van_don")
    op.execute("DROP TYPE loai_bien_dong")
    op.execute("DROP TYPE khu_ton")
    op.execute("DROP TYPE trang_thai_phan_bo")
    op.execute("DROP TYPE trang_thai_giao_dich")
    op.execute("DROP TYPE loai_giao_dich")
    op.execute("DROP TYPE trang_thai_thanh_toan")
    op.execute("DROP TYPE phuong_thuc_thanh_toan")
    op.execute("DROP TYPE hinh_thuc_nhan")
    op.execute("DROP TYPE kenh_ban")
    op.execute("DROP TYPE trang_thai_don")
    op.execute("DROP TYPE trang_thai_lo")
    op.execute("DROP TYPE trang_thai_noi_dung")
    op.execute("DROP TYPE trang_thai_kinh_doanh")
    op.execute("DROP TYPE loai_san_pham")
