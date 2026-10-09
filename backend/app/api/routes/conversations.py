from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_department_access, require_org_admin
from app.db.supabase import get_service_client
from app.schemas.conversations import (
    Conversation,
    ConversationCreate,
    Message,
    MessageCreate,
)
from app.services.ai_provider import generate_text

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _org_id(current_user) -> str:
    profile = (
        current_user["client"]
        .table("user_profiles")
        .select("organization_id")
        .eq("id", current_user["id"])
        .maybe_single()
        .execute()
    )
    org_id = (profile.data or {}).get("organization_id")
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return str(org_id)


@router.get("", response_model=list[Conversation])
def list_conversations(
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only'])),
    limit: int = Query(default=20, ge=1, le=50),
):
    """List AI conversations for the caller's organization."""
    supabase = current_user["client"]
    organization_id = _org_id(current_user)
    response = (
        supabase.table("ai_conversations")
        .select("id,organization_id,created_by,title,status,created_at,updated_at")
        .eq("organization_id", organization_id)
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data or []


@router.post("", response_model=Conversation, status_code=201)
def create_conversation(
    body: ConversationCreate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    """Start a new AI conversation (read-only users cannot create one)."""
    org_id = _org_id(current_user)
    supabase = current_user["client"]

    response = (
        supabase.table("ai_conversations")
        .insert(
            {
                "organization_id": org_id,
                "created_by": current_user["id"],
                "title": body.title or "Office conversation",
                "status": "active",
            }
        )
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Conversation could not be created.")
    return response.data[0]


@router.get("/{conversation_id}/messages", response_model=list[Message])
def list_messages(
    conversation_id: UUID,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only'])),
    limit: int = Query(default=50, ge=1, le=100),
):
    """List messages in a conversation."""
    supabase = current_user["client"]

    # Verify ownership / access via RLS; also guard explicitly.
    conv = (
        supabase.table("ai_conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .maybe_single()
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")

    response = (
        supabase.table("ai_messages")
        .select("id,conversation_id,role,content,model,confidence,created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return response.data or []


@router.post("/{conversation_id}/messages", response_model=Message, status_code=201)
def post_message(
    conversation_id: UUID,
    body: MessageCreate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    """Post a message; read-only users cannot mutate conversation history."""
    supabase = current_user["client"]

    conv = (
        supabase.table("ai_conversations")
        .select("id,organization_id,status")
        .eq("id", str(conversation_id))
        .maybe_single()
        .execute()
    )
    if not conv.data:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.data.get("status") != "active":
        raise HTTPException(status_code=409, detail="Conversation is not active.")

    # Assistant messages are written only through the backend's trusted service client.
    # Create it before persisting the user message so missing server configuration
    # fails without leaving a partial conversation turn.
    try:
        trusted_client = get_service_client()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail="Trusted AI message storage is not configured.",
        ) from exc

    # Store user message with the caller's JWT; RLS permits only role='user'.
    user_msg = (
        supabase.table("ai_messages")
        .insert(
            {
                "conversation_id": str(conversation_id),
                "role": "user",
                "content": body.content,
            }
        )
        .execute()
    )
    if not user_msg.data:
        raise HTTPException(status_code=500, detail="Message could not be saved.")

    # Lightweight context for the assistant (counts only — full office assistant
    # endpoint remains available for deep queries). A failed count must not
    # abort the turn after the user message is persisted or be presented as zero.
    def count_label(table_name: str) -> str:
        try:
            result = (
                supabase.table(table_name)
                .select("id", count="exact")
                .limit(1)
                .execute()
            )
            count = getattr(result, "count", None)
            if count is None:
                count = len(result.data or [])
            return str(count)
        except Exception:
            return "unavailable"

    evidence_summary = (
        f"Roads: {count_label('roads')}; "
        f"Sections: {count_label('road_sections')}; "
        f"Work orders: {count_label('work_orders')}."
    )

    prompt = (
        "You are the AI-RMMS office assistant. Answer briefly using only the "
        "supplied summary facts. If you cannot answer from them, say so. "
        "Do not invent numbers, costs, or decisions.\n\n"
        f"Organization summary: {evidence_summary}\n"
        f"User message: {body.content}"
    )

    try:
        ai_result = generate_text(prompt)
    except Exception:
        # A provider/network error must not leave the persisted user message
        # without a corresponding assistant response.
        ai_result = None

    if ai_result:
        assistant_content = ai_result.text
        model_name = ai_result.model
    else:
        assistant_content = (
            "I received your message. The AI provider is not configured or "
            "temporarily unavailable. Please use the structured office-assistant "
            "endpoint for evidence-based answers, or try again later."
        )
        model_name = None

    # Persist the generated assistant reply using the server-only service role.
    # The conversation was first verified through the caller's RLS-scoped client.
    assistant_msg = (
        trusted_client.table("ai_messages")
        .insert(
            {
                "conversation_id": str(conversation_id),
                "role": "assistant",
                "content": assistant_content,
                "model": model_name,
            }
        )
        .execute()
    )
    if not assistant_msg.data:
        raise HTTPException(status_code=500, detail="Assistant reply could not be saved.")

    # Updating the list-sort timestamp is best-effort: the assistant reply
    # is already saved, so a timestamp failure must not turn success into an
    # API error that encourages clients to resend the same message.
    try:
        trusted_client.table("ai_conversations").update(
            {"updated_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", str(conversation_id)).execute()
    except Exception:
        pass

    return assistant_msg.data[0]
