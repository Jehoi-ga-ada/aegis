from sqlalchemy import create_engine, Column, Float, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone
from ports.repository import TradeRepositoryPort
import os

Base = declarative_base()

class Trade(Base):
    __tablename__ = 'trades'
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    price = Column(Float)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.now(timezone.utc))

class Account(Base):
    __tablename__ = 'account'
    id = Column(Integer, primary_key=True)
    balance_usd = Column(Float, default=1000.0)
    btc_held = Column(Float, default=0.0)


class PostgresTradeAdapter(TradeRepositoryPort):
    def get_all_trades(self, limit: int = 100):
        with SessionLocal() as session:
            return session.query(Trade).order_by(Trade.timestamp.desc()).limit(limit).all()
        
    def get_balance(self):
        with SessionLocal() as session:
            return session.query(Account).first()

DB_URL = os.getenv("DB_URL", "postgresql://user:password@localhost:5432/aegis_vault")
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

    session = SessionLocal()
    try:
        existing_account = session.query(Account).first()
        
        if not existing_account:
            print("VAULT: No account found. Seeding initial $1,000.00...")
            seed_account = Account(balance_usd=1000.0, btc_held=0.0)
            session.add(seed_account)
            session.commit()
            print("VAULT: Seed successful.")
        else:
            print(f"VAULT: Existing account found. Balance: ${existing_account.balance_usd:.2f}")
    except Exception as e:
        session.rollback()
        print(f"VAULT ERROR: Could not seed database: {e}")
    finally:
        session.close()