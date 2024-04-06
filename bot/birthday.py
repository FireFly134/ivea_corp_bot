import asyncio
import logging
from copy import copy
from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd

from send_msg_telegram import send_msg

from sqlalchemy import create_engine

from work import id_telegram, ivea_metrika

engine = create_engine(ivea_metrika)  # данные для соединия с сервером

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

month_name = {
    1: "Января",
    2: "Февраля",
    3: "Марта",
    4: "Апреля",
    5: "Мая",
    6: "Июня",
    7: "Июля",
    8: "Августа",
    9: "Сентября",
    10: "Октября",
    11: "Ноября",
    12: "Декабря",
}


def finder(
    begin_text: str, testing: bool = False
) -> Tuple[str, dict[int, str]]:
    info = pd.read_sql(
        # "SELECT * FROM birthday WHERE verified = 'true';",
        """
SELECT bday.birthday, dkc.family_name, dkc.name,
dkc.position_at_work, dkc.user_id
FROM birthday as bday
JOIN doc_key_corp as dkc ON bday.id_user = dkc.id
WHERE bday.verified = 'true' AND dkc.user_id > 0;""",
        engine,
    )
    info["birthday"] = pd.to_datetime(info["birthday"])
    now = datetime.now()
    month_and_day = datetime(now.year, now.month, now.day).strftime("%m-%d")
    month_and_tomorrow_day = (now + timedelta(days=+1)).strftime("%m-%d")
    birthday_list: str = copy(begin_text)
    dict_text = dict()
    for idx, row in info.iterrows():
        if (
            int(now.strftime("%d")) == 1 or testing
        ):  # срабатывает каждый первый день месяца и отправляет лист
            if int(row["birthday"].strftime("%m")) == int(now.strftime("%m")):
                birthday_list += f"{row['birthday'].strftime('%d')} \
{month_name[int(row['birthday'].strftime('%m'))]} - {row['family_name']} \
{row['name']} ({row['position_at_work']})\n"
        if row["birthday"].strftime("%m-%d") == month_and_day:
            dict_text[int(row["user_id"])] = (
                f"🎊🎉🎂 Сегодня свой день рождения отмечает \
{row['family_name']} {row['name']} ({row['position_at_work']})🎂🎉🎊"
            )
            logging.info(
                f"Cегодня свой день рождения отмечает {row['family_name']} \
{row['name']} ({row['position_at_work']})"
            )
        elif row["birthday"].strftime("%m-%d") == month_and_tomorrow_day:
            dict_text[int(row["user_id"])] = (
                f"🎂 Завтра свой день рождения отмечает \
{row['family_name']} {row['name']} ({row['position_at_work']}) 🎂"
            )
            logging.info(
                f"Завтра свой день рождения отмечает \
{row['family_name']} {row['name']} ({row['position_at_work']})"
            )
    return birthday_list, dict_text


def send_sms_birthday(dict_text: dict[int, str]) -> None:
    info_corp = pd.read_sql(
        "SELECT * FROM doc_key_corp WHERE user_id > 0;", engine
    )
    for idx, row in info_corp.iterrows():
        res: bool = True
        for user_id, value in dict_text.items():
            if row["user_id"] != user_id:
                res = asyncio.run(
                    send_msg(user_id=int(row["user_id"]), msg=value)
                )
            elif "Сегодня" in value:
                logging.info("🎊🎉🎂 С днём рождения!!! 🎂🎉🎊")
                res = asyncio.run(
                    send_msg(
                        user_id=user_id,
                        msg="🎊🎉🎂 С днём рождения!!! 🎂🎉🎊",
                    )
                )
            if not res:
                logging.error(
                    f'ERROR msg don\'t send - chat_id=\
{row["user_id"]} - "{row["name"]} {row["family_name"]}"'
                )
    return


def main() -> None:
    begin_text: str = "В этом месяце дни рождения у следующих людей:\n"

    birthday_list, dict_text = finder(begin_text=begin_text)
    if dict_text:
        send_sms_birthday(dict_text=dict_text)
    if birthday_list != begin_text:
        logging.info(birthday_list)
        for user_id in [
            id_telegram["Boss"],
            id_telegram["Pavel"],
            id_telegram["my"],
        ]:
            if send_msg(user_id=user_id, msg=birthday_list):
                logging.info(f"chat_id={user_id}")
    return


if __name__ == "__main__":
    main()
