from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / 'backend'
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.stores.puzzle_store import build_puzzle_store  # noqa: E402
from app.stores.session_store import build_session_store  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Clean up expired cryptic-solver runtime data.')
    parser.add_argument('--session-ttl-hours', type=int, default=168, help='Remove sessions older than this many hours since last update. Default: 168 (7 days).')
    parser.add_argument('--import-ttl-hours', type=int, default=168, help='Remove imported puzzle directories older than this many hours. Default: 168 (7 days).')
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    session_store = build_session_store(REPO_ROOT)
    puzzle_store = build_puzzle_store(REPO_ROOT)

    removed_sessions = session_store.cleanup_expired(args.session_ttl_hours)
    removed_imports = puzzle_store.cleanup_expired_imports(args.import_ttl_hours)

    print(f'removed_sessions={removed_sessions}')
    print(f'removed_imports={removed_imports}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
