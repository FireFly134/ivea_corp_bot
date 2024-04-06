# coding=UTF-8
#
#
import datetime
import json
import logging
import smtplib as smtp
from threading import Thread
from typing import Any

import bs4

import requests

from sqlalchemy import create_engine

from update_price import main as update_price

from .work import data_email, db
from ..send_email import send_email

engine = create_engine(db, encoding="utf8")

data_json: dict[str, Any] = {}


def exchange_def() -> None:
    global data_json
    exchange: str = ""
    try:
        res = requests.get("https://www.cnprussia.ru/")
        soup = bs4.BeautifulSoup(res.text, "lxml")
        exchange = (
            soup.find("div", class_="slogan-2")
            .text.split("-")[1]
            .split("руб")[0]
            .strip()
        )

    except Exception as ex:
        logging.error(ex)
    if exchange:
        if exchange.isnumeric():
            data_json.update({"rub": int(exchange)})
            print("Курс =", exchange, "руб.")
    else:
        logging.error("No data (exchange)")


def parsing(url: str, type_name: str) -> None:
    global data_json
    data: list[Any] = list()
    headers: dict[int, str] = {
        0: "Тип",
        1: "Артикул",
        2: "Название",
        3: "Наличие",
        4: "Свободно",
        5: "Ожидаемая дата поступления",
    }
    try:
        soup = bs4.BeautifulSoup(requests.get(url).text, "lxml")
        if "Будущие поставки" in type_name:
            # Поменялась таблица с будущими поставками

            rows = soup.find(
                "table",
                class_="table table-bordered anchor-table table-future",
            ).find_all("tr")
            for row in rows:
                item: dict[Any, Any] = {}
                cells = row.find_all("td")
                if cells:
                    for index in headers:
                        try:
                            if index == 0:
                                item[headers[0]] = type_name
                            elif index == 3:
                                count = 0
                                if str(cells[2].text).isnumeric():
                                    count += int(cells[2].text)
                                if str(cells[5].text).isnumeric():
                                    count += int(cells[5].text)
                                if str(cells[8].text).isnumeric():
                                    count += int(cells[8].text)
                                item[headers[int(int(index))]] = count
                            elif index == 4:
                                free = 0
                                if str(cells[4].text).isnumeric():
                                    free += int(cells[4].text)
                                if str(cells[7].text).isnumeric():
                                    free += int(cells[7].text)
                                if str(cells[10].text).isnumeric():
                                    free += int(cells[10].text)
                                item[headers[int(int(index))]] = free
                            elif index == 5:
                                item[headers[5]] = "07.10.1994"
                            else:
                                item[headers[int(int(index))]] = cells[
                                    index - 1
                                ].text
                        except Exception as err:
                            print(f"function 'parsing' - 75 page -\n{err}")
                    data.append(item)
        else:
            rows = soup.find(
                "table", class_="table table-bordered anchor-table"
            ).find_all("tr")
            for row in rows:
                item = {}
                cells = row.find_all("td")
                if cells:
                    for index in headers:
                        try:
                            if index == 0:
                                item[headers[0]] = type_name
                            elif index == 5:
                                item[headers[5]] = "07.10.1994"
                            else:
                                item[headers[int(int(index))]] = cells[
                                    index
                                ].text
                        except Exception as err:
                            print(f"function 'parsing' - 114 page -\n{err}")
                    data.append(item)
        print(f"{type_name} - завершено.")
    except Exception as ex:
        logging.error(ex)
        send_error(str(ex))
    if data:
        # data_json.update({'data': data})  #
        data_json["data"] += data
    else:
        logging.error("No data")
        send_error("No data")


def send_error(error: str) -> None:
    send_email_list = [
        "kostik55555@yandex.ru",
        "menace34@bk.ru",
    ]
    # 'info@ivea-water.ru',
    mail: bool = False
    for s_e in send_email_list:
        server = smtp.SMTP_SSL("smtp.yandex.ru")
        try:
            server.login(data_email["email"], data_email["password"])
            mail = True
        except Exception:
            logging.error("Не верный логин или пароль, или почта не доступна.")

        if mail:
            send_email(
                list_file=[],
                server=server,
                addressees=s_e,
                text=f"Здравствуйте. На сервере произошла ошибка - \
{str(error)}",
                subject='Ошибка в файле "cnp_main" при считывании данных',
            )


def save_json() -> None:
    with open(
        f"./ivea_corp/cnp/json_files/{datetime.date.today()}_data.json",
        "w",
    ) as file:
        json.dump(data_json, file)


def save_json_in_sql() -> None:
    with open(
        f"./ivea_corp/cnp/json_files/{datetime.date.today()}_data.json"
    ) as json_file:
        # data = json_file.read()
        data = json.load(json_file)
    # engine.execute(f"UPDATE data_json
    # SET json = '{{\"data{data.split('data')[1]}' WHERE id = 1")
    text = str(data).replace("'", "''")
    engine.execute(f"UPDATE data_json SET json = '{text}' WHERE id = 1")


if __name__ == "__main__":
    print("Узнаем курс.")
    exchange_def()
    print("Парсим таблицы с официального сайта.")
    data_json.update({"data": []})
    # Стоит условике на "Будущие поставки"
    a = Thread(
        target=parsing,
        args=(
            "https://www.cnprussia.ru/gde-kupit/future/",
            "Будущие поставки",
        ),
    )
    b = Thread(
        target=parsing,
        args=(
            "https://www.cnprussia.ru/stocks/?region=74&group=\
%D0%9A%D0%B0%D0%BD%D0%B0%D0%BB%D0%B8%D0%B7%D0%B0%D1%86%D0%B8%D0%BE%D0%BD%D0%\
BD%D1%8B%D0%B5+%D0%BD%D0%B0%D1%81%D0%BE%D1%81%D1%8B+%28WQ%29",
            "Остатки на центральном складе",
        ),
    )
    c = Thread(
        target=parsing,
        args=(
            "https://www.cnprussia.ru/stocks/?region=161",
            "Остатки на складе Ростов-на-Дону",
        ),
    )
    # Запускаем процессы .start()
    a.start()
    b.start()
    c.start()
    # Ждем выполнение процессов .join()
    a.join()
    b.join()
    c.join()
    print("Сохраняем полученную информацию в json файл")
    save_json()
    # save_json_in_sql()
    print("Обновляем информацию на сайте")
    update_price()
