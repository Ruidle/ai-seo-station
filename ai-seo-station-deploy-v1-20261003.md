# 部署实例｜AI-SEO 独立站优化助手（虎翼系优化版 · 已开源）

> 部署基准：IMA《最高级的自动化部署》唯一基准（2026-08-16 真机跑通版）
> 项目类型：AI 应用 · 外贸独立站 SEO 运营助手（虎翼系赛道定制）
> 落地日期：2026-08-16　|　**开源日期：2026-10-03**
> 所在文件夹：Ruidle的知识库 / 实例项目（folder_7494751943132828）

## 〇、开源信息

| 项 | 信息 |
|---|---|
| **GitHub 仓库** | **https://github.com/Ruidle/ai-seo-station** |
| **许可证** | MIT License（允许商用 / 修改 / 分发，保留版权声明） |
| **主要语言** | Python（后端 Flask）+ 原生 JavaScript（前端 Tailwind） |
| **提交历史** | 3 次提交：初始版本 → README 与 MIT LICENSE → 截图改用 jsDelivr CDN 提升国内可访问性 |
| **创建时间** | 2026-10-03 |
| **源码分发包** | `ai-seo-station-source-v1-20261003.zip`（362 KB / 45 文件，166 MB → 362 KB） |

```bash
git clone https://github.com/Ruidle/ai-seo-station.git
```

> 已完整开源，欢迎 Fork、二次开发与商业使用；衍生时请保留原仓库出处与 LICENSE 声明。

## 一、这是什么

AI-SEO 独立站优化助手：面向外贸独立站 SEO 运营人员，覆盖站内 + 站外完整工作流。已针对虎翼系站点（tigerwing.net / tigeraid.cn / kj128.cn / sourcingagent.cn / 海链易）的真实业务场景做行业化校准。

| 模块 | 能力 |
|---|---|
| ① AI 关键词挖掘 | LangChain×DeepSeek 拓词（行业词库注入 + 多语言）+ 规则兜底 |
| ② 竞品解析 | BeautifulSoup 抓竞品页，抽 TDK + 高频词 |
| ③ 站内优化 | 多语言 + 分页面类型 TDK 生成 + 标签缺陷检测 + 整改建议 |
| ④ 外链台账 | SQLite 台账 CRUD + AI 生成博客外链素材 |
| ⑤ 指标&报告 | 录入收录/排名/流量 → 自动 SEO 报告（MD/CSV 导出） |
| ⑥ 文件中心 | 上传解析 9 种格式 + 内容 SEO 审计 + 一键导入/导出（CSV/JSON/XLSX） |

技术栈：Flask · BeautifulSoup · LangChain(DeepSeek) · SQLite(WAL) · waitress 部署

## 二、虎翼系赛道优化（本实例核心差异化）

基于对虎翼系 5 个公开站的真实 WebFetch 调研（业务定位 / 核心产品词 / 页面类型 / 多语言支持 / 目标市场），做了 4 项行业化校准：

| 优化项 | 落地 | 真机验证 |
|---|---|---|
| ① 行业化词库 | `prompts.py` 内置 INDUSTRY_SEED（独立站/跨境/小语种站群/Shopify/Amazon FBA/OEM/ODM/Private Label 等）注入拓词 | 俄语+行业化返回纯外贸词：`внешнеторговый независимый сайт`、`дропшиппинг из Китая в Россию` |
| ② 多语言 TDK | LANG_NAMES 15 语种（en/ru/es/ar/de/fr/ja/ko/pt…），关键词/站内/文档拓词均按 `target_lang` 输出 | 各语种真实输出对应语言 |
| ③ 分页面类型审计 | PAGE_TYPES（产品/分类/博客/落地）+ `_audit_defects` 按类型差异化 | 产品页专属缺陷："缺 Product 结构化数据"+"缺 CTA" 精准命中 |
| ④ 跨境信任信号 | `detect_trust_signals` 9 项（隐私政策/支付方式/多语言切换/公司认证/客户案例/社媒/联系方式…）纳入综合 seo_score | 命中"联系方式"、缺失 8 项，计入评分 |

## 三、文件中心模块（⑥）

- **上传解析**：PDF(pypdf) / DOCX(python-docx) / TXT·MD / HTML(BeautifulSoup 取正文) / CSV / XLSX(openpyxl) / RTF(正则去控制字) / ODT(odfpy)；非白名单（如 .exe）直接 400 拒绝
- **基于文档的 SEO 增值**：`/api/files/keywords`（从正文拓词）、`/api/files/audit`（关键词密度/可读性/结构评分 + 整改清单 + 重写开头）
- **一键导入 / 导出**：`/api/import`（CSV/JSON/XLSX 批量灌入关键词/外链/指标）、`/api/export?entity=...&fmt=csv|json|xlsx`；可下载导入模板

## 四、与基准的差异点（仅 1 处）

基准是 FastAPI+uvicorn；本项目是 Flask → 用 **waitress** 纯 Python WSGI 起服务：

```
# 基准
python -m uvicorn backend.app:app --port 8011
# 本项目（WSGI，跨平台免编译）
waitress-serve --listen=127.0.0.1:8011 backend.app:app
```

其余 8 条防闪退铁律（完整路径 powershell / 释放端口 / Wait-Process 保活 / Registered tunnel connection 信号 / 密钥不进仓库）**原样复用**。

## 五、真机跑通记录

- 双击 `start_seo.bat` → venv → 装依赖(清华源) → waitress(127.0.0.1:8011) → `/api/health` 200 → cloudflared → 公网链接活
- 本地：http://127.0.0.1:8011 ｜ 公网：https://xxx.trycloudflare.com（每次重启随机）
- AI 真实模式：Windows 用户级 `DEEPSEEK_API_KEY` 自动生效，真调 DeepSeek（非假数据）；无 key 时规则兜底
- 虎翼系优化验证：俄语行业化拓词 / 产品页审计 / 博客页审计 三个接口 `source=deepseek`（真实输出），信任信号逻辑真实命中
- 文件中心验证：9 种格式上传均 200 且解析出正文；CSV/JSON/XLSX 导入导出均 200，XLSX 头部 `PK` 有效；`.exe` 拒绝 400

## 六、复用 skills（本库）

- **L2 提示词工程**：系统提示词版本化（关键词/站内/外链/文档拓词/内容审计），角色+任务+约束+JSON schema
- **J 后端 AI 应用模式**：LangChain `with_structured_output(method="function_calling")` + 失败降级（DeepSeek 不支持 response_format 的 json_schema，已绕开）
- **最高级的自动化部署**：一键脚本基准（本实例即其实战落地）

## 七、目录

```
ai-seo-station/
├── backend/{__init__,app,db,llm,prompts,seo,report,files,dataio}.py
├── frontend/index.html              # 原生 HTML + Tailwind CDN（零框架依赖）
├── data/app.db                      # SQLite(WAL)，gitignore
├── requirements.txt / .env.example / .gitignore
├── start_seo.bat / start_seo.ps1    # 一键启动（8 铁律）
└── DEPLOY_NOTES.md
```

## 八、红线

- `.env` / venv / `data/*.db` / cloudflared.exe / PUBLIC_URL.txt / uploads/ → 全 gitignore，密钥永不进仓库
- quick tunnel 域名每次随机变；黑窗口开着链接才活
- IMA 实例统一归入「实例项目」文件夹（folder_7494751943132828）；IMA 无删除/修改 API，更新实例=新增最终版 + IMA 网页端手动删旧版
