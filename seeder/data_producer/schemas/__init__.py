from .base import BaseSchema
from .ecommerce import EcommerceSchema

SCHEMA_REGISTRY = {
    "ecommerce": EcommerceSchema,
}

def get_schema(name: str) -> BaseSchema:
    if name not in SCHEMA_REGISTRY:
        raise ValueError(f"Unknown schema '{name}'. Available: {list(SCHEMA_REGISTRY.keys())}")
    return SCHEMA_REGISTRY[name]()
