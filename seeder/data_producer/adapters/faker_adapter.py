import logging
import time
from typing import Iterator, List, Dict, Any
from ..schemas.base import BaseSchema

logger = logging.getLogger("data_producer.faker")


class FakerAdapter:
    """
    Generates synthetic records in-process using a BaseSchema.

    Args:
        schema:      Instantiated BaseSchema (e.g. EcommerceSchema())
        batch_size:  Records per yielded batch
        max_batches: Stop after N batches. None = run forever.
    """

    def __init__(self, schema: BaseSchema, batch_size: int, max_batches: int = None):
        self.schema      = schema
        self.batch_size  = batch_size
        self.max_batches = max_batches

    def stream(self) -> Iterator[List[Dict[str, Any]]]:
        batch_num = 0
        while self.max_batches is None or batch_num < self.max_batches:
            t0    = time.perf_counter()
            batch = [self.schema.generate_record() for _ in range(self.batch_size)]
            ms    = (time.perf_counter() - t0) * 1000
            batch_num += 1
            logger.info(
                "[FakerAdapter] batch=%d  records=%d  generated_in=%.1fms",
                batch_num, len(batch), ms,
            )
            yield batch
