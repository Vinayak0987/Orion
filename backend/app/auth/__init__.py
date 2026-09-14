"""Authentication and user/website data layer.

This package is self-contained: it depends only on `app.config` and third-party
libraries (argon2, PyJWT, pymongo/mongomock), never on the agent stack
(langgraph/chromadb/structlog). That keeps its tests runnable offline in
isolation and means auth changes cannot regress the generation/operating suite.

Data separation: user accounts live in MongoDB (see `store.py`), distinct from
the agent data in SQLite (`app.db.sqlite`) and ChromaDB.
"""
