"""SEO 核心逻辑：关键词挖掘、竞品解析、站内审计、外链素材。

- AI 路径走 LangChain×DeepSeek 结构化输出（见 llm.py / prompts.py）。
- 无 key 时每处都有规则兜底，保证演示模式免 key 直接跑（基准要求）。
"""
import re
from collections import Counter
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from . import llm, prompts

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}

_STOPWORDS = set(
    "the a an and or of to in for on with is are be as at by from this that these those "
    "we you your our their it its can will may our we're we have has have not but if then so "
    "our products product us more about what which who when where how why all any each our company "
    "us china factory price quality service best good top new use used using one two three".split()
)


# ---------------- 1. 关键词挖掘拓展 ----------------
_MODIFIERS = [
    "wholesale", "supplier", "manufacturer", "factory", "price", "buy", "for sale",
    "custom", "OEM", "ODM", "bulk", "discount", "near me", "cost", "quote", "best",
]


def expand_keywords(seed: str, lang: str = "en", industry: bool = True) -> dict:
    seed = (seed or "").strip()
    if not seed:
        return {"keywords": [], "source": "none"}
    lang_name = prompts.LANG_NAMES.get(lang, lang)
    industry_block = ""
    if industry:
        industry_block = (
            "行业词根参考（外贸独立站/跨境/采购代理赛道）：\n"
            f"业务：{', '.join(prompts.INDUSTRY_SEED['business'])}\n"
            f"平台：{', '.join(prompts.INDUSTRY_SEED['platform'])}\n"
            f"属性：{', '.join(prompts.INDUSTRY_SEED['attr'])}\n"
        )
    # 真实模式
    if llm.has_key():
        human = (
            f"种子词：{seed}\n"
            f"输出语言：{lang_name}\n"
            f"{industry_block}"
            "请拓展 SEO 关键词（覆盖核心词/长尾词/购买意图词/疑问词）。"
        )
        out = llm.structured(
            [("system", prompts.SYSTEM_KEYWORDS), ("human", human)],
            prompts.KeywordExpand,
        )
        if out and out.keywords:
            kws = list(dict.fromkeys([k.strip() for k in out.keywords if k.strip()]))
            return {"keywords": kws, "source": "deepseek", "lang": lang}
    # 规则兜底（演示模式，保持英文）
    base = seed.lower()
    kws = {base}
    for m in _MODIFIERS:
        kws.add(f"{m} {base}")
        kws.add(f"{base} {m}")
    kws.add(f"{base} vs")
    kws.add(f"how to choose {base}")
    kws.add(f"{base} reviews")
    return {"keywords": list(kws)[:25], "source": "rule", "lang": lang}


# ---------------- 2. 竞品网站解析 ----------------
def _word_freq(text: str, top: int = 20) -> list:
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
    words = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    return [w for w, _ in Counter(words).most_common(top)]


def parse_competitor(url: str) -> dict:
    url = (url or "").strip()
    if not url:
        return {"error": "url 为空"}
    if not url.startswith("http"):
        url = "https://" + url
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        return {"error": f"抓取失败：{e}"}

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_desc = ""
    meta_kw = ""
    canonical = ""
    for m in soup.find_all("meta"):
        name = (m.get("name") or "").lower()
        if name == "description":
            meta_desc = m.get("content", "")
        elif name == "keywords":
            meta_kw = m.get("content", "")
        elif (m.get("rel") or "").lower() == "canonical":
            canonical = m.get("href", "")
    h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:10]
    text = soup.get_text(" ", strip=True)
    top_words = _word_freq(text, 20)
    result = {
        "url": url,
        "title": title,
        "description": meta_desc,
        "keywords": meta_kw,
        "canonical": canonical,
        "h1": h1s,
        "top_words": top_words,
    }
    # 落库
    try:
        from . import db

        conn = db.get_conn()
        db.insert_returning_id(
            conn,
            "INSERT INTO competitors(url,title,description,keywords,top_words) VALUES(?,?,?,?,?)",
            (url, title, meta_desc, meta_kw, ",".join(top_words)),
        )
        conn.close()
    except Exception:
        pass
    return result


# ---------------- 3. 站内页面审计 ----------------
def _audit_defects(soup: BeautifulSoup, title: str, desc: str, page_type: str = "homepage") -> list:
    defects = []
    if not title:
        defects.append("缺失 <title> 标签")
    elif len(title) > 60:
        defects.append(f"<title> 过长（{len(title)} 字符，建议 ≤60）")
    elif len(title) < 20:
        defects.append(f"<title> 过短（{len(title)} 字符，建议 ≥20）")

    if not desc:
        defects.append("缺失 meta description")
    elif len(desc) > 160:
        defects.append(f"meta description 过长（{len(desc)} 字符，建议 ≤160）")
    elif len(desc) < 70:
        defects.append(f"meta description 过短（{len(desc)} 字符，建议 ≥70）")

    h1 = soup.find_all("h1")
    if not h1:
        defects.append("缺失 <h1> 标签")
    elif len(h1) > 1:
        defects.append(f"存在多个 <h1>（{len(h1)} 个，应仅 1 个）")

    imgs = soup.find_all("img")
    no_alt = [i for i in imgs if not i.get("alt")]
    if imgs and len(no_alt) == len(imgs):
        defects.append("所有 <img> 均缺失 alt 属性")
    elif no_alt:
        defects.append(f"{len(no_alt)} 张图片缺失 alt 属性")

    if not soup.find("link", attrs={"rel": "canonical"}):
        defects.append("缺失 canonical 标签")
    if not soup.find("meta", attrs={"name": "viewport"}):
        defects.append("缺失 viewport meta（移动端不友好）")
    if not (soup.find("html") and soup.find("html").get("lang")):
        defects.append("缺失 <html lang> 属性")

    # 页面类型专属检测
    if page_type == "product":
        has_product = False
        for s in soup.find_all("script", attrs={"type": "application/ld+json"}):
            if "Product" in (s.string or ""):
                has_product = True
                break
        if not has_product:
            defects.append("产品页建议添加 Product 结构化数据（price/availability）")
        btns = [b.get_text(strip=True).lower() for b in soup.find_all("button")]
        forms = soup.find_all("form")
        if not forms and not any(k in " ".join(btns) for k in ("add to cart", "buy", "inquiry", "询盘", "get quote")):
            defects.append("产品页缺少明确 CTA（加购/询盘按钮）")
    elif page_type == "category":
        links = soup.find_all("a", href=True)
        internal = [a for a in links if a["href"].startswith(("/", "?")) or "http" not in a["href"]]
        if len(internal) < 5:
            defects.append(f"分类页内链偏少（{len(internal)} 条），建议增加相关产品/类目内链")
    elif page_type == "blog":
        if not soup.find("article") and not soup.find("time"):
            defects.append("博客页建议使用 <article>/<time> 语义标签（提升 E-E-A-T）")
    elif page_type == "landing":
        if not soup.find_all("form"):
            defects.append("落地页缺少转化表单（建议加询盘/订阅表单）")
    return defects


def detect_trust_signals(html: str) -> dict:
    """跨境信任信号检测：外贸站转化关键项。返回命中/缺失项与评分(0-100)。"""
    text = (html or "").lower()
    signals = {
        "隐私政策": ["privacy", "隐私政策", "privacypolicy"],
        "关于我们/公司实勘": ["about", "关于我们", "aboutus", "company profile", "实勘"],
        "联系方式": ["contact", "联系我们", "email", "@", "phone", "tel:"],
        "支付方式展示": ["paypal", "alipay", "支付宝", "payment", "escrow", "western union", "tt "],
        "多语言切换": ["hreflang", "/en/", "/ru/", "/es/", "language", "语言切换", "translator"],
        "认证/证书": ["certification", "iso", "认证", "verified", "ce ", "rohs", "fda"],
        "客户案例/评价": ["testimonial", "review", "案例", "客户评价", "case study", "feedback"],
        "社媒矩阵": ["facebook", "twitter", "linkedin", "instagram", "youtube", "tiktok"],
        "版权/备案": ["copyright", "版权", "备案", "icp"],
    }
    present, missing = [], []
    for name, kws in signals.items():
        if any(k in text for k in kws):
            present.append(name)
        else:
            missing.append(name)
    score = round(len(present) / len(signals) * 100)
    return {"present": present, "missing": missing, "score": score}


def audit_onpage(url: str = "", html: str = "", target_lang: str = "en", page_type: str = "homepage") -> dict:
    if url and not html:
        if not url.startswith("http"):
            url = "https://" + url
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            return {"error": f"抓取失败：{e}"}
    if not html:
        return {"error": "url 与 html 至少提供一个"}

    soup = BeautifulSoup(html, "lxml")
    title = soup.title.get_text(strip=True) if soup.title else ""
    desc = ""
    for m in soup.find_all("meta"):
        if (m.get("name") or "").lower() == "description":
            desc = m.get("content", "")
            break
    defects = _audit_defects(soup, title, desc, page_type)
    trust = detect_trust_signals(html)

    # 生成建议 TDK（按语言 + 页面类型）
    topic = title or (url or "该页面")
    suggested_title, suggested_description, suggestions = _gen_meta(topic, desc, defects, target_lang, page_type)

    # 综合评分：缺陷 + 信任信号缺失
    penalty = len(defects) * 8 + len(trust["missing"]) * 3
    seo_score = max(0, min(100, 100 - penalty))

    try:
        from . import db

        conn = db.get_conn()
        db.insert_returning_id(
            conn,
            "INSERT INTO pages(url,suggested_title,suggested_description,defects) VALUES(?,?,?,?)",
            (url or "", suggested_title, suggested_description, "\n".join(defects)),
        )
        conn.close()
    except Exception:
        pass

    return {
        "url": url,
        "title": title,
        "description": desc,
        "page_type": page_type,
        "target_lang": target_lang,
        "defects": defects,
        "trust_signals": trust,
        "seo_score": seo_score,
        "suggested_title": suggested_title,
        "suggested_description": suggested_description,
        "suggestions": suggestions,
    }


def _gen_meta(topic: str, desc: str, defects: list, target_lang: str = "en", page_type: str = "homepage") -> tuple:
    lang_name = prompts.LANG_NAMES.get(target_lang, target_lang)
    ptype = prompts.PAGE_TYPES.get(page_type, page_type)
    if llm.has_key():
        human = (
            f"页面主题：{topic}\n"
            f"页面类型：{ptype}\n"
            f"目标语言：{lang_name}\n"
            f"现有 description：{desc}\n"
            f"检测到的缺陷：{'; '.join(defects) or '无'}"
        )
        out = llm.structured(
            [("system", prompts.SYSTEM_ONPAGE), ("human", human)],
            prompts.OnpageMeta,
        )
        if out:
            return out.title, out.description, out.suggestions
    # 规则兜底
    t = (topic[:50]).strip()
    if target_lang == "zh":
        suggested_title = f"{t} | 厂家直供 OEM/ODM 定制"
        suggested_description = (f"专业{t}生产厂家与供应商，工厂直供价格，低 MOQ，"
                                  f"支持 OEM/ODM 定制，欢迎在线询价。")[:150]
        suggestions = [
            "为图片补充含关键词的 alt 属性",
            "添加 Product/Organization 结构化数据",
            "在正文前 100 词自然植入主关键词",
            "建设 2-3 条站内相关内链",
            "补充客户案例与支付方式等跨境信任信号",
        ]
        return suggested_title, suggested_description, suggestions
    suggested_title = f"{t} | Factory Direct Supply & OEM"
    suggested_description = (
        f"Professional {t} manufacturer & supplier. Factory direct price, low MOQ, "
        f"custom OEM/ODM service. Get quote today."[:150]
    )
    suggestions = [
        "为图片补充 alt 属性，含目标关键词",
        "添加结构化数据（Product/Organization Schema）",
        "在正文前 100 词自然植入主关键词",
        "建设 2-3 条站内相关内链",
        "补充客户案例与支付方式等跨境信任信号",
    ]
    return suggested_title, suggested_description, suggestions


# ---------------- 4. 外链博客素材 ----------------
def generate_backlink_article(topic: str, anchor: str, target_url: str = "") -> dict:
    topic = (topic or "").strip()
    if not topic:
        return {"error": "topic 为空"}
    if llm.has_key():
        human = f"主题：{topic}\n锚文本：{anchor}\n目标 URL：{target_url or '（由用户填充）'}"
        out = llm.structured(
            [("system", prompts.SYSTEM_BACKLINK), ("human", human)],
            prompts.BacklinkArticle,
        )
        if out:
            return {
                "title": out.title,
                "outline": out.outline,
                "content": out.content,
                "source": "deepseek",
            }
    # 规则兜底
    title = f"How to Choose the Right {topic}: A Practical Guide"
    outline = [
        f"Why {topic} matters for your business",
        f"Key factors to evaluate when sourcing {topic}",
        f"Common mistakes to avoid",
        f"How to work with a reliable {topic} supplier",
        "Final checklist before ordering",
    ]
    content = (
        f"Choosing the right {topic} can directly impact your cost and quality. "
        f"Start by defining your specs and MOQ, then compare 2-3 verified factories. "
        f"When evaluating a {topic} supplier, check certifications, lead time, and after-sales policy. "
        f"A reliable partner helps you avoid delays and defects. "
        f"Learn more from our {anchor} guide before placing bulk orders."
    )
    return {"title": title, "outline": outline, "content": content, "source": "rule"}


# ---------------- 5. 文档关键词提取（上传文件后） ----------------
def extract_doc_keywords(text: str, lang: str = "en", industry: bool = True) -> dict:
    text = (text or "").strip()
    if not text:
        return {"keywords": [], "source": "none"}
    snippet = text[:4000]
    lang_name = prompts.LANG_NAMES.get(lang, lang)
    industry_block = ""
    if industry:
        industry_block = (
            "行业词根参考（外贸独立站/跨境/采购代理赛道）：\n"
            f"业务：{', '.join(prompts.INDUSTRY_SEED['business'])}\n"
            f"平台：{', '.join(prompts.INDUSTRY_SEED['platform'])}\n"
        )
    if llm.has_key():
        human = (
            f"输出语言：{lang_name}\n"
            f"{industry_block}"
            f"文档内容：\n{snippet}"
        )
        out = llm.structured(
            [("system", prompts.SYSTEM_DOC_KEYWORDS), ("human", human)],
            prompts.DocKeywords,
        )
        if out and out.keywords:
            kws = list(dict.fromkeys([k.strip() for k in out.keywords if k.strip()]))
            return {"keywords": kws, "source": "deepseek", "lang": lang}
    # 规则兜底：词频
    words = re.findall(r"[a-zA-Z][a-zA-Z\-]{2,}", text.lower())
    top = [w for w, _ in Counter(words).most_common(20) if w not in _STOPWORDS]
    return {"keywords": top, "source": "rule", "lang": lang}


# ---------------- 6. 内容 SEO 审计（上传文件后） ----------------
def analyze_content(text: str, keyword: str = "", lang: str = "en", page_type: str = "blog") -> dict:
    text = (text or "").strip()
    keyword = (keyword or "").strip()
    if not text:
        return {"error": "内容为空"}
    snippet = text[:4000]
    if llm.has_key():
        human = (
            f"目标关键词：{keyword or '（未指定，请自行判断文档主题词）'}\n"
            f"语言：{lang}\n"
            f"页面类型：{prompts.PAGE_TYPES.get(page_type, page_type)}\n"
            f"内容：\n{snippet}"
        )
        out = llm.structured(
            [("system", prompts.SYSTEM_CONTENT_AUDIT), ("human", human)],
            prompts.ContentAudit,
        )
        if out:
            return {
                "seo_score": max(0, min(100, int(out.seo_score))),
                "keyword_density_note": out.keyword_density_note,
                "readability_note": out.readability_note,
                "structure_note": out.structure_note,
                "issues": out.issues,
                "suggestions": out.suggestions,
                "optimized_intro": out.optimized_intro,
                "source": "deepseek",
            }
    # 规则兜底：基础指标
    words = re.findall(r"[a-zA-Z'][a-zA-Z'\-]*", text.lower())
    wc = len(words)
    kw = keyword.lower()
    kwc = text.lower().count(kw) if kw else 0
    density = round(kwc / max(1, wc) * 100, 2)
    issues = []
    if wc < 300:
        issues.append(f"正文偏短（{wc} 词，建议 ≥300 利于排名）")
    if kw:
        if kwc == 0:
            issues.append(f"全文未出现目标关键词「{keyword}」，需在开头与正文自然植入")
        elif density > 3:
            issues.append(f"关键词密度偏高（{density}%），有堆砌风险，建议 1%-2%")
        elif density < 0.3:
            issues.append(f"关键词密度偏低（{density}%），可适当增加自然出现")
    else:
        issues.append("未指定目标关键词，无法评估关键词布局")
    if text.count("\n#") == 0 and text.lower().count("##") == 0 and "<h" not in text.lower():
        issues.append("缺少清晰的小标题层级（H2/H3），不利阅读与抓取")
    score = max(0, min(100, 100 - len(issues) * 15))
    suggestions = [
        "在首段前 100 词自然植入主关键词",
        "用 H2/H3 拆分长文，提升可读性",
        "补充 FAQ 段落覆盖长尾疑问词",
        "为正文图片补充含关键词的 alt 文本",
    ]
    optimized_intro = (
        f"{keyword + ' ' if keyword else ''}是外贸独立站获取自然流量的核心载体。"
        f"本文从采购商真实搜索意图出发，系统梳理选型要点与供应商评估维度，"
        f"帮助读者快速建立判断框架并降低采购风险。"
    )
    return {
        "seo_score": score,
        "keyword_density_note": f"目标词出现 {kwc} 次，密度约 {density}%",
        "readability_note": f"全文约 {wc} 词",
        "structure_note": "未检测到结构化小标题" if (text.count("\n#") == 0) else "已检测到小标题结构",
        "issues": issues,
        "suggestions": suggestions,
        "optimized_intro": optimized_intro,
        "source": "rule",
    }
