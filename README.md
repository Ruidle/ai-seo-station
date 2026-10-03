# 🚀 AI-SEO 独立站优化助手

**Python · Flask · DeepSeek API · LangChain · SQLite · Waitress**

面向外贸 / 跨境独立站的一站式 AI SEO 工作台：从关键词挖掘、竞品解析、站内审计，到外链台账与数据报告，覆盖 SEO 运营的完整工作流。无 API Key 时自动降级为**规则兜底演示模式**，零配置即可体验全部功能。

---

## 📌 开源仓库

| 项 | 信息 |
| --- | --- |
| **仓库地址** | **https://github.com/Ruidle/ai-seo-station** |
| **许可证** | MIT License（允许商用 / 修改 / 分发，保留版权声明） |
| **主要语言** | Python（后端）+ 原生 JavaScript（前端） |
| **提交历史** | 3 次提交，含初始版本、README 与 MIT LICENSE、截图 CDN 优化 |

```bash
git clone https://github.com/Ruidle/ai-seo-station.git
```

> 本项目已完整开源，采用 MIT 协议。欢迎 Fork、二次开发与商业使用；使用或衍生时请保留原仓库出处与 LICENSE 声明。

---

## 📸 项目截图

**主界面：6 大模块 + 数据导入导出工具栏**

![主界面](https://cdn.jsdelivr.net/gh/Ruidle/ai-seo-station@main/docs/screenshot-1-home.png)

**关键词挖掘：一个种子词批量生成行业化长尾词（支持 11 个语种）**

![关键词挖掘结果](https://cdn.jsdelivr.net/gh/Ruidle/ai-seo-station@main/docs/screenshot-2-keywords.png)

**站内优化：页面综合评分 + 缺陷检测 + TDK 改写建议 + 跨境信任信号体检**

![站内审计报告](https://cdn.jsdelivr.net/gh/Ruidle/ai-seo-station@main/docs/screenshot-3-audit.png)

---

## ✨ 功能特性

| 模块 | 能力 |
| --- | --- |
| ① 关键词挖掘 | AI 拓展长尾词，支持行业化词根（外贸 / 跨境 / OEM）与 11 个语种，结果自动落库 |
| ② 竞品解析 | 抓取竞品 TDK（Title / Description / Keywords）与页面高频词，快速拆解对手打法 |
| ③ 站内优化 | 支持 URL 在线审计或粘贴 HTML：综合评分、缺陷清单、TDK 智能改写、跨境信任信号检测 |
| ④ 外链台账 | 外链登记 / 状态管理，AI 一键生成外链博客素材（客座文章） |
| ⑤ 指标 & 报告 | 收录量 / 排名 / 流量等指标录入，AI 汇总生成阶段性 SEO 分析报告 |
| ⑥ 文件中心 | 上传 PDF / DOCX / XLSX / HTML 等 9 种格式，自动提取正文并做关键词与内容 SEO 分析 |
| 数据互通 | 关键词 / 外链 / 指标支持 CSV · JSON · XLSX 批量导入导出，附标准模板下载 |

---

## 🚀 三步启动

> 环境要求：Python 3.10+

```bash
# ① 克隆项目并安装依赖
git clone https://github.com/Ruidle/ai-seo-station.git
cd ai-seo-station
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate
pip install -r requirements.txt

# ② 配置 Key（可选 —— 不配置则自动进入规则兜底演示模式）
copy .env.example .env          # macOS / Linux 用: cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY；也可直接设置系统环境变量 DEEPSEEK_API_KEY

# ③ 启动服务
python -m backend.app
```

浏览器打开 **http://127.0.0.1:8011** 即可使用。

**Windows 用户更省事**：双击 `start_seo.bat`，脚本会自动创建虚拟环境、安装依赖、启动服务，并通过 Cloudflare Tunnel 生成可公网访问的网址（首次运行自动下载 cloudflared）。

---

## 🧱 项目结构

```
ai-seo-station/
├── backend/
│   ├── app.py        # Flask 主应用：路由与 JSON API
│   ├── seo.py        # SEO 核心逻辑：拓词 / 竞品 / 审计 / 外链文章
│   ├── llm.py        # DeepSeek（OpenAI 兼容协议）封装 + 无 Key 规则兜底
│   ├── files.py      # 多格式文件正文提取
│   ├── report.py     # 指标与报告生成
│   ├── dataio.py     # CSV / JSON / XLSX 导入导出
│   └── db.py         # SQLite 初始化与连接
├── frontend/
│   └── index.html    # 单页应用（Tailwind CSS + 原生 JS）
├── docs/             # 项目截图
├── .env.example      # 环境变量模板
├── requirements.txt
├── start_seo.bat     # Windows 一键启动入口
└── start_seo.ps1     # 一键启动 + Cloudflare Tunnel 脚本
```

---

## 🔌 主要 API

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 健康检查 |
| POST | `/api/keywords/expand` | 关键词拓展 |
| POST | `/api/competitor/parse` | 竞品页面解析 |
| POST | `/api/onpage/audit` | 站内页面审计 |
| GET/POST | `/api/backlinks` | 外链台账增查 |
| POST | `/api/backlinks/generate` | AI 生成外链文章 |
| GET/POST | `/api/metrics` | SEO 指标录入查询 |
| POST | `/api/report/generate` | 生成分析报告 |
| POST | `/api/files/upload` | 文件上传解析 |
| GET | `/api/export` | 数据导出（csv/json/xlsx） |
| POST | `/api/import` | 数据批量导入 |

---

## ☁️ 公网部署

`start_seo.ps1` 内置 **Cloudflare Quick Tunnel**：本地服务启动后自动拉起 `cloudflared`，生成的 `https://*.trycloudflare.com` 临时公网地址会自动复制到剪贴板，无需域名、无需注册，方便演示与客户分享。长期部署建议使用固定域名 + 正规云服务器（Waitress 生产级 WSGI，已内置在依赖中）。

---

## 📄 License

[MIT](LICENSE)

本项目开源托管于 **https://github.com/Ruidle/ai-seo-station** ，遵循 MIT 许可证。
