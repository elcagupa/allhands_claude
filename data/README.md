# AlpenRail — Data Directory

Place your 8 Parquet files here **exactly as named below** before running anything.

## Required Files

| File | Expected rows | Primary key |
|---|---|---|
| `stations.parquet` | ~17 | station_code |
| `weather.parquet` | ~8,000 | date + canton |
| `journeys.parquet` | ~31,000 | journey_id |
| `passengers.parquet` | ~42,000 | passenger_id |
| `tickets.parquet` | ~660,000 | ticket_id |
| `onboard_sales.parquet` | ~228,000 | sale_id |
| `partner_bookings.parquet` | ~99,000 | booking_id |
| `campaigns.parquet` | 10 | campaign_id |

## Validate After Placing Files

```bash
python scripts/db.py
```

Or in a notebook:

```python
from scripts.db import audit
audit()
```
