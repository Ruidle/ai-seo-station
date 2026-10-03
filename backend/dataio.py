"""一键导入 / 导出（文件中心 · 数据互通）。

- 导入：上传 CSV / JSON / XLSX -> 批量灌入 keywords / backlinks / metrics 三张表。
- 导出：把 keywords / backlinks / metrics / reports / uploads 全量导出为 CSV / JSON / XLSX。
- 设计：解析失败的行跳过不中断；类型转换用 try，避免脏数据让整批失败。
复用 db 层（SQLite WAL），密钥不进本模块。
"""
import csv
import io
import json

from . import db


# 各实体导入规格：表名、列、插入 SQL、行映射
IMPORT_SPECS = {
    "keywords": {
        "table": "keywords",
        "columns": ["seed", "kw", "source"],
        "sql": "INSERT INTO keywords(seed,kw,source) VALUES(?,?,?)",
        "map": lambda r: (
            (r.get("seed") or "").strip(),
            (r.get("kw") or "").strip(),
            (r.get("source") or "rule").strip() or "rule",
        ),
        "req": ["kw"],
    },
    "backlinks": {
        "table": "backlinks",
        "columns": ["site", "url", "anchor", "type", "status", "note"],
        "sql": "INSERT INTO backlinks(site,url,anchor,type,status,note) VALUES(?,?,?,?,?,?)",
        "map": lambda r: (
            (r.get("site") or "").strip(),
            (r.get("url") or "").strip(),
            (r.get("anchor") or "").strip(),
            (r.get("type") or "guest-post").strip() or "guest-post",
            (r.get("status") or "planned").strip() or "planned",
            (r.get("note") or "").strip(),
        ),
        "req": ["url"],
    },
    "metrics": {
        "table": "metrics",
        "columns": ["site", "date", "indexed", "avg_ranking", "traffic", "kw_count"],
        "sql": "INSERT INTO metrics(site,date,indexed,avg_ranking,traffic,kw_count) VALUES(?,?,?,?,?,?)",
        "map": lambda r: (
            (r.get("site") or "").strip(),
            (r.get("date") or "").strip(),
            _to_int(r.get("indexed")),
            _to_float(r.get("avg_ranking")),
            _to_int(r.get("traffic")),
            _to_int(r.get("kw_count")),
        ),
        "req": ["site", "date"],
    },
}

# 导入模板示例（供 /api/import/template 下载）
TEMPLATES = {
    "keywords": [["seed", "kw", "source"], ["led street light", "led street light 100w", "rule"]],
    "backlinks": [["site", "url", "anchor", "type", "status", "note"],
                  ["example.com", "https://example.com/guest-post", "led street light", "guest-post", "planned", ""]],
    "metrics": [["site", "date", "indexed", "avg_ranking", "traffic", "kw_count"],
                ["mysite.com", "2026-08-16", "120", "15.5", "300", "40"]],
}

# 导出实体 -> 表 + 列
EXPORT_SPECS = {
    "keywords": ("keywords", ["id", "seed", "kw", "source", "created_at"]),
    "backlinks": ("backlinks", ["id", "site", "url", "anchor", "type", "status", "note", "created_at"]),
    "metrics": ("metrics", ["id", "site", "date", "indexed", "avg_ranking", "traffic", "kw_count", "created_at"]),
    "reports": ("reports", ["id", "site", "score", "created_at"]),
    "uploads": ("uploads", ["id", "filename", "ext", "size", "created_at"]),
}


def _to_int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


# ---------------- 解析导入文件 ----------------
def parse_import_file(path: str, ext: str) -> list:
    """解析 CSV/JSON/XLSX 为 list[dict]。失败抛异常（由路由捕获）。"""
    ext = (ext or "").lower()
    if ext == ".json":
        return json.loads(io.open(path, encoding="utf-8").read())
    if ext == ".csv":
        with io.open(path, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    if ext == ".xlsx":
        import openpyxl

        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = []
        for ws in wb.worksheets:
            it = ws.iter_rows(values_only=True)
            header = [str(h).strip() if h is not None else "" for h in next(it)]
            for r in it:
                if all(c is None for c in r):
                    continue
                rows.append({header[i]: (r[i] if i < len(r) else None) for i in range(len(header))})
        return rows
    raise ValueError(f"不支持的导入格式：{ext}")


def do_import(rows: list, entity: str) -> int:
    """批量插入，返回成功条数。脏行跳过不中断。"""
    spec = IMPORT_SPECS.get(entity)
    if not spec:
        raise ValueError(f"未知导入实体：{entity}")
    conn = db.get_conn()
    n = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        if any((r.get(k) or "").strip() == "" for k in spec["req"]):
            continue  # 缺必填列跳过
        try:
            conn.execute(spec["sql"], spec["map"](r))
            n += 1
        except Exception:
            continue
    conn.commit()
    conn.close()
    return n


# ---------------- 导出 ----------------
def gather_export(entity: str):
    """返回 (columns, rows)。entity='all' 合并全部表。"""
    if entity == "all":
        parts = []
        for e in ("keywords", "backlinks", "metrics", "reports", "uploads"):
            cols, rows = _gather_one(e)
            parts.append((e, cols, rows))
        return parts
    return _gather_one(entity)


def _gather_one(entity: str):
    table, cols = EXPORT_SPECS[entity]
    conn = db.get_conn()
    rows = conn.execute(f"SELECT {','.join(cols)} FROM {table} ORDER BY id DESC").fetchall()
    conn.close()
    return cols, [dict(r) for r in rows]


def build_export(entity: str, fmt: str):
    """返回 (bytes, mimetype, file_ext)。"""
    data = gather_export(entity)
    if entity == "all":
        if fmt == "json":
            payload = {e: rows for e, _, rows in data}
            return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", "json"
        if fmt == "xlsx":
            return _to_xlsx_multi(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
        # csv：多 sheet 合并为一个长表（带 entity 列）
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["entity", "key", "value"])
        for e, _, rows in data:
            for r in rows:
                for k, v in r.items():
                    w.writerow([e, k, v])
        return buf.getvalue().encode("utf-8"), "text/csv", "csv"

    cols, rows = data
    if fmt == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8"), "application/json", "json"
    if fmt == "xlsx":
        return _to_xlsx_single(entity, cols, rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    # csv
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols)
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode("utf-8"), "text/csv", "csv"


def _to_xlsx_single(sheet_name: str, cols: list, rows: list) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    ws.append(cols)
    for r in rows:
        ws.append([r.get(c, "") for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _to_xlsx_multi(data: list) -> bytes:
    import openpyxl

    wb = openpyxl.Workbook()
    first = True
    for e, cols, rows in data:
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = e[:31]
        ws.append(cols)
        for r in rows:
            ws.append([r.get(c, "") for c in cols])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
