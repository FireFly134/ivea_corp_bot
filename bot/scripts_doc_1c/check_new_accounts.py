import json
import logging
import smtplib
from asyncio import run
from datetime import datetime

from call_api import call

import pandas as pd

import requests

from send_email import send_email

from send_query_sql import insert_and_update_sql

from sqlalchemy import create_engine

import telegram

from work import (
    TELEGRAM_TOKEN,
    data_email,
    datas,
    header,
    id_telegram,
    ivea_metrika,
    space_id,
    web_django,
)

from .check_path import check_root_path
from .service_send_sheta import send_msg_sheta

# data for connecting to the server
engine = create_engine(ivea_metrika)
engine_web_django = create_engine(web_django)

bot = telegram.Bot(TELEGRAM_TOKEN)

s = requests.Session()
link = "https://id.entera.pro/api/v1/login"
s.post(link, headers=header, json=datas)
link = "https://passport.yandex.com/auth"

e = requests.Session()
datas2 = {"login": data_email["email"], "password": data_email["password"]}
e.post(link, data=datas2, headers=header)

mail = False
server = smtplib.SMTP_SSL("smtp.yandex.ru")
try:
    server.login(data_email["email"], data_email["password"])
    mail = True
except Exception:
    logging.error("Не верный логин или пароль, или почта не доступна.")


async def entera(
    search: str = "", document_date_from: str = "", document_date_to: str = ""
) -> tuple[str, str]:
    url: str = "https://app.entera.pro/api/v1/documents"
    name_file: str = ""
    site = s.get(
        url,
        headers=header,
        params={
            "spaceId": space_id,
            "search": search,
            "documentDateFrom": document_date_from,
            "documentDateTo": document_date_to,
            "documentType": ["OFFER", "NONSTANDARD", "UNKNOWN", "CERTIFICATE"],
        },
    )
    answer = json.loads(site.text)
    for i in range(len(answer["documents"])):
        if answer["documents"][i]["number"] == search:
            url = f"{url}/{answer['documents'][i]['id']}/file"
            name_file = str(answer["documents"][i]["pages"][0]["file"]["name"])
            return url, name_file
    if "0000" not in search:
        search = "0" + search
        url, name_file = await entera(
            search, document_date_from, document_date_to
        )
    return url, name_file


async def find_new_accounts(
    list_info: list[str],
    test: bool,
) -> int:
    counter: int = 0

    info2 = pd.read_sql(
        f"""
    SELECT
        MAX(invoice_analysis_invoice.id) AS id,
        invoice_analysis_invoice.number AS number,
        MAX(invoice_analysis_invoice.comment) AS comment,
        MAX(invoice_analysis_invoice.info) AS info,
        MAX(invoice_analysis_invoice.date_of_the_incoming_document) AS \
    date_of_the_incoming_document,
        MAX(invoice_analysis_invoice.incoming_document_number) AS \
    incoming_document_number,
        MAX(invoice_analysis_invoice.sum) AS sum,
        MAX(employee_cards_counterparty.title) AS contragent_title,
        MAX(employee_cards_counterparty.inn) AS contragent_inn
    FROM
        invoice_analysis_invoice
    INNER JOIN
        employee_cards_counterparty ON (
        invoice_analysis_invoice.counterparty_id = \
employee_cards_counterparty.id
        )
    WHERE
        number LIKE ('0000-%%')
        AND date_of_the_incoming_document > '\
{datetime.now().strftime('%Y')}-01-01'
    GROUP BY
        number
    ORDER BY
        id DESC
    LIMIT 10;
    """,
        engine_web_django,
    )
    # Что мы сделали в запросе?
    # - описали колонки которые мы хотим видеть из 2х таблиц (SELECT)
    # - Показываем что мы хотим соединить 2 таблици (INNER JOIN) колонками ...
    # invoice_analysis_invoice.counterparty_id = employee_cards_counterparty.id
    # - в этой таблице должны быть те строки в котороых в колонке number будут
    # элементы начинающиеся на '0000-' и дата не ранее 1 января этого года
    # - Потом группируем все строки с одинаковым "number" ...
    # (для этих целей у нас в SELECT все помещается в MAX) т.к. значения ...
    # должны быть индентичны, нам без разници что попадет в колонки
    # - Ну и на конец, делаем сортировку по id, тем самым берем только ...
    # ...свежие строки и при помощи limit выводим первые 10 записей.

    list_info2 = info2["number"].tolist()
    # Получаем уникальные элементы из list_info2,
    # которые отсутствуют в list_info
    unique_names = list(set(list_info2) - set(list_info))
    if test:
        unique_names.append("0000-000095")
        print("find_new_accounts list_info =", set(list_info))
        print("find_new_accounts list_info2 =", set(list_info2))
        print("find_new_accounts unique_names =", unique_names)
    for num_1c in unique_names:
        df = info2[info2["number"] == str(num_1c)]
        for idx, row in df.iterrows():
            if row["info"] != "Удален":
                logging.info(f"Accounts - {num_1c}")
                try:
                    url, name_file = await entera(
                        search=str(row["incoming_document_number"]),
                        document_date_to=str(
                            row["date_of_the_incoming_document"]
                        ),
                    )
                    try:
                        id_list: str = str(row["comment"])
                        id_list = (
                            id_list.replace(".", ",")
                            .strip("/")
                            .strip("\\")
                            .strip("?")
                        )
                        if id_list[-1:] == ",":
                            id_list = id_list[:-1]
                        info_doc = pd.read_sql(
                            f"""SELECT id, short_name
                                FROM documents WHERE id in ({id_list});""",
                            engine,
                        )
                        comment: str = ""
                        for idx2, row2 in info_doc.iterrows():
                            comment += f'{row2["short_name"]} ({row2["id"]}), '
                        comment = comment[:-2]
                    except Exception:
                        comment = str(row["comment"])
                    result = False
                    if not test:
                        result = await insert_and_update_sql(
                            f"""INSERT INTO doc_entera_1c (
                                                            num_1c,
                                                            contragent,
                                                            inn,
                                                            date_doc,
                                                            sum,
                                                            link,
                                                            comment,
                                                            name_file,
                                                            num_doc,
                                                            year
                                ) VALUES(
                                        {num_1c!r},
                                        {row['contragent_title']!r},
                                        {row['contragent_inn']!r},
                                        '{row[
                                'date_of_the_incoming_document'
                            ].strftime('%d.%m.%Y')}',
                                        {row['sum']!r},
                                        {url!r},
                                        {comment!r},
                                        {name_file!r},
                                        {row['incoming_document_number']!r},
                                        {datetime.now().strftime('%Y')!r}
                                    );"""
                        )
                    else:
                        counter += 1
                        await send_msg_sheta(
                            user_list=[str(id_telegram["my"])],
                            num_1c=str(num_1c),
                        )
                    if result:
                        counter += 1
                        await send_msg_sheta(num_1c=str(num_1c))

                except Exception:
                    text = f"Entera ошибка поиска {num_1c!r}. \
Счёт №{row['incoming_document_number']!r}, \
documentDateTo={str(row['date_of_the_incoming_document'])}"
                    logging.error(text)
            else:
                logging.info(
                    f"""Accounts have been deleted - {num_1c}
№{row['incoming_document_number']!r},
documentDateTo={str(row['date_of_the_incoming_document'])}"""
                )
            break
    return counter


async def check_delete_accounts(
    info: pd.DataFrame, list_old_num_1c: list[str], test: bool
) -> int:
    counter: int = 0
    info_del = info[info["delete"]]
    info2 = pd.read_sql(
        f"""
SELECT
    MAX(invoice_analysis_invoice.id) AS id,
    invoice_analysis_invoice.number AS number,
    MAX(invoice_analysis_invoice.comment) AS comment,
    MAX(invoice_analysis_invoice.info) AS info,
    MAX(invoice_analysis_invoice.date_of_the_incoming_document) AS \
date_of_the_incoming_document,
    MAX(invoice_analysis_invoice.incoming_document_number) AS \
incoming_document_number,
    MAX(invoice_analysis_invoice.sum) AS sum,
    MAX(employee_cards_counterparty.title) AS contragent_title,
    MAX(employee_cards_counterparty.inn) AS contragent_inn
FROM
    invoice_analysis_invoice
INNER JOIN
    employee_cards_counterparty ON (
    invoice_analysis_invoice.counterparty_id = employee_cards_counterparty.id
    )
WHERE
    number LIKE ('0000-%%')
    AND date_of_the_incoming_document > '{datetime.now().strftime('%Y')}-01-01'
    AND info = 'Удален'
GROUP BY
    number;
""",
        engine_web_django,
    )

    list_info = info_del["num_1c"].tolist()
    list_info2 = info2["number"].tolist()
    # Получаем уникальные элементы из list_info2,
    # которые отсутствуют в list_info
    unique_names = list(set(list_info2) - set(list_info))
    if test:
        unique_names.append("0000-000095")
        print("DELETE list_info =", set(list_info))
        print("DELETE list_info2 =", set(list_info2))
        print("DELETE unique_names =", unique_names)
    for num_1c in unique_names:
        if num_1c in list_old_num_1c:
            counter += 1
            await delete_accounts(info, num_1c, test)
    return counter


async def delete_accounts(info: pd.DataFrame, num_1c: str, test: bool) -> None:
    info_delete = info[info["num_1c"] == num_1c]
    for idx, row in info_delete.iterrows():
        logging.info(f"Delete order {num_1c}")
        text = f"""Счёт № {num_1c} от \
{row['date_doc']!r}
Контрагент: {row['contragent']!r}
Комментарий: {row['comment']!r}
🚫ОТМЕНА! НЕ ОПЛАЧИВАТЬ!🚫"""
        text2 = f"ОТМЕНА!....... НЕ ОПЛАЧИВАТЬ!.......\
Контрагент: ...{row['contragent']!r}.....\
сумма:...{row['sum']!r}"
        if not test:
            await insert_and_update_sql(
                f"UPDATE doc_entera_1c SET delete = True \
                         WHERE num_1c = '{num_1c}';"
            )
            await bot.send_message(chat_id=id_telegram["Boss"], text=text)

            call(
                "89253538733",
                "Автоматическое оповещение.........." + text2,
            )

            call(
                "89264942722",
                "Автоматическое оповещение.........." + text2,
            )  # Звонок Бухгалтеру.

            if mail:
                try:
                    answer = send_email(
                        list_file=[],
                        server=server,
                        text=text,
                        subject=f"ОТМЕНА! НЕ ОПЛАЧИВАТЬ! \
Счёт № {num_1c} от {row['date_doc']!r}",
                    )
                    if "Письмо с документом отправлено!" != str(answer):
                        await bot.send_message(
                            chat_id=id_telegram["my"],
                            text=answer + "\n\n" + text,
                        )
                except Exception:
                    logging.error(
                        "Не удалось отправить сообщение на \
почту."
                    )
        else:
            await bot.send_message(chat_id=id_telegram["my"], text=text)
            call(
                "89616599948",
                "Автоматическое оповещение.........." + text2,
            )
            answer = send_email(
                list_file=[],
                server=server,
                text=text,
                addressees="Kostik55555@yandex.ru",
                subject=f"ОТМЕНА! НЕ ОПЛАЧИВАТЬ! Счёт № \
{num_1c} от {row['date_doc']!r}",
            )
            await bot.send_message(
                chat_id=id_telegram["my"],
                text="test!!!\n" + answer + "\n\n",
            )
            break


async def read_scheta(test: bool = False) -> None:
    logging.info("---Start read_scheta_xls---")
    print("---Start read_scheta_xls---")
    print("Mode test =", test)

    # Заходим в БД и считываем документы которые у нас уже есть в данном году.
    info = pd.read_sql(
        f"""SELECT * FROM doc_entera_1c
            WHERE year = '{datetime.now().strftime('%Y')}';""",
        engine,
    )
    list_info = info["num_1c"].tolist()

    counter_new = await find_new_accounts(list_info, test)
    counter_del = await check_delete_accounts(info, list_info, test)

    logging.info(f"New accounts total: {counter_new}")
    logging.info(f"Delete accounts total: {counter_del}")


if __name__ == "__main__":
    check_root_path()
    run(read_scheta(True))
