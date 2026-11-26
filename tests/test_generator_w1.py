import csv
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / "04_generate_data.py"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def generate(out_dir):
    subprocess.run(
        [sys.executable, str(GENERATOR), "--orders", "1000", "--seed", "42", "--out", str(out_dir)],
        check=True,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
    )
    return out_dir / "custom_1000"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.reader(f))


def audit(base):
    mysql = base / "mysql"
    inventory = {(int(row[0]), int(row[1])) for row in read_csv(mysql / "inventory.csv")}
    orders = {int(row[0]): int(row[2]) for row in read_csv(mysql / "orders.csv")}
    items = read_csv(mysql / "order_item.csv")

    seen = set()
    for row in items:
        order_id, product_id = int(row[0]), int(row[2])
        key = (order_id, product_id)
        assert key not in seen, "duplicate product within order: %r" % (key,)
        seen.add(key)
        assert order_id in orders, "order item references unknown order: %s" % order_id
        store_id = orders[order_id]
        assert (store_id, product_id) in inventory, (
            "missing store inventory row: order=%s store=%s product=%s"
            % (order_id, store_id, product_id)
        )

    manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["orders"] == 1000
    assert manifest["counts"]["order_item"] == len(items)
    assert manifest["orders_with_missing_inventory"] == 0
    assert manifest["order_items_with_missing_inventory"] == 0
    assert len(orders) == 1000
    assert 1000 <= len(items) <= 8000
    return {
        "orders": len(orders),
        "order_items": len(items),
        "inventory_rows": len(inventory),
        "missing_inventory_items": 0,
    }


def main():
    with tempfile.TemporaryDirectory(prefix="hqtcsql-generator-") as temp:
        root = Path(temp)
        first = generate(root / "run1")
        second = generate(root / "run2")
        result = audit(first)
        audit(second)

        files1 = sorted(p.relative_to(first) for p in first.rglob("*") if p.is_file() and p.name != "manifest.json")
        files2 = sorted(p.relative_to(second) for p in second.rglob("*") if p.is_file() and p.name != "manifest.json")
        assert files1 == files2, "generated file sets differ"
        for relative in files1:
            assert sha256(first / relative) == sha256(second / relative), (
                "non-deterministic generated file: %s" % relative
            )

        print("PASS: generator pilot, inventory integrity, unique order lines, and deterministic CSV/JSONL")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
