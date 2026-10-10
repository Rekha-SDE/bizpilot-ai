import os
import json
import logging
import threading
import time
from collections import defaultdict, deque
from typing import List, Union

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

# Load the project .env before importing modules that read configuration,
# including database.py. Explicit process environment settings take precedence.
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

from database import engine, get_db
import ai_service
import models
import schemas
import search_service



# Automatically create database tables if they do not exist
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="BizPilot AI")
logger = logging.getLogger("uvicorn.error")

cors_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]
chat_rate_limit = max(1, int(os.getenv("CHAT_RATE_LIMIT_PER_MINUTE", "10")))
chat_rate_window = max(1, int(os.getenv("CHAT_RATE_WINDOW_SECONDS", "60")))
_chat_requests = defaultdict(deque)
_chat_rate_lock = threading.Lock()


def enforce_chat_rate_limit(request: Request) -> None:
    """Limit chat requests per client IP with a small in-memory sliding window."""
    forwarded_for = request.headers.get("x-forwarded-for", "")
    # Proxies append the connecting address to this header; use the last hop so
    # a caller cannot bypass the limit by supplying an extra left-hand value.
    client_ip = forwarded_for.split(",")[-1].strip() if forwarded_for else ""
    if not client_ip:
        client_ip = request.client.host if request.client else "unknown"

    now = time.monotonic()
    with _chat_rate_lock:
        for ip, timestamps in list(_chat_requests.items()):
            while timestamps and now - timestamps[0] >= chat_rate_window:
                timestamps.popleft()
            if not timestamps:
                _chat_requests.pop(ip, None)

        timestamps = _chat_requests[client_ip]
        if len(timestamps) >= chat_rate_limit:
            retry_after = max(1, int(chat_rate_window - (now - timestamps[0])))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Chat request limit reached. Please wait before trying again.",
                headers={"Retry-After": str(retry_after)},
            )
        timestamps.append(now)


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    """Log safe 422 details without logging request values or credentials."""
    if request.url.path != "/chat":
        return await request_validation_exception_handler(request, exc)

    detail = [
        {
            "loc": [str(part) for part in error.get("loc", ())],
            "msg": str(error.get("msg", "Invalid value")),
            "type": str(error.get("type", "validation_error")),
        }
        for error in exc.errors()
    ]
    logger.warning("422 request validation for %s: %s", request.url.path, json.dumps(detail))
    return JSONResponse(status_code=422, content={"detail": detail})

# Allow CORS so the frontend works both via the web server and if opened locally as a file
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def serve_index():
    """Serve the single-page frontend for creating and viewing ideas."""
    index_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>BizPilot AI</h1><p>index.html not found.</p>")


@app.get("/health")
def health_check(response: Response, db: Session = Depends(get_db)):
    """Check backend, database, and provider-key presence without revealing the key."""
    ai_configured = ai_service.get_ai_config()["is_configured"]
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "connected",
            "ai_configured": ai_configured,
        }
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "error",
            "database": "unavailable",
            "ai_configured": ai_configured,
        }


@app.post(
    "/ideas",
    response_model=schemas.BusinessIdeaResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_idea(idea_in: schemas.BusinessIdeaCreate, db: Session = Depends(get_db)):
    """Create and save a new business idea locally."""
    idea = models.BusinessIdea(
        title=idea_in.title,
        description=idea_in.description,
    )
    db.add(idea)
    db.commit()
    db.refresh(idea)
    return idea


@app.get(
    "/ideas",
    response_model=List[schemas.BusinessIdeaResponse],
)
def list_ideas(db: Session = Depends(get_db)):
    """List all saved business ideas, sorted newest first."""
    return db.query(models.BusinessIdea).order_by(models.BusinessIdea.id.desc()).all()


@app.post(
    "/chat",
    response_model=None,
)
def chat_with_guide(
    request: Request,
    chat_in: Union[schemas.ChatQuestionRequest, schemas.StreamingChatRequest],
):
    """Keep the legacy single-question contract and stream full chat histories."""
    enforce_chat_rate_limit(request)
    if isinstance(chat_in, schemas.StreamingChatRequest):
        return _stream_chat_response(chat_in)
    return ai_service.get_business_guide_answer(chat_in.question)


def _stream_chat_response(chat_in: schemas.StreamingChatRequest):
    """Stream a chat completion while keeping provider credentials server-side."""
    config = ai_service.get_ai_config()
    system_prompt = (
        "You are BizPilot AI, an expert business advisor for small businesses and startups in India. "
        "Answer any question accurately and clearly. Use the user's preferred location, currency and language. "
        "Give practical steps, realistic cost estimates and local insights. If you are unsure, say so instead of guessing. "
        "Ask a clarifying question when the request is vague."
    )
    preferences = (
        f"\n\nUser preferences for this conversation:\n"
        f"Preferred location: {chat_in.location.strip() or 'Not provided'}\n"
        f"Preferred currency: {chat_in.currency.strip() or 'INR'}\n"
        f"Preferred language: {chat_in.language.strip() or 'en'}"
    )
    provider_messages = [{"role": "system", "content": system_prompt + preferences}]
    provider_messages.extend(
        message.model_dump()
        for message in chat_in.messages
        if message.content.strip()
    )

    def event_stream():
        def send(event):
            return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        if not config["is_configured"]:
            yield send({"type": "error", "message": "AI is not configured. Add AI_API_KEY to the backend .env file and restart the server."})
            return
        try:
            for delta in ai_service.stream_ai_provider(provider_messages, config):
                yield send({"type": "delta", "text": delta})
            yield send({"type": "done"})
        except Exception as error:
            if getattr(error, "code", None) == 429:
                message = "The AI provider is rate limiting requests. Wait a moment, then retry."
            else:
                message = "The AI service could not complete this reply. Check your connection and try again."
            yield send({"type": "error", "message": message})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/chat", response_model=None)
def stream_chat_compat(request: Request, chat_in: schemas.StreamingChatRequest):
    """Backward-compatible alias for clients using the earlier streaming path."""
    enforce_chat_rate_limit(request)
    return _stream_chat_response(chat_in)


@app.post(
    "/opportunity-suggestions",
    response_model=schemas.BusinessOpportunityResponse,
)
def suggest_business_opportunities(request_in: schemas.BusinessOpportunityRequest):
    """Suggest budget-aware business possibilities, optionally supported by live search."""
    return ai_service.suggest_business_opportunities(
        location=request_in.location,
        budget=request_in.budget,
        currency=request_in.currency,
        interests=request_in.interests,
    )


@app.post(
    "/plan",
    response_model=schemas.BusinessPlanResponse,
)
def create_business_plan(plan_in: schemas.BusinessPlanRequest):
    """Generate a structured business plan based on idea, location, and budget."""
    return ai_service.generate_business_plan(
        idea=plan_in.idea,
        location=plan_in.location,
        budget=plan_in.budget,
        currency=plan_in.currency,
    )


@app.post(
    "/market-research",
    response_model=schemas.MarketResearchResponse,
)
def get_market_research(research_in: schemas.MarketResearchRequest):
    """Conduct market research on a business idea and location."""
    return search_service.get_market_research(
        idea=research_in.idea,
        location=research_in.location,
    )


@app.post(
    "/competitor-analysis",
    response_model=schemas.CompetitorAnalysisResponse,
)
def analyze_competitors(request_in: schemas.CompetitorAnalysisRequest):
    """Analyze local competitors for a business type and location."""
    return search_service.get_competitor_analysis(
        business_type=request_in.business_type,
        location=request_in.location,
    )


@app.post(
    "/plans",
    response_model=schemas.SavedBusinessPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_business_plan(plan_in: schemas.BusinessPlanDetails, db: Session = Depends(get_db)):
    """Save a generated business plan locally."""
    saved_plan = models.SavedBusinessPlan(
        idea=plan_in.idea,
        location=plan_in.location,
        budget=plan_in.budget,
        currency=plan_in.currency,
        target_customers=plan_in.target_customers,
        startup_costs=plan_in.startup_costs,
        operating_costs=plan_in.operating_costs,
        resources=plan_in.resources,
        risks=plan_in.risks,
        launch_steps=plan_in.launch_steps,
        estimates_and_assumptions=plan_in.estimates_and_assumptions,
        disclaimer=plan_in.disclaimer,
    )
    db.add(saved_plan)
    db.commit()
    db.refresh(saved_plan)
    return saved_plan


@app.get(
    "/plans",
    response_model=List[schemas.SavedBusinessPlanResponse],
)
def list_saved_plans(db: Session = Depends(get_db)):
    """List all saved business plans, newest first."""
    return db.query(models.SavedBusinessPlan).order_by(models.SavedBusinessPlan.id.desc()).all()


@app.get(
    "/plans/{plan_id}",
    response_model=schemas.SavedBusinessPlanResponse,
)
def get_saved_plan(plan_id: int, db: Session = Depends(get_db)):
    """Retrieve a specific saved business plan by ID."""
    plan = db.query(models.SavedBusinessPlan).filter(models.SavedBusinessPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Business plan with ID {plan_id} not found",
        )
    return plan


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
    )







