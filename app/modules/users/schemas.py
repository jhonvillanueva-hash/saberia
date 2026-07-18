from pydantic import BaseModel


class MonthlyUsageResponse(BaseModel):
    """Response schema for monthly conversion usage."""
    year: int
    month: int
    conversions_used: int
    conversions_limit: int
    remaining: int

    class Config:
        from_attributes = True