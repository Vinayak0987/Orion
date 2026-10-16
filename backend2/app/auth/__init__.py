"""Authentication and user/website data layer.

Self-contained: depends only on `app.config` and third-party libraries
(argon2, PyJWT, pymongo/mongomock), never on the mission engine. User accounts
live in MongoDB (see store.py), distinct from the agent/mission data in SQLite.
"""
