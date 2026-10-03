"""AI-SEO 独立站优化助手 · Flask 主应用。

- 路由：GET / 服务前端；/api/health 健康检查；4 大模块 JSON 接口。
- 包方式导出 app 对象，供一键脚本 waitress-serve --listen=127.0.0.1:8011 backend.app:app 使用。
- 密钥：优先读 Windows 用户级 DEEPSEEK_API_KEY；本地 .env 仅作补充（不进仓库）。
"""
import csv
import io
import json
import os
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "index.html"
UPLOAD_DIR = ROOT / "uploads"


def _load_dotenv():
    """极简 .env 加载（不引第三方库）。已存在的环境变量不覆盖。"""
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


_load_dotenv()

from . import db, report, seo, files, dataio  # noqa: E402

db.init_db()

app = Flask(__name__, static_folder=str(ROOT / "frontend"))
CORS(app)


@app.route("/")
def index():
    return send_file(str(FRONTEND))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "ts": os.urandom(4).hex()})


@app.route("/api/keywords/expand", methods=["POST"])
def api_keywords_expand():
    data = request.get_json(silent=True) or {}
    seed = (data.get("seed") or "").strip()
    lang = (data.get("lang") or "en").strip()
    industry = data.get("industry", True)
    if not seed:
        return jsonify({"error": "请提供种子关键词 seed"}), 400
    # 落库 + 返回
    res = seo.expand_keywords(seed, lang, industry)
    try:
        conn = db.get_conn()
        for kw in res["keywords"]:
            conn.execute(
                "INSERT INTO keywords(seed,kw,source) VALUES(?,?,?)",
                (seed, kw, res["source"]),
            )
        conn.commit()
        conn.close()
    except Exception:
        pass
    return jsonify(res)


@app.route("/api/competitor/parse", methods=["POST"])
def api_competitor_parse():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "请提供竞品 URL"}), 400
    return jsonify(seo.parse_competitor(url))


@app.route("/api/onpage/audit", methods=["POST"])
def api_onpage_audit():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    html = (data.get("html") or "").strip()
    target_lang = (data.get("target_lang") or "en").strip()
    page_type = (data.get("page_type") or "homepage").strip()
    if not url and not html:
        return jsonify({"error": "请提供 url 或 html"}), 400
    return jsonify(seo.audit_onpage(url=url, html=html, target_lang=target_lang, page_type=page_type))


@app.route("/api/backlinks", methods=["GET", "POST"])
def api_backlinks():
    if request.method == "GET":
        conn = db.get_conn()
        rows = conn.execute("SELECT * FROM backlinks ORDER BY id DESC").fetchall()
        conn.close()
        return jsonify([dict(r) for r in rows])
    data = request.get_json(silent=True) or {}
    conn = db.get_conn()
    rid = db.insert_returning_id(
        conn,
        "INSERT INTO backlinks(site,url,anchor,type,status,note) VALUES(?,?,?,?,?,?)",
        (
            data.get("site", ""),
            data.get("url", ""),
            data.get("anchor", ""),
            data.get("type", "guest-post"),
            data.get("status", "planned"),
            data.get("note", ""),
        ),
    )
    conn.close()
    return jsonify({"id": rid, "ok": True}), 201


@app.route("/api/backlinks/<int:bid>", methods=["DELETE"])
def api_backlink_delete(bid):
    conn = db.get_conn()
    conn.execute("DELETE FROM backlinks WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


@app.route("/api/backlinks/generate", methods=["POST"])
def api_backlinks_generate():
    data = request.get_json(silent=True) or {}
    topic = (data.get("topic") or "").strip()
    anchor = (data.get("anchor") or topic).strip()
    target_url = (data.get("target_url") or "").strip()
    if not topic:
        return jsonify({"error": "请提供 topic"}), 400
    return jsonify(seo.generate_backlink_article(topic, anchor, target_url))


@app.route("/api/metrics", methods=["GET", "POST"])
def api_metrics():
    if request.method == "GET":
        site = (request.args.get("site") or "").strip()
        return jsonify(report.list_metrics(site))
    data = request.get_json(silent=True) or {}
    try:
        rid = report.add_metric(
            site=(data.get("site") or "").strip(),
            date=(data.get("date") or "").strip(),
            indexed=int(data.get("indexed") or 0),
            avg_ranking=float(data.get("avg_ranking") or 0),
            traffic=int(data.get("traffic") or 0),
            kw_count=int(data.get("kw_count") or 0),
        )
        return jsonify({"id": rid, "ok": True}), 201
    except Exception as e:
        return jsonify({"error": f"参数错误：{e}"}), 400


@app.route("/api/report/generate", methods=["POST"])
def api_report_generate():
    data = request.get_json(silent=True) or {}
    site = (data.get("site") or "").strip()
    return jsonify(report.generate_report(site))


# ================= ⑥ 文件中心 =================
@app.route("/api/files", methods=["GET"])
def api_files_list():
    conn = db.get_conn()
    rows = conn.execute(
        "SELECT id,filename,ext,size,length(text) AS chars,created_at FROM uploads ORDER BY id DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/files/upload", methods=["POST"])
def api_files_upload():
    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"error": "未收到文件"}), 400
    fn = secure_filename(f.filename)
    ext = Path(fn).suffix.lower()
    if not files.allowed_ext(ext):
        return jsonify({"error": f"不支持的格式：{ext}（支持 PDF/DOCX/TXT/MD/HTML/CSV/XLSX/RTF/ODT）"}), 400
    UPLOAD_DIR.mkdir(exist_ok=True)
    save_path = UPLOAD_DIR / fn
    f.save(str(save_path))
    text = files.extract_text(str(save_path), ext)
    if text.startswith("[解析失败"):
        return jsonify({"error": text, "filename": fn}), 422
    conn = db.get_conn()
    rid = db.insert_returning_id(
        conn,
        "INSERT INTO uploads(filename,ext,size,text) VALUES(?,?,?,?)",
        (fn, ext, os.path.getsize(save_path), text[:50000]),
    )
    conn.close()
    return jsonify({
        "id": rid, "filename": fn, "ext": ext,
        "char_count": len(text), "preview": text[:1000], "source": "parsed",
    })


@app.route("/api/files/<int:fid>", methods=["DELETE"])
def api_files_delete(fid):
    conn = db.get_conn()
    row = conn.execute("SELECT filename FROM uploads WHERE id=?", (fid,)).fetchone()
    if row:
        conn.execute("DELETE FROM uploads WHERE id=?", (fid,))
        conn.commit()
        try:
            (UPLOAD_DIR / row["filename"]).unlink(missing_ok=True)
        except Exception:
            pass
    conn.close()
    return jsonify({"ok": True})


def _load_upload_text(fid: int = None, text: str = "") -> str:
    """优先用上传文件 id 取正文，否则用直接传入的 text。"""
    if fid:
        conn = db.get_conn()
        row = conn.execute("SELECT text FROM uploads WHERE id=?", (fid,)).fetchone()
        conn.close()
        if row:
            return row["text"] or ""
    return text or ""


@app.route("/api/files/keywords", methods=["POST"])
def api_files_keywords():
    data = request.get_json(silent=True) or {}
    text = _load_upload_text(data.get("id"), data.get("text"))
    lang = (data.get("lang") or "en").strip()
    industry = data.get("industry", True)
    if not text.strip():
        return jsonify({"error": "请提供文件 id 或 text"}), 400
    return jsonify(seo.extract_doc_keywords(text, lang, industry))


@app.route("/api/files/audit", methods=["POST"])
def api_files_audit():
    data = request.get_json(silent=True) or {}
    text = _load_upload_text(data.get("id"), data.get("text"))
    keyword = (data.get("keyword") or "").strip()
    lang = (data.get("lang") or "en").strip()
    page_type = (data.get("page_type") or "blog").strip()
    if not text.strip():
        return jsonify({"error": "请提供文件 id 或 text"}), 400
    return jsonify(seo.analyze_content(text, keyword, lang, page_type))


# ================= 一键导入 / 导出 =================
@app.route("/api/import/template")
def api_import_template():
    entity = (request.args.get("entity") or "keywords").strip()
    fmt = (request.args.get("fmt") or "csv").strip().lower()
    spec = dataio.TEMPLATES.get(entity)
    if not spec:
        return jsonify({"error": f"未知实体：{entity}"}), 400
    if fmt == "json":
        obj = [dict(zip(spec[0], row)) for row in spec[1:]]
        body = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
        mt = "application/json"
    else:
        buf = io.StringIO()
        csv.writer(buf).writerows(spec)
        body = buf.getvalue().encode("utf-8")
        mt = "text/csv"
    return send_file(
        io.BytesIO(body), mimetype=mt,
        as_attachment=True, download_name=f"import_template_{entity}.{fmt}",
    )


@app.route("/api/import", methods=["POST"])
def api_import():
    f = request.files.get("file")
    entity = (request.form.get("entity") or "keywords").strip()
    if not f or not f.filename:
        return jsonify({"error": "未收到文件"}), 400
    if entity not in dataio.IMPORT_SPECS:
        return jsonify({"error": f"未知导入实体：{entity}"}), 400
    ext = Path(secure_filename(f.filename)).suffix.lower()
    if ext not in (".csv", ".json", ".xlsx"):
        return jsonify({"error": f"仅支持 CSV/JSON/XLSX，收到：{ext}"}), 400
    UPLOAD_DIR.mkdir(exist_ok=True)
    tmp = UPLOAD_DIR / f"import_{int(os.urandom(3).hex(),16)}{ext}"
    f.save(str(tmp))
    try:
        rows = dataio.parse_import_file(str(tmp), ext)
        n = dataio.do_import(rows, entity)
    except Exception as e:
        return jsonify({"error": f"导入失败：{e}"}), 400
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
    return jsonify({"imported": n, "entity": entity, "total_rows": len(rows)})


@app.route("/api/export")
def api_export():
    entity = (request.args.get("entity") or "all").strip()
    fmt = (request.args.get("fmt") or "csv").strip().lower()
    if fmt not in ("csv", "json", "xlsx"):
        return jsonify({"error": "fmt 仅支持 csv/json/xlsx"}), 400
    if entity != "all" and entity not in dataio.EXPORT_SPECS:
        return jsonify({"error": f"未知导出实体：{entity}"}), 400
    try:
        body, mt, fext = dataio.build_export(entity, fmt)
    except Exception as e:
        return jsonify({"error": f"导出失败：{e}"}), 400
    name = "ai-seo-export" if entity == "all" else f"ai-seo-{entity}"
    return send_file(
        io.BytesIO(body), mimetype=mt,
        as_attachment=True, download_name=f"{name}.{fext}",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8011, debug=False)
