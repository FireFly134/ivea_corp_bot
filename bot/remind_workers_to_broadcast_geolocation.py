import logging
from asyncio import run

import pandas as pd

from sqlalchemy import create_engine

from .send_msg_telegram import send_msg
from .work import ivea_metrika

engine = create_engine(ivea_metrika)  # данные для соединия с сервером

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


async def send_working() -> None:
    info = pd.read_sql("SELECT * FROM user_worker_key_corp;", engine)
    for idx, row in info.iterrows():
        res = await send_msg(
            user_id=row["user_id"],
            msg='Выберите пункт "Транслировать геопозицию" и укажите в \
течение 8 часов',
        )
        if not res:
            logging.info(f"Не смог отправить смс {row['user_id']}")
    return


if __name__ == "__main__":
    # If it's not a weekend, we should ask ( 9 AM )
    run(send_working())
