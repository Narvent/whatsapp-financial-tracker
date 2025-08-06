from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class MemberBase(BaseModel):
    name: str
    category: str
    default_amount: int

class MemberCreate(MemberBase):
    pass

class Member(MemberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class MonthBase(BaseModel):
    name: str

class MonthCreate(MonthBase):
    pass

class Month(MonthBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class ContributionBase(BaseModel):
    amount: int
    paid: bool = False

class ContributionCreate(ContributionBase):
    member_id: int
    month_id: int

class Contribution(ContributionBase):
    id: int
    member_id: int
    month_id: int
    paid_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 