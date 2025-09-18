#SFEvent/market_event_db_utils.py

from sqlalchemy import (
    create_engine, Column,
    String, Boolean, DateTime, Float, DECIMAL, Integer
)
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import declarative_base, sessionmaker
import uuid
from datetime import datetime
from decimal import Decimal

Base = declarative_base()

class MarketEvent(Base):
    __tablename__ = "MarketEvents"
    Id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    Symbol = Column(String(40), nullable=False)
    Exchange = Column(String(40), nullable=False)
    Timeframe = Column(String(10), nullable=False)
    Date = Column(DateTime, nullable=False)
    TradingViewLink = Column(String(512), nullable=False)
    Close = Column(DECIMAL(38, 8), default=Decimal('0'))
    VolumeUsd = Column(DECIMAL(38, 2), default=Decimal('0'))
    CloseOffLow = Column(DECIMAL(5, 2), default=Decimal('0'))
    PinDown = Column(Boolean, default=False)
    Confluence = Column(Boolean, default=False)
    IsEngulfing = Column(Boolean, default=False)
    ConsolidationBo = Column(Boolean, default=False)
    ConsolidationBoDirectionBo = Column(Integer, default=0)
    ConsolidationBoBoxAge = Column(Integer, default=0)
    ConsolidationBoBoxHeight = Column(DECIMAL(6, 2), default=Decimal('0.0'))
    ConsolidationBoStrength = Column(String(20), default="")
    ChannelBo = Column(Boolean, default=False)
    ChannelBoChannelDirection = Column(Integer, default=0)
    ChannelBoChannelAge = Column(Integer, default=0)
    ChannelBoChannelSlope = Column(Float, default=0.0)
    ChannelBoChannelHeight = Column(DECIMAL(6, 2), default=Decimal('0.0'))
    WedgeBo = Column(Boolean, default=False)
    WedgeBoChannelDirection = Column(Integer, default=0)
    WedgeBoChannelAge = Column(Integer, default=0)
    WedgeBoChannelSlope = Column(Float, default=0.0)
    WedgeBoChannelHeight = Column(DECIMAL(6, 2), default=Decimal('0.0'))
    Sma50Bo = Column(Boolean, default=False)
    Sma50BoType = Column(String(50), default="")
    Sma50BoStrength = Column(String(20), default="")
    PinUp = Column(Boolean, default=False)
    TrendBo = Column(Boolean, default=False)
    LoadedBar = Column(Boolean, default=False)


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