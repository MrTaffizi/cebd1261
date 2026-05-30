# © 2026 Mohammed A. Shehab. All rights reserved.
"""
elastic_agent.py — Full-text search on ES orders index, answers via LLM.
CEBD 1261 — Session 7 | Lab 1
"""

import json
import os

from elasticsearch import Elasticsearch

from agents.base_agent import BaseAgent
from agents.utils import build_llm, wants_chart, build_chart


class ElasticAgent(BaseAgent):
    """
    Runs a multi_match query across all fields in the orders index
    and asks the LLM to answer the user's query from the top hits.
    """

    INDEX = "orders"
    MAX   = 20

    def __init__(self):
        super().__init__(name="ElasticAgent")
        self._es     = Elasticsearch(os.environ.get("ES_URL", "http://elasticsearch:9200"))
        self._llm    = build_llm()
        self._prompt = self.load_prompt("elastic.md")

    def run(self, query: str) -> dict:
        hits     = self._search(query)
        prompt   = self._prompt.format(
            query=query,
            count=len(hits),
            data=json.dumps(hits, default=str, indent=2),
        )
        response = self._llm(prompt)
        chart    = build_chart(query, hits) if wants_chart(query) else None
        return {"response": response, "chart": chart}

    def _search(self, query: str) -> list[dict]:
        if not query.strip() or query.strip() == "*":
            es_query = {"match_all": {}}
        else:
            es_query = {
                "multi_match": {
                    "query":     query,
                    "fields":    ["*"],
                    "type":      "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        resp = self._es.search(
            index=self.INDEX,
            body={"query": es_query, "size": self.MAX},
        )
        return [h["_source"] for h in resp["hits"]["hits"]]