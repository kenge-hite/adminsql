"""Launcher used both for `python run.py` and as the PyInstaller entry point."""

from app.main import main

if __name__ == "__main__":
    raise SystemExit(main())
