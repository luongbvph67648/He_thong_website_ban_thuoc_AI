"""Router của máy chủ mô phỏng, gắn vào ứng dụng ở `/api/v1/mo-phong` theo từng chế độ `mo_phong` đang bật."""

from fastapi import APIRouter

from app.tich_hop.mo_phong import ghn, momo, vnpay

router_thanh_toan = APIRouter(prefix="/mo-phong")
router_thanh_toan.include_router(vnpay.router)
router_thanh_toan.include_router(momo.router)

router_van_chuyen = APIRouter(prefix="/mo-phong")
router_van_chuyen.include_router(ghn.router)
