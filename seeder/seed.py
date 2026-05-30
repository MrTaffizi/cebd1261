# © 2026 Mohammed A. Shehab. All rights reserved.
"""
seed.py
=======
CEBD 1261 — Session 08 | Lab 1

Smart seeder: checks existing counts in MongoDB and ElasticSearch.
- If both already have TARGET records → skip entirely.
- If either is short → generate only the missing records and insert.

Target: 100,000 records.

ACI note:
    Docker Compose supports depends_on + healthcheck to delay the seeder
    until MongoDB and ES are ready. ACI Container Groups have no such
    mechanism — all containers start simultaneously. wait_for_services()
    fills this gap by retrying both connections every RETRY_INTERVAL
    seconds for up to RETRY_TIMEOUT seconds before seeding begins.
"""

import logging
import os
import random
import time
from datetime import date, datetime

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient

from data_producer import FakerAdapter, get_schema

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
MONGODB_URI     = os.environ["MONGODB_URI"]
ES_URL          = os.environ.get("ES_URL", "http://localhost:9200")
MONGO_DB        = "cebd1261"
MONGO_COLL      = "orders"
ES_INDEX        = "orders"
TARGET          = 10_000
BATCH_SIZE      = 500

# ── ACI startup retry config ───────────────────────────────────────────────────
# MongoDB and ES start at the same time as the seeder on ACI (no depends_on).
# Retry every RETRY_INTERVAL seconds for up to RETRY_TIMEOUT seconds.
RETRY_INTERVAL  = 5    # seconds between each attempt
RETRY_TIMEOUT   = 180  # 3 minutes maximum wait

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


# ── Startup wait (ACI has no depends_on) ─────────────────────────────────────
def wait_for_services() -> None:
    """
    Block until both MongoDB and ElasticSearch are reachable, or timeout.

    Why this exists:
        Docker Compose uses depends_on + healthcheck to hold the seeder
        until its dependencies are healthy. ACI Container Groups start all
        containers simultaneously with no equivalent mechanism. Without this
        function the seeder exits immediately with a connection error on
        every cold deploy.

    Strategy:
        Poll both services every RETRY_INTERVAL seconds.
        Only proceed when BOTH respond successfully.
        Abort with a non-zero exit if RETRY_TIMEOUT is exceeded.
    """
    log.info("Waiting for MongoDB and ElasticSearch to be ready …")
    deadline = time.time() + RETRY_TIMEOUT
    attempt  = 0

    while time.time() < deadline:
        attempt += 1
        mongo_ok = False
        es_ok    = False

        # ── Check MongoDB ──────────────────────────────────────────────────────
        try:
            client   = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            client.close()
            mongo_ok = True
        except Exception as e:
            log.info("  [attempt %d] MongoDB not ready: %s", attempt, e)

        # ── Check ElasticSearch ────────────────────────────────────────────────
        try:
            es    = Elasticsearch(ES_URL, request_timeout=3)
            info  = es.cluster.health(wait_for_status="yellow", timeout="3s")
            es_ok = info["status"] in ("green", "yellow")
        except Exception as e:
            log.info("  [attempt %d] ElasticSearch not ready: %s", attempt, e)

        if mongo_ok and es_ok:
            log.info("Both services ready after %d attempt(s).", attempt)
            return

        remaining = int(deadline - time.time())
        log.info(
            "  MongoDB=%s  ES=%s — retrying in %ds (%ds remaining) …",
            "✓" if mongo_ok else "✗",
            "✓" if es_ok    else "✗",
            RETRY_INTERVAL,
            remaining,
        )
        time.sleep(RETRY_INTERVAL)

    log.error(
        "Services did not become ready within %ds. Aborting.",
        RETRY_TIMEOUT,
    )
    raise SystemExit(1)


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
    log.info("CEBD 1261 — Session 08 | Smart Data Seeder")
    log.info("Target: %d records", TARGET)
    log.info("=" * 60)

    wait_for_services()

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