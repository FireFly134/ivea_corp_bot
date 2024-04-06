from asyncio import run
from datetime import datetime

import pandas as pd

from send_query_sql import insert_and_update_sql

from sqlalchemy import create_engine

import telegram
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from work import (
    TELEGRAM_TOKEN,
    id_telegram,
    ivea_metrika,
    web_django,
)

from .check_path import check_root_path
from .service_abc import main as service_abc

engine = create_engine(ivea_metrika)  # данные для соединие с БД
engine2 = create_engine(web_django)


async def send_msg_sheta(
    num_1c: str,
    msg: str = "",
    user_list: list[str] = [str(id_telegram["Boss"]), str(id_telegram["my"])],
    year: str = str(datetime.now().strftime("%Y")),
) -> None:
    bot = telegram.Bot(TELEGRAM_TOKEN)
    info_sheta = pd.read_sql(
        f"""SELECT * FROM invoice_analysis_invoice
                                WHERE number = '{num_1c}'""",
        engine2,
    )
    info_df = pd.read_sql(
        f"""SELECT * FROM doc_entera_1c
        WHERE num_1c = '{num_1c}' and year = '{year}';""",
        engine,
    )
    info2 = pd.read_sql(
        "SELECT * FROM employee_cards_pricechangelog;",
        engine2,
    )
    for idx, row in info_df.iterrows():
        price_analysis: str = ""
        inaccuracy: int = 11  # разница цены которая не считается
        table_type, total = service_abc(inn=str(row["inn"]))
        f_sum_doc = (
            "{:,}".format(float(row["sum"]))
            .replace(",", "\u00A0")
            .replace(".", ",")
        )
        df_isin = info_sheta[info_sheta["number"].isin([num_1c])]
        for idx2, row2 in df_isin.iterrows():
            df_info_isin = info2[
                info2["nomenclature"].isin([row2["nomenclature"]])
            ]
            df_info_isin = df_info_isin[
                df_info_isin["counterparty_id"].isin([row2["counterparty_id"]])
            ]
            if not df_info_isin.empty:
                min_price: float = round(
                    float(min(df_info_isin["min_price"].to_list())), 2
                )
                max_price: float = round(
                    float(min(df_info_isin["max_price"].to_list())), 2
                )
                price_one: float = round(
                    float(row2["total"]) / float(row2["amount"]), 2
                )
                if (
                    price_one < (min_price + inaccuracy)
                    and "🟩" not in price_analysis
                ):
                    price_analysis += "🟩"
                elif (min_price + inaccuracy) < price_one < (
                    max_price + inaccuracy
                ) and "🟨" not in price_analysis:
                    price_analysis += "🟨"
                elif (
                    price_one > (max_price + inaccuracy)
                    and "🟥" not in price_analysis
                ):
                    price_analysis += "🟥"
            elif "❗️" not in price_analysis:
                price_analysis += "❗️"
        if table_type == "" and total == "0,00":
            text = f"Заполните данные по новому контрагенту: \
{row['contragent']}"
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Заполнить данные",
                        callback_data=f"explanation-{row['id']}",
                    ),
                ]
            ]
            await insert_and_update_sql(
                f"""INSERT INTO new_kontragent_in_sheta
                                        (
                                        id_entera_1c, text, explanation
                                        )
                                        VALUES('{row['id']}','{text}', '');"""
            )
            await bot.send_message(
                chat_id=id_telegram["my"],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            await bot.send_message(
                chat_id=id_telegram["supply"],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            # supply
        else:
            text = f"Счёт №{row['num_doc']} от {row['date_doc']} \
на сумму {f_sum_doc} руб.\n\n{table_type} Контрагент: {row['contragent']}\
({total} руб.)\n\nКомментарий: {row['comment']}{msg}\n{price_analysis}"
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Отправить",
                        callback_data=f"send_email_1c_doc-{row['id']}",
                    ),
                    InlineKeyboardButton(
                        "Состав", callback_data=f"item_1c_doc-{row['id']}"
                    ),
                ]
            ]
            for id_t in user_list:
                await bot.send_message(
                    chat_id=id_t,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )


if __name__ == "__main__":
    check_root_path()
    run(
        send_msg_sheta(
            num_1c="0000-000134", user_list=[str(id_telegram["my"])]
        )
    )
    # [str(id_telegram["Boss"]), str(id_telegram["my"])]
