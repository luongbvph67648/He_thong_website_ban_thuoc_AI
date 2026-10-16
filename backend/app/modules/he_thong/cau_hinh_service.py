"""Cấu hình hệ thống của Admin (AD08).

- Chỉ các khóa trong `KHOA_CAU_HINH` (bốn khóa `ai_*` thuộc AD09); mỗi giá trị được kiểm tra kiểu và khoảng trước
  khi ghi.
- Khóa lạc quan bằng `phien_ban` (dấu vân tay nội dung): một trang mở từ trước không ngầm ghi đè thay đổi của Admin
  khác.
- Khóa dòng `cau_hinh` `FOR UPDATE` nên hai Admin sửa cùng khóa được tuần tự hóa; ghi `nhan_vien_cap_nhat_id` và
  nhật ký.
- Không cần xóa cache: mọi nơi dùng đọc `cau_hinh` mỗi lần (`core.cau_hinh.doc_cau_hinh`) nên có hiệu lực ngay.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cau_hinh_khoa import KHOA_CAU_HINH, KhoaCauHinh, dau_van_tay, kiem_tra_gia_tri
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import CauHinh, NhanVien
from app.modules.he_thong.schemas import CauHinhDoc, NhanVienTomTat, TruongSoDoc

BANG = "cau_hinh"


def _doc(k: KhoaCauHinh, dong: CauHinh | None) -> CauHinhDoc:
    gia_tri = None if dong is None else dong.gia_tri
    return CauHinhDoc(
        khoa=k.khoa,
        nhom=k.nhom,
        nhan=k.nhan,
        mo_ta=None if dong is None else dong.mo_ta,
        kieu=k.kieu,
        don_vi=k.don_vi,
        toi_thieu=k.toi_thieu,
        toi_da=k.toi_da,
        truong=[TruongSoDoc(**vars(t)) for t in k.truong],
        gia_tri=gia_tri,
        phien_ban=dau_van_tay(gia_tri),
        nhan_vien_cap_nhat=(
            NhanVienTomTat.model_validate(dong.nhan_vien_cap_nhat) if dong and dong.nhan_vien_cap_nhat else None
        ),
        updated_at=None if dong is None else dong.updated_at,
    )


async def _tai(db: AsyncSession, *, khoa: str | None = None) -> dict[str, CauHinh]:
    truy_van = (
        select(CauHinh)
        .where(CauHinh.khoa.in_([khoa] if khoa else list(KHOA_CAU_HINH)))
        .options(selectinload(CauHinh.nhan_vien_cap_nhat))
        .execution_options(populate_existing=True)
    )
    return {d.khoa: d for d in (await db.execute(truy_van)).scalars()}


async def danh_sach(db: AsyncSession) -> list[CauHinhDoc]:
    """Mọi khóa của AD08 theo thứ tự hiển thị; khóa chưa có trong bảng vẫn có mặt với `gia_tri = None`."""
    co_san = await _tai(db)
    return [_doc(k, co_san.get(k.khoa)) for k in KHOA_CAU_HINH.values()]


async def cap_nhat(
    db: AsyncSession, actor: NhanVien, khoa: str, gia_tri: object, phien_ban: str, *, ip: str
) -> CauHinhDoc:
    """Đặt giá trị mới cho `khoa` nếu `phien_ban` còn là bản hiện tại. Đặt đúng giá trị hiện tại thì không ghi gì."""
    await dam_bao_la_admin(db, actor)
    moi = kiem_tra_gia_tri(khoa, gia_tri)  # 404 khóa lạ, 400 giá trị sai: trước khi giữ khóa dòng
    k = KHOA_CAU_HINH[khoa]
    dong = (await db.execute(select(CauHinh).where(CauHinh.khoa == khoa).with_for_update())).scalar_one_or_none()
    cu = None if dong is None else dong.gia_tri
    if dau_van_tay(cu) != phien_ban:
        raise LoiNghiepVu(
            "DU_LIEU_DA_THAY_DOI",
            "Cấu hình này vừa được người khác thay đổi, hãy tải lại rồi kiểm tra trước khi lưu",
        )
    if dong is not None and cu == moi:
        return _doc(k, (await _tai(db, khoa=khoa))[khoa])
    bay_gio = bay_gio_utc()
    if dong is None:  # khóa chưa seed: tạo mới (hai Admin tạo cùng lúc thì bên thua nhận 409)
        try:
            async with db.begin_nested():
                db.add(CauHinh(khoa=khoa, gia_tri=moi, nhan_vien_cap_nhat_id=actor.id, updated_at=bay_gio))
                await db.flush()
        except IntegrityError as loi:
            raise LoiNghiepVu("DU_LIEU_DA_THAY_DOI", "Cấu hình này vừa được người khác tạo, hãy tải lại") from loi
    else:
        dong.gia_tri = moi
        dong.nhan_vien_cap_nhat_id = actor.id
        dong.updated_at = bay_gio
        await db.flush()
    await ghi_nhat_ky(
        db,
        nhan_vien_id=actor.id,
        hanh_dong="tao" if dong is None else "sua",
        bang=BANG,
        ban_ghi_id=khoa,
        gia_tri_cu=cu,
        gia_tri_moi=moi,
        ip=ip,
    )
    return _doc(k, (await _tai(db, khoa=khoa))[khoa])
