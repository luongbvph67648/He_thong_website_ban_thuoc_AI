"""Công cụ kiểm tra registry và ma trận phân quyền (spec 10 mục 3).

- `duyet_route(app)`: liệt kê mọi (phương thức, đường dẫn mẫu) kèm cây dependency THẬT của route.
- `kiem_tra_registry(...)`: đối chiếu khai báo với dependency `yeu_cau_quyen` thật gắn trên route.
- `ky_vong_duoc_phep(...)`, `kiem_tra_ma_tran(...)`: sinh ca đúng/sai từ `quyen.yaml` rồi gọi route thật.
"""

import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache

import yaml
from fastapi import FastAPI

from app.core.danh_muc_quyen import QUYEN_YAML
from tests.phan_quyen.registry import TIEN_TO_NOI_BO

PHUONG_THUC_DOC = {"GET", "HEAD", "OPTIONS"}
VAI_TRO = ("PHARMACIST", "WAREHOUSE", "ADMIN")


@dataclass(frozen=True)
class RouteThong:
    phuong_thuc: str
    duong_dan: str
    dependant: object

    @property
    def khoa(self) -> tuple[str, str]:
        return self.phuong_thuc, self.duong_dan


def _duyet(router, tien_to: str) -> Iterator[RouteThong]:
    for route in router.routes:
        if hasattr(route, "original_router"):  # include_router: FastAPI mới giữ router gốc kèm ngữ cảnh include
            yield from _duyet(route.original_router, tien_to + route.include_context.prefix)
        elif hasattr(route, "dependant") and hasattr(route, "methods"):
            for phuong_thuc in sorted(route.methods - {"HEAD", "OPTIONS"}):
                yield RouteThong(phuong_thuc, tien_to + route.path, route.dependant)


def duyet_route(app: FastAPI) -> list[RouteThong]:
    return list(_duyet(app.router, ""))


def tim_yeu_cau_quyen(dependant) -> list:
    """Mọi dependency `yeu_cau_quyen` (có thuộc tính `ma_quyen`) trong cây dependency của route."""
    tim = []
    for con in dependant.dependencies:
        if hasattr(con.call, "ma_quyen"):
            tim.append(con.call)
        tim.extend(tim_yeu_cau_quyen(con))
    return tim


def route_noi_bo(app: FastAPI) -> list[RouteThong]:
    return [r for r in duyet_route(app) if r.duong_dan.startswith(TIEN_TO_NOI_BO + "/")]


@cache
def quyen_yaml() -> dict:
    return yaml.safe_load(QUYEN_YAML.read_text(encoding="utf-8"))


@cache
def muc_cua_vai_tro(vai_tro: str) -> dict[str, str]:
    return {q["ma"]: q["vai_tro"][vai_tro] for q in quyen_yaml()["quyen"] if vai_tro in q["vai_tro"]}


def kiem_tra_registry(
    app: FastAPI,
    registry: dict[tuple[str, str], tuple[str, str]],
    cong_khai: frozenset[tuple[str, str]],
    cho_phep_chua_doi_mk: frozenset[tuple[str, str]],
) -> list[str]:
    """Danh sách vi phạm (rỗng là đạt)."""
    loi: list[str] = []
    ma_hop_le = {q["ma"] for q in quyen_yaml()["quyen"]}
    thuc_te = {r.khoa: r for r in route_noi_bo(app)}

    for khoa, r in thuc_te.items():
        yeu_cau = tim_yeu_cau_quyen(r.dependant)
        if khoa in cong_khai:
            if yeu_cau:
                loi.append(f"{khoa}: khai báo công khai nhưng route lại có yeu_cau_quyen")
            continue
        if khoa not in registry:
            loi.append(f"{khoa}: route nội bộ chưa có trong registry (thêm vào tests/phan_quyen/registry.py)")
            continue
        if len(yeu_cau) != 1:
            loi.append(f"{khoa}: cần đúng 1 Depends(yeu_cau_quyen(...)), tìm thấy {len(yeu_cau)}")
            continue
        ma, muc = registry[khoa]
        dep = yeu_cau[0]
        if (dep.ma_quyen, dep.muc) != (ma, muc):
            loi.append(f"{khoa}: registry ghi {(ma, muc)} nhưng route dùng {(dep.ma_quyen, dep.muc)}")
        if ma not in ma_hop_le:
            loi.append(f"{khoa}: mã quyền {ma!r} không có trong quyen.yaml")
        if muc == "xem" and khoa[0] not in PHUONG_THUC_DOC:
            loi.append(f"{khoa}: thao tác ghi không được khai báo mức 'xem'")
        if dep.ke_ca_chua_doi_mat_khau != (khoa in cho_phep_chua_doi_mk):
            loi.append(f"{khoa}: ke_ca_chua_doi_mat_khau={dep.ke_ca_chua_doi_mat_khau} không khớp danh sách được phép")

    for khoa in [*registry, *cong_khai]:
        if khoa not in thuc_te:
            loi.append(f"{khoa}: có trong registry nhưng không có route tương ứng (registry lỗi thời)")
    return loi


def ky_vong_duoc_phep(vai_tro: str, ma: str, muc: str, phuong_thuc: str) -> bool:
    """Theo quyen.yaml: vai trò có `ma` ở mức đủ cho thao tác này không (ghi luôn cần `day_du`)."""
    co = muc_cua_vai_tro(vai_tro).get(ma)
    if co is None:
        return False
    can = muc if phuong_thuc in PHUONG_THUC_DOC else "day_du"
    return can == "xem" or co == "day_du"


def duong_dan_thu(duong_dan: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", duong_dan)


async def goi_route(client, phuong_thuc: str, duong_dan: str):
    kwargs = {"json": {}} if phuong_thuc in {"POST", "PUT", "PATCH"} else {}
    return await client.request(phuong_thuc, duong_thu(duong_dan), **kwargs)


duong_thu = duong_dan_thu


async def kiem_tra_ma_tran(clients: dict[str, object], registry: dict[tuple[str, str], tuple[str, str]]) -> list[str]:
    """Gọi từng route của registry bằng từng vai trò. Không đủ quyền phải nhận 403 KHONG_CO_QUYEN; đủ quyền thì KHÔNG
    được nhận 403 (có thể 404/422 vì dữ liệu giả)."""
    loi: list[str] = []
    for (phuong_thuc, duong_dan), (ma, muc) in registry.items():
        for vai_tro in VAI_TRO:
            phan_hoi = await goi_route(clients[vai_tro], phuong_thuc, duong_dan)
            duoc = ky_vong_duoc_phep(vai_tro, ma, muc, phuong_thuc)
            if duoc and phan_hoi.status_code == 403:
                loi.append(f"{vai_tro} {phuong_thuc} {duong_dan}: đáng lẽ được phép nhưng nhận 403")
            if not duoc and not (phan_hoi.status_code == 403 and phan_hoi.json()["ma_loi"] == "KHONG_CO_QUYEN"):
                loi.append(
                    f"{vai_tro} {phuong_thuc} {duong_dan}: đáng lẽ 403 KHONG_CO_QUYEN, nhận {phan_hoi.status_code}"
                )
    return loi
