from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field, field_validator



class BusinessIdeaCreate(BaseModel):
    """Schema for validating new business idea submissions."""

    title: str = Field(..., min_length=1, max_length=200, description="Title of the business idea")
    description: str = Field(..., min_length=1, description="Description of the business idea")

    @field_validator("title", "description")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class BusinessIdeaResponse(BaseModel):
    """Schema for returning saved business ideas."""

    id: int
    title: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatQuestionRequest(BaseModel):
    """Schema for submitting a question to the AI Business Guide."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The business question to ask the guide",
    )

    @field_validator("question")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Question cannot be empty or only whitespace")
        return trimmed


class ChatResponse(BaseModel):
    """Schema for responses from the AI Business Guide."""

    answer: str
    configured: bool


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str

    @field_validator("content")
    @classmethod
    def require_content_for_user_messages(cls, value: str, info) -> str:
        if info.data.get("role") == "user" and not value.strip():
            raise ValueError("User messages cannot be empty")
        return value


class StreamingChatRequest(BaseModel):
    messages: List[ChatHistoryMessage] = Field(..., min_length=1)
    location: str = Field(default="", max_length=200)
    currency: str = Field(default="INR", max_length=10)
    language: str = Field(default="en", max_length=40)

    @field_validator("messages")
    @classmethod
    def require_latest_user_message(cls, messages):
        if not messages or messages[-1].role != "user":
            raise ValueError("The latest conversation message must be from the user")
        return messages


class BusinessPlanRequest(BaseModel):
    """Schema for requesting a structured business plan."""

    idea: str = Field(..., min_length=1, max_length=1000, description="Business idea description")
    location: str = Field(..., min_length=1, max_length=200, description="Target location or market")
    budget: float = Field(..., gt=0, description="Available startup budget (greater than 0)")
    currency: str = Field(default="USD", min_length=1, max_length=10, description="Currency code (e.g. USD, EUR, GBP, INR)")

    @field_validator("idea", "location", "currency")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class BusinessPlanDetails(BaseModel):
    """Structured business plan sections with labeled estimates and assumptions."""

    idea: str
    location: str
    budget: float
    currency: str
    target_customers: List[str]
    startup_costs: List[str]
    operating_costs: List[str]
    resources: List[str]
    risks: List[str]
    launch_steps: List[str]
    estimates_and_assumptions: List[str]
    disclaimer: str = (
        "All figures, costs, and timelines are estimates and assumptions for initial planning only. "
        "Profit, revenue, and business success are never guaranteed."
    )


class BusinessPlanResponse(BaseModel):
    """API response for business plan generation."""

    configured: bool
    message: Optional[str] = None
    plan: Optional[BusinessPlanDetails] = None


class MarketResearchRequest(BaseModel):
    """Schema for requesting market research on a business idea and location."""

    idea: str = Field(..., min_length=1, max_length=1000, description="Business idea description")
    location: str = Field(..., min_length=1, max_length=200, description="Target city, region, or market")

    @field_validator("idea", "location")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class MarketSource(BaseModel):
    """Source reference for market research finding."""

    title: str
    url: str
    snippet: str
    retrieved_at: str


class MarketResearchDetails(BaseModel):
    """Structured market research findings with separated facts, estimates, and sources."""

    idea: str
    location: str
    query: str
    retrieved_at: str
    sources: List[MarketSource]
    sourced_facts: List[str]
    estimates_and_assumptions: List[str]
    disclaimer: str = (
        "Market research data, sources, and projections are estimates and assumptions for informational purposes only. "
        "Market outcomes fluctuate and business success or profit is never guaranteed."
    )


class MarketResearchResponse(BaseModel):
    """API response for market research."""

    configured: bool
    message: Optional[str] = None
    research: Optional[MarketResearchDetails] = None


class CompetitorAnalysisRequest(BaseModel):
    """Schema for requesting competitor analysis for a business type and location."""

    business_type: str = Field(..., min_length=1, max_length=500, description="Type of business (e.g. Coffee Shop, Yoga Studio)")
    location: str = Field(..., min_length=1, max_length=200, description="Target city or area")

    @field_validator("business_type", "location")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed


class CompetitorEntry(BaseModel):
    """Information for a single identified competitor supported by search results."""

    name: str
    details: str
    source_title: str
    source_url: str
    retrieved_at: str


class CompetitorAnalysisDetails(BaseModel):
    """Competitor analysis report derived strictly from search results."""

    business_type: str
    location: str
    query: str
    retrieved_at: str
    competitors: List[CompetitorEntry]
    summary_of_findings: str
    unavailable_details_note: str
    disclaimer: str = (
        "Competitor information is sourced strictly from public web results for informational purposes. "
        "Private financials, pricing, and customer counts are not guaranteed and business success or profit is never promised."
    )


class CompetitorAnalysisResponse(BaseModel):
    """API response for competitor analysis."""

    configured: bool
    message: Optional[str] = None
    analysis: Optional[CompetitorAnalysisDetails] = None


class BusinessOpportunityRequest(BaseModel):
    """Inputs for location and budget based business opportunity suggestions."""

    location: str = Field(..., min_length=1, max_length=200)
    budget: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=1, max_length=10)
    interests: Optional[str] = Field(default=None, max_length=500)

    @field_validator("location", "currency")
    @classmethod
    def validate_not_blank(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or only whitespace")
        return trimmed

    @field_validator("interests")
    @classmethod
    def normalize_optional_interests(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() or None if value is not None else None


class BusinessOpportunitySuggestion(BaseModel):
    idea: str
    reason: str
    estimated_cost: str
    assumptions: List[str]
    risks: List[str]


class BusinessOpportunityResponse(BaseModel):
    configured: bool
    message: Optional[str] = None
    suggestions: List[BusinessOpportunitySuggestion] = Field(default_factory=list)
    used_live_search: bool = False
    sources: List[MarketSource] = Field(default_factory=list)
    disclaimer: str = (
        "Ideas are possibilities for further validation. Costs are estimates based on stated assumptions; "
        "they are not quotes. No profit, revenue, or business success is guaranteed."
    )


class SavedBusinessPlanResponse(BusinessPlanDetails):
    """Schema for returning a saved business plan with database ID and timestamp."""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True





