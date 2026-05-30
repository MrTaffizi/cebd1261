from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseSchema(ABC):

    @abstractmethod
    def generate_record(self) -> Dict[str, Any]:
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass
