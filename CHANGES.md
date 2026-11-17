# Changes: Vendor history filtering and search

Added searchable document history and dashboard filters for reviewing past spending patterns.

## Added

- Dashboard vendor search by partial vendor name.
- Verdict filter for `normal`, `review`, and `unusual` documents.
- Minimum and maximum amount range filters.
- Filter summary and clear-filter link in the dashboard UI.
- Query-string preserving history links so review context is visible in the browser URL.
- Vendor normalization helper in the parser service for more consistent vendor matching/search.
- Database indexes on commonly filtered `Document` fields.
- Detail page link to quickly search history for the current document vendor.

## Modified files

- `app/main.py` wires filter query params into the dashboard database query.
- `app/templates/index.html` adds the search/filter form and filtered-state messaging.
- `app/templates/detail.html` adds a vendor-history shortcut.
- `app/services/parser.py` normalizes parsed vendor names.
- `app/models.py` adds indexes for dashboard filtering fields.

## Integration

No new dependencies or migrations are required for the MVP. Existing SQLite databases continue to work; indexes are created automatically by SQLAlchemy metadata creation on app startup for new databases. To run:

```bash
uvicorn app.main:app --reload
```
