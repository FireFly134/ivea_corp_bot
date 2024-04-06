import asyncio
from typing import Any

from models import (
    add_insert_for_check_user_and_birthday,
    drop_and_create_db,
    meta_data_obj_user,
    test_engine,
)

from pytest import mark

from send_query_sql import insert_and_update_sql


@mark.parametrize(
    "text_sql, param",
    [
        (
            "SELECT * FROM doc_key_corp WHERE user_id = :user_id",
            {"user_id": 1234567890},
        ),
        ("SELECT * FROM doc_key_corp;", None),
    ],
)
def test_select(text_sql: str, param: dict[str, Any] | None) -> None:
    drop_and_create_db(meta_data=meta_data_obj_user)
    add_insert_for_check_user_and_birthday()
    rez = asyncio.run(
        insert_and_update_sql(text_sql, param=param, eng=test_engine)
    )
    assert rez
