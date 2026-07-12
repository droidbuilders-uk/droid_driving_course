from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship, DeclarativeBase
try:
    from pydantic import BaseModel, ConfigDict
    HAS_PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel
    ConfigDict = None
    HAS_PYDANTIC_V2 = False
from datetime import datetime
from typing import Optional, List

# --- SQLAlchemy Models ---

class Base(DeclarativeBase):
    pass

class Droid(Base):
    __tablename__ = "droids"
    droid_uid = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    member_uid = Column(Integer, ForeignKey("members.member_uid"), nullable=False)
    material = Column(String)
    weight = Column(String)
    transmitter_type = Column(String)
    new = Column(Boolean, default=False)
    
    member = relationship("Member", back_populates="droids")
    runs = relationship("Run", back_populates="droid")

class Member(Base):
    __tablename__ = "members"
    member_uid = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String)
    badge_id = Column(String, nullable=False)
    new = Column(Boolean, default=False)
    
    droids = relationship("Droid", back_populates="member")
    runs = relationship("Run", back_populates="member")

class Gate(Base):
    __tablename__ = "gates"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    penalty = Column(Integer, nullable=False)

class Run(Base):
    __tablename__ = "runs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(DateTime, default=datetime.utcnow)
    middle_start = Column(DateTime)
    droid_uid = Column(Integer, ForeignKey("droids.droid_uid"), nullable=False)
    member_uid = Column(Integer, ForeignKey("members.member_uid"), nullable=False)
    first_half_time = Column(Integer)
    second_half_time = Column(Integer)
    clock_time = Column(Integer)
    final_time = Column(Integer)
    type = Column(String)
    
    droid = relationship("Droid", back_populates="runs")
    member = relationship("Member", back_populates="runs")
    penalties = relationship("Penalty", back_populates="run", cascade="all, delete-orphan")

class Penalty(Base):
    __tablename__ = "penalties"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    gate_id = Column(Integer, ForeignKey("gates.id"), nullable=False)
    status = Column(String, default="FAIL")
    
    run = relationship("Run", back_populates="penalties")

class Config(Base):
    __tablename__ = "course"
    config_name = Column(String, primary_key=True)
    config_value = Column(String)

# --- Pydantic Schemas (for API Validation) ---

class DroidBase(BaseModel):
    name: str
    member_uid: int
    material: Optional[str] = None
    weight: Optional[str] = None
    transmitter_type: Optional[str] = None

class DroidSchema(DroidBase):
    droid_uid: int
    if HAS_PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class MemberBase(BaseModel):
    name: str
    email: Optional[str] = None
    badge_id: str

class MemberSchema(MemberBase):
    member_uid: int
    if HAS_PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class PenaltySchema(BaseModel):
    gate_id: int
    timestamp: datetime
    status: str = "FAIL"
    if HAS_PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True

class RunSchema(BaseModel):
    id: int
    start: datetime
    droid_uid: int
    member_uid: int
    final_time: Optional[int] = None
    num_penalties: int = 0
    if HAS_PYDANTIC_V2:
        model_config = ConfigDict(from_attributes=True)
    else:
        class Config:
            orm_mode = True
