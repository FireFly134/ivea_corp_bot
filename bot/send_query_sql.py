from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from work import ivea_metrika

engine = create_engine(ivea_metrika)


async def insert_and_update_sql(
    text_for_sql: str | Any,
    param: dict[str, Any] | None = None,
    eng: Any = engine,
) -> bool:
    try:
        with eng.connect() as con:
            if type(text_for_sql) is str:
                con.execute(text(text_for_sql), parameters=param)
            else:
                con.execute(text_for_sql, parameters=param)
            con.commit()
        return True
    except SQLAlchemyError as err:
        print("ERROR insert_and_update_sql - " + str(err))
        return False
