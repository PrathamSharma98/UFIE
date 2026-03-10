"""AI Copilot API routes with separate ChatGPT and Gemini endpoints."""

from fastapi import APIRouter
from app.models.schemas import AIQueryRequest, AIQueryResponse
from app.services.ai_copilot import copilot
from app.database import data_store
from app.services.ward_scoring import calculate_ward_scores
import json

router = APIRouter(prefix="/api/ai-query", tags=["AI Copilot"])


def _build_context(request_context: str | None) -> str:
    """Build context from current data if not provided."""
    if request_context:
        return request_context
    try:
        scores = calculate_ward_scores(
            data_store.get_wards(), data_store.get_hotspots(),
            data_store.get_drainage(), data_store.get_pumps()
        )
        summary = {
            "total_wards": len(scores),
            "critical_wards": len([s for s in scores if s.get("category") == "Critical Risk"]),
            "avg_readiness": round(sum(s.get("readiness_score", 0) for s in scores) / max(len(scores), 1), 1),
            "total_hotspots": len(data_store.get_hotspots().get("features", [])),
        }
        return json.dumps(summary)
    except Exception:
        return ""


@router.post("/", response_model=AIQueryResponse)
async def ai_query(request: AIQueryRequest):
    """Smart-routed AI query (auto-selects ChatGPT or Gemini)."""
    context = _build_context(request.context)
    result = await copilot.query(request.query, context)
    return AIQueryResponse(**result)


@router.post("/chatgpt", response_model=AIQueryResponse)
async def chatgpt_query(request: AIQueryRequest):
    """Query ChatGPT specifically for flood analysis."""
    context = _build_context(request.context)
    result = await copilot.query_chatgpt(request.query, context)
    suggestions = copilot._generate_follow_up_suggestions(request.query, result.get("response", ""))
    return AIQueryResponse(
        query=request.query,
        response=result["response"],
        sources=[result.get("source", "ChatGPT")],
        suggestions=suggestions,
    )


@router.post("/gemini", response_model=AIQueryResponse)
async def gemini_query(request: AIQueryRequest):
    """Query Gemini specifically for policy/planning insights."""
    context = _build_context(request.context)
    result = await copilot.query_gemini(request.query, context)
    suggestions = copilot._generate_follow_up_suggestions(request.query, result.get("response", ""))
    return AIQueryResponse(
        query=request.query,
        response=result["response"],
        sources=[result.get("source", "Gemini")],
        suggestions=suggestions,
    )
