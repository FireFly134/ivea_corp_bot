import logging
from asyncio import run

import telegram

from work import TELEGRAM_TOKEN, id_telegram


async def send_msg(user_id: int | str, msg: str) -> bool:
    try:
        bot = telegram.Bot(TELEGRAM_TOKEN)
        await bot.send_message(chat_id=user_id, text=msg)
        return True
    except telegram.error.BadRequest as err:
        logging.error(f"{user_id} - {err}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(process)d-%(levelname)s %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
    )
    logging.info(run(send_msg(user_id=id_telegram["my"], msg="Test")))
