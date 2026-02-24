import redis
import json
from typing import Any, Optional
from app.core.config import settings
from app.core.logger import logger

# Shared connection pool — do NOT create per-request connections
_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=100,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


def key_my_tasks(user_id: int) -> str:
    return f"user:{user_id}:my_tasks"

def key_eligible_users(task_id: int) -> str:
    return f"task:{task_id}:eligible_users"

def key_active_count(user_id: int) -> str:
    return f"user:{user_id}:active_count"

def key_task_detail(task_id: int) -> str:
    return f"task:{task_id}:detail"


def cache_get(key: str) -> Optional[Any]:
    try:
        val = get_redis().get(key)
        if val:
            logger.debug(f"[CACHE HIT] {key}")
            return json.loads(val)
        logger.debug(f"[CACHE MISS] {key}")
        return None
    except Exception as e:
        # Cache failure must NEVER break the API — fall through to DB
        logger.warning(f"[CACHE GET ERROR] {key}: {e}")
        return None


def cache_set(key: str, value: Any, ttl: int) -> None:
    try:
        get_redis().setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"[CACHE SET ERROR] {key}: {e}")


def cache_delete(*keys: str) -> None:
    try:
        if keys:
            get_redis().delete(*keys)
            logger.debug(f"[CACHE DELETE] {keys}")
    except Exception as e:
        logger.warning(f"[CACHE DELETE ERROR] {keys}: {e}")


def cache_delete_pattern(pattern: str) -> None:
    try:
        r = get_redis()
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
            logger.info(f"[CACHE FLUSH] pattern={pattern} count={len(keys)}")
    except Exception as e:
        logger.warning(f"[CACHE PATTERN DELETE ERROR] {pattern}: {e}")


# ── Targeted invalidation helpers ─────────────────────────────────
def invalidate_user(user_id: int) -> None:
    """Call when: user gets a task assigned/unassigned, or status changes."""
    cache_delete(key_my_tasks(user_id), key_active_count(user_id))


def invalidate_task(task_id: int) -> None:
    """Call when: task rules change or task is deleted."""
    cache_delete(key_eligible_users(task_id), key_task_detail(task_id))


def invalidate_assignment(old_assignee_id: Optional[int], new_assignee_id: Optional[int], task_id: int) -> None:
    """Call on every assignment change — clears both sides."""
    keys = [key_task_detail(task_id), key_eligible_users(task_id)]
    if old_assignee_id:
        keys += [key_my_tasks(old_assignee_id), key_active_count(old_assignee_id)]
    if new_assignee_id:
        keys += [key_my_tasks(new_assignee_id), key_active_count(new_assignee_id)]
    cache_delete(*keys)