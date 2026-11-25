"""Write examples/orders_batch.jsonl: 2,000 order events, a few of them violating the contract."""
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

rnd = random.Random(0)
out = Path(__file__).with_name("orders_batch.jsonl")
with out.open("w") as f:
    for i in range(2000):
        rec = {
            "order_id": f"O{i:07d}", "customer_id": f"C{rnd.randint(1, 900)}",
            "created_at": (datetime(2025, 11, 1) + timedelta(minutes=i * 7)).isoformat(),
            "status": rnd.choice(["placed", "paid", "shipped"]), "amount": round(rnd.uniform(5, 1300), 2),
            "currency": "USD", "channel": rnd.choice(["web", "app", "store"]),
        }
        if i % 250 == 7:
            rec["status"] = "on_hold"          # producer shipped a new status before the contract allowed it
        if i % 400 == 11:
            rec["amount"] = -rec["amount"]     # refunds sent as negative orders
        if i % 500 == 3:
            rec["currency"] = "CAD"
        if i % 666 == 5:
            del rec["channel"]
        f.write(json.dumps(rec) + "\n")
print(f"wrote {out}")
