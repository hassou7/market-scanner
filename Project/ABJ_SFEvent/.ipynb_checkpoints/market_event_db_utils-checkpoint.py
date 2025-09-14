# market_event.py

from sqlalchemy import (
    create_engine, Column,
    String, Boolean, DateTime, Float, DECIMAL, Integer
)
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
from datetime import datetime

Base = declarative_base()

class MarketEvent(Base):
    __tablename__ = "MarketEvents"
    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Symbol = Column(String(40), nullable=False)
    Exchange = Column(String(40), nullable=False)
    Timeframe = Column(String(10), nullable=False)
    Date = Column(DateTime, nullable=False)
    TradingViewLink = Column(String(512), nullable=False)
    Close = Column(DECIMAL(38, 8))
    VolumeUsd = Column(DECIMAL(38, 2))
    CloseOffLow = Column(DECIMAL(5, 2))
    PinDown = Column(Boolean)
    Confluence = Column(Boolean)
    IsEngulfing = Column(Boolean)
    ConsolidationBo = Column(Boolean)
    ConsolidationBoDirectionBo = Column(Integer)
    ConsolidationBoBoxAge = Column(Integer)
    ConsolidationBoBoxHeight = Column(DECIMAL(6, 2))
    ChannelBo = Column(Boolean)
    ChannelBoChannelDirection = Column(Integer)
    ChannelBoChannelAge = Column(Integer)
    ChannelBoChannelSlope = Column(Float)
    ChannelBoChannelHeight = Column(DECIMAL(6, 2))
    WedgeBo = Column(Boolean)
    WedgeBoChannelDirection = Column(Integer)
    WedgeBoChannelAge = Column(Integer)
    WedgeBoChannelSlope = Column(Float)
    WedgeBoChannelHeight = Column(DECIMAL(6, 2))
    Sma50Bo = Column(Boolean)
    Sma50BoType = Column(String(50))
    Sma50BoStrength = Column(DECIMAL(6, 2))


def insert_market_event(event: MarketEvent, conn_string: str):
    """Insert a MarketEvent in Postgres, skip if duplicate."""
    engine = create_engine(conn_string)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        if getattr(event, "Id", None) in (None, ""):
            event.Id = uuid.uuid4()
        data = {c.name: getattr(event, c.name) for c in MarketEvent.__table__.columns}
        stmt = insert(MarketEvent).values(**data).on_conflict_do_nothing(
            index_elements=['Symbol', 'Exchange', 'Timeframe', 'Date']
        )
        res = session.execute(stmt)
        session.commit()
        inserted = (res.rowcount or 0) > 0
        if inserted:
            print(f"✅ MarketEvent inséré : {event.Symbol} @ {event.Exchange} "
                  f"({event.Timeframe}) | Close={event.Close} | Date={event.Date}")
        else:
            print(f"⚠️ Doublon ignoré : {event.Symbol} @ {event.Exchange} "
                  f"({event.Timeframe}) | Date={event.Date}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
