from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Member(Base):
    __tablename__ = "members"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    category = Column(String)  # Parents, GenMillennial, GenAlpha
    default_amount = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    contributions = relationship("Contribution", back_populates="member")
    
    def __repr__(self):
        return f"<Member(name='{self.name}', category='{self.category}')>"

class Month(Base):
    __tablename__ = "months"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    contributions = relationship("Contribution", back_populates="month")
    
    def __repr__(self):
        return f"<Month(name='{self.name}')>"

class Contribution(Base):
    __tablename__ = "contributions"
    
    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"))
    month_id = Column(Integer, ForeignKey("months.id"))
    amount = Column(Integer)
    paid = Column(Boolean, default=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    member = relationship("Member", back_populates="contributions")
    month = relationship("Month", back_populates="contributions")
    
    def __repr__(self):
        return f"<Contribution(member='{self.member.name}', month='{self.month.name}', amount={self.amount})>" 