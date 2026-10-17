"""T8.2: nhật ký hệ thống bất biến và index theo thời gian.

- Trigger chặn UPDATE và DELETE trên `nhat_ky_he_thong` (spec 02: "chỉ INSERT"); TRUNCATE vẫn dùng được cho quản trị
  CSDL và test. Trước đây chỉ ứng dụng không có route sửa/xóa, nay DB cũng từ chối.
- Index `created_at` cho trang nhật ký và thống kê (quét tuần tự 400.000 dòng ~30 ms).

Viết tay bằng SQL. Không sửa migration cũ.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_nhat_ky_he_thong__created_at", "nhat_ky_he_thong", ["created_at"])
    op.execute(
        """
        CREATE FUNCTION nhat_ky_chi_them() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'nhat_ky_he_thong chỉ được INSERT (không UPDATE/DELETE)' USING ERRCODE = 'integrity_constraint_violation';
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER trg_nhat_ky_chi_them BEFORE UPDATE OR DELETE ON nhat_ky_he_thong "
        "FOR EACH ROW EXECUTE FUNCTION nhat_ky_chi_them()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_nhat_ky_chi_them ON nhat_ky_he_thong")
    op.execute("DROP FUNCTION nhat_ky_chi_them()")
    op.drop_index("ix_nhat_ky_he_thong__created_at", table_name="nhat_ky_he_thong")
