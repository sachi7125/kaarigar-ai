"""SQLAlchemy models — the single system of record (PostgreSQL).

Tables: artisan, listing (unique|batch + remaining_count), offer (status, expiry),
follower (email only), issue_report, event.
Roadmap: Day 5. NOTE: the permanent listing/storefront URL id scheme is FROZEN once a
stall QR is printed — decide the id format here deliberately (watchlist).
"""
# TODO(day5): define models; stock decrement happens under a row lock in services/stock.py.

