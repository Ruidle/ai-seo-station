"""提示词工程（IMA skills/L2）：角色 + 任务 + 约束 + 钉死 JSON schema。

所有 AI 输出都是生产系统要解析的 -> 必须结构化（schema 写死，无多余文字）。
系统提示控制在 500 词内，含明确反模式（不编造、不输出解释）。

本文件已按「虎翼系外贸独立站 / 跨境电商 / 采购代理」赛道校准：
- INDUSTRY_SEED 行业词根（来自 tigerwing.net / tigeraid.cn / kj128.cn / sourcingagent.cn 真实抓取）
- LANG_NAMES 目标语言（外贸站刚需，虎翼主打 26 语站群 + Yandex 俄语市场）
- PAGE_TYPES 分页面类型审计
"""
from pydantic import BaseModel, Field


# ---------------- 行业化 / 多语言 / 页面类型 配置（基于虎翼系站点调研校准） ----------------
# 目标赛道：外贸独立站 / 跨境电商 / 采购代理（ODM/OEM / Private Label）
INDUSTRY_SEED = {
    "business": ["外贸独立站", "跨境独立站", "品牌出海", "小语种站群", "多语言建站",
                 "采购代理", "sourcing agent", "ODM", "OEM", "Private Label", "代工", "一站式的跨境服务"],
    "platform": ["Google SEO", "Yandex", "Shopify", "Amazon FBA", "速卖通", "阿里国际站",
                 "TikTok Shop", "Ozon", "WordPress", "独立站", "站群", "AMP 建站", "海外推广"],
    "attr": ["wholesale", "supplier", "manufacturer", "factory", "custom", "bulk", "MOQ",
             "price", "quote", "best", "top", "2026", "China", "OEM", "ODM", "dropshipping",
             "logistics", "payment", "warehouse"],
    "longtail": ["how to source", "where to buy", "best manufacturer in China", "vs",
                 "sourcing guide", "top 10 manufacturers", "private label", "OEM factory"],
}

# 目标语言（外贸站刚需；虎翼系主打 26 语站群 + Yandex 俄语市场）
LANG_NAMES = {
    "zh": "中文", "en": "English", "ru": "俄语(Русский)", "es": "西班牙语(Español)",
    "ar": "阿拉伯语(العربية)", "de": "德语(Deutsch)", "fr": "法语(Français)",
    "ja": "日语(日本語)", "ko": "韩语(한국어)", "pt": "葡萄牙语(Português)",
    "vi": "越南语(Tiếng Việt)", "th": "泰语(ไทย)", "tr": "土耳其语(Türkçe)",
    "it": "意大利语(Italiano)", "nl": "荷兰语(Nederlands)",
}

# 页面类型（分类型审计，不同类型 SEO 标准不同）
PAGE_TYPES = {
    "homepage": "首页（品牌词 + 导航 + 核心卖点）",
    "product": "产品页（属性词覆盖 + 结构化数据 + 图片 alt + CTA）",
    "category": "分类页（类目词覆盖 + 内链 + 分页）",
    "blog": "博客/文章页（长尾词 + 可读性 + 内链 + E-E-A-T）",
    "landing": "落地页/专题页（转化元素 + 表单 + 信任信号）",
}


# ---------------- 1. 关键词挖掘拓展 ----------------
class KeywordExpand(BaseModel):
    keywords: list[str] = Field(description="拓展出的关键词列表，10-25 个，去重，用英文/目标语言书写")


SYSTEM_KEYWORDS = """你是资深 B2B 外贸独立站 / 跨境电商 / 采购代理 SEO 专家，擅长关键词挖掘。
目标：基于用户给的种子词，拓展出高转化潜力的 SEO 关键词。
任务：
- 覆盖 4 类：核心词、长尾词、购买意图词（buy/wholesale/price/supplier/manufacturer/OEM/ODM）、疑问词（how/what/why）。
- 站在海外采购商搜索视角，符合真实搜索习惯（可参考调用方提供的行业词根）。
- 关键词用调用方指定的「输出语言」书写（英文站用 English，俄语站用 Русский，中文站用中文）。
约束：
- 只返回与种子词强相关、可落地的关键词。
- 不编造数据、不重复。
输出格式：JSON，字段 keywords(list[str])。
"""


# ---------------- 2. 站内 TDK 生成 ----------------
class OnpageMeta(BaseModel):
    title: str = Field(description="建议的 title，50-60 字符，含主关键词")
    description: str = Field(description="建议的 meta description，120-160 字符，含关键词与卖点")
    suggestions: list[str] = Field(description="针对该页面的其它 SEO 优化建议，3-5 条")


SYSTEM_ONPAGE = """你是外贸独立站 On-Page SEO 优化专家，专注跨境/采购代理赛道。
目标：为给定页面的主题生成最优 title 与 meta description，并给出整改建议。
任务：
- title 控制在 50-60 字符，前置主关键词，体现差异化卖点（工厂直供/定制/MOQ/多语言）。
- meta description 120-160 字符，含关键词 + 行动号召，不堆砌。
- 输出语言严格使用调用方指定的「目标语言」。
- 按调用方指定的「页面类型」调整侧重点：
  · 产品页：突出属性词、型号、OEM/ODM、价格/MOQ；
  · 分类页：覆盖类目词、引导内链；
  · 博客页：突出长尾词、实用价值；
  · 落地页：突出转化与信任；
  · 首页：突出品牌词与核心定位。
- suggestions 给出可执行的页面级优化建议（结构化数据、内链、图片 alt、信任信号等）。
约束：
- 不编造事实、不堆砌关键词。
- 基于用户提供的页面主题/现有标签，不凭空夸大。
输出格式：JSON，字段 title(str) / description(str) / suggestions(list[str])。
"""


# ---------------- 3. 外链博客素材生成 ----------------
class BacklinkArticle(BaseModel):
    title: str = Field(description="博客标题，含目标锚文本关键词")
    outline: list[str] = Field(description="文章大纲，4-6 个要点")
    content: str = Field(description="可直接发布的博客正文，300-500 词，自然植入锚文本")


SYSTEM_BACKLINK = """你是外链建设内容写手，擅长为外贸独立站产出可发布的客座博客。
目标：围绕主题生成一篇自然植入锚文本的外链博客素材。
任务：
- title 含目标关键词，吸引点击。
- outline 4-6 个逻辑要点。
- content 300-500 词，专业、可读，锚文本（目标 URL）自然出现 1-2 次，不硬广。
约束：
- 不抄袭、不堆砌链接、不编造公司数据。
- 内容对读者有真实价值。
输出格式：JSON，字段 title(str) / outline(list[str]) / content(str)。
"""


# ---------------- 4. 文档关键词提取（上传文件后） ----------------
class DocKeywords(BaseModel):
    keywords: list[str] = Field(description="从文档中提取的 SEO 关键词，10-20 个，去重，按相关性排序")


SYSTEM_DOC_KEYWORDS = """你是外贸独立站 SEO 关键词分析师。
目标：从用户上传的文档正文中，提取可用于 SEO 部署的高价值关键词。
任务：
- 识别文档主题相关的核心词、长尾词、采购意图词（buy/wholesale/supplier/price/OEM/ODM）。
- 站在海外采购商搜索视角，符合真实搜索习惯（可参考调用方提供的行业词根）。
- 关键词用调用方指定的「输出语言」书写。
约束：
- 只输出文档中真实出现的概念，不编造无关词。
- 不重复、不输出整句。
输出格式：JSON，字段 keywords(list[str])。
"""


# ---------------- 5. 内容 SEO 审计（上传文件后） ----------------
class ContentAudit(BaseModel):
    seo_score: int = Field(description="综合 SEO 评分 0-100")
    keyword_density_note: str = Field(description="关键词密度点评（是否植入、是否堆砌）")
    readability_note: str = Field(description="可读性点评（句式、篇幅、受众）")
    structure_note: str = Field(description="结构点评（标题层级、段落、列表）")
    issues: list[str] = Field(description="发现的问题清单，按严重度排序，3-6 条")
    suggestions: list[str] = Field(description="可执行的整改建议，3-6 条")
    optimized_intro: str = Field(description="重写后的开头段落（150-250 词，自然植入目标关键词）")


SYSTEM_CONTENT_AUDIT = """你是外贸独立站内容 SEO 优化专家，专注跨境/采购代理赛道。
目标：对用户提供的正文内容做 SEO 审计，并给出整改方案。
任务：
- 围绕「目标关键词」评估关键词密度、可读性、结构三个维度，各给一句点评。
- 按调用方指定的「页面类型」调整审计重点（产品页重属性词+FAQ、博客页重长尾+E-E-A-T、落地页重转化）。
- 评估「跨境信任信号」是否充分：是否提及隐私政策/支付方式/多语言/公司实勘/客户案例或评价；不足则在 issues/suggestions 指出。
- seo_score 按 0-100 综合打分（未见关键词/无结构/篇幅过短/缺信任信号要扣分）。
- issues 列出真实问题（如未植入关键词、段落过长、缺少小标题、密度过高、缺信任信号）。
- suggestions 给可落地整改动作（如加 H2、补 FAQ、自然植入关键词、补充客户案例）。
- optimized_intro 重写一段更利于 SEO 的开头。
约束：
- 不编造数据、不夸大评分。
- 点评必须基于用户提供的内容，不凭空。
输出格式：JSON，字段 seo_score(int) / keyword_density_note(str) / readability_note(str) / structure_note(str) / issues(list[str]) / suggestions(list[str]) / optimized_intro(str)。
"""
