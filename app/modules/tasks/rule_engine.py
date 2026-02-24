from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Callable, Optional
from app.modules.auth.model import User
from app.modules.tasks.model import Task
from app.core import cache
from app.core.logger import logger

PYTHON_RULE_REGISTRY: dict[str, Callable[[User, any, dict], bool]] = {
    "max_active_tasks": lambda user, value, ctx: ctx["get_count"](user.id) < int(value),
}


# ================================================================
# ACTIVE TASK COUNT — CACHED
# ================================================================

def get_active_count(db: Session, user_id: int) -> int:
    key = cache.key_active_count(user_id)
    cached = cache.cache_get(key)
    if cached is not None:
        return int(cached)

    count = (
        db.query(func.count(Task.id))
        .filter(
            Task.assigned_to == user_id,
            Task.status != "done",
            Task.is_active == True,
        )
        .scalar() or 0
    )
    cache.cache_set(key, count, ttl=30)
    return count


# ================================================================
# STEP 1 — DB-LEVEL FILTERING
# ================================================================

def build_db_query(db: Session, rules: dict):
    query = db.query(User).filter(User.is_active == True)

    if dept := rules.get("department"):
        query = query.filter(User.department == dept)

    if location := rules.get("location"):
        query = query.filter(User.location == location)

    if min_exp := rules.get("min_experience"):
        query = query.filter(User.experience_years >= int(min_exp))

    return query


# ================================================================
# STEP 2 — PYTHON-LEVEL FILTERING
# ================================================================

def apply_python_rules(
    users: list[User],
    rules: dict,
    count_fn: Callable[[int], int],
) -> list[User]:
    active_python_rules = {
        k: v for k, v in rules.items()
        if k in PYTHON_RULE_REGISTRY
    }

    unknown_rules = {
        k for k in rules
        if k not in PYTHON_RULE_REGISTRY and k not in {"department", "location", "min_experience"}
    }
    if unknown_rules:
        logger.warning(f"[RuleEngine] Unknown rules skipped: {unknown_rules}")

    if not active_python_rules:
        return users

    ctx = {"get_count": count_fn}
    return [
        user for user in users
        if all(
            PYTHON_RULE_REGISTRY[rule_key](user, rule_val, ctx)
            for rule_key, rule_val in active_python_rules.items()
        )
    ]


# ================================================================
# STEP 3 — RANKING
# ================================================================

def rank_candidates(
    users: list[User],
    count_fn: Callable[[int], int],
) -> list[User]:
    return sorted(users, key=lambda u: (count_fn(u.id), u.id))


# ================================================================
# MAIN ENTRY POINT
# ================================================================

def find_eligible_users(db: Session, rules: dict) -> list[User]:
    if not rules:
        logger.warning("[RuleEngine] Empty rules — task will match all active users.")

    # Step 1: DB-level filter
    candidates = build_db_query(db, rules).all()
    logger.debug(f"[RuleEngine] DB filter → {len(candidates)} candidates. Rules: {rules}")

    if not candidates:
        return []

    # Step 2: Python-level filter (uses cached counts)
    count_fn = lambda uid: get_active_count(db, uid)
    eligible = apply_python_rules(candidates, rules, count_fn)
    logger.debug(f"[RuleEngine] Python filter → {len(eligible)} eligible users.")

    # Step 3: Rank
    ranked = rank_candidates(eligible, count_fn)
    return ranked


def assign_task(db: Session, task: Task) -> Optional[int]:
    rules = task.assignment_rules or {}
    old_assignee = task.assigned_to

    logger.info(f"[RuleEngine] Evaluating Task {task.id} | rules={rules}")

    eligible = find_eligible_users(db, rules)

    # Edge case: no eligible users
    if not eligible:
        logger.warning(
            f"[RuleEngine] Task {task.id} ('{task.title}') — NO eligible users. "
            f"Rules: {rules}. Task left unassigned. Will retry."
        )
        task.assigned_to = None
        db.commit()
        cache.invalidate_assignment(old_assignee, None, task.id)
        return None

    # Pick best user (least busy, deterministic)
    winner = eligible[0]
    task.assigned_to = winner.id
    db.commit()

    cache.invalidate_assignment(old_assignee, winner.id, task.id)

    logger.info(
        f"[RuleEngine] Task {task.id} → User {winner.id} ({winner.email}) | "
        f"dept={winner.department} exp={winner.experience_years}yrs | "
        f"active_tasks={get_active_count(db, winner.id)} | "
        f"eligible_pool={len(eligible)}"
    )
    return winner.id


def recompute_single(db: Session, task_id: int) -> Optional[int]:
    task = db.query(Task).filter(Task.id == task_id, Task.is_active == True).first()
    if not task:
        logger.error(f"[RuleEngine] Recompute failed — Task {task_id} not found.")
        return None
    return assign_task(db, task)


def recompute_for_user_profile_change(db: Session, user_id: int) -> dict:
    cache.invalidate_user(user_id)

    unassigned_tasks = (
        db.query(Task)
        .filter(Task.assigned_to == None, Task.is_active == True)
        .all()
    )

    total = len(unassigned_tasks)
    assigned_to_user = 0
    assigned_to_others = 0
    still_unassigned = 0

    for task in unassigned_tasks:
        result = assign_task(db, task)
        if result == user_id:
            assigned_to_user += 1
        elif result is not None:
            assigned_to_others += 1
        else:
            still_unassigned += 1

    summary = {
        "user_id": user_id,
        "tasks_evaluated": total,
        "assigned_to_this_user": assigned_to_user,
        "assigned_to_others": assigned_to_others,
        "still_unassigned": still_unassigned,
    }
    logger.info(f"[RuleEngine] User {user_id} profile recompute: {summary}")
    return summary