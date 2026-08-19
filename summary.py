CLEAN_SHIPMENTS = [
    {
        "shipment_id": "SH00001",
        "carrier": "DHL",
        "ship_date": "27/01/2024",
        "status": "Delayed",
        "origin": "Pune",
        "destination": "Bangalore",
        "freight_cost": 89.12,
        "expected_delivery_date": "27/01/2024",
        "delivered_date": "27/01/2024",
        "delay_days": 0.0,
    },
    {
        "shipment_id": "SH00007",
        "carrier": "DHL",
        "ship_date": "12/06/2024",
        "status": "In Transit",
        "origin": "Delhi",
        "destination": "Pune",
        "freight_cost": 358.08,
        "expected_delivery_date": "12/06/2024",
        "delivered_date": "12/06/2024",
        "delay_days": 0.0,
    },
    {
        "shipment_id": "SH00010",
        "carrier": "DHL",
        "ship_date": "13/01/2024",
        "status": "Delivered",
        "origin": "Chennai",
        "destination": "Pune",
        "freight_cost": 332.35,
        "expected_delivery_date": "27/01/2024",
        "delivered_date": "27/01/2024",
        "delay_days": 0.0,
    },
]


def compute_carrier_summary(records: list[dict]) -> list[dict]:
    groups = {}

    for record in records:
        carrier = record.get("carrier")
        if carrier not in groups:
            groups[carrier] = []
        groups[carrier].append(record)

    summary = []

    for carrier, group_records in groups.items():
        shipment_count = len(group_records)

        total_freight_cost = sum(
            r.get("freight_cost")
            for r in group_records
            if r.get("freight_cost") is not None
        )

        delayed_count = sum(
            1 for r in group_records if r.get("status") == "Delayed"
        )

        avg_delay_days = round(
            sum(r.get("delay_days", 0) for r in group_records) / shipment_count, 1
        )

        summary.append(
            {
                "carrier": carrier,
                "shipment_count": shipment_count,
                "total_freight_cost": round(total_freight_cost, 2),
                "delayed_count": delayed_count,
                "avg_delay_days": avg_delay_days,
            }
        )

    return summary


if __name__ == "__main__":
    print("=== SHIPMENT RECORDS ===")
    for record in CLEAN_SHIPMENTS:
        print(record)

    print("\n=== CARRIER SUMMARY ===")
    summary = compute_carrier_summary(CLEAN_SHIPMENTS)

    for item in summary:
        print(item)