"""Chat API — conversations, messages, and global context.

Powers the multi-conversation Command Center.

  GET    /conversations                 list the user's conversations
  POST   /conversations                 create a new conversation
  GET    /conversations/{id}            conversation + its messages
  PUT    /conversations/{id}            rename
  DELETE /conversations/{id}            delete (+ its messages)

  POST   /conversations/{id}/messages   append a message (user or assistant)
  PUT    /messages/{id}                 update an assistant message (content/outputs/status/mission_id)

  GET    /context                       list global context facts
  PUT    /context                       upsert a fact {key, value}
  DELETE /context/{key}                 remove a fact

Phase 1: single-user ('default-user').
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.chat import store

router = APIRouter(tags=["chat"])
DEFAULT_USER = "default-user"


class CreateConversationRequest(BaseModel):
    title: str | None = None


class RenameConversationRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class AddMessageRequest(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = ""
    mission_id: str | None = None
    attachments: list = []
    outputs: list = []
    status: str = "done"


class UpdateMessageRequest(BaseModel):
    content: str | None = None
    mission_id: str | None = None
    outputs: list | None = None
    status: str | None = None


class ContextRequest(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)


# --- conversations -----------------------------------------------------------

@router.get("/conversations")
async def list_conversations() -> dict:
    return {"conversations": store.list_conversations(DEFAULT_USER)}


@router.post("/conversations", status_code=201)
async def create_conversation(req: CreateConversationRequest) -> dict:
    return store.create_conversation(DEFAULT_USER, req.title or "New chat")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str) -> dict:
    conv = store.get_conversation(conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    conv["messages"] = store.list_messages(conversation_id)
    return conv


@router.put("/conversations/{conversation_id}")
async def rename_conversation(conversation_id: str, req: RenameConversationRequest) -> dict:
    if not store.rename_conversation(conversation_id, req.title):
        raise HTTPException(404, "Conversation not found")
    return {"id": conversation_id, "title": req.title}


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    if not store.delete_conversation(conversation_id):
        raise HTTPException(404, "Conversation not found")
    return {"deleted": conversation_id}


# --- messages ----------------------------------------------------------------

@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def add_message(conversation_id: str, req: AddMessageRequest) -> dict:
    if store.get_conversation(conversation_id) is None:
        raise HTTPException(404, "Conversation not found")
    return store.add_message(
        conversation_id, req.role, req.content, req.mission_id,
        req.attachments, req.outputs, req.status,
    )


@router.put("/messages/{message_id}")
async def update_message(message_id: str, req: UpdateMessageRequest) -> dict:
    fields = {k: v for k, v in req.model_dump().items() if v is not None}
    if fields:
        store.update_message(message_id, **fields)
    return {"id": message_id, **fields}


# --- global context ----------------------------------------------------------

@router.get("/context")
async def get_context() -> dict:
    return {"context": store.list_context(DEFAULT_USER)}


@router.put("/context")
async def set_context(req: ContextRequest) -> dict:
    return store.set_context(DEFAULT_USER, req.key, req.value)


@router.delete("/context/{key}")
async def delete_context(key: str) -> dict:
    if not store.delete_context(DEFAULT_USER, key):
        raise HTTPException(404, "Context key not found")
    return {"deleted": key}
