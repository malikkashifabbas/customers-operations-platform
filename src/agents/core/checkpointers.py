"""Checkpointers give a graph memory per thread_id; the Postgres one survives restarts."""

from collections.abc import Iterator
from contextlib import contextmanager
from urllib.parse import quote

from langgraph.checkpoint.postgres import PostgresSaver

from config.env import env


def postgres_url() -> str:
    password = quote(env.postgres_password.get_secret_value(), safe="")
    return f"postgresql://{env.postgres_user}:{password}@{env.postgres_host}:{env.postgres_port}/{env.postgres_db}"


@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    with PostgresSaver.from_conn_string(postgres_url()) as saver:
        saver.setup()
        yield saver
