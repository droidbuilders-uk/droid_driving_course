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
    
    # Load initial config from CSV if available and table is empty
    db = SessionLocal()
    try:
        import csv
        import os
        if db.query(Config).count() == 0 and os.path.exists('db/config.csv'):
            logger.info("Loading initial config values from db/config.csv")
            with open('db/config.csv', 'rt') as fin:
                dr = csv.DictReader(fin)
                for row in dr:
                    config = Config(config_name=row['config_name'], config_value=row['config_value'])
                    db.add(config)
                db.commit()
    except Exception as e:
        logger.error(f"Error loading initial config: {e}")
    finally:
        db.close()

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
