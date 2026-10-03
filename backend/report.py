"""SEO 分析报告：录入指标 -> 自动生成报告（Markdown + CSV 导出）。

报告包含：核心指标概览、趋势（与上一期对比）、诊断项、行动清单。
分数按收录量/排名/流量/词数加权粗算（0-100），仅作运营参考。
"""
import csv
import io
import json
from . import db


def add_metric(site: str, date: str, indexed: int, avg_ranking: float,
               traffic: int, kw_count: int) -> int:
    conn = db.get_conn()
    rid = db.insert_returning_id(
        conn,
        "INSERT INTO metrics(site,date,indexed,avg_ranking,traffic,kw_count) VALUES(?,?,?,?,?,?)",
        (site, date, indexed, avg_ranking, traffic, kw_count),
    )
    conn.close()
    return rid


def list_metrics(site: str = "") -> list:
    conn = db.get_conn()
    if site:
        rows = conn.execute(
            "SELECT * FROM metrics WHERE site=? ORDER BY date DESC", (site,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM metrics ORDER BY date DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _score(m: dict) -> int:
    s = 0
    s += min(40, (m.get("indexed") or 0) // 25)          # 收录越多越好
    s += max(0, 30 - int((m.get("avg_ranking") or 50) * 0.6))  # 排名越靠前越好
    s += min(20, (m.get("traffic") or 0) // 50)          # 流量
    s += min(10, (m.get("kw_count") or 0) // 10)          # 覆盖词数
    return max(0, min(100, s))


def generate_report(site: str) -> dict:
    metrics = list_metrics(site)
    if not metrics:
        return {"error": "暂无指标数据，请先录入"}

    cur = metrics[0]
    prev = metrics[1] if len(metrics) > 1 else None
    score = _score(cur)

    lines = []
    lines.append(f"# SEO 分析报告 · {site or '全局'}")
    lines.append("")
    lines.append(f"> 生成时间基于最新一期数据（{cur['date']}）｜综合 SEO 评分：**{score}/100**")
    lines.append("")
    lines.append("## 一、核心指标")
    lines.append("")
    lines.append("| 指标 | 最新 | 上期 | 变化 |")
    lines.append("|---|---|---|---|")
    if prev:
        d_idx = cur["indexed"] - prev["indexed"]
        d_rank = round((prev["avg_ranking"] - cur["avg_ranking"]), 1)  # 排名下降=变好
        d_traffic = cur["traffic"] - prev["traffic"]
        d_kw = cur["kw_count"] - prev["kw_count"]
        lines.append(f"| 收录量 | {cur['indexed']} | {prev['indexed']} | {d_idx:+d} |")
        lines.append(f"| 平均排名 | {cur['avg_ranking']} | {prev['avg_ranking']} | {d_rank:+g} |")
        lines.append(f"| 流量 | {cur['traffic']} | {prev['traffic']} | {d_traffic:+d} |")
        lines.append(f"| 覆盖词数 | {cur['kw_count']} | {prev['kw_count']} | {d_kw:+d} |")
    else:
        lines.append(f"| 收录量 | {cur['indexed']} | - | - |")
        lines.append(f"| 平均排名 | {cur['avg_ranking']} | - | - |")
        lines.append(f"| 流量 | {cur['traffic']} | - | - |")
        lines.append(f"| 覆盖词数 | {cur['kw_count']} | - | - |")

    lines.append("")
    lines.append("## 二、诊断与行动清单")
    lines.append("")
    actions = []
    if (cur["indexed"] or 0) < 100:
        actions.append("- 收录偏低：提交 sitemap 至 Google Search Console，检查 robots.txt 是否误屏蔽。")
    if (cur["avg_ranking"] or 99) > 20:
        actions.append("- 排名靠后：针对核心词补齐内容深度，建设 3-5 条高质量外链。")
    if (cur["traffic"] or 0) < 200:
        actions.append("- 流量不足：拓展长尾词（见关键词挖掘模块），优化高流量低转化页。")
    if not actions:
        actions.append("- 核心指标健康，维持内容更新与外链节奏，监控波动。")
    lines.extend(actions)
    lines.append("")
    lines.append("## 三、历史数据（CSV）")
    lines.append("")
    csv_text = _to_csv(metrics)
    lines.append("```csv")
    lines.append(csv_text)
    lines.append("```")

    markdown = "\n".join(lines)

    # 落库
    conn = db.get_conn()
    db.insert_returning_id(
        conn,
        "INSERT INTO reports(site,score,markdown,csv) VALUES(?,?,?,?)",
        (site, score, markdown, csv_text),
    )
    conn.close()

    return {"site": site, "score": score, "markdown": markdown, "csv": csv_text}


def _to_csv(metrics: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "indexed", "avg_ranking", "traffic", "kw_count"])
    for m in reversed(metrics):  # 时间正序
        w.writerow([m["date"], m["indexed"], m["avg_ranking"], m["traffic"], m["kw_count"]])
    return buf.getvalue()
