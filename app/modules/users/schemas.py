from pydantic import BaseModel


class MonthlyUsageResponse(BaseModel):
    year: int
    month: int
    conversions_used: int
    conversions_limit: int
    remaining: int

    class Config:
        from_attributes = True