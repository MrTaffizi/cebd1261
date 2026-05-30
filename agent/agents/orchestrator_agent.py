# © 2026 Mohammed A. Shehab. All rights reserved.
"""
orchestrator_agent.py — Classifies intent and dispatches to specialist agents.
CEBD 1261 — Session 7 | Lab 1
"""

import os
import time
import requests

from agents.base_agent import BaseAgent
from agents.mongo_agent import MongoAgent
from agents.elastic_agent import ElasticAgent
from agents.utils import OPENROUTER_URL


class OrchestratorAgent(BaseAgent):

    def __init__(self):
        super().__init__(name="OrchestratorAgent")
        self._api_key = os.environ["OPENROUTER_API_KEY"]
        self._model   = os.environ.get("OPENROUTER_MODEL", "mistralai/ministral-14b-2512")
        self._prompt  = self.load_prompt("orchestrator.md")
        self._chat_p  = self.load_prompt("chat.md")
        self._agents  = {
            "mongo":   MongoAgent(),
            "elastic": ElasticAgent(),
        }

    def run(self, query: str) -> dict:
        t0 = time.time()
        intent = self._classify(query)
        t1 = time.time()

        if intent in self._agents:
            result = self._agents[intent].run(query)
        else:
            result = self._direct_chat(query)

        t2 = time.time()
        result["intent"] = intent
        result["timing"] = {
            "classify_ms":  round((t1 - t0) * 1000),
            "agent_ms":     round((t2 - t1) * 1000),
            "total_ms":     round((t2 - t0) * 1000),
        }
        return result

    def _classify(self, query: str) -> str:
        prompt = self._prompt.format(query=query)
        label  = self._call(prompt, max_tokens=10, temperature=0)
        label  = label.strip().lower().split()[0] if label.strip() else "chat"
        return label if label in ("mongo", "elastic") else "chat"

    def _direct_chat(self, query: str) -> dict:
        prompt   = self._chat_p.format(query=query)
        response = self._call(prompt)
        return {"response": response, "chart": None}

    def _call(self, prompt: str, max_tokens: int = 512, temperature: float = 0.3) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "http://localhost:8080",
            "X-Title":       "CEBD1261-Lab1",
        }
        payload = {
            "model":       self._model,
            "messages":    [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        resp = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()