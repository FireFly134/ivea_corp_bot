# coding=UTF-8
#
#
import logging
from datetime import datetime

import pandas as pd

from sqlalchemy import create_engine

import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from .work import TELEGRAM_TOKEN, id_telegram, ivea_metrika

engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером
bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


def main() -> None:
    try:
        now: datetime = datetime.now()
        info: pd.DataFrame = pd.read_sql_query(
            "SELECT * FROM doc_date ORDER BY date_end ASC", engine2
        )
        list_doc: str = ""
        text: str = ""
        doc_id: str = ""
        j: int = 0
        for idx, row in info.iterrows():
            date_end = str(row["date_end"] - now).split(" ")[0]
            if date_end == "0":
                j += 1
                if row["noct"] > 0:
                    doc_id += "," + str(row["id"])
                    days = str(row["date_end"] - row["date1"]).split(" ")[0]
                    list_doc += (
                        str(j)
                        + ") "
                        + str(row["doc_name"])
                        + " "
                        + str(row["work_name"])
                        + "\nВыполнение задачи переносилось "
                        + str(row["noct"])
                        + " раз(а) на общее количество "
                        + days
                        + " дн. Причина: "
                        + str(row["coment"])
                        + "\n\n"
                    )
                else:
                    doc_id += "," + str(row["id"])
                    list_doc += (
                        str(j)
                        + ") "
                        + str(row["doc_name"])
                        + " "
                        + str(row["work_name"])
                        + "\n\n"
                    )
                text = (
                    'Завершение работ в период - 1 день - "'
                    + str(row["date_end"].strftime("%d.%m.%Y"))
                    + '"\n\n'
                    + list_doc
                )
        if text != "":
            info_user = pd.read_sql(
                "SELECT user_id FROM key_for_people WHERE access > 0;", engine2
            )
            keyboard: list[list[InlineKeyboardButton]] = [
                [
                    InlineKeyboardButton(
                        "Перенести срок договора",
                        callback_data="go_next_contract" + doc_id,
                    )
                ]
            ]
            for idx, row in info_user.iterrows():
                try:
                    if str(row["user_id"]) == str(id_telegram["Boss"]) or str(
                        row["user_id"]
                    ) == str(id_telegram["my"]):
                        bot.send_message(
                            chat_id=str(row["user_id"]),
                            text=text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                    else:
                        bot.send_message(
                            chat_id=str(row["user_id"]), text=text
                        )
                except Exception as err:
                    logging.error(
                        "Error2: doc_control_v1.1(53) - \
                        Не удалось отправить сообщение пользователю!  - "
                        + str(err)
                        + "\n"
                    )
    except Exception as err:
        logging.error(
            "Error: doc_control_v1.1(55) - \
            Не удалось отправить сообщение пользователю!  - "
            + str(err)
        )


if __name__ == "__main__":
    main()
