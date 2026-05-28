import csv
import json

CSV_PATH = "data/Brigade_Bangalore_10_April_26 (1).csv"
OUTPUT_PATH = "data/pos_events.jsonl"
STORE_CODE = "STORE_BLR_002"

rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))

seen_invoices = set()
events = []

for row in rows:
    invoice = row.get("invoice_number")
    if invoice and invoice not in seen_invoices:
        seen_invoices.add(invoice)
        date = row.get("order_date", "")
        time = row.get("order_time", "")
        events.append({
            "event_type": "purchase",
            "store_code": STORE_CODE,
            "camera_id": "POS",
            "event_timestamp": f"{date} {time}",
            "invoice_number": invoice,
            "is_staff": False,
        })

with open(OUTPUT_PATH, "w") as f:
    for e in events:
        f.write(json.dumps(e) + "\n")

print(f"DONE. Generated {len(events)} unique purchase events.")
print(f"(Total rows in CSV: {len(rows)}, deduplicated to unique invoices)")
print(f"Saved -> {OUTPUT_PATH}")