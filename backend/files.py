"""文件解析模块（文件中心）。

支持上传后按扩展名分发解析为纯文本，供「文档拓词 / 内容 SEO 审计」复用：
  .pdf   -> pypdf
  .docx  -> python-docx（正文 + 表格）
  .txt/.md/.csv -> 直接读取
  .html/.htm -> BeautifulSoup 取正文（去 script/style）
  .xlsx  -> openpyxl 逐工作表读取
  .rtf   -> 正则去 RTF 标记
  .odt   -> odfpy 取段落

设计：第三方库在各自函数内惰性 import，缺包也不影响服务启动；
任一格式解析失败返回带原因的占位串，绝不抛异常让接口崩。
"""
import re
from pathlib import Path

from bs4 import BeautifulSoup

# 允许上传的扩展名（白名单，防任意文件落盘后被执行）
ALLOWED_EXT = {
    ".pdf", ".docx", ".txt", ".md", ".html", ".htm",
    ".csv", ".xlsx", ".rtf", ".odt",
}


def allowed_ext(ext: str) -> bool:
    return (ext or "").lower() in ALLOWED_EXT


def extract_text(path: str, ext: str) -> str:
    """解析文件为纯文本。失败返回 '[解析失败: ...]' 占位串。"""
    ext = (ext or "").lower()
    try:
        if ext in (".txt", ".md", ".csv"):
            return Path(path).read_text(encoding="utf-8", errors="ignore")
        if ext in (".html", ".htm"):
            return _html(path)
        if ext == ".pdf":
            return _pdf(path)
        if ext == ".docx":
            return _docx(path)
        if ext == ".xlsx":
            return _xlsx(path)
        if ext == ".rtf":
            return _rtf(path)
        if ext == ".odt":
            return _odt(path)
    except Exception as e:  # 兜底：解析失败不让接口崩
        return f"[解析失败: {e}]"
    return ""


def _html(path: str) -> str:
    html = Path(path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return soup.get_text("\n", strip=True)


def _pdf(path: str) -> str:
    from pypdf import PdfReader

    reader = PdfReader(path)
    pages = [(p.extract_text() or "") for p in reader.pages]
    return "\n".join(pages).strip()


def _docx(path: str) -> str:
    import docx

    doc = docx.Document(path)
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))
    return "\n".join(parts).strip()


def _xlsx(path: str) -> str:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for ws in wb.worksheets:
        out.append(f"# Sheet: {ws.title}")
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c) for c in row]
            if any(cells):
                out.append(" | ".join(cells))
    return "\n".join(out).strip()


def _rtf(path: str) -> str:
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"\\[A-Za-z]+\d* ?", " ", text)   # 去控制字 \xxx(数字)(空格)
    text = re.sub(r"\\[^A-Za-z]", " ", text)        # 去控制符 \{ \} \\ \*
    text = re.sub(r"[{}]", " ", text)               # 去花括号组标记
    return re.sub(r"\s+", " ", text).strip()


def _odt(path: str) -> str:
    from odf.opendocument import load
    from odf.text import P

    doc = load(path)
    parts = []
    for elem in doc.getElementsByType(P):
        if elem.firstChild:
            parts.append(str(elem.firstChild.data))
    return "\n".join(p for p in parts if p.strip()).strip()
