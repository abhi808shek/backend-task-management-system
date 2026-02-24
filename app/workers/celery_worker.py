import time
from celery import Celery
from celery.utils.log import get_task_logger
from app.db.session import SessionLocal
from app.core.config import settings

logger = get_task_logger(__name__)

# ── Celery app setup ───────────────────────────────────────────────
celery_app = Celery(
    "task_management",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,

    # ── Redis connection timeouts ──────────────────────────────────
    # These ensure Redis failures are fast-fail (2s) not 20s hangs
    redis_socket_connect_timeout=2,
    redis_socket_timeout=2,
    broker_transport_options={
        "max_retries": 2,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 1,
        "connect_timeout": 2,
    },

    # Queue routing
    task_routes={
        "tasks.assign_task":        {"queue": "critical"},
        "tasks.recompute_for_user": {"queue": "default"},
        "tasks.bulk_recompute":     {"queue": "bulk"},
        "tasks.retry_unassigned":   {"queue": "default"},
    },
    task_default_queue="default",

    # Rate limiting on bulk ops
    task_annotations={
        "tasks.bulk_recompute": {"rate_limit": "10/m"},
    },

    # Beat schedule — periodic retry of unassigned tasks
    beat_schedule={
        "retry-unassigned-tasks-every-10-minutes": {
            "task": "tasks.retry_unassigned",
            "schedule": 600,
        },
    },
)


# ================================================================
# REDIS HEALTH CHECK
# ================================================================

def is_redis_available() -> bool:
    """
    Fast Redis health check with 2s timeout.
    Used before every dispatch to decide sync vs async execution.
    """
    try:
        import redis
        r = redis.Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        r.ping()
        return True
    except Exception:
        return False


# ================================================================
# SAFE DISPATCH — core helper used everywhere
# ================================================================

def dispatch_task_assignment(task_id: int, queue: str = "critical") -> None:
    """
    Tries to queue via Celery. If Redis is down, runs synchronously.
    API always returns fast — never blocked by Redis state.

    Flow:
      Redis UP   → async_assign_task.apply_async() → returns in <5ms
      Redis DOWN → run_assignment_sync(task_id)    → runs inline, still fast
    """
    if is_redis_available():
        try:
            async_assign_task.apply_async(
                args=[task_id],
                queue=queue,
                retry=False,          # don't retry the DISPATCH — just fire once
            )
            logger.info(f"[Dispatch] Task {task_id} queued to Celery [{queue}].")
            return
        except Exception as e:
            logger.warning(f"[Dispatch] Celery queue failed for task {task_id}: {e}. Falling back to sync.")

    # Fallback: run synchronously in-process
    logger.warning(f"[Dispatch] Redis unavailable — running assignment synchronously for task {task_id}.")
    run_assignment_sync(task_id)


def dispatch_user_recompute(user_id: int) -> None:
    """
    Same pattern as dispatch_task_assignment but for user profile changes.
    Redis DOWN → runs synchronously, still updates assignments correctly.
    """
    if is_redis_available():
        try:
            async_recompute_for_user.apply_async(
                args=[user_id],
                queue="default",
                retry=False,
            )
            logger.info(f"[Dispatch] User {user_id} recompute queued to Celery.")
            return
        except Exception as e:
            logger.warning(f"[Dispatch] Celery queue failed for user {user_id}: {e}. Falling back to sync.")

    logger.warning(f"[Dispatch] Redis unavailable — running user recompute synchronously for user {user_id}.")
    run_user_recompute_sync(user_id)


# ================================================================
# SYNC FALLBACKS — run when Redis is unavailable
# ================================================================

def run_assignment_sync(task_id: int) -> None:
    """
    Synchronous rule engine execution.
    Called when Redis/Celery is unavailable.
    Runs in the same process — slightly slower but always works.
    """
    db = SessionLocal()
    try:
        from app.modules.tasks.rule_engine import recompute_single
        start = time.time()
        assigned_to = recompute_single(db, task_id)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(f"[SyncFallback] Task {task_id} → user={assigned_to} | {duration}ms")
    except Exception as e:
        db.rollback()
        logger.error(f"[SyncFallback] Task {task_id} assignment failed: {e}")
    finally:
        db.close()


def run_user_recompute_sync(user_id: int) -> None:
    """
    Synchronous user recompute fallback.
    """
    db = SessionLocal()
    try:
        from app.modules.tasks.rule_engine import recompute_for_user_profile_change
        start = time.time()
        summary = recompute_for_user_profile_change(db, user_id)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(f"[SyncFallback] User {user_id} recompute done in {duration}ms | {summary}")
    except Exception as e:
        db.rollback()
        logger.error(f"[SyncFallback] User {user_id} recompute failed: {e}")
    finally:
        db.close()


# ================================================================
# CELERY TASKS
# ================================================================

@celery_app.task(
    name="tasks.assign_task",
    bind=True,
    max_retries=5,
    default_retry_delay=60,
)
def async_assign_task(self, task_id: int):
    """
    Async rule engine execution via Celery.
    Retry schedule (exponential backoff):
      Attempt 1: immediate
      Attempt 2: 60s  → Attempt 3: 120s → Attempt 4: 240s
      Attempt 5: 480s → Attempt 6: 960s → give up
    """
    start = time.time()
    logger.info(f"[Celery] Task {task_id} assignment started (attempt {self.request.retries + 1})")

    db = SessionLocal()
    try:
        from app.modules.tasks.rule_engine import recompute_single
        assigned_to = recompute_single(db, task_id)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(f"[Celery] Task {task_id} → user={assigned_to} | {duration}ms")
        return {"task_id": task_id, "assigned_to": assigned_to, "duration_ms": duration}

    except Exception as exc:
        db.rollback()
        retry_num = self.request.retries
        countdown = 60 * (2 ** retry_num)  # 60, 120, 240, 480, 960
        logger.error(f"[Celery] Task {task_id} failed (attempt {retry_num + 1}): {exc}. Retry in {countdown}s.")
        raise self.retry(exc=exc, countdown=countdown)

    finally:
        db.close()


@celery_app.task(
    name="tasks.recompute_for_user",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def async_recompute_for_user(self, user_id: int):
    start = time.time()
    logger.info(f"[Celery] User {user_id} profile recompute started.")

    db = SessionLocal()
    try:
        from app.modules.tasks.rule_engine import recompute_for_user_profile_change
        summary = recompute_for_user_profile_change(db, user_id)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(f"[Celery] User {user_id} recompute done in {duration}ms | {summary}")
        return {**summary, "duration_ms": duration}

    except Exception as exc:
        db.rollback()
        logger.error(f"[Celery] User {user_id} recompute failed: {exc}")
        raise self.retry(exc=exc)

    finally:
        db.close()


@celery_app.task(
    name="tasks.bulk_recompute",
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    rate_limit="10/m",
)
def async_bulk_recompute(self, task_ids: list[int] = None):
    """Chunked bulk recompute — 50 tasks per batch."""
    start = time.time()
    db = SessionLocal()
    CHUNK_SIZE = 50

    try:
        from app.modules.tasks.model import Task
        from app.modules.tasks.rule_engine import assign_task

        tasks = (
            db.query(Task).filter(Task.id.in_(task_ids), Task.is_active == True).all()
            if task_ids
            else db.query(Task).filter(Task.assigned_to == None, Task.is_active == True).all()
        )

        total = len(tasks)
        assigned = 0
        unassigned = 0

        for i in range(0, total, CHUNK_SIZE):
            for task in tasks[i:i + CHUNK_SIZE]:
                result = assign_task(db, task)
                assigned += 1 if result else 0
                unassigned += 0 if result else 1
            db.commit()

        duration = round((time.time() - start) * 1000, 2)
        summary = {"total": total, "assigned": assigned, "still_unassigned": unassigned, "duration_ms": duration}
        logger.info(f"[Celery] BulkRecompute complete: {summary}")
        return summary

    except Exception as exc:
        db.rollback()
        logger.error(f"[Celery] BulkRecompute failed: {exc}")
        raise self.retry(exc=exc)

    finally:
        db.close()


@celery_app.task(name="tasks.retry_unassigned")
def retry_unassigned_tasks():
    """Beat task — runs every 10 min. Retries tasks with no eligible user."""
    db = SessionLocal()
    try:
        from app.modules.tasks.model import Task
        unassigned = db.query(Task).filter(
            Task.assigned_to == None, Task.is_active == True
        ).all()

        if not unassigned:
            return {"retried": 0}

        for task in unassigned:
            dispatch_task_assignment(task.id, queue="default")

        logger.info(f"[Beat] Retried {len(unassigned)} unassigned tasks.")
        return {"retried": len(unassigned)}

    finally:
        db.close()