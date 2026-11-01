"""Migrate SQLite data to MongoDB.

This script transfers:
- Missions from SQLite missions table to MongoDB missions collection
- Mission tasks from SQLite mission_tasks table to MongoDB mission_tasks collection
- Execution traces from SQLite execution_traces table to MongoDB execution_traces collection
- Departments from SQLite departments table to MongoDB departments collection
- Department members from SQLite department_members table to MongoDB department_members collection
- Agents from SQLite agents table to MongoDB agents collection
- Conversations from SQLite conversations table to MongoDB conversations collection
- Messages from SQLite messages table to MongoDB messages collection
- Global context from SQLite global_context table to MongoDB global_context collection
- Tools from SQLite tools table to MongoDB tools collection
- MCP servers from SQLite mcp_servers table to MongoDB mcp_servers collection
- Integrations from SQLite integrations table to MongoDB integrations collection
- Documents from SQLite documents table to MongoDB documents collection
- Memory entries from SQLite memory_entries table to MongoDB memory_entries collection
- OAuth connections from SQLite oauth_connections table to MongoDB oauth_connections collection

Run this once to migrate your data.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.db.sqlite import connection
from app.auth import store as auth_store


def migrate_missions():
    """Migrate missions from SQLite to MongoDB."""
    print("Migrating missions...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM missions").fetchall()
        print(f"Found {len(rows)} missions in SQLite")

    for row in rows:
        mission = dict(row)
        mission_id = mission.get("id") or mission.get("_id")
        if not mission_id:
            continue

        # Check if already exists in MongoDB
        existing = auth_store.get_mission(mission_id, mission.get("created_by", "default-user"))
        if existing:
            print(f"  Skipping {mission_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.create_mission(
                mission_id=mission_id,
                user_id=mission.get("created_by", "default-user"),
                prompt=mission.get("prompt", ""),
                title=mission.get("title"),
                department_id=mission.get("department_id"),
                conversation_id=mission.get("conversation_id"),
                mode=mission.get("mode", "action"),
            )
            # Update with additional fields not in create_mission signature
            import json
            updates = {}
            if mission.get("status"):
                updates["status"] = mission.get("status")
            if mission.get("created_at"):
                updates["created_at"] = mission.get("created_at")
            if mission.get("completed_at"):
                updates["completed_at"] = mission.get("completed_at")
            if updates:
                auth_store.update_mission(mission_id, **updates)
            print(f"  Migrated {mission_id}")
        except Exception as e:
            print(f"  Error migrating {mission_id}: {e}")


def migrate_departments():
    """Migrate departments from SQLite to MongoDB."""
    print("\nMigrating departments...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM departments").fetchall()
        print(f"Found {len(rows)} departments in SQLite")

    for row in rows:
        dept = dict(row)
        dept_id = dept.get("id") or dept.get("_id")
        if not dept_id:
            continue

        # Check if already exists (auth_store.get_department only takes dept_id)
        existing = auth_store.get_department(dept_id)
        if existing:
            print(f"  Skipping {dept_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.create_department(
                department_id=dept_id,
                created_by=dept.get("created_by", "default-user"),
                name=dept.get("name", ""),
                description=dept.get("description", ""),
                purpose=dept.get("purpose", ""),
                responsibilities=dept.get("responsibilities", []),
                dept_type=dept.get("dept_type", "custom"),
                instructions=dept.get("instructions", ""),
                status=dept.get("status", "active"),
            )
            print(f"  Migrated {dept_id}")
        except Exception as e:
            print(f"  Error migrating {dept_id}: {e}")


def migrate_agents():
    """Migrate agents from SQLite to MongoDB."""
    print("\nMigrating agents...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM agents").fetchall()
        print(f"Found {len(rows)} agents in SQLite")

    for row in rows:
        agent = dict(row)
        agent_id = agent.get("id") or agent.get("_id")
        if not agent_id:
            continue

        # Check if already exists
        existing = auth_store.get_agent(agent_id)
        if existing:
            print(f"  Skipping {agent_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            tools = agent.get("tools", "[]")
            if isinstance(tools, str):
                tools = json.loads(tools)
            sub_agents = agent.get("sub_agents", "[]")
            if isinstance(sub_agents, str):
                sub_agents = json.loads(sub_agents)
            permissions = agent.get("permissions", "{}")
            if isinstance(permissions, str):
                permissions = json.loads(permissions)

            auth_store.create_agent(
                agent_id=agent_id,
                name=agent.get("name", ""),
                system_prompt=agent.get("system_prompt", ""),
                agent_type=agent.get("agent_type", "general"),
                model=agent.get("model", "groq:llama-3.1-8b-instant"),
                temperature=agent.get("temperature", 0.7),
                tools=tools,
                sub_agents=sub_agents,
                department_id=agent.get("department_id"),
                created_by=agent.get("created_by", "default-user"),
                origin=agent.get("origin", "reusable"),
                role_title=agent.get("role_title"),
            )
            print(f"  Migrated {agent_id}")
        except Exception as e:
            print(f"  Error migrating {agent_id}: {e}")


def migrate_mission_tasks():
    """Migrate mission tasks from SQLite to MongoDB."""
    print("\nMigrating mission tasks...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM mission_tasks").fetchall()
        print(f"Found {len(rows)} mission tasks in SQLite")

    for row in rows:
        task = dict(row)
        task_id = task.get("id") or task.get("_id")
        if not task_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().mission_tasks.find_one({"_id": task_id})
        if existing:
            print(f"  Skipping {task_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            tools_needed = task.get("tools_needed", "[]")
            if isinstance(tools_needed, str):
                tools_needed = json.loads(tools_needed)
            depends_on = task.get("depends_on", "[]")
            if isinstance(depends_on, str):
                depends_on = json.loads(depends_on)
            result = task.get("result")
            if isinstance(result, str):
                result = json.loads(result) if result else None

            auth_store.create_mission_task(
                task_id=task_id,
                mission_id=task.get("mission_id"),
                title=task.get("title", ""),
                agent_type=task.get("agent_type", "general"),
                agent_id=task.get("agent_id"),
                tools_needed=tools_needed,
                depends_on=depends_on,
                status=task.get("status", "pending"),
            )
            # Update with result if exists
            if result:
                auth_store.update_mission_task(task_id, result=result)
            if task.get("completed_at"):
                auth_store.update_mission_task(task_id, completed_at=task.get("completed_at"))
            print(f"  Migrated {task_id}")
        except Exception as e:
            print(f"  Error migrating {task_id}: {e}")


def migrate_execution_traces():
    """Migrate execution traces from SQLite to MongoDB."""
    print("\nMigrating execution traces...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM execution_traces").fetchall()
        print(f"Found {len(rows)} execution traces in SQLite")

    for row in rows:
        trace = dict(row)
        trace_id = trace.get("id") or trace.get("_id")
        if not trace_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().execution_traces.find_one({"_id": trace_id})
        if existing:
            print(f"  Skipping {trace_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            tool_input = trace.get("tool_input")
            if isinstance(tool_input, str):
                tool_input = json.loads(tool_input) if tool_input else None
            tool_output = trace.get("tool_output")
            if isinstance(tool_output, str):
                tool_output = json.loads(tool_output) if tool_output else None

            auth_store.create_execution_trace(
                trace_id=trace_id,
                mission_id=trace.get("mission_id"),
                task_id=trace.get("task_id"),
                agent_id=trace.get("agent_id"),
                trace_type=trace.get("trace_type"),
                provider=trace.get("provider"),
                model=trace.get("model"),
                input_tokens=trace.get("input_tokens"),
                output_tokens=trace.get("output_tokens"),
                cost_usd=trace.get("cost_usd"),
                tool_name=trace.get("tool_name"),
                tool_input=tool_input,
                tool_output=tool_output,
                latency_ms=trace.get("latency_ms"),
                success=bool(trace.get("success", 1)),
                error_message=trace.get("error_message"),
            )
            print(f"  Migrated {trace_id}")
        except Exception as e:
            print(f"  Error migrating {trace_id}: {e}")


def migrate_department_members():
    """Migrate department members from SQLite to MongoDB."""
    print("\nMigrating department members...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM department_members").fetchall()
        print(f"Found {len(rows)} department members in SQLite")

    for row in rows:
        member = dict(row)
        member_id = member.get("id") or member.get("_id")
        if not member_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().department_members.find_one({"_id": member_id})
        if existing:
            print(f"  Skipping {member_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            permissions = member.get("permissions", "{}")
            if isinstance(permissions, str):
                permissions = json.loads(permissions)

            auth_store.create_department_member(
                member_id=member_id,
                department_id=member.get("department_id"),
                agent_id=member.get("agent_id"),
                role=member.get("role", "specialist"),
                status=member.get("status", "active"),
                instructions=member.get("instructions", ""),
                permissions=permissions,
            )
            print(f"  Migrated {member_id}")
        except Exception as e:
            print(f"  Error migrating {member_id}: {e}")


def migrate_conversations():
    """Migrate conversations from SQLite to MongoDB."""
    print("\nMigrating conversations...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM conversations").fetchall()
        print(f"Found {len(rows)} conversations in SQLite")

    for row in rows:
        conv = dict(row)
        conv_id = conv.get("id") or conv.get("_id")
        if not conv_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().conversations.find_one({"_id": conv_id})
        if existing:
            print(f"  Skipping {conv_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.create_conversation(
                conversation_id=conv_id,
                title=conv.get("title", "New chat"),
                created_by=conv.get("created_by", "default-user"),
            )
            print(f"  Migrated {conv_id}")
        except Exception as e:
            print(f"  Error migrating {conv_id}: {e}")


def migrate_messages():
    """Migrate messages from SQLite to MongoDB."""
    print("\nMigrating messages...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM messages").fetchall()
        print(f"Found {len(rows)} messages in SQLite")

    for row in rows:
        msg = dict(row)
        msg_id = msg.get("id") or msg.get("_id")
        if not msg_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().messages.find_one({"_id": msg_id})
        if existing:
            print(f"  Skipping {msg_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            attachments = msg.get("attachments", "[]")
            if isinstance(attachments, str):
                attachments = json.loads(attachments)
            outputs = msg.get("outputs", "[]")
            if isinstance(outputs, str):
                outputs = json.loads(outputs)
            charts = msg.get("charts", "[]")
            if isinstance(charts, str):
                charts = json.loads(charts)

            auth_store.create_message(
                message_id=msg_id,
                conversation_id=msg.get("conversation_id"),
                role=msg.get("role"),
                content=msg.get("content", ""),
                mission_id=msg.get("mission_id"),
                attachments=attachments,
                outputs=outputs,
                status=msg.get("status", "done"),
            )
            # Update with charts if exists
            if charts:
                auth_store.update_message(msg_id, charts=charts)
            print(f"  Migrated {msg_id}")
        except Exception as e:
            print(f"  Error migrating {msg_id}: {e}")


def migrate_global_context():
    """Migrate global context from SQLite to MongoDB."""
    print("\nMigrating global context...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM global_context").fetchall()
        print(f"Found {len(rows)} global context entries in SQLite")

    for row in rows:
        ctx = dict(row)
        ctx_id = ctx.get("id") or ctx.get("_id")
        if not ctx_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().global_context.find_one({"user_id": ctx.get("user_id"), "key": ctx.get("key")})
        if existing:
            print(f"  Skipping {ctx.get('user_id')}/{ctx.get('key')} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.set_global_context(
                context_id=ctx_id,
                user_id=ctx.get("user_id", "default-user"),
                key=ctx.get("key"),
                value=ctx.get("value"),
            )
            print(f"  Migrated {ctx.get('user_id')}/{ctx.get('key')}")
        except Exception as e:
            print(f"  Error migrating {ctx.get('user_id')}/{ctx.get('key')}: {e}")


def migrate_tools():
    """Migrate tools from SQLite to MongoDB."""
    print("\nMigrating tools...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM tools").fetchall()
        print(f"Found {len(rows)} tools in SQLite")

    for row in rows:
        tool = dict(row)
        tool_id = tool.get("id") or tool.get("_id")
        if not tool_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().tools.find_one({"_id": tool_id})
        if existing:
            print(f"  Skipping {tool_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            input_schema = tool.get("input_schema", "{}")
            if isinstance(input_schema, str):
                input_schema = json.loads(input_schema)
            config = tool.get("config", "{}")
            if isinstance(config, str):
                config = json.loads(config)

            doc = {
                "_id": tool_id,
                "name": tool.get("name"),
                "display_name": tool.get("display_name"),
                "description": tool.get("description"),
                "type": tool.get("type", "builtin"),
                "category": tool.get("category", "utility"),
                "input_schema": input_schema,
                "config": config,
                "enabled": bool(tool.get("enabled", 1)),
                "requires_key": tool.get("requires_key"),
                "degraded": bool(tool.get("degraded", 0)),
                "created_at": tool.get("created_at"),
                "updated_at": tool.get("updated_at"),
            }
            auth_store.get_db().tools.insert_one(doc)
            print(f"  Migrated {tool_id}")
        except Exception as e:
            print(f"  Error migrating {tool_id}: {e}")


def migrate_mcp_servers():
    """Migrate MCP servers from SQLite to MongoDB."""
    print("\nMigrating MCP servers...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM mcp_servers").fetchall()
        print(f"Found {len(rows)} MCP servers in SQLite")

    for row in rows:
        server = dict(row)
        server_id = server.get("id") or server.get("_id")
        if not server_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().mcp_servers.find_one({"_id": server_id})
        if existing:
            print(f"  Skipping {server_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            doc = {
                "_id": server_id,
                "name": server.get("name"),
                "description": server.get("description"),
                "server_url": server.get("server_url"),
                "status": server.get("status", "connected"),
                "tool_count": server.get("tool_count", 0),
                "last_active": server.get("last_active"),
                "auth_token": server.get("auth_token"),
                "auth_scheme": server.get("auth_scheme", "bearer"),
                "created_at": server.get("created_at"),
            }
            auth_store.get_db().mcp_servers.insert_one(doc)
            print(f"  Migrated {server_id}")
        except Exception as e:
            print(f"  Error migrating {server_id}: {e}")


def migrate_integrations():
    """Migrate integrations from SQLite to MongoDB."""
    print("\nMigrating integrations...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM integrations").fetchall()
        print(f"Found {len(rows)} integrations in SQLite")

    for row in rows:
        integ = dict(row)
        integ_id = integ.get("id") or integ.get("_id")
        if not integ_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().integrations.find_one({"_id": integ_id})
        if existing:
            print(f"  Skipping {integ_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            doc = {
                "_id": integ_id,
                "name": integ.get("name"),
                "description": integ.get("description"),
                "category": integ.get("category"),
                "auth_kind": integ.get("auth_kind", "oauth"),
                "status": integ.get("status", "available"),
                "account_label": integ.get("account_label"),
                "credential": integ.get("credential"),
                "connected_at": integ.get("connected_at"),
                "connect_method": integ.get("connect_method", "api_key"),
                "oauth_provider": integ.get("oauth_provider"),
                "mcp_url": integ.get("mcp_url"),
                "docs_url": integ.get("docs_url"),
                "logo_key": integ.get("logo_key"),
                "created_at": integ.get("created_at"),
                "updated_at": integ.get("updated_at"),
            }
            auth_store.get_db().integrations.insert_one(doc)
            print(f"  Migrated {integ_id}")
        except Exception as e:
            print(f"  Error migrating {integ_id}: {e}")


def migrate_documents():
    """Migrate documents from SQLite to MongoDB."""
    print("\nMigrating documents...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM documents").fetchall()
        print(f"Found {len(rows)} documents in SQLite")

    for row in rows:
        doc = dict(row)
        doc_id = doc.get("id") or doc.get("_id")
        if not doc_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().documents.find_one({"_id": doc_id})
        if existing:
            print(f"  Skipping {doc_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.create_document(
                doc_id=doc_id,
                name=doc.get("name"),
                doc_type=doc.get("type"),
                size_bytes=doc.get("size_bytes", 0),
                chunks_count=doc.get("chunks_count", 0),
                status=doc.get("status", "processing"),
                uploaded_by=doc.get("uploaded_by", "default-user"),
                file_path=doc.get("file_path"),
                source_url=doc.get("source_url"),
                department_id=doc.get("department_id"),
            )
            # Update with processing error if exists
            if doc.get("processing_error"):
                auth_store.update_document(doc_id, processing_error=doc.get("processing_error"))
            print(f"  Migrated {doc_id}")
        except Exception as e:
            print(f"  Error migrating {doc_id}: {e}")


def migrate_memory_entries():
    """Migrate memory entries from SQLite to MongoDB."""
    print("\nMigrating memory entries...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM memory_entries").fetchall()
        print(f"Found {len(rows)} memory entries in SQLite")

    for row in rows:
        mem = dict(row)
        mem_id = mem.get("id") or mem.get("_id")
        if not mem_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().memory_entries.find_one({"_id": mem_id})
        if existing:
            print(f"  Skipping {mem_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            auth_store.create_memory_entry(
                entry_id=mem_id,
                agent_id=mem.get("agent_id"),
                content=mem.get("content"),
                department_id=mem.get("department_id"),
                source_mission_id=mem.get("source_mission_id"),
                expires_at=mem.get("expires_at"),
            )
            print(f"  Migrated {mem_id}")
        except Exception as e:
            print(f"  Error migrating {mem_id}: {e}")


def migrate_oauth_connections():
    """Migrate OAuth connections from SQLite to MongoDB."""
    print("\nMigrating OAuth connections...")
    with connection() as conn:
        rows = conn.execute("SELECT * FROM oauth_connections").fetchall()
        print(f"Found {len(rows)} OAuth connections in SQLite")

    for row in rows:
        conn_data = dict(row)
        conn_id = conn_data.get("id") or conn_data.get("_id")
        if not conn_id:
            continue

        # Check if already exists
        existing = auth_store.get_db().oauth_connections.find_one({"_id": conn_id})
        if existing:
            print(f"  Skipping {conn_id} (already exists)")
            continue

        # Create in MongoDB
        try:
            import json
            scopes = conn_data.get("scopes", "[]")
            if isinstance(scopes, str):
                scopes = json.loads(scopes)

            doc = {
                "_id": conn_id,
                "user_id": conn_data.get("user_id"),
                "provider": conn_data.get("provider"),
                "account_id": conn_data.get("account_id"),
                "account_label": conn_data.get("account_label"),
                "access_token": conn_data.get("access_token"),
                "refresh_token": conn_data.get("refresh_token"),
                "expires_at": conn_data.get("expires_at"),
                "scopes": scopes,
                "status": conn_data.get("status", "connected"),
                "created_at": conn_data.get("created_at"),
                "updated_at": conn_data.get("updated_at"),
            }
            auth_store.get_db().oauth_connections.insert_one(doc)
            print(f"  Migrated {conn_id}")
        except Exception as e:
            print(f"  Error migrating {conn_id}: {e}")


if __name__ == "__main__":
    print("Starting SQLite to MongoDB migration...")
    print(f"SQLite DB: {settings.sqlite_file}")

    migrate_missions()
    migrate_mission_tasks()
    migrate_execution_traces()
    migrate_departments()
    migrate_department_members()
    migrate_agents()
    migrate_conversations()
    migrate_messages()
    migrate_global_context()
    migrate_tools()
    migrate_mcp_servers()
    migrate_integrations()
    migrate_documents()
    migrate_memory_entries()
    migrate_oauth_connections()

    print("\nMigration complete!")
