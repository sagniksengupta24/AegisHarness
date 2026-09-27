# Python Stack Rules for Aegis

1. Follow PEP 8 and use type annotations for all function and method signatures.
2. Keep dependencies minimal and specify them in `pyproject.toml`.
3. Never use wildcard imports (`from module import *`).
4. Ensure all unit and integration tests run deterministically under `pytest`.
5. Use context managers (`with`) for file operations and network sockets.
