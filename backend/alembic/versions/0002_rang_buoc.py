"""Ràng buộc bổ sung mà DBML không biểu diễn được (docs/spec/02-database.md mục 4).

- Hàm f_unaccent và các index tìm kiếm: GIN pg_trgm, HNSW pgvector, index một phần
- 42 ràng buộc CHECK
- 5 partial unique index
- Sequence cho mã chứng từ

Viết tay bằng SQL. Không nhập từ model: migration là bản chụp bất biến, không đổi theo code.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (bảng, tên ràng buộc, biểu thức)
CHECKS: list[tuple[str, str, str]] = [
    ("don_vi_quy_doi", "ck_don_vi_quy_doi_he_so_ge_1", "he_so >= 1"),
    ("don_vi_quy_doi", "ck_don_vi_quy_doi_gia_ban_ge_0", "gia_ban >= 0"),
    ("lo_thuoc", "ck_lo_thuoc_ton_ge_0", "so_luong_ton >= 0"),
    ("lo_thuoc", "ck_lo_thuoc_giu_ge_0", "so_luong_giu >= 0"),
    ("lo_thuoc", "ck_lo_thuoc_giu_le_ton", "so_luong_giu <= so_luong_ton"),
    ("lo_thuoc", "ck_lo_thuoc_biet_tru_ge_0", "so_luong_biet_tru >= 0"),
    ("lo_thuoc", "ck_lo_thuoc_han_sau_nsx", "ngay_san_xuat IS NULL OR han_su_dung > ngay_san_xuat"),
    ("ct_gio_hang", "ck_ct_gio_hang_so_luong_gt_0", "so_luong > 0"),
    ("ct_don_hang", "ck_ct_don_hang_so_luong_gt_0", "so_luong > 0"),
    ("ct_phieu_nhap", "ck_ct_phieu_nhap_so_luong_gt_0", "so_luong > 0"),
    ("ct_phieu_huy", "ck_ct_phieu_huy_so_luong_gt_0", "so_luong > 0"),
    ("ct_phieu_xuat_tra", "ck_ct_phieu_xuat_tra_so_luong_gt_0", "so_luong > 0"),
    ("ct_yeu_cau_doi_tra", "ck_ct_yeu_cau_doi_tra_so_luong_gt_0", "so_luong > 0"),
    ("ct_phieu_nhap", "ck_ct_phieu_nhap_co_so_gt_0", "so_luong_co_so > 0"),
    ("ct_phieu_nhap", "ck_ct_phieu_nhap_gia_nhap_ge_0", "gia_nhap >= 0"),
    ("phan_bo_lo", "ck_phan_bo_lo_co_so_gt_0", "so_luong_co_so > 0"),
    ("phan_bo_lo", "ck_phan_bo_lo_gia_von_ge_0", "gia_von >= 0"),
    ("ct_phieu_dieu_chinh", "ck_ct_phieu_dieu_chinh_thay_doi_khac_0", "so_luong_thay_doi <> 0"),
    ("don_hang", "ck_don_hang_tam_tinh_ge_0", "tam_tinh >= 0"),
    ("don_hang", "ck_don_hang_giam_gia_ge_0", "giam_gia >= 0"),
    ("don_hang", "ck_don_hang_phi_van_chuyen_ge_0", "phi_van_chuyen >= 0"),
    ("don_hang", "ck_don_hang_tong_tien_dung", "tong_tien = tam_tinh - giam_gia + phi_van_chuyen"),
    (
        "don_hang",
        "ck_don_hang_phuong_thuc_tt_bat_buoc",
        "phuong_thuc_tt IS NOT NULL OR trang_thai IN ('cho_khach_xac_nhan', 'da_huy')",
    ),
    ("ct_don_hang", "ck_ct_don_hang_giam_gia_phan_bo_ge_0", "giam_gia_phan_bo >= 0"),
    ("ct_don_hang", "ck_ct_don_hang_thanh_tien_dung", "thanh_tien = so_luong * don_gia - giam_gia_phan_bo"),
    ("thanh_toan", "ck_thanh_toan_so_tien_gt_0", "so_tien > 0"),
    ("van_don", "ck_van_don_loai_khop_doi_tra", "(loai = 'tra_hang') = (yeu_cau_doi_tra_id IS NOT NULL)"),
    ("khuyen_mai", "ck_khuyen_mai_ket_thuc_sau_bat_dau", "ket_thuc > bat_dau"),
    ("khuyen_mai", "ck_khuyen_mai_gia_tri_gt_0", "gia_tri > 0"),
    ("khuyen_mai", "ck_khuyen_mai_phan_tram_le_100", "loai_giam <> 'phan_tram' OR gia_tri <= 100"),
    ("khuyen_mai", "ck_khuyen_mai_luot_moi_khach_ge_1", "luot_moi_khach >= 1"),
    ("khuyen_mai_pham_vi", "ck_khuyen_mai_pham_vi_mot_trong_hai", "num_nonnulls(danh_muc_id, san_pham_id) = 1"),
    ("thong_bao", "ck_thong_bao_mot_nguoi_nhan", "num_nonnulls(khach_hang_id, nhan_vien_id) = 1"),
    ("phien_dang_nhap", "ck_phien_dang_nhap_mot_chu_so_huu", "num_nonnulls(khach_hang_id, nhan_vien_id) = 1"),
    (
        "phieu_dieu_chinh",
        "ck_phieu_dieu_chinh_khac_nguoi_lap",
        "nguoi_duyet_id IS NULL OR nguoi_duyet_id <> nguoi_lap_id",
    ),
    ("phieu_huy", "ck_phieu_huy_khac_nguoi_lap", "nguoi_duyet_id IS NULL OR nguoi_duyet_id <> nguoi_lap_id"),
    ("phieu_xuat_tra", "ck_phieu_xuat_tra_khac_nguoi_lap", "nguoi_duyet_id IS NULL OR nguoi_duyet_id <> nhan_vien_id"),
    ("danh_gia", "ck_danh_gia_so_sao_1_5", "so_sao BETWEEN 1 AND 5"),
    ("tuong_tac_hoat_chat", "ck_tuong_tac_hoat_chat_a_nho_hon_b", "hoat_chat_a_id < hoat_chat_b_id"),
    (
        "ct_yeu_cau_don_thuoc",
        "ck_ct_yeu_cau_don_thuoc_do_tin_cay_0_1",
        "do_tin_cay_ai IS NULL OR do_tin_cay_ai BETWEEN 0 AND 1",
    ),
    ("de_xuat_nhap_hang", "ck_de_xuat_nhap_hang_ky_hop_le", "ky_ket_thuc > ky_bat_dau"),
    ("de_xuat_nhap_hang", "ck_de_xuat_nhap_hang_de_xuat_ge_0", "so_luong_de_xuat >= 0"),
]

# (tên, câu lệnh tạo). Tên dùng để DROP ở downgrade.
INDEX_DAC_BIET: list[tuple[str, str]] = [
    (
        "san_pham_ten_trgm",
        "CREATE INDEX san_pham_ten_trgm ON san_pham USING gin (f_unaccent(lower(ten)) gin_trgm_ops)",
    ),
    (
        "hoat_chat_ten_trgm",
        "CREATE INDEX hoat_chat_ten_trgm ON hoat_chat USING gin (f_unaccent(lower(ten)) gin_trgm_ops)",
    ),
    (
        "hoat_chat_khac_trgm",
        "CREATE INDEX hoat_chat_khac_trgm ON hoat_chat USING gin (f_unaccent(lower(coalesce(ten_khac, ''))) gin_trgm_ops)",
    ),
    (
        "tai_lieu_tri_thuc_hnsw",
        "CREATE INDEX tai_lieu_tri_thuc_hnsw ON tai_lieu_tri_thuc USING hnsw (embedding vector_cosine_ops)",
    ),
    (
        "lich_su_tim_kiem_rong",
        "CREATE INDEX lich_su_tim_kiem_rong ON lich_su_tim_kiem (created_at) WHERE so_ket_qua = 0",
    ),
    (
        "dia_chi_mot_mac_dinh",
        "CREATE UNIQUE INDEX dia_chi_mot_mac_dinh ON dia_chi (khach_hang_id) WHERE la_mac_dinh",
    ),
    (
        "don_vi_mot_co_so",
        "CREATE UNIQUE INDEX don_vi_mot_co_so ON don_vi_quy_doi (san_pham_id) WHERE he_so = 1",
    ),
    (
        "don_vi_mot_mac_dinh",
        "CREATE UNIQUE INDEX don_vi_mot_mac_dinh ON don_vi_quy_doi (san_pham_id) WHERE la_mac_dinh",
    ),
    (
        "anh_mot_anh_chinh",
        "CREATE UNIQUE INDEX anh_mot_anh_chinh ON anh_san_pham (san_pham_id) WHERE la_anh_chinh",
    ),
    (
        "don_thuoc_mot_don_mo",
        "CREATE UNIQUE INDEX don_thuoc_mot_don_mo ON don_hang (yeu_cau_don_thuoc_id) "
        "WHERE yeu_cau_don_thuoc_id IS NOT NULL AND trang_thai <> 'da_huy'",
    ),
]

SEQUENCES = [
    "seq_phieu_nhap",
    "seq_phieu_kiem_ke",
    "seq_phieu_dieu_chinh",
    "seq_phieu_huy",
    "seq_phieu_xuat_tra",
    "seq_lenh_thu_hoi",
    "seq_nhan_vien",
]


def upgrade() -> None:
    # Hàm IMMUTABLE bọc unaccent, bắt buộc để dùng được trong index biểu thức.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )
    for _, cau_lenh in INDEX_DAC_BIET:
        op.execute(cau_lenh)
    for bang, ten, bieu_thuc in CHECKS:
        op.execute(f"ALTER TABLE {bang} ADD CONSTRAINT {ten} CHECK ({bieu_thuc})")
    for ten in SEQUENCES:
        op.execute(f"CREATE SEQUENCE {ten}")


def downgrade() -> None:
    for ten in reversed(SEQUENCES):
        op.execute(f"DROP SEQUENCE {ten}")
    for bang, ten, _ in reversed(CHECKS):
        op.execute(f"ALTER TABLE {bang} DROP CONSTRAINT {ten}")
    for ten, _ in reversed(INDEX_DAC_BIET):
        op.execute(f"DROP INDEX {ten}")
    op.execute("DROP FUNCTION f_unaccent(text)")
