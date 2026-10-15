"""T0.3: model SQLAlchemy khớp ERD (docs/database/ERD_da_chinh_sua.dbml)."""

import subprocess
import sys
from enum import StrEnum

import pytest
from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, Float, func, select, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models import Base, enums
from app.models.ban_hang import CtDonHang, DonHang
from app.models.kho import LoThuoc
from app.models.san_pham import DanhMuc, DonViQuyDoi, SanPham
from scripts.so_sanh_schema import cau_truc_tu_model, db_tam, lay_cau_truc, so_sanh, so_sanh_model_voi_erd

# ---------- Cấu trúc tổng thể ----------


def test_co_du_65_bang():
    assert len(Base.metadata.tables) == 65


def _enum_python():
    return {
        ten: lop
        for ten, lop in vars(enums).items()
        if isinstance(lop, type) and issubclass(lop, StrEnum) and lop is not StrEnum
    }


def _enum_sqlalchemy():
    return {v.name: v for k, v in vars(enums).items() if k.startswith("KIEU_") and isinstance(v, Enum)}


def test_co_du_33_enum_native_dung_thu_tu():
    assert len(_enum_python()) == 33
    kieu = _enum_sqlalchemy()
    assert len(kieu) == 33
    for ten, v in kieu.items():
        assert v.native_enum, ten
        lop = _enum_python()["".join(w.capitalize() for w in ten.split("_"))]
        assert list(v.enums) == [m.value for m in lop], f"enum {ten} lệch thứ tự giá trị"


def test_enum_trang_thai_don_dung_thu_tu_trong_erd():
    assert [m.value for m in enums.TrangThaiDon] == [
        "cho_khach_xac_nhan", "cho_thanh_toan", "cho_xac_nhan", "da_xac_nhan", "dang_soan_hang",
        "cho_lay_hang", "dang_giao", "da_giao", "hoan_tat", "giao_that_bai", "hoan_ve_kho", "da_huy",
    ]  # fmt: skip  # không còn doi_tra (DB06)


def test_cot_embedding_la_vector_1024():
    kieu = Base.metadata.tables["tai_lieu_tri_thuc"].c.embedding.type
    assert isinstance(kieu, Vector)
    assert kieu.dim == 1024


def test_khong_co_cot_float_tien_dung_numeric():
    for bang in Base.metadata.tables.values():
        for cot in bang.columns:
            assert not isinstance(cot.type, Float), f"{bang.name}.{cot.name} dùng float"
    assert Base.metadata.tables["don_hang"].c.tong_tien.type.asdecimal


def test_cot_metadata_cua_erd_khong_de_len_thuoc_tinh_cua_declarative():
    """Cột `metadata` của tai_lieu_tri_thuc phải đặt tên thuộc tính khác để không đè Base.metadata."""
    from app.models.ai import TaiLieuTriThuc

    assert TaiLieuTriThuc.__table__.c["metadata"] is TaiLieuTriThuc.metadata_.property.columns[0]
    assert Base.metadata is not TaiLieuTriThuc.metadata_


def test_mapper_cau_hinh_khong_canh_bao():
    """Chạy ở tiến trình riêng: cảnh báo của SQLAlchemy (quan hệ chồng chéo, thiếu back_populates...) bị coi là lỗi."""
    ma = (
        "import warnings, sqlalchemy.exc as e;"
        "warnings.filterwarnings('error', category=e.SAWarning);"
        "import app.models; from sqlalchemy.orm import configure_mappers; configure_mappers(); print('ok')"
    )
    kq = subprocess.run([sys.executable, "-c", ma], capture_output=True, text=True, cwd=".")
    assert kq.returncode == 0, kq.stderr[-1500:]
    assert kq.stdout.strip().endswith("ok")


# ---------- Khớp DDL của ERD ----------


async def test_model_khop_ddl_cua_erd():
    """create_all() từ model và DDL của ERD phải cho cùng cấu trúc: bảng, cột (kiểu, nullable, default, identity),
    khóa ngoại, index, enum."""
    khac = await so_sanh_model_voi_erd(settings.DATABASE_URL)
    assert khac == []


async def test_cong_cu_so_sanh_phat_hien_duoc_khac_biet():
    """Công cụ so sánh chỉ đáng tin nếu nó thực sự bắt được lỗi."""
    async with db_tam(settings.DATABASE_URL, "kt_so_sanh") as engine:
        goc = await cau_truc_tu_model(engine)
        assert so_sanh(goc, goc) == []
        async with engine.begin() as conn:
            for cau in (
                "ALTER TABLE san_pham ALTER COLUMN ten TYPE varchar(300)",
                "ALTER TABLE san_pham ALTER COLUMN so_dang_ky SET NOT NULL",
                "ALTER TABLE san_pham ALTER COLUMN ton_toi_thieu SET DEFAULT 5",
                "ALTER TABLE san_pham ALTER COLUMN id DROP IDENTITY",
                "ALTER TABLE san_pham DROP CONSTRAINT fk_san_pham_danh_muc_id_danh_muc",
                "DROP INDEX ix_san_pham__loai_san_pham",
                "ALTER TABLE san_pham DROP COLUMN la_noi_bat",
                "ALTER TYPE loai_san_pham ADD VALUE 'moi'",
                "DROP TABLE anh_san_pham",
            ):
                await conn.execute(text(cau))
        sau = await lay_cau_truc(engine)
    khac = "\n".join(so_sanh(goc, sau, "goc", "sau"))
    for ky_vong in (
        "cột san_pham.ten: kieu khác",
        "cột san_pham.so_dang_ky: bat_buoc khác",
        "cột san_pham.ton_toi_thieu: mac_dinh khác",
        "cột san_pham.id: identity khác",
        "khóa ngoại: chỉ có ở goc",
        "index",
        "san_pham', 'la_noi_bat'",
        "enum loai_san_pham: giá trị/thứ tự khác",
        "bảng: chỉ có ở goc: anh_san_pham",
    ):
        assert ky_vong in khac, f"không phát hiện: {ky_vong}\n{khac}"


# ---------- Quan hệ chạy thật trên DB ----------


async def test_quan_he_nap_bang_selectinload_va_cam_lazy_load_ngam(engine_co_bang):
    async with AsyncSession(engine_co_bang, expire_on_commit=False) as db, db.begin():
        goc = DanhMuc(ten="Thuốc", slug="thuoc")
        con = DanhMuc(ten="Giảm đau", slug="giam-dau", danh_muc_cha=goc)
        db.add_all([goc, con])
        await db.flush()
        sp = SanPham(
            sku="SP1", ten="Paracetamol", slug="para", loai_san_pham=enums.LoaiSanPham.thuoc_khong_ke_don,
            danh_muc_id=con.id, don_vi_co_so="viên",
        )  # fmt: skip
        db.add(sp)
        await db.flush()
        db.add_all([
            DonViQuyDoi(san_pham_id=sp.id, ten_don_vi="viên", he_so=1, gia_ban=1000),
            DonViQuyDoi(san_pham_id=sp.id, ten_don_vi="hộp", he_so=100, gia_ban=90000),
        ])  # fmt: skip

    async with AsyncSession(engine_co_bang) as db:
        # Server default (created_at, trang_thai...) được đọc lại, kiểu enum trả về là StrEnum.
        sp = (await db.scalars(select(SanPham).options(selectinload(SanPham.don_vi_quy_doi)))).one()
        assert sorted(d.ten_don_vi for d in sp.don_vi_quy_doi) == ["hộp", "viên"]
        assert sp.trang_thai is enums.TrangThaiKinhDoanh.dang_kinh_doanh
        assert sp.created_at is not None

    async with AsyncSession(engine_co_bang) as db:  # session mới: không dính identity map của session trên
        # Không nạp trước thì truy cập quan hệ phải báo lỗi chứ không âm thầm chạy truy vấn (lazy="raise").
        sp2 = (await db.scalars(select(SanPham))).one()
        with pytest.raises(InvalidRequestError):
            _ = sp2.don_vi_quy_doi
        with pytest.raises(InvalidRequestError):
            _ = sp2.danh_muc

    async with AsyncSession(engine_co_bang) as db:
        # Quan hệ tự tham chiếu của cây danh mục: cha -> con và con -> cha.
        cha = (
            await db.scalars(select(DanhMuc).where(DanhMuc.slug == "thuoc").options(selectinload(DanhMuc.danh_muc_con)))
        ).one()
        assert [c.slug for c in cha.danh_muc_con] == ["giam-dau"]
        con = (
            await db.scalars(
                select(DanhMuc).where(DanhMuc.slug == "giam-dau").options(selectinload(DanhMuc.danh_muc_cha))
            )
        ).one()
        assert con.danh_muc_cha.slug == "thuoc"


async def test_khoa_ngoai_kep_chan_don_vi_cua_san_pham_khac(engine_co_bang):
    """ct_don_hang.(don_vi_id, san_pham_id) phải trỏ tới đơn vị thuộc ĐÚNG sản phẩm đó."""
    from sqlalchemy.exc import IntegrityError

    async with AsyncSession(engine_co_bang) as db, db.begin():
        dm = DanhMuc(ten="X", slug="x")
        db.add(dm)
        await db.flush()
        sp = [
            SanPham(sku=f"S{i}", ten=f"SP{i}", slug=f"s{i}", loai_san_pham=enums.LoaiSanPham.thuoc_khong_ke_don,
                    danh_muc_id=dm.id, don_vi_co_so="viên")
            for i in (1, 2)
        ]  # fmt: skip
        db.add_all(sp)
        await db.flush()
        dv = DonViQuyDoi(san_pham_id=sp[0].id, ten_don_vi="viên", he_so=1, gia_ban=1000)
        don = DonHang(
            ma_don="DH1", trang_thai=enums.TrangThaiDon.cho_xac_nhan, tam_tinh=1000, tong_tien=1000,
            phuong_thuc_tt=enums.PhuongThucThanhToan.cod,
        )  # fmt: skip
        db.add_all([dv, don])
        await db.flush()
        dv_id, sp1_id, sp2_id, don_id = dv.id, sp[0].id, sp[1].id, don.id

    def dong(san_pham_id):
        return CtDonHang(
            don_hang_id=don_id, san_pham_id=san_pham_id, don_vi_id=dv_id, ten_san_pham="x", ten_don_vi="viên",
            he_so=1, so_luong=1, don_gia=1000, thanh_tien=1000,
        )  # fmt: skip

    async with AsyncSession(engine_co_bang) as db, db.begin():
        db.add(dong(sp1_id))  # đúng sản phẩm của đơn vị: hợp lệ

    with pytest.raises(IntegrityError):
        async with AsyncSession(engine_co_bang) as db, db.begin():
            db.add(dong(sp2_id))  # đơn vị của sản phẩm 1 gắn vào sản phẩm 2: bị chặn


async def test_server_default_va_enum_tren_lo_thuoc(engine_co_bang):
    async with AsyncSession(engine_co_bang, expire_on_commit=False) as db, db.begin():
        dm = DanhMuc(ten="X", slug="x")
        db.add(dm)
        await db.flush()
        sp = SanPham(sku="S", ten="S", slug="s", loai_san_pham=enums.LoaiSanPham.thuoc_ke_don,
                     danh_muc_id=dm.id, don_vi_co_so="viên")  # fmt: skip
        db.add(sp)
        await db.flush()
        lo = LoThuoc(san_pham_id=sp.id, so_lo="L1", han_su_dung=func.current_date(), gia_nhap=800)
        db.add(lo)
        await db.flush()
        await db.refresh(lo)
        assert (lo.so_luong_ton, lo.so_luong_giu, lo.so_luong_biet_tru) == (0, 0, 0)
        assert lo.trang_thai is enums.TrangThaiLo.dang_ban
