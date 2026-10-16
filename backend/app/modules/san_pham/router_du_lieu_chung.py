"""Dữ liệu dùng chung của Admin (AD05): `/api/v1/noi-bo/{thuong-hieu,nha-san-xuat,hoat-chat}`. Cần `master_data.manage`.

Ba nhóm cùng một khuôn nên route được dựng bằng `tao_router`; tên hàm route kèm tên nhóm để `operation_id` không trùng.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.core.db import Db
from app.core.phan_quyen import yeu_cau_quyen
from app.core.phan_trang import PhanTrang, SapXepQuery, Trang, tao_trang
from app.core.tham_so import IdInt, tu_khoa_tim
from app.models.he_thong import NhanVien
from app.modules.san_pham import du_lieu_chung as dich_vu
from app.modules.san_pham.du_lieu_chung import HOAT_CHAT, NHA_SAN_XUAT, THUONG_HIEU, Nhom
from app.modules.san_pham.schemas_du_lieu_chung import (
    HoatChatDoc,
    HoatChatSua,
    HoatChatTao,
    NhaSanXuatDoc,
    NhaSanXuatSua,
    NhaSanXuatTao,
    ThuongHieuDoc,
    ThuongHieuSua,
    ThuongHieuTao,
)
from app.modules.tai_khoan.phien_http import dia_chi_ip

DuLieuXem = Annotated[NhanVien, Depends(yeu_cau_quyen("master_data.manage", "xem"))]
DuLieuSua = Annotated[NhanVien, Depends(yeu_cau_quyen("master_data.manage"))]


def tao_router(duong_dan: str, tag: str, nhom: Nhom, doc, tao_schema, sua_schema, mo_ta_tim: str) -> APIRouter:
    router = APIRouter(prefix=f"/noi-bo/{duong_dan}", tags=[tag])
    ten = nhom.bang

    async def danh_sach(
        actor: DuLieuXem,
        db: Db,
        tp: PhanTrang,
        q: tu_khoa_tim(mo_ta_tim) = None,  # type: ignore[valid-type]
        sap_xep: SapXepQuery = None,
    ):
        dong, tong = await dich_vu.danh_sach(db, nhom, doc, q=q, sap_xep=sap_xep, tp=tp)
        return tao_trang(dong, tong, tp)

    async def chi_tiet(ban_ghi_id: IdInt, actor: DuLieuXem, db: Db):
        return await dich_vu.lay_mot(db, nhom, doc, ban_ghi_id)

    async def tao(du_lieu: tao_schema, request: Request, actor: DuLieuSua, db: Db):  # type: ignore[valid-type]
        return await dich_vu.tao(db, actor, nhom, doc, du_lieu, ip=dia_chi_ip(request))

    async def sua(ban_ghi_id: IdInt, du_lieu: sua_schema, request: Request, actor: DuLieuSua, db: Db):  # type: ignore[valid-type]
        return await dich_vu.sua(db, actor, nhom, doc, ban_ghi_id, du_lieu, ip=dia_chi_ip(request))

    async def xoa(ban_ghi_id: IdInt, request: Request, actor: DuLieuSua, db: Db) -> Response:
        await dich_vu.xoa(db, actor, nhom, ban_ghi_id, ip=dia_chi_ip(request))
        return Response(status_code=204)

    for ham, hau_to in ((danh_sach, "danh_sach"), (chi_tiet, "chi_tiet"), (tao, "tao"), (sua, "sua"), (xoa, "xoa")):
        ham.__name__ = f"{hau_to}_{ten}"
    router.add_api_route(
        "", danh_sach, methods=["GET"], response_model=Trang[doc], summary=f"Danh sách {nhom.nhan} (AD05)"
    )
    router.add_api_route(
        "/{ban_ghi_id}", chi_tiet, methods=["GET"], response_model=doc, summary=f"Chi tiết {nhom.nhan} (AD05)"
    )
    router.add_api_route(
        "", tao, methods=["POST"], status_code=201, response_model=doc, summary=f"Thêm {nhom.nhan} (AD05)"
    )
    router.add_api_route("/{ban_ghi_id}", sua, methods=["PATCH"], response_model=doc, summary=f"Sửa {nhom.nhan} (AD05)")
    router.add_api_route(
        "/{ban_ghi_id}", xoa, methods=["DELETE"], status_code=204, summary=f"Xóa {nhom.nhan} chưa được dùng (AD05)"
    )
    return router


thuong_hieu_router = tao_router(
    "thuong-hieu", "Thương hiệu", THUONG_HIEU, ThuongHieuDoc, ThuongHieuTao, ThuongHieuSua, "Tìm theo tên"
)
nha_san_xuat_router = tao_router(
    "nha-san-xuat", "Nhà sản xuất", NHA_SAN_XUAT, NhaSanXuatDoc, NhaSanXuatTao, NhaSanXuatSua, "Tìm theo tên"
)
hoat_chat_router = tao_router(
    "hoat-chat", "Hoạt chất", HOAT_CHAT, HoatChatDoc, HoatChatTao, HoatChatSua, "Tìm theo tên hoặc tên khác"
)
