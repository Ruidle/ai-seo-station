# AI-SEO 独立站优化助手 · 部署说明

> 本项目的部署严格遵循 IMA 个人知识库《最高级的自动化部署》基准（2026-08-16 真机跑通版）。
> 与基准的差异仅一处：基准是 FastAPI+uvicorn，本项目是 Flask → 用 **waitress** 纯 Python WSGI 起服务，其余 8 条防闪退铁律原样复用。
> 最后更新：2026-08-16

## 一、项目定位

面向外贸独立站 SEO 运营人员的 AI 助手，覆盖站内 + 站外完整工作流：

1. **AI 关键词挖掘拓展** —— LangChain×DeepSeek 拓词；无 key 时规则兜底
2. **竞品网站解析** —— BeautifulSoup 抓竞品页，抽 TDK + 高频词
3. **站内页面优化** —— AI 生成 title/meta 描述 + 标签缺陷检测 + 整改建议
4. **站外外链台账** —— SQLite 台账 CRUD + AI 生成博客外链素材
5. **指标 & 报告** —— 录入收录/排名/流量，自动生成 SEO 分析报告（MD/CSV 导出）
6. **⑥ 文件中心** —— 上传解析 PDF/DOCX/TXT/MD/HTML/CSV/XLSX/RTF/ODT，从文档 AI 拓词 + 内容 SEO 审计；全局一键导入 / 导出（CSV/JSON/XLSX）

技术栈：Python Flask · BeautifulSoup · LangChain(DeepSeek) · SQLite(WAL) · waitress 部署
文件解析：pypdf · python-docx · openpyxl · odfpy（纯 Python 轻量包）

## 二、目录结构

```
ai-seo-station/
├── backend/{__init__.py, app.py, db.py, llm.py, prompts.py, seo.py, report.py, files.py, dataio.py}
├── frontend/index.html        # 原生 HTML + Tailwind CDN（零框架依赖）
├── uploads/                   # 上传文件落盘，gitignore
├── data/app.db                # SQLite(WAL)，gitignore（含 uploads 表）
├── requirements.txt
├── .env.example / .gitignore
├── start_seo.bat / start_seo.ps1   # 一键启动（8 铁律）
└── DEPLOY_NOTES.md
```

## 二之一、文件中心模块说明（新增）

**支持上传格式（白名单）**：PDF · DOCX · TXT · MD · HTML · CSV · XLSX · RTF · ODT。
非白名单扩展名（如 .exe）直接 400 拒绝，杜绝任意文件落盘执行风险。

**解析链路**：`backend/files.py` 按扩展名分发 →
- PDF → pypdf；DOCX → python-docx（正文+表格）；XLSX → openpyxl 逐表；
- HTML → BeautifulSoup 取正文（去 script/style）；ODT → odfpy；RTF → 正则去控制字。
- 解析结果存入 `uploads` 表（正文截断 5 万字符），前端可回看预览。

**基于上传内容的 SEO 增值**（借鉴开源 AI-seo-optimizer 的内容优化器思路）：
- `POST /api/files/keywords` —— 从文档正文 AI 提取关键词（真实 DeepSeek；无 key 规则词频兜底）
- `POST /api/files/audit` —— 内容 SEO 审计：关键词密度/可读性/结构评分(0-100) + 问题清单 + 整改建议 + 重写开头

**一键导入 / 导出**（`backend/dataio.py`）：
- 导入：`POST /api/import`（CSV/JSON/XLSX）→ 批量灌入 keywords / backlinks / metrics；脏行跳过不中断
- 模板：`GET /api/import/template?entity=&fmt=csv|json` 下载对应列模板
- 导出：`GET /api/export?entity=all|keywords|backlinks|metrics|reports|uploads&fmt=csv|json|xlsx`
- 前端顶栏「导入」选文件+实体、「导出」选实体+格式，一键下载。

## 二之二、虎翼系赛道优化（行业化 / 多语言 / 分类型审计 / 跨境信任信号）

本项目已按虎翼系站点（tigerwing.net / tigeraid.cn / kj128.cn / sourcingagent.cn）的真实业务校准，
从「通用 SEO 工具」升级为「外贸独立站 / 跨境 / 采购代理赛道专属助手」。

**1. 行业化关键词词库（INDUSTRY_SEED）**
`backend/prompts.py` 内置外贸/跨境/采购代理赛道词根（业务/平台/属性/长尾四类），
`seo.expand_keywords` 默认 `industry=True` 把词根注入 DeepSeek 提示词；前端①勾选「行业化」即生效。
实测：俄语+行业化拓词得到 `внешнеторговый независимый сайт`(外贸独立站)、`дропшиппинг из Китая в Россию`、`продвижение в Google и Yandex`。

**2. 多语言 TDK 生成（LANG_NAMES）**
覆盖 15 种语言（en/zh/ru/es/ar/de/fr/ja/ko/pt/vi/th/tr/it/nl），对应虎翼主打 26 语站群 + Yandex 俄语市场。
关键词拓词、站内 TDK 生成、文档关键词提取均接受 `lang` 参数按指定语种输出；无 key 时中文模式也有规则兜底。

**3. 分页面类型审计（PAGE_TYPES）**
`page_type` ∈ homepage/product/category/blog/landing，不同类型 SEO 标准差异化：
- 产品页：检测 Product 结构化数据(price/availability) + CTA 按钮
- 分类页：检测内链数量
- 博客页：检测 <article>/<time> 语义标签（E-E-A-T）
- 落地页：检测转化表单
前端③站内优化、⑥文件审计均已接入页面类型选择。

**4. 跨境信任信号 & 合规检测（detect_trust_signals）**
`seo.detect_trust_signals` 检测 9 项外贸站转化关键信号：隐私政策 / 关于我们·公司实勘 / 联系方式 /
支付方式展示 / 多语言切换 / 认证·证书 / 客户案例·评价 / 社媒矩阵 / 版权·备案，输出命中与缺失清单 + 评分(0-100)。
缺失项按每项 -3 纳入站内审计综合评分，并出现在整改建议中（提示补充客户案例、支付方式等）。

## 三、一键启动（双击即用）

双击 `start_seo.bat`：

```
[1/6] 定位 Python（优先托管路径）
[2/6] venv 就绪 + 依赖安装（清华源）
[3/6] waitress 起服务 127.0.0.1:8011（包方式 backend.app:app）
[4/6] 等待 /api/health 返回 200
[5/6] cloudflared 起 quick tunnel（缺失自动下载）
[6/6] 拿到 *.trycloudflare.com 公网域名 → 写 PUBLIC_URL.txt + 复制剪贴板 + 开浏览器
```

- 本地访问：http://127.0.0.1:8011
- 公网访问：https://xxx.trycloudflare.com（每次重启域名随机变，保持黑窗口开）
- 停止：在窗口按回车 / 关窗口（下次启动脚本自动清理端口）

## 四、8 条防闪退铁律（与基准一致）

1. `.bat` 用完整路径 `%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe` 调 powershell + `if errorlevel 1 pause`
2. 服务从项目根目录以**包方式** `backend.app:app` 起（Flask 经 waitress）
3. 启动前 `Get-NetTCPConnection` 释放 8000/8011 端口（杀僵尸进程）
4. 默认端口 8011，避开 8000 常见冲突
5. `.ps1` 按候选路径定位托管 python（双击环境无 PATH）
6. 隧道保活用 `Wait-Process -Id $cfProc.Id`（绝不用 Read-Host）
7. 隧道就绪判定读日志 `Registered tunnel connection`（绝不本机回环探测公网 URL）
8. `.env`/venv/`data/*.db`/cloudflared.exe/PUBLIC_URL.txt → 全进 .gitignore，密钥永不进仓库

## 五、AI 模式

- **真实模式**：Windows 用户级环境变量 `DEEPSEEK_API_KEY` 自动生效，真调 DeepSeek（OpenAI 兼容）
- **演示模式**：无 key 时关键词/文案走规则兜底，保证免 key 直接跑
- 结构化输出走 LangChain `with_structured_output(Pydantic)`（J 篇：JSON schema 校验兜底）
- 提示词遵循 L2 工程：角色 + 任务 + 约束 + 钉死 JSON schema

## 六、复用 IMA skills

- **L2 提示词工程** → 3 套系统提示词（关键词/站内/外链）版本化管理于 `prompts.py`
- **J 后端 AI 应用模式** → LangChain×DeepSeek 结构化输出 + 失败降级
- **最高级的自动化部署** → 一键脚本基准（本文件即其实战落地实例）
