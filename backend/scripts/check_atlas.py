from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db import get_db  # noqa: E402


def main() -> None:
    db = get_db()
    db.command("ping")
    required = ["courses", "sections", "students", "payments", "enrollment_requests", "agent_verdicts", "notifications", "audit_events"]
    counts = {name: db[name].count_documents({}) for name in required}
    failures = [name for name, count in counts.items() if count == 0]
    print(json.dumps({"database": db.name, "counts": counts, "healthy": not failures, "empty_collections": failures}, ensure_ascii=False, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
