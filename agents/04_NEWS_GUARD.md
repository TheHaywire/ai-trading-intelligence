# Role: News Guard & Calendars
Block openings/closings in ±4 minutes (240s) window around major events for *impacted symbols*, unless add-on is enabled or program exempt.

## Tasks
- `news_guard.py`:
  - load calendars from `news_events_seed.json`
  - function impacted(symbol) -> set of economies
  - is_blocked(symbol, ts, add_on_enabled) -> bool
  - upcoming_blocks(symbol, now, horizon)
- `utils/calendars.py` helpers for time windows & symbol→economy mapping.
- Apply only to directly affected instruments (e.g., USD news → USD pairs, US indices/commodities if configured).

Provide minimal seed JSON and mapping logic; allow operator overrides.
