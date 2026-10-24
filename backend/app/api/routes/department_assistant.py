"""Secure AI assistant scoped to the departments the current user can access."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_current_user
from app.schemas.office_assistant import OfficeAssistantRequest, OfficeAssistantResponse
from app.services.ai_audit import log_analysis_run, resolve_organization_id
from app.services.ai_provider import generate_text
from app.services.cross_module_context import collect_cross_module_context
from app.services.semantic_search import search_document_chunks

router = APIRouter(prefix="/ai", tags=["ai"])

DEPARTMENTS = {
    "road_asset": "Road Asset Management",
    "machinery_maintenance": "Machinery Maintenance",
    "finance": "Finance",
    "human_resources": "Human Resources",
    "general_assets": "General Assets",
}
ALLOWED_ROLES = ["department_manager", "officer", "read_only"]


@router.post("/department-assistant", response_model=OfficeAssistantResponse)
def department_assistant(
    request: OfficeAssistantRequest,
    current_user=Depends(get_current_user),
):
    """Answer using only modules the caller is authorized to access."""
    client = current_user["client"]
    user_id = current_user["id"]

    try:
        organization_id = resolve_organization_id(client, user_id)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Organization membership could not be verified.",
        ) from exc
    if not organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Active organization membership is required.",
        )

    try:
        membership = (
            client.table("organization_members")
            .select("role")
            .eq("organization_id", str(organization_id))
            .eq("user_id", user_id)
            .eq("is_active", True)
            .maybe_single()
            .execute()
        )
        is_org_admin = bool(
            membership.data and membership.data.get("role") in {"owner", "admin"}
        )
        allowed_modules = set()
        for department_code in DEPARTMENTS:
            if is_org_admin:
                allowed_modules.add(department_code)
                continue
            result = client.rpc(
                "has_department_role",
                {
                    "p_organization_id": str(organization_id),
                    "p_department_code": department_code,
                    "p_allowed_roles": ALLOWED_ROLES,
                },
            ).execute()
            if result.data is True:
                allowed_modules.add(department_code)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Department permissions could not be verified.",
        ) from exc

    if not allowed_modules:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to a department in this organization.",
        )

    question = (request.question or request.query or "").strip()
    context = collect_cross_module_context(
        client,
        organization_id=str(organization_id),
        allowed_modules=allowed_modules,
    )
    evidence = list(context.evidence)
    modules = [
        DEPARTMENTS[code] for code in DEPARTMENTS if code in allowed_modules
    ]
    document_evidence = []

    if request.include_documents and current_user.get("access_token"):
        try:
            matches = search_document_chunks(
                question,
                organization_id=str(organization_id),
                access_token=current_user["access_token"],
                limit=5,
                minimum_similarity=0.35,
            )
            document_ids = list(dict.fromkeys(str(item.document_id) for item in matches))
            if document_ids:
                metadata = (
                    client.table("documents")
                    .select("id,organization_id,department_code")
                    .eq("organization_id", str(organization_id))
                    .in_("id", document_ids)
                    .execute()
                )
                authorized_ids = {
                    str(row["id"])
                    for row in (metadata.data or [])
                    if str(row.get("organization_id")) == str(organization_id)
                    and row.get("department_code") in allowed_modules
                }
                document_evidence = [
                    item.content[:280].strip()
                    for item in matches
                    if str(item.document_id) in authorized_ids
                ]
                if document_evidence:
                    modules.append("Authorized Document Intelligence")
                    evidence.append(
                        f"Relevant authorized document excerpts retrieved: {len(document_evidence)}."
                    )
        except Exception:
            # Missing or unverified document metadata must fail closed.
            document_evidence = []

    payload = {
        "authorized_departments": modules,
        "summary": context.summary,
        "samples": context.samples,
        "evidence": evidence,
        "document_evidence": document_evidence,
    }
    prompt = (
        "You are the AI-RMMS Department AI Assistant. Answer using only the "
        "provided verified organizational records and authorized document excerpts. "
        "Never infer or disclose data from departments not listed in authorized_departments. "
        "If information is absent, clearly say it is unavailable. Distinguish recorded "
        "facts from recommendations. Explain the evidence behind conclusions. "
        "Recommendations are advisory only: never claim to approve spending, contracts, "
        "staff decisions, or work orders. Do not invent figures or events.\n\n"
        f"Question: {question}\n\n"
        f"Verified context: {payload}"
    )
    result = generate_text(
        prompt,
        system_instruction=(
            "You are an evidence-grounded assistant for road-maintenance operations. "
            "Respect department permissions and disclose uncertainty."
        ),
    )
    if result:
        answer = result.text
    else:
        answer = (
            "The AI provider is unavailable or not configured right now. "
            "Here is the verified operational evidence available to you: "
            + "; ".join(evidence[:8])
        )

    try:
        log_analysis_run(
            client,
            organization_id=str(organization_id),
            analysis_type="department_assistant",
            status="completed",
            result={
                "ai_generated": bool(result),
                "authorized_departments": [
                    code for code in DEPARTMENTS if code in allowed_modules
                ],
            },
            evidence={
                "evidence": evidence,
                "document_evidence_count": len(document_evidence),
            },
            created_by=user_id,
            input_reference=question[:500],
        )
    except Exception:
        # Audit logging failure must not leak data or break an otherwise valid answer.
        pass

    return OfficeAssistantResponse(
        query=question,
        answer=answer,
        evidence=evidence,
        modules_consulted=modules,
        document_evidence=document_evidence,
        advisory=True,
        ai_generated=bool(result),
    )
