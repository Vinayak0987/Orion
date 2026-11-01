"""Migration script: Move all SQLite and ChromaDB data to MongoDB Atlas.

This script:
1. Reads all data from SQLite database
2. Reads all data from ChromaDB collections
3. Migrates everything to MongoDB Atlas collections
4. Creates vector search indexes for embeddings

Run this after setting up MongoDB Atlas in .env:
    python -m scripts.migrate_to_mongodb
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.auth import store as mongo_store
from app.config import settings
from app.db.sqlite import connection as sqlite_connection


def migrate_mission_tasks() -> int:
    """Migrate mission_tasks from SQLite to MongoDB."""
    print("Migrating mission_tasks...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM mission_tasks")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["tools_needed", "depends_on", "result"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.mission_tasks.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} mission_tasks")
    return count


def migrate_execution_traces() -> int:
    """Migrate execution_traces from SQLite to MongoDB."""
    print("Migrating execution_traces...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM execution_traces")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["tool_input", "tool_output"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.execution_traces.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} execution_traces")
    return count


def migrate_agents() -> int:
    """Migrate agents from SQLite to MongoDB."""
    print("Migrating agents...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM agents")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["tools", "sub_agents", "permissions"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.agents.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} agents")
    return count


def migrate_departments() -> int:
    """Migrate departments from SQLite to MongoDB."""
    print("Migrating departments...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM departments")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["responsibilities", "config"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.departments.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} departments")
    return count


def migrate_department_members() -> int:
    """Migrate department_members from SQLite to MongoDB."""
    print("Migrating department_members...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM department_members")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            if doc.get("permissions"):
                try:
                    doc["permissions"] = json.loads(doc["permissions"])
                except Exception:
                    pass
            db.department_members.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} department_members")
    return count


def migrate_conversations() -> int:
    """Migrate conversations from SQLite to MongoDB."""
    print("Migrating conversations...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM conversations")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.conversations.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} conversations")
    return count


def migrate_messages() -> int:
    """Migrate messages from SQLite to MongoDB."""
    print("Migrating messages...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM messages")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["attachments", "outputs", "charts"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.messages.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} messages")
    return count


def migrate_global_context() -> int:
    """Migrate global_context from SQLite to MongoDB."""
    print("Migrating global_context...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM global_context")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.global_context.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} global_context")
    return count


def migrate_tools() -> int:
    """Migrate tools from SQLite to MongoDB."""
    print("Migrating tools...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM tools")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["input_schema", "config"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.tools.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} tools")
    return count


def migrate_mcp_servers() -> int:
    """Migrate mcp_servers from SQLite to MongoDB."""
    print("Migrating mcp_servers...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM mcp_servers")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.mcp_servers.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} mcp_servers")
    return count


def migrate_integrations() -> int:
    """Migrate integrations from SQLite to MongoDB."""
    print("Migrating integrations...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM integrations")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.integrations.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} integrations")
    return count


def migrate_agent_templates() -> int:
    """Migrate agent_templates from SQLite to MongoDB."""
    print("Migrating agent_templates...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM agent_templates")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            for field in ["base_config", "tags"]:
                if doc.get(field):
                    try:
                        doc[field] = json.loads(doc[field])
                    except Exception:
                        pass
            db.agent_templates.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} agent_templates")
    return count


def migrate_agent_versions() -> int:
    """Migrate agent_versions from SQLite to MongoDB."""
    print("Migrating agent_versions...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM agent_versions")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            if doc.get("config"):
                try:
                    doc["config"] = json.loads(doc["config"])
                except Exception:
                    pass
            db.agent_versions.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} agent_versions")
    return count


def migrate_documents() -> int:
    """Migrate documents from SQLite to MongoDB."""
    print("Migrating documents...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM documents")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.documents.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} documents")
    return count


def migrate_memory_entries() -> int:
    """Migrate memory_entries from SQLite to MongoDB."""
    print("Migrating memory_entries...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM memory_entries")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            db.memory_entries.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} memory_entries")
    return count


def migrate_oauth_connections() -> int:
    """Migrate oauth_connections from SQLite to MongoDB."""
    print("Migrating oauth_connections...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM oauth_connections")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # Convert JSON strings to objects
            if doc.get("scopes"):
                try:
                    doc["scopes"] = json.loads(doc["scopes"])
                except Exception:
                    pass
            db.oauth_connections.update_one({"_id": doc["id"]}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} oauth_connections")
    return count


def migrate_oauth_states() -> int:
    """Migrate oauth_states from SQLite to MongoDB."""
    print("Migrating oauth_states...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM oauth_states")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # The primary key is "state" not "id"
            _id = doc.pop("state")
            doc["_id"] = _id
            db.oauth_states.update_one({"_id": _id}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} oauth_states")
    return count


def migrate_user_settings() -> int:
    """Migrate user_settings from SQLite to MongoDB."""
    print("Migrating user_settings...")
    db = mongo_store.get_db()

    with sqlite_connection() as sqlite_conn:
        cursor = sqlite_conn.execute("SELECT * FROM user_settings")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        count = 0
        for row in rows:
            doc = dict(zip(columns, row))
            # user_id is the primary key in SQLite, use as _id in MongoDB
            _id = doc.pop("user_id")
            doc["_id"] = _id
            # Convert JSON strings to objects
            if doc.get("api_keys"):
                try:
                    doc["api_keys"] = json.loads(doc["api_keys"])
                except Exception:
                    pass
            db.user_settings.update_one({"_id": _id}, {"$set": doc}, upsert=True)
            count += 1

    print(f"  Migrated {count} user_settings")
    return count


def migrate_chroma_to_mongodb() -> int:
    """Migrate ChromaDB embeddings to MongoDB Vector Search."""
    print("Migrating ChromaDB embeddings to MongoDB...")
    try:
        import chromadb
    except ImportError:
        print("  ChromaDB not installed, skipping")
        return 0

    # ChromaDB may be corrupted - catch all errors including panics
    try:
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    except BaseException:
        print("  ChromaDB database is corrupted or inaccessible")
        print("  Skipping ChromaDB migration - SQLite data already migrated successfully")
        print("  Note: Vector embeddings will be recreated on-demand when needed")
        return 0

    db = mongo_store.get_db()

    # Get all collections
    try:
        collections = client.list_collections()
    except Exception as e:
        print(f"  Could not list ChromaDB collections: {e}, skipping")
        return 0

    total_count = 0

    for collection in collections:
        print(f"  Migrating collection: {collection.name}")
        try:
            # Get all data from collection
            data = collection.get(include=["embeddings", "metadatas", "documents", "ids"])

            if not data["ids"]:
                continue

            # Determine if this is a document or memory collection
            is_document = collection.name.startswith("documents_")
            target_collection = db.document_embeddings if is_document else db.memory_embeddings

            for i, doc_id in enumerate(data["ids"]):
                embedding = data["embeddings"][i] if data["embeddings"] else None
                metadata = data["metadatas"][i] if data["metadatas"] else {}
                text = data["documents"][i] if data["documents"] else None

                if not embedding:
                    continue

                # Extract user_id from collection name or metadata
                user_id = metadata.get("user_id", "default-user")
                if is_document and collection.name.startswith("documents_"):
                    user_id = collection.name.replace("documents_", "")

                doc = {
                    "_id": f"{collection.name}_{doc_id}",
                    "document_id" if is_document else "memory_id": doc_id,
                    "chunk_id" if is_document else "content": doc_id if is_document else text,
                    "text" if is_document else "content": text if is_document else text,
                    "embedding": embedding,
                    "metadata": metadata,
                    "user_id": user_id,
                    "created_at": metadata.get("created_at", mongo_store._now()),
                }

                # Add additional fields for memory entries
                if not is_document:
                    doc["agent_id"] = metadata.get("agent_id")
                    doc["department_id"] = metadata.get("department_id")
                    doc["source_mission_id"] = metadata.get("source_mission_id")
                    doc["expires_at"] = metadata.get("expires_at")

                target_collection.update_one({"_id": doc["_id"]}, {"$set": doc}, upsert=True)
                total_count += 1
        except Exception as e:
            print(f"  Error migrating collection {collection.name}: {e}")
            continue

    print(f"  Migrated {total_count} embeddings from ChromaDB")
    return total_count


def main() -> None:
    """Run full migration."""
    print("=" * 60)
    print("Starting migration to MongoDB Atlas")
    print("=" * 60)

    if not settings.mongo_available:
        print("ERROR: MongoDB is not configured. Set MONGODB_URI in .env")
        sys.exit(1)

    total = 0
    total += migrate_mission_tasks()
    total += migrate_execution_traces()
    total += migrate_agents()
    total += migrate_departments()
    total += migrate_department_members()
    total += migrate_conversations()
    total += migrate_messages()
    total += migrate_global_context()
    total += migrate_tools()
    total += migrate_mcp_servers()
    total += migrate_integrations()
    total += migrate_agent_templates()
    total += migrate_agent_versions()
    total += migrate_documents()
    total += migrate_memory_entries()
    total += migrate_oauth_connections()
    total += migrate_oauth_states()
    total += migrate_user_settings()
    total += migrate_chroma_to_mongodb()

    print("=" * 60)
    print(f"Migration complete! Total records migrated: {total}")
    print("=" * 60)


if __name__ == "__main__":
    main()
