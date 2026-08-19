CLEAN_SHIPMENTS = [
    {
        "shipment_id": "SHO0013",
        "carrier": "FEDEX",
        "ship_date": "02/02/2024",
        "status": "Delayed",
        "origin": "Pune",
        "destination": "Bangalore",
        "freight_cost": 357.1,
        "expected_delivery_date": "08/02/2024",
        "delivered_date": "11/02/2024",
        "delay_days": 182.0,
    },
    {
        "shipment_id": "SHO0018",
        "carrier": "DHL",
        "ship_date": "05/20/2024",
        "status": "Delayed",
        "origin": "Pune",
        "destination": "Chennai",
        "freight_cost": 101.25,
        "expected_delivery_date": "05/26/2024",
        "delivered_date": "05/27/2024",
        "delay_days": 6.0,
    },
    {
        "shipment_id": "SHO0029",
        "carrier": "DHL",
        "ship_date": "01/07/2024",
        "status": "Delayed",
        "origin": "Hyderabad",
        "destination": "Chennai",
        "freight_cost": 389.36,
        "expected_delivery_date": "01/11/2024",
        "delivered_date": "01/18/2024",
        "delay_days": 4.0,
    },
    {
        "shipment_id": "SHO0031",
        "carrier": "FEDEX",
        "ship_date": "04/12/2024",
        "status": "Delivered",
        "origin": "Delhi",
        "destination": "Bangalore",
        "freight_cost": 492.08,
        "expected_delivery_date": "04/18/2024",
        "delivered_date": "04/21/2024",
        "delay_days": 6.0,
    },
    {
        "shipment_id": "SHO0048",
        "carrier": "FEDEX",
        "ship_date": "04/04/2024",
        "status": "Delayed",
        "origin": "Bangalore",
        "destination": "Delhi",
        "freight_cost": 334.47,
        "expected_delivery_date": "04/11/2024",
        "delivered_date": "04/13/2024",
        "delay_days": 7.0,
    },
    {
        "shipment_id": "SHO0056",
        "carrier": "BLUEDART",
        "ship_date": "01/31/2024",
        "status": "Delivered",
        "origin": "Hyderabad",
        "destination": "Mumbai",
        "freight_cost": 305.06,
        "expected_delivery_date": "02/07/2024",
        "delivered_date": "07/02/2024",
        "delay_days": 7.0,
    },
    {
        "shipment_id": "SHO0062",
        "carrier": "DHL",
        "ship_date": "04/25/2024",
        "status": "Delivered",
        "origin": "Pune",
        "destination": "Chennai",
        "freight_cost": 329.4,
        "expected_delivery_date": "04/29/2024",
        "delivered_date": "04/27/2024",
        "delay_days": 4.0,
    },
    {
        "shipment_id": "SHO0063",
        "carrier": "BLUEDART",
        "ship_date": "04/18/2024",
        "status": "Delayed",
        "origin": "Chennai",
        "destination": "Hyderabad",
        "freight_cost": 308.72,
        "expected_delivery_date": "04/25/2024",
        "delivered_date": "04/28/2024",
        "delay_days": 7.0,
    },
    {
        "shipment_id": "SHO0082",
        "carrier": "BLUEDART",
        "ship_date": "04/06/2024",
        "status": "Delivered",
        "origin": "Bangalore",
        "destination": "Pune",
        "freight_cost": 288.63,
        "expected_delivery_date": "06/08/2024",
        "delivered_date": "06/09/2024",
        "delay_days": 63.0,
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

        delayed_count = sum(1 for r in group_records if r.get("status") == "Delayed")

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
