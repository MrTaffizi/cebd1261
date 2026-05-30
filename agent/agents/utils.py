# © 2026 Mohammed A. Shehab. All rights reserved.
"""
utils.py — Shared helpers for all agents.
CEBD 1261 — Session 7 | Lab 1
"""

import os
import requests
from collections import defaultdict
from typing import Callable


# ── LLM caller ────────────────────────────────────────────────────────────────

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def build_llm() -> Callable[[str], str]:
    api_key = os.environ["OPENROUTER_API_KEY"]
    model   = os.environ.get("OPENROUTER_MODEL", "mistralai/ministral-14b-2512")

    def call(prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:8080",
            "X-Title":       "CEBD1261-Lab1",
        }
        payload = {
            "model":       model,
            "messages":    [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens":  512,
        }
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    return call


# ── Chart detection ───────────────────────────────────────────────────────────

_CHART_KEYWORDS = {
    "chart", "plot", "graph", "visualize", "visualise",
    "bar", "pie", "line", "histogram", "scatter", "trend",
    "show me a chart", "show chart", "draw", "time series",
    "over time", "daily", "monthly",
}

def wants_chart(query: str) -> bool:
    q = query.lower()
    return any(kw in q for kw in _CHART_KEYWORDS)


# ── Chart builder ─────────────────────────────────────────────────────────────

def build_chart(query: str, records: list[dict]) -> dict | None:
    if not records:
        return None
    q = query.lower()

    # ── Time series ───────────────────────────────────────────────────────────
    if "daily" in q or ("time" in q and "series" in q) or "over time" in q or "trend" in q:
        return _time_series_chart(records)

    if "monthly" in q or "month" in q:
        return _monthly_chart(records)

    # ── Histogram: orders by hour ─────────────────────────────────────────────
    if "hour" in q or "histogram" in q:
        return _histogram_hour(records)

    # ── Revenue / multi-metric bar ────────────────────────────────────────────
    if "revenue" in q or "sales" in q:
        return _revenue_by_category(records)

    # ── Profit margin ─────────────────────────────────────────────────────────
    if "profit" in q or "margin" in q:
        return _margin_chart(records)

    # ── Scatter: discount vs final price ─────────────────────────────────────
    if "scatter" in q or "discount" in q:
        return _scatter_chart(records)

    # ── Pie charts ────────────────────────────────────────────────────────────
    if "payment" in q:
        return _pie_chart(records, "payment_method", "Orders by Payment Method")

    if "status" in q:
        return _pie_chart(records, "status", "Orders by Status")

    if "tier" in q or "price_tier" in q:
        return _pie_chart(records, "price_tier", "Orders by Price Tier")

    # ── Bar: country ──────────────────────────────────────────────────────────
    if "country" in q:
        return _count_bar(records, "customer_country", "Top Countries by Orders")

    # ── Default: category bar ─────────────────────────────────────────────────
    return _count_bar(records, "category", "Orders by Category")


# ── Chart builders ─────────────────────────────────────────────────────────────

def _time_series_chart(records: list[dict]) -> dict | None:
    """Line chart: orders and revenue over daily dates."""
    dated = [(r.get("order_date"), r.get("orders", 1), r.get("revenue", 0))
             for r in records if r.get("order_date")]
    if not dated:
        return None
    dated.sort(key=lambda x: x[0])
    labels  = [d[0] for d in dated]
    orders  = [d[1] for d in dated]
    revenue = [d[2] for d in dated]
    return {
        "type": "line",
        "data": {
            "labels": labels,
            "datasets": [
                {
                    "label": "Orders",
                    "data": orders,
                    "borderColor": "#0D9488",
                    "backgroundColor": "rgba(13,148,136,0.1)",
                    "fill": True,
                    "tension": 0.3,
                    "yAxisID": "y",
                },
                {
                    "label": "Revenue ($)",
                    "data": revenue,
                    "borderColor": "#6366F1",
                    "backgroundColor": "rgba(99,102,241,0.05)",
                    "fill": False,
                    "tension": 0.3,
                    "yAxisID": "y1",
                },
            ],
        },
        "options": {
            "responsive": True,
            "interaction": {"mode": "index", "intersect": False},
            "plugins": {"title": {"display": True, "text": "Daily Orders & Revenue"}},
            "scales": {
                "x":  {"ticks": {"maxTicksLimit": 20, "maxRotation": 45}},
                "y":  {"type": "linear", "position": "left",  "title": {"display": True, "text": "Orders"}},
                "y1": {"type": "linear", "position": "right", "title": {"display": True, "text": "Revenue ($)"},
                       "grid": {"drawOnChartArea": False}},
            },
        },
    }


def _monthly_chart(records: list[dict]) -> dict | None:
    """Grouped bar chart: orders and revenue by month."""
    monthly = [(r.get("month"), r.get("orders", 1), r.get("revenue", 0))
               for r in records if r.get("month")]
    if not monthly:
        # fallback: group daily data by month prefix
        monthly = {}
        for r in records:
            d = r.get("order_date", "")
            if len(d) >= 7:
                m = d[:7]
                monthly[m] = (monthly.get(m, (0, 0))[0] + r.get("orders", 1),
                              monthly.get(m, (0, 0))[1] + r.get("revenue", 0))
        monthly = [(k, v[0], v[1]) for k, v in sorted(monthly.items())]
    if not monthly:
        return None
    labels  = [m[0] for m in monthly]
    orders  = [m[1] for m in monthly]
    revenue = [round(m[2], 2) for m in monthly]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Orders", "data": orders, "backgroundColor": "#0D9488", "yAxisID": "y"},
                {"label": "Revenue ($)", "data": revenue, "backgroundColor": "#FCD34D", "yAxisID": "y1"},
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {"title": {"display": True, "text": "Monthly Orders & Revenue"}},
            "scales": {
                "y":  {"type": "linear", "position": "left",  "title": {"display": True, "text": "Orders"}},
                "y1": {"type": "linear", "position": "right", "title": {"display": True, "text": "Revenue ($)"},
                       "grid": {"drawOnChartArea": False}},
            },
        },
    }


def _histogram_hour(records: list[dict]) -> dict | None:
    """Histogram: order volume by hour of day (0–23)."""
    counts: dict = defaultdict(int)
    for r in records:
        h = r.get("order_hour") if r.get("order_hour") is not None else r.get("orders")
        if h is not None:
            counts[int(h)] += r.get("orders", 1)
    if not counts:
        return None
    labels = [str(h) for h in range(24)]
    data   = [counts.get(h, 0) for h in range(24)]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{
                "label": "Orders",
                "data": data,
                "backgroundColor": [_palette(24)[h] for h in range(24)],
                "borderRadius": 4,
            }],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False},
                        "title": {"display": True, "text": "Order Volume by Hour of Day"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Hour (0–23)"}},
                "y": {"title": {"display": True, "text": "Number of Orders"}},
            },
        },
    }


def _revenue_by_category(records: list[dict]) -> dict | None:
    """Horizontal grouped bar: orders + revenue by category."""
    cats = [(r.get("category"), r.get("orders", 1), r.get("revenue", r.get("final_price", 0)))
            for r in records if r.get("category")]
    if not cats:
        return None
    # aggregate
    agg: dict = defaultdict(lambda: [0, 0])
    for cat, o, rev in cats:
        agg[cat][0] += o
        agg[cat][1] += rev
    labels  = sorted(agg.keys())
    orders  = [agg[l][0] for l in labels]
    revenue = [round(agg[l][1], 2) for l in labels]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [
                {"label": "Orders",      "data": orders,  "backgroundColor": "#0D9488", "yAxisID": "y"},
                {"label": "Revenue ($)", "data": revenue, "backgroundColor": "#FCD34D", "yAxisID": "y1"},
            ],
        },
        "options": {
            "responsive": True,
            "plugins": {"title": {"display": True, "text": "Orders & Revenue by Category"}},
            "scales": {
                "y":  {"position": "left",  "title": {"display": True, "text": "Orders"}},
                "y1": {"position": "right", "title": {"display": True, "text": "Revenue ($)"},
                       "grid": {"drawOnChartArea": False}},
            },
        },
    }


def _margin_chart(records: list[dict]) -> dict | None:
    """Bar chart: avg profit margin by category."""
    agg: dict = defaultdict(list)
    for r in records:
        cat = r.get("category")
        m   = r.get("profit_margin")
        if cat and m is not None:
            agg[cat].append(float(m))
    if not agg:
        return None
    labels = sorted(agg.keys())
    data   = [round(sum(agg[l]) / len(agg[l]), 4) for l in labels]
    colors = ["#10B981" if v >= 0.3 else "#F59E0B" if v >= 0.2 else "#EF4444" for v in data]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{"label": "Avg Profit Margin", "data": data, "backgroundColor": colors, "borderRadius": 4}],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False},
                        "title":  {"display": True, "text": "Average Profit Margin by Category"}},
            "scales": {
                "y": {"min": 0, "max": 0.5, "ticks": {"format": {"style": "percent"}},
                      "title": {"display": True, "text": "Profit Margin"}},
            },
        },
    }


def _scatter_chart(records: list[dict]) -> dict | None:
    """Scatter: discount applied vs final price."""
    points = [{"x": float(r["discount_applied"]), "y": float(r["final_price"])}
              for r in records
              if r.get("discount_applied") is not None and r.get("final_price") is not None]
    if not points:
        return None
    return {
        "type": "scatter",
        "data": {
            "datasets": [{
                "label": "Discount vs Final Price",
                "data": points[:500],
                "backgroundColor": "rgba(13,148,136,0.4)",
                "pointRadius": 3,
            }],
        },
        "options": {
            "responsive": True,
            "plugins": {"title": {"display": True, "text": "Discount Applied vs Final Price"}},
            "scales": {
                "x": {"title": {"display": True, "text": "Discount Applied (0–0.30)"}},
                "y": {"title": {"display": True, "text": "Final Price ($)"}},
            },
        },
    }


def _pie_chart(records: list[dict], field: str, title: str) -> dict | None:
    counts: dict = defaultdict(int)
    for r in records:
        val = r.get(field) or r.get("_id")
        n   = r.get("orders", 1)
        if val is not None:
            counts[str(val)] += n
    if not counts:
        return None
    labels = sorted(counts.keys())
    data   = [counts[l] for l in labels]
    return {
        "type": "doughnut",
        "data": {
            "labels": labels,
            "datasets": [{"data": data, "backgroundColor": _palette(len(labels)), "hoverOffset": 6}],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"position": "right"},
                        "title":  {"display": True, "text": title}},
        },
    }


def _count_bar(records: list[dict], field: str, title: str) -> dict | None:
    counts: dict = defaultdict(int)
    for r in records:
        val = r.get(field) or r.get("_id")
        n   = r.get("orders", 1)
        if val is not None:
            counts[str(val)] += n
    if not counts:
        return None
    items  = sorted(counts.items(), key=lambda x: -x[1])
    labels = [i[0] for i in items]
    data   = [i[1] for i in items]
    return {
        "type": "bar",
        "data": {
            "labels": labels,
            "datasets": [{"label": title, "data": data,
                          "backgroundColor": _palette(len(labels)), "borderRadius": 4}],
        },
        "options": {
            "responsive": True,
            "plugins": {"legend": {"display": False},
                        "title":  {"display": True, "text": title}},
            "scales": {"y": {"title": {"display": True, "text": "Orders"}}},
        },
    }


def _palette(n: int) -> list[str]:
    base = ["#0D9488","#0F2240","#FCD34D","#6366F1","#F59E0B",
            "#10B981","#EF4444","#8B5CF6","#EC4899","#14B8A6",
            "#3B82F6","#F97316","#84CC16","#06B6D4","#A855F7"]
    return [base[i % len(base)] for i in range(n)]