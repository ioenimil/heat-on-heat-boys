import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple

from faker import Faker
from sqlalchemy import text
from sqlalchemy.engine import Engine

from utils.logger import get_logger

logger = get_logger(__name__)

random.seed(42)
Faker.seed(42)
faker = Faker()
faker.seed_instance(42)

CATEGORIES = ["IT_SUPPORT", "FACILITIES", "HR_REQUEST"]
PRIORITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
STATUSES = ["OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED", "CLOSED"]

CATEGORY_WEIGHTS = [0.50, 0.25, 0.25]
PRIORITY_WEIGHTS = [0.10, 0.25, 0.45, 0.20]
STATUS_WEIGHTS = [0.15, 0.10, 0.20, 0.40, 0.15]

PASSWORD_HASH = (
    "$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy"
)

SLA_HOURS = {
    ("IT_SUPPORT", "CRITICAL"): 4,
    ("IT_SUPPORT", "HIGH"): 8,
    ("IT_SUPPORT", "MEDIUM"): 24,
    ("IT_SUPPORT", "LOW"): 72,
    ("FACILITIES", "CRITICAL"): 8,
    ("FACILITIES", "HIGH"): 16,
    ("FACILITIES", "MEDIUM"): 48,
    ("FACILITIES", "LOW"): 96,
    ("HR_REQUEST", "CRITICAL"): 8,
    ("HR_REQUEST", "HIGH"): 24,
    ("HR_REQUEST", "MEDIUM"): 72,
    ("HR_REQUEST", "LOW"): 168,
}


def _fetch_user_ids_by_role(engine: Engine, role: str) -> List[str]:
    query = text(
        """
        SELECT id
        FROM users
        WHERE role = :role AND is_active = TRUE
        ORDER BY created_at
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query, {"role": role}).scalars().all()
    return [str(row) for row in rows]


def _fetch_department_map(engine: Engine) -> Dict[str, str]:
    query = text(
        """
        SELECT id, category
        FROM departments
        WHERE is_active = TRUE
        """
    )
    with engine.connect() as connection:
        rows = connection.execute(query).mappings().all()
    return {str(row["category"]): str(row["id"]) for row in rows}


def seed_users(engine: Engine) -> Tuple[List[str], List[str]]:
    with engine.connect() as connection:
        existing_count = int(
            connection.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        )

    if existing_count > 3:
        logger.info(
            "Users already seeded (count=%d). Skipping new user inserts.",
            existing_count,
        )
        return (
            _fetch_user_ids_by_role(engine, "AGENT"),
            _fetch_user_ids_by_role(engine, "USER"),
        )

    department_map = _fetch_department_map(engine)
    department_cycle = [
        department_map.get("IT_SUPPORT"),
        department_map.get("HR_REQUEST"),
        department_map.get("FACILITIES"),
    ]
    department_cycle = [dept_id for dept_id in department_cycle if dept_id]
    if not department_cycle:
        logger.error("No department UUIDs found. Cannot seed agents.")
        return ([], [])

    now_utc = datetime.now(timezone.utc)
    insert_user_stmt = text(
        """
        INSERT INTO users (
            id, email, password, full_name, role, department, is_active, created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :email, :password, :full_name, :role, :department, TRUE, :created_at, :updated_at
        )
        RETURNING id, role
        """
    )

    inserted_agent_ids: List[str] = []
    inserted_user_ids: List[str] = []
    with engine.begin() as connection:
        for index in range(5):
            payload = {
                "email": f"agent{index + 1}@servicehub.local",
                "password": PASSWORD_HASH,
                "full_name": faker.name(),
                "role": "AGENT",
                "department": department_cycle[index % len(department_cycle)],
                "created_at": now_utc,
                "updated_at": now_utc,
            }
            row = connection.execute(insert_user_stmt, payload).mappings().one()
            inserted_agent_ids.append(str(row["id"]))

        for index in range(20):
            payload = {
                "email": f"user{index + 1}@servicehub.local",
                "password": PASSWORD_HASH,
                "full_name": faker.name(),
                "role": "USER",
                "department": None,
                "created_at": now_utc,
                "updated_at": now_utc,
            }
            row = connection.execute(insert_user_stmt, payload).mappings().one()
            inserted_user_ids.append(str(row["id"]))

    logger.info(
        "Inserted users successfully: agents=%d users=%d",
        len(inserted_agent_ids),
        len(inserted_user_ids),
    )
    return (
        _fetch_user_ids_by_role(engine, "AGENT"),
        _fetch_user_ids_by_role(engine, "USER"),
    )


def _random_created_at_utc() -> datetime:
    now_utc = datetime.now(timezone.utc)
    seconds_in_60_days = 60 * 24 * 60 * 60
    seconds_back = random.uniform(0, seconds_in_60_days)
    return now_utc - timedelta(seconds=seconds_back)


def _build_ticket(
    agent_ids: List[str],
    user_ids: List[str],
    department_map: Dict[str, str],
) -> dict:
    category = random.choices(CATEGORIES, weights=CATEGORY_WEIGHTS, k=1)[0]
    priority = random.choices(PRIORITIES, weights=PRIORITY_WEIGHTS, k=1)[0]
    status = random.choices(STATUSES, weights=STATUS_WEIGHTS, k=1)[0]

    created_at = _random_created_at_utc()
    sla_hours = SLA_HOURS[(category, priority)]
    sla_deadline = created_at + timedelta(hours=sla_hours)

    ticket = {
        "title": f"{category.replace('_', ' ').title()} request - {faker.word()}",
        "description": faker.paragraph(nb_sentences=3),
        "category": category,
        "priority": priority,
        "status": status,
        "department_id": None,
        "assigned_to_id": None,
        "requester_id": random.choice(user_ids),
        "sla_deadline": sla_deadline,
        "first_response_at": None,
        "resolved_at": None,
        "closed_at": None,
        "is_sla_breached": False,
        "created_at": created_at,
        "updated_at": created_at,
    }

    if status != "OPEN":
        ticket["assigned_to_id"] = random.choice(agent_ids)
        ticket["department_id"] = department_map[category]
        first_response_hours = random.uniform(0.5, sla_hours * 0.5)
        ticket["first_response_at"] = created_at + timedelta(hours=first_response_hours)

    if status in {"RESOLVED", "CLOSED"}:
        breached = random.random() < 0.15
        if breached:
            resolved_at = sla_deadline + timedelta(hours=random.uniform(1, 12))
            ticket["is_sla_breached"] = True
        else:
            resolved_at = created_at + timedelta(hours=random.uniform(1, sla_hours * 0.9))

        ticket["resolved_at"] = resolved_at
        ticket["updated_at"] = resolved_at

        if status == "CLOSED":
            ticket["closed_at"] = resolved_at + timedelta(hours=random.uniform(1, 72))

    return ticket


def seed_tickets(
    engine: Engine,
    agent_ids: List[str],
    user_ids: List[str],
    count: int = 200,
) -> int:
    with engine.connect() as connection:
        existing_count = int(
            connection.execute(text("SELECT COUNT(*) FROM service_requests")).scalar_one()
        )
    if existing_count > 0:
        logger.info(
            "service_requests already seeded (count=%d). Skipping ticket inserts.",
            existing_count,
        )
        return existing_count

    if not agent_ids or not user_ids:
        logger.error("Cannot seed tickets: missing agent_ids or user_ids.")
        return 0

    department_map = _fetch_department_map(engine)
    missing_categories = [category for category in CATEGORIES if category not in department_map]
    if missing_categories:
        logger.error(
            "Cannot seed tickets: department mapping missing categories %s",
            ", ".join(missing_categories),
        )
        return 0

    payloads = [
        _build_ticket(agent_ids=agent_ids, user_ids=user_ids, department_map=department_map)
        for _ in range(count)
    ]

    insert_ticket_stmt = text(
        """
        INSERT INTO service_requests (
            id, title, description, category, priority, status,
            department_id, assigned_to_id, requester_id, sla_deadline,
            first_response_at, resolved_at, closed_at, is_sla_breached,
            created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), :title, :description, :category, :priority, :status,
            :department_id, :assigned_to_id, :requester_id, :sla_deadline,
            :first_response_at, :resolved_at, :closed_at, :is_sla_breached,
            :created_at, :updated_at
        )
        """
    )

    with engine.begin() as connection:
        connection.execute(insert_ticket_stmt, payloads)

    logger.info("Inserted %d service_requests rows.", len(payloads))
    return len(payloads)


def run_seeder(engine: Engine) -> None:
    logger.info("Seeder run started.")
    logger.info("Seeding users...")
    agent_ids, user_ids = seed_users(engine)

    if not agent_ids or not user_ids:
        logger.error("Seeder aborted: empty agent_ids or user_ids after user seeding.")
        return

    logger.info("Seeding tickets...")
    inserted_count = seed_tickets(engine, agent_ids, user_ids, count=200)
    logger.info("Seeder run completed. tickets=%d", inserted_count)
