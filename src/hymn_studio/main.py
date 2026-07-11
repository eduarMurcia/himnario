from __future__ import annotations

import sys

from hymn_studio.app import create_app


def main() -> int:
    app = create_app(sys.argv)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
