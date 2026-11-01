# Legacy SQLite Database

**Status: LEGACY - DO NOT USE FOR PRIMARY STORAGE**

This directory contains legacy SQLite databases that are no longer used for primary storage.

## Migration Status

- ✅ **All data migrated to MongoDB Atlas**
- ✅ **MongoDB Atlas is the primary storage backend**
- ✅ **3,905 documents across 28 collections in MongoDB**

## Current Purpose

SQLite files in this directory are kept for:

1. **Test isolation** - Tests use local SQLite for fast, isolated test runs
2. **Migration scripts** - One-time tools to migrate data from SQLite to MongoDB
3. **Local tool databases** - The `localdb` tool creates SQLite DBs for agent-specific data
4. **Backward compatibility** - Some legacy code paths still reference SQLite

## Files

- `orion2.db` - Legacy main database (migrated to MongoDB, kept as backup)
- `chroma2/` - Legacy ChromaDB vector store (migrated to MongoDB vector search)

## MongoDB Atlas

All production data now lives in MongoDB Atlas:
- Database: `orion_app`
- Collections: 28 (agents, departments, missions, users, conversations, etc.)
- Vector Search: Document and memory embeddings

## Migration Date

November 1, 2026
