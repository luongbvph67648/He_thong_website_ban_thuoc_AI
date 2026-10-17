"""Mã nguồn phải chạy được trên Windows/macOS (hệ tệp không phân biệt hoa thường)."""

import subprocess
from collections import defaultdict
from pathlib import PurePosixPath

from app.core.config import BACKEND_DIR


def test_khong_co_hai_tep_chi_khac_nhau_o_chu_hoa_thuong():
    ra = subprocess.run(
        ["git", "ls-files"], cwd=BACKEND_DIR.parent, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    theo_ten: dict[str, set[str]] = defaultdict(set)
    theo_goc: dict[str, set[str]] = defaultdict(
        set
    )  # TS/JS import không kèm đuôi: `./ThuocTrenDon` khớp cả .ts lẫn .tsx
    for duong_dan in ra:
        p = PurePosixPath(duong_dan)
        theo_ten[duong_dan.lower()].add(duong_dan)
        if p.suffix in {".ts", ".tsx", ".js", ".jsx"}:
            theo_goc[str(p.with_suffix("")).lower()].add(duong_dan)
    trung = [
        sorted(v)
        for v in (*theo_ten.values(), *theo_goc.values())
        if len({x.lower() for x in v}) < len(v)
        or (len(v) > 1 and len({str(PurePosixPath(x).with_suffix("")) for x in v}) > 1)
    ]
    assert not trung, f"Tệp trùng tên khi bỏ phân biệt hoa thường (Windows sẽ lỗi): {trung}"
