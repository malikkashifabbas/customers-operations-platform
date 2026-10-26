"""Checkpointers give a graph memory per thread_id; the Postgres one survives restarts."""

from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from urllib.parse import quote

from langgraph.checkpoint.postgres import PostgresSaver
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from config.env import env


def postgres_url() -> str:
    password = quote(env.postgres_password.get_secret_value(), safe="")
    return f"postgresql://{env.postgres_user}:{password}@{env.postgres_host}:{env.postgres_port}/{env.postgres_db}"


@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    with PostgresSaver.from_conn_string(postgres_url()) as saver:
        saver.setup()
        yield saver


@lru_cache(maxsize=1)
def get_pool_checkpointer() -> PostgresSaver:
    """One shared checkpointer for the web server: requests borrow pooled connections instead of opening new ones."""
    pool = ConnectionPool(
        postgres_url(),
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=True,
    )
    saver = PostgresSaver(pool)
    saver.setup()
    return saver
