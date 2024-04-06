# coding=UTF-8
#
#
import logging
from asyncio import run
from datetime import datetime

import pandas as pd

from sqlalchemy import create_engine

import telegram

from .send_query_sql import insert_and_update_sql
from .work import (
    TELEGRAM_TOKEN,
    id_telegram,
    ivea_metrika,
)

engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером
bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)


async def main() -> None:
    """This function looks into the database for the availability of new
    documents and notifies in a telegram if there are such agreements."""
    logging.info("Checking for new documents...")
    info: pd.DataFrame = pd.read_sql_query(
        """SELECT id, short_name, counterparty, number_doc, subject_contract
            FROM documents
            WHERE send_sms_new_doc = 'false' ORDER BY id ASC;""",
        engine2,
    )
    info2 = pd.read_sql_query(
        "SELECT doc_name, sum_stage, date_end, work_name FROM doc_date;",
        engine2,
    )
    if not info.empty:
        logging.info(f"I find {len(info)} new documents!")
        if len(info) == 1:
            text_begin: str = "В работу добавлен новый договор:"
        else:
            text_begin = "В работу добавлены новые договора:"
        await bot.send_message(
            chat_id=id_telegram["Boss"], text=text_begin, parse_mode="HTML"
        )
        await bot.send_message(chat_id=id_telegram["my"], text=text_begin)
        for idx, row in info.iterrows():
            test_stage_for_msg: str = ""
            sum_stage: float = 0.0
            df = info2[info2["doc_name"] == row["short_name"]]
            for idx2, row2 in df.iterrows():
                sum_stage += float(row2["sum_stage"])
                f_row_sum_stage = (
                    "{:,}".format(row2["sum_stage"])
                    .replace(",", "\u00A0")
                    .replace(".", ",")
                )
                test_stage_for_msg += f"- {row2['work_name']} / \
{f_row_sum_stage} / {row2['date_end'].strftime('%d.%m.%Y')}\n"
            f_sum_stage = (
                "{:,}".format(sum_stage)
                .replace(",", "\u00A0")
                .replace(".", ",")
            )
            text: str = f"""<b>{row['id']} / {row['counterparty']} /\
{row['number_doc']} / {row['short_name']} / {f_sum_stage} руб.</b>

{test_stage_for_msg}
<b>Предмет договора:</b> {row['subject_contract']}"""
            if text != "":
                await bot.send_message(
                    chat_id=id_telegram["Boss"], text=text, parse_mode="HTML"
                )
                await bot.send_message(
                    chat_id=id_telegram["my"], text=text, parse_mode="HTML"
                )
            logging.info(text)
        list_doc_id: str = str(info["id"].to_list()).strip("[").strip("]")
        await insert_and_update_sql(
            f"UPDATE documents SET \
        send_sms_new_doc = 'true' WHERE id in ({list_doc_id});"
        )

    else:
        logging.info("There are no new documents.")


async def check_date_work_group() -> None:
    info: pd.DataFrame = pd.read_sql_query(
        f"SELECT * FROM user_worker_key_corp \
        WHERE date_ower_num_group < '{datetime.now()}';",
        engine2,
    )
    for idx, row in info.iterrows():
        sms = f"""Время нахождения в бригаде вышло, \
пожалуйста обновите информацию.
ФИО: {row['name']}
Номер телефона: {row['tel']}"""
        keyboard = [
            [
                telegram.InlineKeyboardButton(
                    "Определить в бригаду",
                    callback_data=f"reg_worker_next-{row['id']}",
                )
            ]
        ]
        await bot.send_message(
            chat_id=id_telegram["Boss"],
            text=sms,
            reply_markup=telegram.InlineKeyboardMarkup(keyboard),
        )
        await bot.send_message(
            chat_id=id_telegram["My"],
            text=sms,
            reply_markup=telegram.InlineKeyboardMarkup(keyboard),
        )


async def check_open_location_today() -> None:
    info_good_boys: pd.DataFrame = pd.read_sql_query(
        f"SELECT name FROM user_worker_key_corp \
WHERE date_time > '{datetime.now().strftime('%Y-%m-%d 01:00:00.000')}';",
        engine2,
    )
    good_boys: list[str] = info_good_boys["name"].tolist()
    info_bad_boys = pd.read_sql_query(
        "SELECT name FROM user_worker_key_corp;", engine2
    )
    bad_boys: list[str] = info_bad_boys["name"].tolist()
    sms = ""
    if good_boys != []:
        sms = "Сегодня включили геолокацию:"
        for name in good_boys:
            if name in bad_boys:
                bad_boys.remove(name)
        for i in range(len(good_boys)):
            sms += f"\n{i+1}) {good_boys[i]}"
    sms += "\nГеолокацию не включили:"
    for i in range(len(bad_boys)):
        sms += f"\n{i+1}) {bad_boys[i]}"
    await bot.send_message(chat_id=id_telegram["Boss"], text=sms)
    # await bot.send_message(chat_id=id_telegram["My"], text=sms)


if __name__ == "__main__":
    # running checking for new documents...
    run(main())
    # We find out the time on the server and convert it to the form we need
    time = str(datetime.now().strftime("%H:%M:00"))
    if (
        time == "06:30:00"
        and datetime.now().strftime("%w") != "0"
        and datetime.now().strftime("%w") != "6"
    ):
        logging.info("Activate the reminder")
        run(check_date_work_group())
    if (
        time == "07:00:00"
        and datetime.now().strftime("%w") != "0"
        and datetime.now().strftime("%w") != "6"
    ):
        logging.info("checking the inclusion of geolocation")
        run(check_open_location_today())
