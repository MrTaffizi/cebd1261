# © 2026 Mohammed A. Shehab. All rights reserved.
"""
seed.py
=======
CEBD 1261 — Session 7 | Lab 1

Smart seeder: checks existing counts in MongoDB and ElasticSearch.
- If both already have TARGET records → skip entirely.
- If either is short → generate only the missing records and insert.

Target: 100,000 records.
"""

import logging
import os
import random
from datetime import date, datetime

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient

from data_producer import FakerAdapter, get_schema

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
MONGODB_URI = os.environ["MONGODB_URI"]
ES_URL      = os.environ.get("ES_URL", "http://elasticsearch:9200")
MONGO_DB    = "cebd1261"
MONGO_COLL  = "orders"
ES_INDEX    = "orders"
TARGET      = 100_000
BATCH_SIZE  = 500

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("seed")


# ── Derived columns ────────────────────────────────────────────────────────────
def add_derived(record: dict) -> dict:
    ts = datetime.strptime(record["order_timestamp"], "%Y-%m-%dT%H:%M:%S")
    unit_price = record["unit_price"]
    quantity   = record["quantity"]

    total_price      = round(unit_price * quantity, 2)
    discount_applied = round(random.uniform(0, 0.30), 2)
    final_price      = round(total_price * (1 - discount_applied), 2)
    cost             = round(total_price * 0.60, 2)
    profit_margin    = round((final_price - cost) / final_price, 4) if final_price else 0.0

    price_tier = "budget" if total_price < 50 else ("mid" if total_price <= 300 else "premium")

    record.update({
        "total_price":      total_price,
        "order_date":       ts.strftime("%Y-%m-%d"),
        "processing_day":   date.today().isoformat(),
        "days_to_deliver":  random.randint(1, 14),
        "order_hour":       ts.hour,
        "is_high_value":    total_price > 500,
        "price_tier":       price_tier,
        "discount_applied": discount_applied,
        "final_price":      final_price,
        "profit_margin":    profit_margin,
    })
    return record


# ── Sanitize for ES ────────────────────────────────────────────────────────────
def _sanitize(record: dict) -> dict:
    out = {}
    for k, v in record.items():
        if k == "_id":
            continue
        elif isinstance(v, bool):
            out[k] = v
        elif isinstance(v, float):
            out[k] = float(v)
        elif isinstance(v, int):
            out[k] = int(v)
        else:
            out[k] = v
    return out


# ── Count helpers ──────────────────────────────────────────────────────────────
def mongo_count() -> int:
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        count  = client[MONGO_DB][MONGO_COLL].count_documents({})
        client.close()
        return count
    except Exception as e:
        log.warning("Could not count MongoDB: %s", e)
        return 0


def es_count() -> int:
    try:
        es = Elasticsearch(ES_URL)
        if not es.indices.exists(index=ES_INDEX):
            return 0
        return es.count(index=ES_INDEX)["count"]
    except Exception as e:
        log.warning("Could not count ElasticSearch: %s", e)
        return 0


# ── Writers ────────────────────────────────────────────────────────────────────
def insert_mongo(records: list[dict]) -> None:
    client = MongoClient(MONGODB_URI)
    client[MONGO_DB][MONGO_COLL].insert_many(records)
    log.info("[MongoDB]  inserted %d documents (total now ~%d)", len(records), TARGET)
    client.close()


def insert_es(records: list[dict]) -> None:
    es = Elasticsearch(ES_URL)

    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(index=ES_INDEX, body={
            "mappings": {"properties": {
                "order_id":         {"type": "keyword"},
                "customer_id":      {"type": "keyword"},
                "customer_name":    {"type": "text"},
                "customer_email":   {"type": "keyword"},
                "customer_country": {"type": "keyword"},
                "product_id":       {"type": "keyword"},
                "product_name":     {"type": "text"},
                "category":         {"type": "keyword"},
                "unit_price":       {"type": "float"},
                "quantity":         {"type": "integer"},
                "order_timestamp":  {"type": "keyword"},
                "payment_method":   {"type": "keyword"},
                "status":           {"type": "keyword"},
                "total_price":      {"type": "float"},
                "order_date":       {"type": "date", "format": "yyyy-MM-dd"},
                "processing_day":   {"type": "date", "format": "yyyy-MM-dd"},
                "days_to_deliver":  {"type": "integer"},
                "order_hour":       {"type": "integer"},
                "is_high_value":    {"type": "boolean"},
                "price_tier":       {"type": "keyword"},
                "discount_applied": {"type": "float"},
                "final_price":      {"type": "float"},
                "profit_margin":    {"type": "float"},
            }}
        })

    actions = [
        {"_index": ES_INDEX, "_id": r["order_id"], "_source": _sanitize(r)}
        for r in records
    ]
    helpers.bulk(es, actions)
    log.info("[ElasticSearch] indexed %d documents (total now ~%d)", len(records), TARGET)


# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log.info("=" * 60)
    log.info("CEBD 1261 — Session 7 Lab 1 | Smart Data Seeder")
    log.info("Target: %d records", TARGET)
    log.info("=" * 60)

    mc = mongo_count()
    ec = es_count()
    log.info("Current counts — MongoDB: %d  |  ElasticSearch: %d", mc, ec)

    # Both stores are already at target — nothing to do
    if mc >= TARGET and ec >= TARGET:
        log.info("Both stores already have %d records. Skipping.", TARGET)
        return

    # How many records does each store need?
    mongo_needed = max(0, TARGET - mc)
    es_needed    = max(0, TARGET - ec)
    needed       = max(mongo_needed, es_needed)

    log.info("Need to generate %d records (Mongo needs %d, ES needs %d)",
             needed, mongo_needed, es_needed)

    # Generate only what's needed
    n_batches = (needed + BATCH_SIZE - 1) // BATCH_SIZE
    schema    = get_schema("ecommerce")
    adapter   = FakerAdapter(schema, batch_size=BATCH_SIZE, max_batches=n_batches)

    records = []
    for batch in adapter.stream():
        records.extend([add_derived(r) for r in batch])
        log.info("  generated %d / %d", len(records), needed)

    # Trim to exact needed count
    records = records[:needed]

    if es_needed > 0:
        log.info("Seeding ElasticSearch (%d records) …", es_needed)
        insert_es(records[:es_needed])

    if mongo_needed > 0:
        log.info("Seeding MongoDB (%d records) …", mongo_needed)
        insert_mongo(records[:mongo_needed])

    log.info("=" * 60)
    log.info("Done — MongoDB: %d  |  ElasticSearch: %d", mongo_count(), es_count())
    log.info("=" * 60)


if __name__ == "__main__":
    main()