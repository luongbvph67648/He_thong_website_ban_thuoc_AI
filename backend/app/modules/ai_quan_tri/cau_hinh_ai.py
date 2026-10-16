"""AD09: cấu hình AI (bật/tắt module, dấu hiệu nguy hiểm, ngưỡng chuyển dược sĩ, lời nhắc bổ sung). Chỉ Admin ghi."""

from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cau_hinh import doc_cau_hinh
from app.core.cau_hinh_khoa import dau_van_tay
from app.core.loi import LoiNghiepVu
from app.core.nhat_ky import ghi_nhat_ky
from app.core.phan_quyen import dam_bao_la_admin
from app.core.thoi_gian import bay_gio_utc
from app.models.he_thong import CauHinh, NhanVien

MODULE_AI = ("tim_kiem", "chat", "tra_anh", "doc_don_thuoc", "goi_y", "du_bao")
MAC_DINH: dict[str, Any] = {
    "ai_module": dict.fromkeys(MODULE_AI, True),
    "ai_dau_hieu_nguy_hiem": [],
    "ai_nguong_chuyen_duoc_si": 0.6,
    "ai_loi_nhac_bo_sung": "",
}
CUM_TU = Annotated[str, Field(min_length=2, max_length=100, pattern=r"^[^\x00]*$")]


class CauHinhAiDoc(BaseModel):
    ai_module: dict[str, bool]
    ai_dau_hieu_nguy_hiem: list[str]
    ai_nguong_chuyen_duoc_si: float
    ai_loi_nhac_bo_sung: str
    phien_ban: str


class CauHinhAiSua(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phien_ban: str
    ai_module: dict[str, bool] | None = None
    ai_dau_hieu_nguy_hiem: Annotated[list[CUM_TU], Field(max_length=200)] | None = None
    ai_nguong_chuyen_duoc_si: Annotated[float, Field(gt=0, le=1)] | None = None
    ai_loi_nhac_bo_sung: Annotated[str, Field(max_length=2000, pattern=r"^[^\x00]*$")] | None = None

    @field_validator("ai_module")
    @classmethod
    def _module(cls, v: dict[str, bool] | None) -> dict[str, bool] | None:
        if v is not None and set(v) != set(MODULE_AI):
            raise ValueError(f"Phải đủ các module: {', '.join(MODULE_AI)}")
        return v


async def doc(db: AsyncSession) -> dict[str, Any]:
    return {k: await doc_cau_hinh(db, k, mac) for k, mac in MAC_DINH.items()}


async def lay(db: AsyncSession) -> CauHinhAiDoc:
    gia_tri = await doc(db)
    return CauHinhAiDoc(**gia_tri, phien_ban=dau_van_tay(gia_tri))


async def module_bat(db: AsyncSession, ten: str) -> bool:
    """Module AI còn bật không; khóa thiếu coi như bật (mặc định của seed)."""
    return bool((await doc_cau_hinh(db, "ai_module", MAC_DINH["ai_module"])).get(ten, True))


async def cap_nhat(db: AsyncSession, nv: NhanVien, vao: CauHinhAiSua, *, ip: str) -> CauHinhAiDoc:
    await dam_bao_la_admin(db, nv)
    cac_dong = {
        r.khoa: r
        for r in (await db.execute(select(CauHinh).where(CauHinh.khoa.in_(list(MAC_DINH))).with_for_update())).scalars()
    }
    cu = {k: (cac_dong[k].gia_tri if k in cac_dong else mac) for k, mac in MAC_DINH.items()}
    if dau_van_tay(cu) != vao.phien_ban:
        raise LoiNghiepVu("DU_LIEU_DA_THAY_DOI", "Cấu hình AI vừa được người khác thay đổi, hãy tải lại rồi kiểm tra")
    moi = dict(cu)
    for k in MAC_DINH:
        gia_tri = getattr(vao, k)
        if gia_tri is not None:
            moi[k] = list(dict.fromkeys(g.strip() for g in gia_tri)) if k == "ai_dau_hieu_nguy_hiem" else gia_tri
    if moi != cu:
        bay_gio = bay_gio_utc()
        for k, v in moi.items():
            if v == cu[k]:
                continue
            if k in cac_dong:
                cac_dong[k].gia_tri, cac_dong[k].nhan_vien_cap_nhat_id, cac_dong[k].updated_at = v, nv.id, bay_gio
            else:
                db.add(CauHinh(khoa=k, gia_tri=v, nhan_vien_cap_nhat_id=nv.id, updated_at=bay_gio))
        await db.flush()
        for k in MAC_DINH:
            if moi[k] != cu[k]:
                await ghi_nhat_ky(
                    db, nhan_vien_id=nv.id, hanh_dong="sua", bang="cau_hinh", ban_ghi_id=k,
                    gia_tri_cu=cu[k], gia_tri_moi=moi[k], ip=ip,
                )  # fmt: skip
    return CauHinhAiDoc(**moi, phien_ban=dau_van_tay(moi))
