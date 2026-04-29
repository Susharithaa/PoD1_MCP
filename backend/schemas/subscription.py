from pydantic import BaseModel


class SubscriptionStatusResponse(BaseModel):
    chat_status: str
    credits: float
    total_spent: float


class TopUpRequest(BaseModel):
    amount: float


class AccessRequestsResponse(BaseModel):
    user_id: str
    email: str
    full_name: str | None
    chat_status: str
    credits: float
