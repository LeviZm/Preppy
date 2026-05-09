"""Header function for database transactions."""

from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from .exceptions import ConflictError

import logging

logger = logging.getLogger(__name__)

@contextmanager
def atomic(conflict_message: str = "A conflicting record already exists."):
    """
    Context manager that wraps a block of database operations
    in a single atomic transaction.

    On success: commits and yields control back to the caller.
    On IntegrityError: rolls back and raises ConflictError.
    On any other exception: rolls back, logs the error, and re-raises.

    Usage:
        with atomic("You already have a recipe with this name."):
            db.session.add(recipe)
            db.session.flush()
            db.session.add(recipe_ingredient)

    Why a context manager and not a decorator?
    A context manager lets you interleave session operations with
    other logic (flush, resolve ingredients, etc.) inside the
    protected block. A decorator wraps an entire function call,
    which works only when the function does nothing but database work.
    """
    try:
        yield
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        logger.warning(
            "IntegrityError during atomic block: %s", str(e.orig)
        )
        raise ConflictError(conflict_message) from e
    except Exception as e:
        db.session.rollback()
        logger.exception(
            "Unexpected error during atomic block: %s", repr(e)
        )
        raise
