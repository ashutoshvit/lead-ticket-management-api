import json
import logging
from datetime import datetime, timezone

from kafka import KafkaProducer
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import OutboxEvent

logger = logging.getLogger(__name__)
_producer: KafkaProducer | None = None


def record_event(db, event_type: str, aggregate_type: str, aggregate_id: int, payload: dict) -> None:
    db.add(OutboxEvent(
        topic=settings.kafka_topic,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=json.dumps({"event_type": event_type, "aggregate_type": aggregate_type,
                            "aggregate_id": aggregate_id, "data": payload}, default=str),
    ))


def dispatch_outbox_once() -> None:
    global _producer
    try:
        if _producer is None:
            _producer = KafkaProducer(
                bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
                value_serializer=lambda value: json.dumps(value).encode("utf-8"),
                key_serializer=lambda value: str(value).encode("utf-8"),
                acks="all",
                retries=3,
                request_timeout_ms=5000,
                max_block_ms=5000,
            )
    except Exception:
        logger.exception("Kafka producer unavailable; outbox events will be retried")
        _producer = None
        return

    with SessionLocal() as db:
        events = db.scalars(select(OutboxEvent).where(OutboxEvent.published_at.is_(None))
                            .order_by(OutboxEvent.id).limit(100)).all()
        for event in events:
            try:
                _producer.send(event.topic, json.loads(event.payload), key=event.aggregate_id).get(timeout=10)
                event.published_at = datetime.now(timezone.utc)
                db.commit()
            except Exception:
                logger.exception("Could not publish outbox event %s; it will be retried", event.id)
                db.rollback()
                break

