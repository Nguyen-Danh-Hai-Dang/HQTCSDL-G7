#!/usr/bin/env python3
"""Reproducible, single-client read benchmark for MySQL and MongoDB."""
import argparse
import csv
import json
import math
import os
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import mysql.connector
from pymongo import MongoClient
from bson import json_util

WARMUPS = 5
REPEATS = 30
ORDER_ID = 8
CUSTOMER_ID = 506
D1 = "2025-03-01 00:00:00"
D2 = "2025-04-01 00:00:00"
DAY1 = "2025-03-15 00:00:00"
DAY2 = "2025-03-22 00:00:00"
EXCLUDED = ["CANCELLED", "RETURNED"]

MYSQL_QUERIES = {
    "Q2": """SELECT order_id, order_date, status FROM orders
             WHERE customer_id=%s ORDER BY order_date DESC, order_id DESC LIMIT 20""",
    "Q3": """SELECT order_id, customer_id, order_date, status FROM orders
             WHERE order_date >= %s AND order_date < %s AND status='SHIPPED'
             ORDER BY order_date, order_id LIMIT 100""",
    "Q4": """SELECT DATE_FORMAT(o.order_date, '%Y-%m') AS month,
                    COUNT(DISTINCT o.order_id) AS orders,
                    SUM(i.quantity * i.unit_price) AS revenue
             FROM orders o JOIN order_item i ON i.order_id=o.order_id
             WHERE o.order_date >= '2024-01-01' AND o.order_date < '2026-01-01'
               AND o.status NOT IN ('CANCELLED','RETURNED')
             GROUP BY month ORDER BY month""",
    "Q5": """SELECT i.product_id, p.name, SUM(i.quantity*i.unit_price) AS revenue
             FROM orders o JOIN order_item i ON i.order_id=o.order_id
             JOIN product p ON p.product_id=i.product_id
             WHERE o.order_date >= %s AND o.order_date < %s
               AND o.status NOT IN ('CANCELLED','RETURNED')
             GROUP BY i.product_id,p.name
             ORDER BY revenue DESC,i.product_id LIMIT 10""",
    "Q6": """SELECT c.category_id,c.name,SUM(i.quantity*i.unit_price) AS revenue
             FROM orders o JOIN order_item i ON i.order_id=o.order_id
             JOIN product p ON p.product_id=i.product_id
             JOIN category c ON c.category_id=p.category_id
             WHERE o.order_date >= %s AND o.order_date < %s
               AND o.status NOT IN ('CANCELLED','RETURNED')
             GROUP BY c.category_id,c.name ORDER BY revenue DESC,c.category_id""",
    "Q7": """SELECT o.order_id,o.order_date,o.status,cu.full_name,cu.email,
                    i.line_no,p.sku,p.name AS product_name,i.quantity,i.unit_price
             FROM orders o JOIN customer cu ON cu.customer_id=o.customer_id
             JOIN order_item i ON i.order_id=o.order_id
             JOIN product p ON p.product_id=i.product_id
             WHERE o.order_id=%s ORDER BY i.line_no""",
    "Q8": """SELECT o.customer_id,cu.full_name,SUM(i.quantity*i.unit_price) AS spend
             FROM orders o JOIN order_item i ON i.order_id=o.order_id
             JOIN customer cu ON cu.customer_id=o.customer_id
             WHERE o.order_date >= %s AND o.order_date < %s
               AND o.status NOT IN ('CANCELLED','RETURNED')
             GROUP BY o.customer_id,cu.full_name
             ORDER BY spend DESC,o.customer_id LIMIT 10""",
}

ORDER_TOTAL = {"$sum": {"$map": {"input": "$items", "as": "i",
    "in": {"$multiply": ["$$i.quantity", "$$i.unit_price"]}}}}

MONGO_PIPELINES = {
    "Q4": [
        {"$match": {"order_date": {"$gte": datetime(2024,1,1,tzinfo=timezone.utc),
                                     "$lt": datetime(2026,1,1,tzinfo=timezone.utc)},
                    "status": {"$nin": EXCLUDED}}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$order_date"}},
                    "orders": {"$sum": 1}, "revenue": {"$sum": ORDER_TOTAL}}},
        {"$sort": {"_id": 1}},
    ],
    "Q5": [
        {"$match": {"order_date": {"$gte": datetime(2025,3,1,tzinfo=timezone.utc),
                                     "$lt": datetime(2025,4,1,tzinfo=timezone.utc)},
                    "status": {"$nin": EXCLUDED}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.product_id",
                    "revenue": {"$sum": {"$multiply": ["$items.quantity","$items.unit_price"]}}}},
        {"$sort": {"revenue": -1, "_id": 1}}, {"$limit": 10},
        {"$lookup": {"from": "products", "localField": "_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": "$p"},
        {"$project": {"_id": 0, "product_id": "$_id", "name": "$p.name", "revenue": 1}},
    ],
    "Q6": [
        {"$match": {"order_date": {"$gte": datetime(2025,3,1,tzinfo=timezone.utc),
                                     "$lt": datetime(2025,4,1,tzinfo=timezone.utc)},
                    "status": {"$nin": EXCLUDED}}},
        {"$unwind": "$items"},
        {"$group": {"_id": "$items.product_id",
                    "revenue": {"$sum": {"$multiply": ["$items.quantity","$items.unit_price"]}}}},
        {"$lookup": {"from": "products", "localField": "_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": "$p"},
        {"$group": {"_id": "$p.category_id", "revenue": {"$sum": "$revenue"}}},
        {"$lookup": {"from": "categories", "localField": "_id", "foreignField": "_id", "as": "c"}},
        {"$unwind": "$c"},
        {"$project": {"_id": 0, "category_id": "$_id", "name": "$c.name", "revenue": 1}},
        {"$sort": {"revenue": -1, "category_id": 1}},
    ],
    "Q7": [
        {"$match": {"_id": ORDER_ID}},
        {"$lookup": {"from": "customers", "localField": "customer_id", "foreignField": "_id", "as": "cu"}},
        {"$unwind": "$cu"}, {"$unwind": "$items"},
        {"$lookup": {"from": "products", "localField": "items.product_id", "foreignField": "_id", "as": "p"}},
        {"$unwind": "$p"},
        {"$project": {"_id": 0, "order_id": "$_id", "order_date": 1, "status": 1,
                      "full_name": "$cu.full_name", "email": "$cu.email",
                      "line_no": "$items.line_no", "sku": "$p.sku", "product_name": "$p.name",
                      "quantity": "$items.quantity", "unit_price": "$items.unit_price"}},
        {"$sort": {"line_no": 1}},
    ],
    "Q8": [
        {"$match": {"order_date": {"$gte": datetime(2025,3,1,tzinfo=timezone.utc),
                                     "$lt": datetime(2025,4,1,tzinfo=timezone.utc)},
                    "status": {"$nin": EXCLUDED}}},
        {"$group": {"_id": "$customer_id", "spend": {"$sum": ORDER_TOTAL}}},
        {"$sort": {"spend": -1, "_id": 1}}, {"$limit": 10},
        {"$lookup": {"from": "customers", "localField": "_id", "foreignField": "_id", "as": "cu"}},
        {"$unwind": "$cu"},
        {"$project": {"_id": 0, "customer_id": "$_id", "full_name": "$cu.full_name", "spend": 1}},
    ],
}

def percentile(values, p):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(p * len(ordered)) - 1)]

def load_mongo(data_dir):
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/?replicaSet=rs0"),
                         serverSelectionTimeoutMS=30000)
    db = client["shop_bench"]
    mapping = {
        "categories": "categories.jsonl", "stores": "stores.jsonl",
        "customers": "customers.jsonl", "products": "products.jsonl",
        "inventory": "inventory.jsonl", "orders": "orders.jsonl",
    }
    for collection, filename in mapping.items():
        coll = db[collection]
        coll.drop()
        batch = []
        path = Path(data_dir) / "mongo" / filename
        with path.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    batch.append(json_util.loads(line))
                if len(batch) >= 5000:
                    coll.insert_many(batch, ordered=True)
                    batch.clear()
        if batch:
            coll.insert_many(batch, ordered=True)
        print(f"Loaded MongoDB {collection}: {coll.count_documents({})}")
    db.customers.create_index([("email", 1)], unique=True)
    db.products.create_index([("sku", 1)], unique=True)
    db.inventory.create_index([("store_id", 1), ("product_id", 1)], unique=True)
    client.close()

def build_indexes():
    started = time.perf_counter()
    my = mysql.connector.connect(host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")), user=os.getenv("MYSQL_USER","root"),
        password=os.getenv("MYSQL_PASSWORD","root"), database="shop_bench")
    cur = my.cursor()
    statements = [
        "CREATE INDEX idx_orders_customer_date ON orders (customer_id, order_date)",
        "CREATE INDEX idx_orders_date ON orders (order_date)",
        "CREATE INDEX idx_orders_status_date ON orders (status, order_date)",
        "CREATE INDEX idx_item_product ON order_item (product_id)",
        "CREATE INDEX idx_payment_order ON payment (order_id)",
        "CREATE INDEX idx_product_category ON product (category_id)",
    ]
    for statement in statements:
        cur.execute(statement)
    cur.execute("ANALYZE TABLE category, customer, product, store, inventory, orders, order_item, payment")
    cur.fetchall()
    cur.close()
    my.close()
    mysql_seconds = time.perf_counter() - started

    started = time.perf_counter()
    client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/?replicaSet=rs0"),
                         serverSelectionTimeoutMS=30000)
    db = client["shop_bench"]
    db.products.create_index([("category_id", 1)])
    db.orders.create_index([("customer_id", 1), ("order_date", -1), ("_id", -1)])
    db.orders.create_index([("order_date", 1)])
    db.orders.create_index([("status", 1), ("order_date", 1), ("_id", 1)])
    db.orders.create_index([("items.product_id", 1)])
    client.close()
    mongo_seconds = time.perf_counter() - started
    return {"mysql_index_build_seconds": mysql_seconds, "mongodb_index_build_seconds": mongo_seconds}

def mysql_run(conn, name):
    cur = conn.cursor()
    if name == "Q1":
        cur.execute("SELECT * FROM orders WHERE order_id=%s", (ORDER_ID,)); a = cur.fetchall()
        cur.execute("SELECT * FROM order_item WHERE order_id=%s ORDER BY line_no", (ORDER_ID,)); b = cur.fetchall()
        cur.execute("SELECT * FROM payment WHERE order_id=%s ORDER BY payment_id", (ORDER_ID,)); c = cur.fetchall()
        result = (a, b, c)
    else:
        sql = MYSQL_QUERIES[name]
        if name == "Q2": params = (CUSTOMER_ID,)
        elif name == "Q3": params = (DAY1, DAY2)
        elif name in ("Q5","Q6","Q8"): params = (D1, D2)
        elif name == "Q7": params = (ORDER_ID,)
        else: params = ()
        cur.execute(sql, params)
        result = cur.fetchall()
    cur.close()
    return result

def mongo_run(db, name):
    if name == "Q1":
        return db.orders.find_one({"_id": ORDER_ID})
    if name == "Q2":
        return list(db.orders.find({"customer_id": CUSTOMER_ID},
            {"order_date": 1, "status": 1}).sort([("order_date",-1),("_id",-1)]).limit(20))
    if name == "Q3":
        return list(db.orders.find({"order_date": {"$gte": datetime(2025,3,15,tzinfo=timezone.utc),
            "$lt": datetime(2025,3,22,tzinfo=timezone.utc)}, "status": "SHIPPED"},
            {"customer_id": 1, "order_date": 1, "status": 1}).sort([("order_date",1),("_id",1)]).limit(100))
    return list(db.orders.aggregate(MONGO_PIPELINES[name], allowDiskUse=True))

def system_info(mysql_conn, mongo_db, scale, mode):
    cur = mysql_conn.cursor()
    cur.execute("SELECT VERSION()")
    mysql_version = cur.fetchone()[0]
    cur.execute("""SELECT COALESCE(SUM(data_length+index_length),0),
                          COALESCE(SUM(data_length),0),COALESCE(SUM(index_length),0)
                   FROM information_schema.tables WHERE table_schema='shop_bench'""")
    mysql_sizes = cur.fetchone()
    cur.close()
    stats = mongo_db.command("dbStats")
    build = mongo_db.command("buildInfo")
    cpu = "unknown"
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                cpu = line.split(":",1)[1].strip()
                break
    except OSError:
        pass
    mem = "unknown"
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem = line.split(":",1)[1].strip()
                break
    except OSError:
        pass
    return {
        "scale": scale, "mode": mode, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "os": platform.platform(), "cpu": cpu, "logical_cpu_count": os.cpu_count(),
        "memory_total": mem, "python": platform.python_version(),
        "mysql_version": mysql_version, "mongodb_version": build["version"],
        "mysql_total_bytes": int(mysql_sizes[0]), "mysql_data_bytes": int(mysql_sizes[1]),
        "mysql_index_bytes": int(mysql_sizes[2]), "mongodb_storage_bytes": int(stats.get("storageSize",0)),
        "mongodb_index_bytes": int(stats.get("indexSize",0)),
        "warmups": WARMUPS, "measured_iterations": REPEATS, "concurrency": 1,
        "cache_policy": "warm cache after 5 warm-up executions; single client",
    }

def run_benchmark(scale, mode, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    mysql_conn = mysql.connector.connect(host=os.getenv("MYSQL_HOST","127.0.0.1"),
        port=int(os.getenv("MYSQL_PORT","3306")), user=os.getenv("MYSQL_USER","root"),
        password=os.getenv("MYSQL_PASSWORD","root"), database="shop_bench",
        connection_timeout=30)
    mongo_client = MongoClient(os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/?replicaSet=rs0"),
                               serverSelectionTimeoutMS=30000)
    mongo_db = mongo_client["shop_bench"]
    meta = system_info(mysql_conn, mongo_db, scale, mode)
    raw_path = out / f"raw_{mode}.csv"
    summary_path = out / f"summary_{mode}.csv"
    raw_rows, summary_rows = [], []
    for db_name, runner in [
        ("mysql", lambda q: mysql_run(mysql_conn, q)),
        ("mongodb", lambda q: mongo_run(mongo_db, q)),
    ]:
        for query in ["Q1","Q2","Q3","Q4","Q5","Q6","Q7","Q8"]:
            for _ in range(WARMUPS):
                runner(query)
            samples = []
            for iteration in range(1, REPEATS+1):
                start = time.perf_counter_ns()
                result = runner(query)
                elapsed = (time.perf_counter_ns()-start)/1_000_000
                samples.append(elapsed)
                raw_rows.append({"scale":scale,"mode":mode,"database":db_name,
                    "query":query,"iteration":iteration,"latency_ms":f"{elapsed:.6f}",
                    "result_count":len(result) if result is not None else 0})
            summary_rows.append({"scale":scale,"mode":mode,"database":db_name,"query":query,
                "iterations":len(samples),"mean_ms":f"{statistics.mean(samples):.6f}",
                "median_ms":f"{statistics.median(samples):.6f}",
                "p95_ms":f"{percentile(samples,.95):.6f}",
                "p99_ms":f"{percentile(samples,.99):.6f}",
                "min_ms":f"{min(samples):.6f}","max_ms":f"{max(samples):.6f}",
                "sequential_ops_per_second":f"{1000/statistics.mean(samples):.3f}"})
            print(f"{scale} {mode} {db_name} {query}: median={statistics.median(samples):.3f}ms p95={percentile(samples,.95):.3f}ms")
    with raw_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(raw_rows[0].keys())); w.writeheader(); w.writerows(raw_rows)
    with summary_path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(summary_rows[0].keys())); w.writeheader(); w.writerows(summary_rows)
    (out/f"meta_{mode}.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    mysql_conn.close()
    mongo_client.close()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--scale",required=True,choices=["s","m"])
    ap.add_argument("--mode",choices=["baseline","indexed"])
    ap.add_argument("--load-mongo",action="store_true")
    ap.add_argument("--build-indexes",action="store_true")
    ap.add_argument("--data-dir",default=None)
    ap.add_argument("--out",default="benchmark/results")
    a=ap.parse_args()
    if a.load_mongo:
        if not a.data_dir: ap.error("--load-mongo requires --data-dir")
        load_mongo(a.data_dir)
    elif a.build_indexes:
        result=build_indexes()
        Path(a.out).mkdir(parents=True,exist_ok=True)
        (Path(a.out)/"index_build.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
        print(json.dumps(result,indent=2))
    elif a.mode:
        run_benchmark(a.scale,a.mode,a.out)
    else:
        ap.error("Choose --load-mongo, --build-indexes or --mode")

if __name__=="__main__":
    main()
