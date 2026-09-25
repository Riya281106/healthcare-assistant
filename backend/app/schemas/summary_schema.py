from pydantic import BaseModel
from typing import List, Optional


class SummaryResponse(BaseModel):
    id: int
    user_id: str
    overall_summary: str
    main_concerns: List[str]
    symptoms: List[str]
    medicines: List[str]
    health_observations: List[str]
    urgency_level: str
    recommended_actions: List[str]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None