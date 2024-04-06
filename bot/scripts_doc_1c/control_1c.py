import logging
import os.path
from asyncio import run
from datetime import datetime, timedelta

from call_api import call

import pandas as pd

from send_query_sql import insert_and_update_sql

from sqlalchemy import create_engine

import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from work import (
    TELEGRAM_TOKEN,
    id_telegram,
    ivea_metrika,
    web_django,
    working_folder_1c,
    y_token,
)

import yadisk

from .check_new_accounts_class import read_scheta as check_new_accounts
from .check_path import check_root_path

# data for connecting to the server
engine = create_engine(ivea_metrika)
engine2 = create_engine(web_django)

bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

logging.info("---Start control_1c!---")


async def download(
    name1: str = "downloaded_file.csv",
    name2: str = "Scheta.xls",
    name3: str = "Kontragent.csv",
    y_path1: str = "/test_dokument/Reestr.csv",
    y_path2: str = "/test_schet/Scheta.xls",
    y_path3: str = "/test_kontragent/Kontragent.csv",
) -> str:
    """It's function for download 3 files, from yandex disc
    Reestr.csv = downloaded_file.csv, Scheta.xls and Kontragent.csv"""
    logging.info("---Start download files---")
    dict_paths = {
        name1: y_path1,
        name2: y_path2,
        name3: y_path3,
    }
    if not os.path.isdir(working_folder_1c):
        os.mkdir(working_folder_1c)
    try:
        # Connecting to Yandex.disk using a token
        y = yadisk.YaDisk(token=y_token)
        for name in dict_paths.keys():
            if y.exists(dict_paths[name]):
                y.download(dict_paths[name], f"{working_folder_1c}{name}")
                logging.info(f'Update file "{name}"')
            else:
                err_msg: str = (
                    f"No directory or file was found... '{dict_paths[name]}'"
                )
                logging.error(err_msg)
                await bot.send_message(
                    chat_id=id_telegram["my"],
                    text=err_msg,
                )
                return err_msg
    except Exception as ex:
        err_msg = f'The problem with the YANDEX token: "{ex}"'
        logging.error(err_msg)
        await bot.send_message(
            chat_id=id_telegram["my"],
            text=err_msg,
        )
        return err_msg
    return "Success!"


async def processing_information_from_a_file_csv(
    df: pd.DataFrame,
) -> tuple[str, str, str, str, float, float]:
    """it's function for test processing information"""
    df = df.loc[df["Ссылка"] == "Поступление на расчетный счет"]
    sms: str = "Новые оплаты:\n"
    sms_osnov: str = 'По договору "Основной" поступила оплата:\n'
    sms_for_tel: str = "Новые оплаты:\n"
    sms_osnov_for_tel: str = 'По договору "Основной" поступила оплата:\n'
    summa: float = 0.0
    summa_osnov: float = 0.0
    q: int = 0
    q_osnov: int = 0
    info = pd.read_sql(
        "SELECT * FROM save_sended_new_payments;",
        engine,
    )
    if not df.empty:
        for idx, row in df.iterrows():
            price = float(
                str(row["Сумма документа"])
                .replace("\xa0", "")
                .replace(",", ".")
            )
            num = row["Номер"]
            num_input = row["Вх. номер"]
            check = info[info["date"] == row["Дата"]]
            check = check[check["price"] == price]
            check = check[check["num"] == num]
            check = check[check["num_input"] == num_input]
            if check.empty:
                text1 = (
                    str(row["Договор"])
                    .strip("договор")
                    .strip("Договор")
                    .strip("ДОГОВОР")
                    .strip("№")
                    .strip("поставки")
                    .strip("счет")
                    .strip("Счет")
                    .strip("счету")
                    .strip("СЧЕТУ")
                    .strip("сч")
                    .strip("Сч")
                    .strip("СЧ")
                    .strip("-")
                    .strip("подряда")
                    .strip("на сервисное обслуживание очистных сооружений")
                )
                if "специф" in text1:
                    text1 = text1.split("специф")[1].split("от")[0].strip()
                elif "спец" in text1:
                    text1 = text1.split("спец")[1].split("от")[0].strip()
                else:
                    text1 = text1.split("от")[0].strip()
                if "_" in text1:
                    text1 = text1.split("_")[0]
                if "основной" in text1.lower():
                    q_osnov += 1
                    sms_osnov += f"{q_osnov}) \
{row['Платильщик']} - {price} руб."
                    sms_osnov_for_tel += sms_osnov + ".....\n"
                    sms_osnov += "\n"
                    summa_osnov += price
                else:
                    q += 1
                    text2 = pd.read_sql_query(
                        f"""SELECT short_name FROM documents
                            WHERE number_doc LIKE ('%%{text1}%%');""",
                        engine,
                    )
                    try:
                        sms += f'{q}) {text2.loc[0, "short_name"]} \
("{row["Платильщик"]}") - {price} руб.'
                        sms_for_tel += sms + ".....\n"
                        sms += "\n"
                    except Exception:
                        logging.info(
                            "Не удалось найти краткое название договора."
                        )
                        sms += f'{q}) {row["Договор"]} \
("{row["Платильщик"]}") - {price} руб.'
                        sms_for_tel += sms + ".....\n"
                        sms += "\n"
                    summa += price
                await insert_and_update_sql(
                    """
INSERT INTO save_sended_new_payments (date, num_input, num, price)
    VALUES(:date, :num_input, :num, :price);
""",
                    param={
                        "date": row["Дата"],
                        "num_input": num_input,
                        "num": num,
                        "price": price,
                    },
                )
    return (
        sms,
        sms_osnov,
        sms_for_tel,
        sms_osnov_for_tel,
        summa,
        summa_osnov,
    )


async def read_csv() -> None:
    logging.info("---Start read_csv---")
    df = pd.read_csv(f"{working_folder_1c}downloaded_file.csv", delimiter="\t")
    if datetime.now().strftime("%w") in ["0", "1", "6"]:
        week = datetime.now().strftime("%w")
        day = 1
        if week == "0":
            day = 2
        elif week == "1":
            day = 3
        df = df.dropna().replace("Основной", "Основной договор")
        df = df[
            df["Дата"].isin(
                [
                    str(
                        (datetime.now() - timedelta(days=day)).strftime(
                            "%d.%m.%Y"
                        )
                    )
                ]
            )
        ]

    else:
        df = df.dropna().replace("Основной", "Основной договор")
        df = df[
            df["Дата"].isin(
                [
                    str(
                        (datetime.now() - timedelta(days=6)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(
                        (datetime.now() - timedelta(days=5)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(
                        (datetime.now() - timedelta(days=4)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(
                        (datetime.now() - timedelta(days=3)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(
                        (datetime.now() - timedelta(days=2)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(
                        (datetime.now() - timedelta(days=1)).strftime(
                            "%d.%m.%Y"
                        )
                    ),
                    str(datetime.now().strftime("%d.%m.%Y")),
                ]
            )
        ]
    (
        sms,
        sms_osnov,
        sms_for_tel,
        sms_osnov_for_tel,
        summa,
        summa_osnov,
    ) = await processing_information_from_a_file_csv(df)

    if (
        sms != "Новые оплаты:\n"
        or sms_osnov != 'По договору "Основной" поступила оплата:\n'
    ):
        if sms != "Новые оплаты:\n":
            if "2)" in sms and "1)" in sms:
                sms += f"на общую сумму {summa} руб."
            await bot.send_message(chat_id=id_telegram["Boss"], text=sms)
            await bot.send_message(chat_id=id_telegram["my"], text=sms)
            call(
                "89253538733",
                "Автоматическое оповещение.........." + sms_for_tel,
            )
            # call("89616599948",
            # "Автоматическое оповещение.........." + sms_for_tel)
        if sms_osnov != 'По договору "Основной" поступила оплата:\n':
            if "2)" in sms_osnov and "1)" in sms_osnov:
                sms_osnov += f"на общую сумму {summa_osnov} руб."
            await bot.send_message(chat_id=id_telegram["Boss"], text=sms_osnov)
            await bot.send_message(chat_id=id_telegram["my"], text=sms_osnov)
            call(
                "89253538733",
                "Автоматическое оповещение.........." + sms_osnov_for_tel,
            )
            # call("89616599948",
            # "Автоматическое оповещение.........."
            # + sms_osnov_for_tel)


async def check_update_kontragent_csv(
    send_msg: bool = True,
) -> None:
    logging.info("---Start check_update_kontragent_csv---")
    df = pd.read_csv(
        f"{working_folder_1c}Kontragent.csv",
        delimiter="\t",
        lineterminator="\n",
    )
    df = df.drop("Имя досье\r", axis=1)
    df = df.dropna()
    info = pd.read_sql("SELECT * FROM employee_cards_counterparty;", engine2)
    list_info = info["inn"].to_list()
    for idx, row in df.iterrows():
        inn = str(row["ИНН"]).replace(".0", "")

        if inn not in list_info:
            try:
                await insert_and_update_sql(
                    f"""INSERT INTO employee_cards_counterparty (
                    inn,
                    title,
                    group_k,
                    type_k,
                    total,
                    load_by_month,
                    standard_deviation
                    ) VALUES(
                    '{inn}',
                    '{row['Полное наименование']}',
                    '{row['Группа']}',
                    '{row['Вид контрагента']}',
                    '0',
                    '0',
                    '0'
                    );""",
                    eng=engine2,
                )
                text = "Добавлен новый контрагент\n"
                if str(row["Полное наименование"]) != "nan":
                    text += f"Полное наименование: \
{row['Полное наименование']}\n"
                if str(row["Группа"]) != "nan":
                    text += f"Группа: {row['Группа']}\n"
                if str(row["Вид контрагента"]) != "nan":
                    text += f"Вид контрагента: {row['Вид контрагента']}\n"
                text += f"ИНН контрагента: {inn}\n"
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Заполнить данные",
                            callback_data=f"update_k_info-{int(inn)}",
                        )
                    ]
                ]
                if send_msg:
                    for user_name in ["supply", "my", "Boss"]:
                        await bot.send_message(
                            chat_id=id_telegram[user_name],
                            text=text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
            except Exception as err:
                text = f"control_1c функция check_update_kontragent_csv \
{err}"
                await bot.send_message(chat_id=id_telegram["my"], text=text)
        else:
            check_info = info[info["inn"] == inn]
            for idx2, row2 in check_info.iterrows():
                if row["Полное наименование"] != row2["title"]:
                    await insert_and_update_sql(
                        f"""UPDATE employee_cards_counterparty
                        SET title = '{row['Полное наименование']}'
                        WHERE inn = '{inn}';""",
                        eng=engine2,
                    )
                if row["Группа"] != row2["group_k"]:
                    await insert_and_update_sql(
                        f"""UPDATE employee_cards_counterparty
                        SET group_k = '{row['Группа']}'
                        WHERE inn = '{inn}';""",
                        eng=engine2,
                    )
                if row["Вид контрагента"] != row2["type_k"]:
                    await insert_and_update_sql(
                        f"""UPDATE employee_cards_counterparty
                        SET type_k = '{row['Вид контрагента']}'
                        WHERE inn = '{inn}';""",
                        eng=engine2,
                    )
                break


async def rw_scheta() -> None:
    logging.info("---Start rw_scheta---")
    list_df = pd.read_excel(f"{working_folder_1c}Scheta.xls")[
        "Номенклатура"
    ].to_list()
    list_info = pd.read_sql(
        "SELECT name FROM main_accounting_for_purchased_equipment;",
        engine2,
    )["name"].to_list()
    # Получаем уникальные элементы из list_df,
    # которые отсутствуют в list_info
    unique_names = list(set(list_df) - set(list_info))

    for name in unique_names:
        try:
            await insert_and_update_sql(
                f"INSERT INTO main_accounting_for_purchased_equipment (name) \
VALUES('{name}')",
                eng=engine2,
            )
        except Exception:
            logging.error(f"Failed to insert name: {name}")


if __name__ == "__main__":
    check_root_path()
    # Download files in Yandex disk
    run(download())
    # read csv file Reestr
    # run(read_csv())
    # check the file for new contractors and record the results in the database
    run(check_update_kontragent_csv())
    # read file "scheta"
    run(check_new_accounts())
    run(rw_scheta())
