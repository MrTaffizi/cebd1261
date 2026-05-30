# © 2026 Mohammed A. Shehab. All rights reserved.
"""
base_agent.py — Abstract base class for all agents.
CEBD 1261 — Session 7 | Lab 1
"""

from abc import ABC, abstractmethod
from pathlib import Path


class BaseAgent(ABC):
    """
    Every agent must inherit from BaseAgent.

    Subclasses:
        - Set self.name in __init__
        - Implement run(query) → dict with keys: response (str), chart (dict|None)
        - Call self.load_prompt(filename) to read a .md prompt file
    """

    PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, query: str) -> dict:
        """
        Process the query and return a response dict.

        Returns:
            {
                "response": str,        # text answer shown in chat
                "chart":    dict | None # chart config if user asked for a chart,
                                        # None otherwise
            }
        """
        ...

    def load_prompt(self, filename: str) -> str:
        """Load a prompt template from the prompts/ directory."""
        path = self.PROMPTS_DIR / filename
        return path.read_text(encoding="utf-8")

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r})"