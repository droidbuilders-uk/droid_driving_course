from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker, Session
from app_models import Base, Droid, Member, Gate, Run, Penalty, Config
import logging

DATABASE_URL = "sqlite:///db/r2_course.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)

def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database V2 initialized")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper functions using SQLAlchemy
def get_config(db: Session, setting: str):
    return db.query(Config).filter(Config.config_name == setting).first()

def set_config(db: Session, setting: str, value: str):
    config = db.query(Config).filter(Config.config_name == setting).first()
    if config:
        config.config_value = str(value)
    else:
        config = Config(config_name=setting, config_value=str(value))
        db.add(config)
    db.commit()

def list_results(db: Session):
    return db.query(Run).filter(Run.final_time.isnot(None)).order_by(Run.final_time.asc()).all()
