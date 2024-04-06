import json
import logging
import smtplib
from asyncio import run
from datetime import datetime
from typing import Any, Tuple

from call_api import call

import pandas as pd

import requests

from send_email import send_email

from send_msg_telegram import send_msg

from send_query_sql import insert_and_update_sql

from sqlalchemy import create_engine, text

from work import (
    data_email,
    datas,
    header,
    id_telegram,
    ivea_metrika,
    numbers_telephone,
    space_id,
    web_django,
)

from .check_path import check_root_path
from .service_send_sheta import send_msg_sheta


class CheckNewAccounts:
    def __init__(self, engine: Any, engine_web_django: Any) -> None:
        self.engine = engine
        self.engine_web_django = engine_web_django
        self.year = datetime.now().strftime("%Y")
        self.first_day_in_year = f"{self.year}-01-01"

        self.info: pd.DataFrame
        self.list_info: list[Any]
        self.get_info_doc_entera_1c()

        self.entera_session = requests.Session()
        self.entera_session.post(
            url="https://id.entera.pro/api/v1/login",
            headers=header,
            json=datas,
        )
        self.begin_general_sql_text = """
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
        AND date_of_the_incoming_document > :first_day_in_year"""
        # Что мы сделали в запросе?
        # - описали колонки которые мы хотим видеть из 2х таблиц (SELECT)
        # - Показываем что мы хотим соединить 2 таблици (INNER JOIN) колонками
        # invoice_analysis_invoice.counterparty_id =
        # employee_cards_counterparty.id
        # - в этой таблице должны быть те строки в котороых в колонке number
        # будут элементы начинающиеся на '0000-'
        # и дата не ранее 1 января этого года...

    def get_info_doc_entera_1c(self) -> None:
        text_sql = text(
            "SELECT * FROM doc_entera_1c WHERE year = :year;"
        ).bindparams(year=self.year)

        self.info = pd.read_sql(
            text_sql,
            self.engine,
        )
        self.list_info = self.info["num_1c"].tolist()

    def entera(
        self,
        search: str,
        document_date_from: str = "",
        document_date_to: str = "",
    ) -> tuple[str, str]:
        url: str = "https://app.entera.pro/api/v1/documents"
        name_file: str = ""
        site = self.entera_session.get(
            url,
            headers=header,
            params={
                "spaceId": space_id,
                "search": search,
                "documentDateFrom": document_date_from,
                "documentDateTo": document_date_to,
                "documentType": [
                    "OFFER",
                    "NONSTANDARD",
                    "UNKNOWN",
                    "CERTIFICATE",
                ],
            },
        )
        answer = json.loads(site.text)
        for i in range(len(answer["documents"])):
            if answer["documents"][i]["number"] == search:
                url = f"{url}/{answer['documents'][i]['id']}/file"
                name_file = str(
                    answer["documents"][i]["pages"][0]["file"]["name"]
                )
                return url, name_file
        if "0000" not in search:
            search = "0" + search
            url, name_file = self.entera(
                search, document_date_from, document_date_to
            )
        return url, name_file

    def find_new_accounts(self) -> Tuple[list[Any], pd.DataFrame]:
        text_sql = text(
            self.begin_general_sql_text
            + """
        GROUP BY
            number
        ORDER BY
            id DESC
        LIMIT 10;
        """
        ).bindparams(first_day_in_year=self.first_day_in_year)
        # ...
        # - Потом группируем все строки с одинаковым "number"
        # (для этих целей у нас в SELECT все помещается в MAX) т.к. значения
        # должны быть индентичны, нам без разници что попадет в колонки
        # - Ну и на конец, делаем сортировку по id, тем самым берем только
        # свежие строки и при помощи limit выводим первые 10 записей.

        info = pd.read_sql(text_sql, self.engine_web_django)
        list_num_1c = info["number"].tolist()
        unique_names = self.get_list_unique_names(list_num_1c, self.list_info)
        return unique_names, info

    def check_delete_accounts(self) -> list[Any]:
        info_del = self.info[self.info["delete"]]
        text_sql = text(
            self.begin_general_sql_text
            + """
        AND info = 'Удален'
    GROUP BY
        number;
    """
        ).bindparams(first_day_in_year=self.first_day_in_year)
        info = pd.read_sql(text_sql, self.engine_web_django)
        list_num_1c_del = info_del["num_1c"].tolist()
        list_num_1c_del2 = info["number"].tolist()
        unique_names = self.get_list_unique_names(
            list_num_1c_del2, list_num_1c_del
        )
        return unique_names

    def generation_text_sql(self, num_1c: str, row: Any) -> Any:
        logging.info(f"Accounts - {num_1c}")
        url, name_file = self.entera(
            search=str(row["incoming_document_number"]),
            document_date_to=str(row["date_of_the_incoming_document"]),
        )
        try:
            id_list: str = str(row["comment"])
            id_list = (
                id_list.replace(".", ",").strip("/").strip("\\").strip("?")
            )
            if id_list[-1:] == ",":
                id_list = id_list[:-1]
            info_doc = pd.read_sql(
                f"""SELECT id, short_name
                       FROM documents WHERE id in ({id_list});""",
                self.engine,
            )
            comment: str = ""
            for idx2, row2 in info_doc.iterrows():
                comment += f'{row2["short_name"]} ({row2["id"]}), '
            comment = comment[:-2]
        except Exception:
            comment = str(row["comment"])
        text_sql = text(
            """
INSERT INTO doc_entera_1c (
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
           :num_1c,
           :contragent,
           :inn,
           :date_doc,
           :sum,
           :link,
           :comment,
           :name_file,
           :num_doc,
           :year
);
"""
        ).bindparams(
            num_1c=num_1c,
            contragent=row["contragent_title"],
            inn=row["contragent_inn"],
            date_doc=row["date_of_the_incoming_document"].strftime("%d.%m.%Y"),
            sum=row["sum"],
            link=url,
            comment=comment,
            name_file=name_file,
            num_doc=row["incoming_document_number"],
            year=self.year,
        )
        return text_sql

    @staticmethod
    def generation_text_about_del(
        num_1c: Any, row: dict[str, Any]
    ) -> Tuple[str, str]:
        msg = f"""Счёт № {num_1c} от \
{row['date_doc']}
Контрагент: {row['contragent']!r}
Комментарий: {row['comment']}
Сумма: {row['sum']}
🚫ОТМЕНА! НЕ ОПЛАЧИВАТЬ!🚫"""
        text_for_call = f"ОТМЕНА!....... НЕ ОПЛАЧИВАТЬ!.......\
Контрагент: ...{row['contragent']}.....\
сумма:...{row['sum']}"
        return msg, text_for_call

    @staticmethod
    def get_list_unique_names(
        list_names: list[str], list_names2: list[str]
    ) -> list[Any]:
        # Получаем уникальные элементы из list_names,
        # которые отсутствуют в list_info
        unique_names: list[str] = list(set(list_names) - set(list_names2))
        return unique_names


def email_connection(
    email: str = data_email["email"], password: str = data_email["password"]
) -> Tuple[bool, smtplib.SMTP_SSL]:
    connect_mail = False
    email_session = requests.Session()
    email_session.post(
        url="https://passport.yandex.com/auth",
        data={
            "login": email,
            "password": password,
        },
        headers=header,
    )
    server: smtplib.SMTP_SSL = smtplib.SMTP_SSL("smtp.yandex.ru")
    try:
        server.login(email, password)
        connect_mail = True
    except Exception:
        logging.error("Не верный логин или пароль, или почта не доступна.")
    return connect_mail, server


async def delete_accounts(
    cna: CheckNewAccounts, num_1c: Any, list_tel_numbers: list[str]
) -> None:
    info_delete = cna.info[cna.info["num_1c"] == num_1c]
    connect_mail, server = email_connection()
    for idx, row in info_delete.iterrows():
        logging.info(f"Delete order {num_1c}")
        msg, text_for_call = cna.generation_text_about_del(num_1c, row)

        await insert_and_update_sql(
            "UPDATE doc_entera_1c SET delete = True \
                     WHERE num_1c = :num_1c;",
            param={"num_1c": num_1c},
        )
        await send_msg(user_id=id_telegram["Boss"], msg=msg)
        for num_tel in list_tel_numbers:
            call(
                user_tel=num_tel,
                user_text="Автоматическое оповещение.........."
                + text_for_call,
            )

        if connect_mail:
            try:
                answer = send_email(
                    list_file=[],
                    server=server,
                    text=msg,
                    subject=f"ОТМЕНА! НЕ ОПЛАЧИВАТЬ! \
Счёт № {num_1c} от {row['date_doc']!r}",
                )
                if "Письмо с документом отправлено!" != str(answer):
                    await send_msg(
                        user_id=id_telegram["my"],
                        msg=answer + "\n\n" + msg,
                    )
            except Exception:
                logging.error(
                    "Не удалось отправить сообщение на \
почту."
                )
    return


async def read_scheta() -> None:
    logging.info("---Start read_scheta_xls---")
    counter_new: int = 0
    counter_del: int = 0
    engine = create_engine(ivea_metrika)
    engine_web_django = create_engine(web_django)
    cna: CheckNewAccounts = CheckNewAccounts(
        engine=engine, engine_web_django=engine_web_django
    )

    list_unique_num1c, info_new_accounts = cna.find_new_accounts()
    for num_1c in list_unique_num1c:
        df = info_new_accounts[info_new_accounts["number"] == str(num_1c)]
        for idx, row in df.iterrows():
            if row["info"] != "Удален":
                try:
                    text_sql = cna.generation_text_sql(num_1c, row)
                    result = await insert_and_update_sql(text_sql)
                    if result:
                        counter_new += 1
                        await send_msg_sheta(num_1c=str(num_1c))
                except Exception:
                    text_err = f"Entera ошибка поиска {num_1c!r}. \
       Счёт №{row['incoming_document_number']!r}, \
       documentDateTo={str(row['date_of_the_incoming_document'])}"
                    logging.error(text_err)
            else:
                logging.info(
                    f"""Accounts have been deleted - {num_1c}
       №{row['incoming_document_number']!r},
       documentDateTo={str(row['date_of_the_incoming_document'])}"""
                )
            break

    list_unique_num1c_for_del = cna.check_delete_accounts()
    for num_1c in list_unique_num1c_for_del:
        if num_1c in cna.list_info:
            counter_del += 1
            await delete_accounts(cna, num_1c, numbers_telephone)

    logging.info(f"New accounts total: {counter_new}")
    logging.info(f"Delete accounts total: {counter_del}")
    return


if __name__ == "__main__":
    check_root_path()
    run(read_scheta())
