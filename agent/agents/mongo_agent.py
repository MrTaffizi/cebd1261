# © 2026 Mohammed A. Shehab. All rights reserved.
"""
mongo_agent.py — Queries MongoDB cebd1261.orders and answers via LLM.
CEBD 1261 — Session 7 | Lab 1
"""

import json
import os

from pymongo import MongoClient

from agents.base_agent import BaseAgent
from agents.utils import build_llm, wants_chart, build_chart


class MongoAgent(BaseAgent):

    DB   = "cebd1261"
    COLL = "orders"

    def __init__(self):
        super().__init__(name="MongoAgent")
        self._col    = MongoClient(os.environ["MONGODB_URI"])[self.DB][self.COLL]
        self._llm    = build_llm()
        self._prompt = self.load_prompt("mongo.md")

    def run(self, query: str) -> dict:
        chart = None
        if wants_chart(query):
            agg_data = self._aggregate_for_chart(query)
            chart    = build_chart(query, agg_data)
            docs     = agg_data
        else:
            docs = self._fetch_sample()

        prompt = self._prompt.format(
            query=query,
            count=len(docs),
            data=json.dumps(docs, default=str, indent=2),
        )
        response = self._llm(prompt)
        return {"response": response, "chart": chart}

    # ── Raw sample for non-chart queries ──────────────────────────────────────
    def _fetch_sample(self) -> list[dict]:
        return list(self._col.find({}, {"_id": 0}).sort("order_date", -1).limit(20))

    # ── Smart aggregation — matches build_chart() routing exactly ─────────────
    def _aggregate_for_chart(self, query: str) -> list[dict]:
        q = query.lower()

        # scatter: fetch raw records with discount + final_price fields
        if "scatter" in q or "discount" in q:
            return list(self._col.find(
                {"discount_applied": {"$exists": True}, "final_price": {"$exists": True}},
                {"_id": 0, "discount_applied": 1, "final_price": 1, "category": 1, "total_price": 1}
            ).limit(500))

        if "daily" in q or ("time" in q and "series" in q) or "over time" in q or "trend" in q:
            return self._agg_daily_orders()

        if "monthly" in q or "month" in q:
            return self._agg_monthly_orders()

        if "hour" in q or "histogram" in q:
            return self._agg_by_hour()

        if "revenue" in q or "sales" in q:
            return self._agg_revenue_by_category()

        if "profit" in q or "margin" in q:
            return self._agg_margin_by_category()

        if "status" in q:
            return self._agg_by_field("status")

        if "payment" in q:
            return self._agg_by_field("payment_method")

        if "tier" in q or "price_tier" in q:
            return self._agg_by_field("price_tier")

        if "country" in q:
            return self._agg_by_field("customer_country", limit=15)

        # default: category counts from ALL records
        return self._agg_by_field("category")

    # ── Aggregation helpers ───────────────────────────────────────────────────
    def _agg_daily_orders(self) -> list[dict]:
        return list(self._col.aggregate([
            {"$group": {"_id": "$order_date",
                        "orders":  {"$sum": 1},
                        "revenue": {"$sum": "$final_price"}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "order_date": "$_id", "orders": 1,
                          "revenue": {"$round": ["$revenue", 2]}}},
        ]))

    def _agg_monthly_orders(self) -> list[dict]:
        return list(self._col.aggregate([
            {"$addFields": {"month": {"$substr": ["$order_date", 0, 7]}}},
            {"$group": {"_id": "$month",
                        "orders":  {"$sum": 1},
                        "revenue": {"$sum": "$final_price"}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "month": "$_id", "orders": 1,
                          "revenue": {"$round": ["$revenue", 2]}}},
        ]))

    def _agg_by_hour(self) -> list[dict]:
        return list(self._col.aggregate([
            {"$group": {"_id": "$order_hour", "orders": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 0, "order_hour": "$_id", "orders": 1}},
        ]))

    def _agg_revenue_by_category(self) -> list[dict]:
        return list(self._col.aggregate([
            {"$group": {"_id": "$category",
                        "orders":    {"$sum": 1},
                        "revenue":   {"$sum": "$final_price"},
                        "avg_price": {"$avg": "$final_price"}}},
            {"$sort": {"revenue": -1}},
            {"$project": {"_id": 0, "category": "$_id", "orders": 1,
                          "revenue":   {"$round": ["$revenue", 2]},
                          "avg_price": {"$round": ["$avg_price", 2]}}},
        ]))

    def _agg_margin_by_category(self) -> list[dict]:
        return list(self._col.aggregate([
            {"$group": {"_id": "$category",
                        "profit_margin": {"$avg": "$profit_margin"},
                        "orders":        {"$sum": 1}}},
            {"$sort": {"profit_margin": -1}},
            {"$project": {"_id": 0, "category": "$_id",
                          "profit_margin": {"$round": ["$profit_margin", 4]},
                          "orders": 1}},
        ]))

    def _agg_by_field(self, field: str, limit: int = 20) -> list[dict]:
        return list(self._col.aggregate([
            {"$group": {"_id": f"${field}", "orders": {"$sum": 1}}},
            {"$sort": {"orders": -1}},
            {"$limit": limit},
            {"$project": {"_id": 0, field: "$_id", "orders": 1}},
        ]))