import asyncio
import json
import logging
import math
import os
import time
from datetime import datetime, timedelta
from random import randint
from typing import Any

from call_api import call

import pandas as pd

from report_log_doc import main as log_doc

from script_for_montage import (
    button_location,
    edit_location,
    handle_text_location,
    read_location,
)

from scripts_doc_1c.Entera import entera, entera_download
from scripts_doc_1c.service_abc import main as service_abc
from scripts_doc_1c.service_send_sheta import send_msg_sheta

from send_email import send_email

from send_query_sql import insert_and_update_sql

from sqlalchemy import create_engine

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaDocument,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from work import (
    TELEGRAM_TOKEN,
    id_telegram,
    ivea_metrika,
    web_django,
    working_folder,
    working_folder_1c,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(process)d-%(levelname)s %(message)s",
    datefmt="%d-%b-%y %H:%M:%S",
)

engine = create_engine(ivea_metrika)  # данные для соединия с БД
engine2 = create_engine(web_django)

user_triger: dict[int | str, dict[str, Any]] = dict()
# словарь выделенный специально для функции снабжения.
# Сюда запишем все необходимые данные.
user_supply: dict[int | str, dict[str, str]] = dict()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.effective_chat and context:
        if update.message.chat:
            if update.message.chat.type == "private":
                try:
                    info: pd.DataFrame = pd.read_sql(
                        f"""SELECT * FROM doc_key_corp
                        WHERE user_id = {update.effective_chat.id!r}""",
                        engine,
                    )
                    if not info.empty:
                        await user2(
                            update, context, "Компания ИВЕА приветствует Вас!"
                        )
                    else:
                        await guest(
                            update,
                            "Для подключения к системе компании ИВЕА, \
                            необходимо ввести код доступа.",
                        )
                except Exception as err:
                    logging.error(f"Function START - error - {err}")


async def user2(
    update: Update, context: ContextTypes.DEFAULT_TYPE, sms: str
) -> None:
    """Данная функция обновляет кнопки пользователя.
    Также обнуляет записи в тригерах 'user_triger' и 'user_supply'"""
    if update.effective_chat:
        if update.effective_chat.id in user_triger:
            user_triger.pop(update.effective_chat.id)
        if update.effective_chat.id in user_supply:
            user_supply.pop(update.effective_chat.id)
        reply_keyboard: list[list[str]] = [
            ["Cписок договоров", "Контакты"],
            ["Нумерация официальных документов"],
            ["Завершение работ в период..."],
        ]
        if update.effective_chat.id == id_telegram["Boss"]:
            reply_keyboard += [
                ["Список комплектаций"],
                ["Список рабочих", "Посмотреть геопозицию"],
                ["Объекты"],
                ["Добавить документ"],
            ]
        if update.effective_chat.id == id_telegram["Pavel"]:
            reply_keyboard += [["Добавить документ"]]
        if update.effective_chat.id == id_telegram["supply"]:
            reply_keyboard += [
                ["Список комплектаций", "Счет в оплату"],
                ["Запросить платёжку", "Напоминание", "Доплатить"],
            ]
        # if update.effective_chat.id == id_telegram['Mihail']:
        # reply_keyboard += [['Объекты'],
        # ['Список рабочих', 'Посмотреть геопозицию']]
        reply_keyboard += [["Корпоративный сайт"]]
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=sms,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, resize_keyboard=True, one_time_keyboard=False
            ),
        )


async def guest(update: Update, sms: str) -> None:
    """Если не находим user_id в БД, то мы предлагаем ввести 'код доступа'
    который зарегистрирует новый user_id"""
    if update.message and update.effective_chat:
        info: pd.DataFrame = pd.read_sql_query(
            f"SELECT name FROM user_worker_key_corp \
            WHERE user_id = {update.effective_chat.id!r};",
            engine,
        )
        if len(info) != 0:
            reply_keyboard = [["Ввести код доступа"]]
        else:
            reply_keyboard = [["Ввести код доступа"], ["Зарегистрироваться"]]
        await update.message.reply_text(
            sms,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, resize_keyboard=True, one_time_keyboard=False
            ),
        )


# Вывод списка документов
async def my_doc(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    flag: str = "doc_list",
    num: int = 0,
) -> None:
    try:
        name_doc: list[Any] = list()
        num_page: list[Any] = list()
        list_doc: pd.DataFrame = pd.DataFrame()
        if flag in ["doc_list", "doc_montage"]:
            list_doc = pd.read_sql(
                """SELECT id, short_name FROM documents
                WHERE scan = 1 and doc_open = 'true' ORDER BY id DESC;""",
                engine,
            )
        elif flag == "contact_get" or flag == "contact_add":
            list_doc = pd.read_sql(
                """SELECT id, short_name FROM documents
                WHERE doc_open = 'true' ORDER BY id DESC;""",
                engine,
            )
        page = 0
        for idx, row in list_doc.iterrows():
            if num * 20 <= page < (num + 1) * 20:
                name_doc += [
                    [
                        InlineKeyboardButton(
                            str(row["short_name"]),
                            callback_data=flag + "-" + str(row["id"]),
                        )
                    ]
                ]
            page += 1
        for i in range(math.ceil(len(list_doc) / 20)):
            if num != i:
                num_page += [
                    InlineKeyboardButton(
                        "стр." + str(i + 1),
                        callback_data=f"choice_answer-{flag}-{i}",
                    )
                ]
        keyboard = name_doc + [num_page]
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Выберите договор:",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception as err:
        logging.error("Error:" + str(err))


# Фильтрация
# TODO Надо переделать фильтрации
async def get_filtr_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:  # msg = сообщение от пользователя
    text: str = "Выберите договор:"
    name_doc: list[list[Any]] = list()
    msg_list: list[str] = list()
    and_like_type_works: str = ""
    and_like_short_name: str = ""
    msg: str = ""
    if update.message:
        if update.message.text:
            msg = update.message.text.lower()

    if " " in msg:
        msg = msg.strip()
    if "," in msg:
        msg_list = msg.split(",")
    if msg_list != []:
        for value in msg_list:
            if value == msg_list[0]:
                and_like_type_works += f"LOWER(type_works) LIKE '%%\
{value.strip()}%%' "
                and_like_short_name += f"LOWER(short_name) LIKE '%%\
{value.strip()}%%' "
            else:
                and_like_type_works += f"AND LOWER(type_works) LIKE '%%\
{value.strip()}%%' "
                and_like_short_name += f"AND LOWER(short_name) LIKE '%%\
{value.strip()}%%' "
    else:
        and_like_type_works = f"LOWER(type_works) LIKE '%%{msg.strip()}%%' "
        and_like_short_name = f"LOWER(short_name) LIKE '%%{msg.strip()}%%' "
    info = pd.read_sql_query(
        f"""SELECT id, name, short_name, type_works
        FROM documents WHERE scan = 1 AND doc_open = 'true'
        AND {and_like_type_works} OR {and_like_short_name} ORDER BY id ASC;""",
        engine,
    )

    try:
        for idx, row in info.iterrows():
            name_doc += [
                [
                    InlineKeyboardButton(
                        str(row["short_name"]),
                        callback_data="doc_list-" + str(row["id"]),
                    )
                ]
            ]
        if update.effective_chat:
            if name_doc == []:
                text = "Договор не найден, попробуйте еще раз."
                user_triger[update.effective_chat.id] = {
                    "triger": "filter",
                    "num_doc": "0",
                }
                name_doc = [
                    [
                        InlineKeyboardButton(
                            text="отмена", callback_data="cancel"
                        )
                    ]
                ]
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                reply_markup=InlineKeyboardMarkup(name_doc),
            )
    except Exception as err:
        logging.error("Error:" + str(err))


async def filter_kontragent(
    update: Update, filter_word: str, num: str
) -> None:
    try:
        text = "Выберите контрагент:"
        keyboard = []
        if filter_word.isdigit():
            search = "inn"
        else:
            search = "title"
        search_info: pd.DataFrame = pd.read_sql(
            f"""SELECT * FROM employee_cards_counterparty
            WHERE LOWER({search}) LIKE '%%{filter_word}%%';""",
            engine2,
        )

        for i in range(len(search_info)):
            keyboard += [
                [
                    InlineKeyboardButton(
                        str(search_info.loc[i, "title"]),
                        callback_data=f"filter_kontragent-{num}-\
{search_info.loc[i, 'inn']}",
                    )
                ]
            ]
        if keyboard == []:
            text = "Контрагент не найден, попробуйте еще раз."
        if update.message:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
    except Exception as err:
        logging.error("Error:" + str(err))


####################################################
# Прием данных с кнопки
####################################################
async def button(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:  # реагирует на нажатие кнопок.
    sms: str = ""
    if update.callback_query and update.effective_chat:
        user_chat_id = update.effective_chat.id
        query = update.callback_query
        await query.answer()
        if query.data:
            if "choice_answer" in query.data:
                if query.message:
                    await query.message.delete()
                await my_doc(
                    update,
                    context,
                    flag=str(query.data.split("-")[1]),
                    num=int(query.data.split("-")[2]),
                )
            elif "contact_get" in query.data:
                info = pd.read_sql(
                    f"""SELECT text, datatime FROM doc_contact
                    WHERE doc_id = {query.data.split("-")[1]!r};""",
                    engine,
                )
                if len(info) > 0:
                    name_station: pd.DataFrame = pd.read_sql(
                        f"""SELECT short_name FROM documents
                        WHERE id = {query.data.split("-")[1]!r};""",
                        engine,
                    )
                    sms = str(name_station.loc[0, "short_name"]) + "\n"
                    for idx, row in info.iterrows():
                        sms += f"{row['datatime']}: {row['text']}\n"
                else:
                    sms = "Для данного договора, контактов нет."
                if query.message:
                    await query.message.delete()
                await user2(update, context, sms)
            elif "contact_add" in query.data:
                user_triger[user_chat_id] = {
                    "triger": "C",
                    "num_doc": query.data.split("-")[1],
                }
                await query.edit_message_text(text="Опишите коротко контакт.")
            elif "doc_list" in query.data:
                if query.message:
                    await query.message.delete()
                info = pd.read_sql(
                    f"""SELECT link, number_doc, short_name, link_group
                    FROM documents WHERE id = {query.data.split('-')[1]};""",
                    engine,
                )
                number_doc: str = str(
                    info.loc[0, "number_doc"]
                )  # .replace('>', '\>').replace('#', '\#').replace('+', '\+')
                # .replace('=', '\=').replace('-', '\-').replace('{', '\{')
                # .replace('}', '\}').replace('.', '\.').replace('!', '\!')
                short_name: str = str(
                    info.loc[0, "short_name"]
                )  # .replace('>', '\>').replace('#', '\#').replace('+', '\+')
                # .replace('=', '\=').replace('-', '\-').replace('{', '\{')
                # .replace('}', '\}').replace('.', '\.').replace('!', '\!')
                link = str(info.loc[0, "link"])
                link_group = str(info.loc[0, "link_group"])
                text_for_url_group = ""
                if "https://t.me/" in link_group:
                    # text_for_url_group = f'\n\nДля данного договора была \
                    # создана группа, для перехода нажмите \
                    # [cюда]({link_group})'
                    text_for_url_group = f"\n\nДля данного договора была \
создана группа ({link_group})"
                # text = f"Документ с номером договора\: [{number_doc} \
                # ({short_name}\)]({link}){text_for_url_group}"
                text = f"Документ с номером договора: {number_doc} (\
{short_name})\nСсылка на документ: {link} {text_for_url_group}"

                # .replace('>', '\>').replace('#', '\#').replace('+', '\+')
                # .replace('=', '\=').replace('-', '\-').replace('{', '\{')
                # .replace('}', '\}').replace('.', '\.').replace('!', '\!')
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Сроки выполнения работ",
                            callback_data="WorkTime#$#"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Акт технической готовности",
                            callback_data="choice3-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Заявка на пропуск, вывоз материалов, контейнера",
                            callback_data="choice4-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Заявка на проведение исследований сточных вод",
                            callback_data="choice5-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Проектная документация",
                            callback_data="choice7-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Другие обращение",
                            callback_data="choice6-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Журнал работ",
                            callback_data="choice_log-"
                            + str(query.data.split("-")[1]),
                        )
                    ],
                ]
                if user_chat_id in [
                    id_telegram["my"],
                    id_telegram["Boss"],
                ]:
                    keyboard += [
                        [
                            InlineKeyboardButton(
                                "Комплектация",
                                callback_data="types-"
                                + str(query.data.split("-")[1]),
                            )
                        ]
                    ]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )  # , parse_mode='MarkdownV2'
            elif "choice1" == query.data:
                if query.message:
                    await query.message.delete()
                await my_doc(update, context, "doc_list")
            elif "choice2" == query.data:
                user_triger[user_chat_id] = {
                    "triger": "filter",
                    "num_doc": "0",
                }
                await query.edit_message_text(
                    text="""Введите слово которое должно содержаться \
в условном названии.\n
Виды работ, которые можно указать через запятую:
- проектирование
- согласование
- стройка
- поставка КОС
- поставка ЛОС
- поставка
- монтаж
- ПНР
- поставка КНС""",
                )
            elif "choice3" in query.data:  # Акт технической готовности
                await query.edit_message_text(
                    text="Запрос на получение акта технической готовности \
    отправлен."
                )
                await choice(
                    update,
                    context,
                    "акт технической готовности",
                    str(query.data.split("-")[1]),
                    0,
                )  # Что запрашиваем, ID документа, номер в матрице
            elif (
                "choice4" in query.data
            ):  # Заявка на пропуск, вывоз материалов, контейнера
                await query.edit_message_text(
                    text="Заявка на пропуск, вывоз материалов, контейнера \
    отправлена."
                )
                await choice(
                    update,
                    context,
                    "заявку на пропуск, вывоз материалов, контейнера",
                    query.data.split("-")[1],
                    1,
                )
            elif (
                "choice5" in query.data
            ):  # Заявка на проведение исследований сточных вод
                await query.edit_message_text(
                    text="Заявка на проведение исследований сточных вод \
    отправлена."
                )
                await choice(
                    update,
                    context,
                    "заявку на проведение исследований сточных вод",
                    query.data.split("-")[1],
                    2,
                )
            elif "choice6" in query.data:  # Другие обращение
                await query.edit_message_text(
                    text="Опишите кратко какая помощь вам необходима по \
Договору"
                )
                user_triger[user_chat_id] = {
                    "triger": "choice6",
                    "num_doc": query.data.split("-")[1],
                }
            elif "choice7" in query.data:  # Проектная документация
                info = pd.read_sql(
                    f"SELECT * FROM documents \
                    WHERE id = {query.data.split('-')[1]};",
                    engine,
                )
                if (
                    info.loc[0, "project_doc_link"] is not None
                    and info.loc[0, "project_doc_link"] != ""
                ):
                    await query.edit_message_text(
                        text=str(info.loc[0, "project_doc_link"])
                    )
                else:
                    await choice(
                        update,
                        context,
                        "проектную документацию",
                        query.data.split("-")[1],
                        4,
                    )
                    await query.edit_message_text(
                        text="Запрос отправлен, ожидайте ответа."
                    )
            elif "choice8" == query.data:
                user_triger[user_chat_id] = {
                    "triger": "filter_kontragent",
                    "num_doc": "8",
                }
                await query.edit_message_text(
                    text="Введите полное название (можно часть полного \
названия) или номер ИНН."
                )
            elif "choice9" == query.data:
                user_triger[user_chat_id] = {
                    "triger": "filter_kontragent",
                    "num_doc": "9",
                }
                await query.edit_message_text(
                    text="Введите полное название (можно часть полного \
названия) или номер ИНН."
                )
            elif "choice_log_give" in query.data:
                if query.message:
                    await query.message.delete()
                log_doc(query.data.split("-")[1])
                with open(working_folder + "report_log_doc.pdf", "rb") as pdf:
                    await context.bot.send_document(
                        chat_id=user_chat_id, document=pdf
                    )
            elif "choice_log_write" in query.data:
                await query.edit_message_text(
                    text="Введите что необходимо записать в журнал."
                )
                user_triger[user_chat_id] = {
                    "triger": "choice_log_write",
                    "num_doc": query.data.split("-")[1],
                }
            elif "choice_log" in query.data:
                if query.message:
                    await query.message.delete()
                info = pd.read_sql(
                    f"""SELECT text, date_time, user_name FROM log_doc
                    WHERE doc_id = '{query.data.split('-')[1]}';""",
                    engine,
                )
                if info.empty:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Заполнить",
                                callback_data="choice_log_write-"
                                + str(query.data.split("-")[1]),
                            )
                        ]
                    ]
                else:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Получить",
                                callback_data="choice_log_give-"
                                + str(query.data.split("-")[1]),
                            ),
                            InlineKeyboardButton(
                                "Заполнить",
                                callback_data="choice_log_write-"
                                + str(query.data.split("-")[1]),
                            ),
                        ]
                    ]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Журнал работ",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "filter_kontragent" in query.data:
                num = query.data.split("-")[1]
                inn = query.data.split("-")[2]
                if num == "8":
                    info = pd.read_sql(
                        f"SELECT * FROM employee_cards_counterparty\
                         WHERE inn = '{inn}';",
                        engine2,
                    )
                    text = ""
                    if str(info.loc[0, "title"]) != "nan":
                        text += f"Полное наименование: {info.loc[0,'title']}\n"
                    if str(info.loc[0, "group_k"]) != "nan":
                        text += f"Группа: {info.loc[0,'group_k']}\n"
                    if str(info.loc[0, "type_k"]) != "nan":
                        text += f"Вид контрагента: {info.loc[0,'type_k']}\n"
                    text += f"ИНН контрагента: {inn}\n"
                    if info.loc[0, "trade_name"] is not None:
                        text += f"Торговое название: \
{info.loc[0,'trade_name']}\n"
                    if info.loc[0, "description"] is not None:
                        text += f"Описание: {info.loc[0,'description']}\n"
                    if info.loc[0, "url"] is not None:
                        text += f"Ссылка на сайт: {info.loc[0,'url']}\n"
                    if info.loc[0, "tel"] is not None:
                        text += f"Контактные номера: {info.loc[0,'tel']}\n"
                    await context.bot.send_message(
                        chat_id=user_chat_id, text=text
                    )
                elif num == "9":
                    user_triger[user_chat_id] = {
                        "triger": "update_k_info",
                        "num_doc": "0",
                        "inn": inn,
                        "trade_name": "None",
                        "description": "None",
                        "url": "None",
                        "tel": "None",
                    }
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"ИНН:{inn}\nВведите торговое название.",
                    )
            elif "go_next_contract" in query.data:
                keyboard = list()
                list_doc_id = query.data.replace(
                    "go_next_contract,", ""
                ).split(",")
                for i in range(len(list_doc_id)):
                    info = pd.read_sql_query(
                        f"""SELECT doc_name,work_name FROM doc_date
                        WHERE id = {list_doc_id[i]};""",
                        engine,
                    )
                    doc = (
                        str(i + 1)
                        + ") "
                        + str(info.loc[0, "doc_name"])
                        + " "
                        + str(info.loc[0, "work_name"])
                    )
                    keyboard += [
                        [
                            InlineKeyboardButton(
                                str(doc),
                                callback_data="go_next2,"
                                + str(list_doc_id[i]),
                            )
                        ]
                    ]
                await query.edit_message_text(
                    text="В каком договоре будем изменять дату?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "go_next2" in query.data:
                go_next2_id = query.data.replace("go_next2,", "")
                await query.edit_message_text(
                    text="Введите новую дату.\nПример: "
                    + str(datetime.now().strftime("%d.%m.%Y"))
                )
                user_triger[user_chat_id] = {
                    "triger": "date",
                    "num_doc": go_next2_id,
                }
            elif "empl_send_doc" in query.data:
                if query.data.split("-")[1] == "go":
                    media_group = []
                    info = pd.read_sql(
                        f"""SELECT * FROM doc_employment
                        WHERE user_id = {user_chat_id}""",
                        engine,
                    )
                    for i in range(8):
                        directory: str = str(info.loc[0, "link_" + str(i + 1)])
                        if directory is not None:
                            media_group.append(
                                InputMediaDocument(open(directory, "rb"))
                            )
                    await context.bot.send_message(
                        chat_id=id_telegram["OK"],
                        text=str(info.loc[0, "name"])
                        + " тел: "
                        + str(info.loc[0, "tel"]),
                    )
                    await context.bot.send_media_group(
                        chat_id=id_telegram["OK"], media=media_group
                    )
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text="Документы отправлены в отдел кадров компании \
ИВЕА. Ожидайте.",
                    )
                else:
                    user_triger[user_chat_id]["triger"] = "empl_send_doc"
                    user_triger[user_chat_id]["num_doc"] = query.data.split(
                        "-"
                    )[
                        1
                    ]  # Это будет номер отправленного документа
                    await query.edit_message_text(
                        text="Отправьте сюда файл в формате PDF"
                    )
            elif "empl_send_end" in query.data:
                user_id = query.data.split("-")[1]
                # В данном случае это ID пользователя
                # (кандадата на трудоустройства)
                info = pd.read_sql(
                    f"SELECT name, tel FROM doc_employment \
                    WHERE user_id = {user_id}",
                    engine,
                )
                await query.edit_message_text(
                    text="Имя кандидата: "
                    + str(info.loc[0, "name"])
                    + "\nКонтактный номер телефона: "
                    + str(info.loc[0, "tel"])
                )
                user_triger[user_chat_id] = {
                    "triger": "None",
                    "num_doc": "empl_send_sms",
                    "id": user_id,
                    "j": "None",
                }
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "трудовой договор (файл для прочтения, печати и \
    подписи)",
                            callback_data="empl_send_sms-0",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "внесена запись в трудовую книгу",
                            callback_data="empl_send_sms-1",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "приказ о назначении на должность",
                            callback_data="empl_send_sms-2",
                        )
                    ],
                ]
                sms = "Что передать?"
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=sms,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "empl_send_sms" in query.data:
                num_doc = query.data.split("-")[1]
                user_triger[user_chat_id]["j"] = num_doc
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Отправить документ",
                            callback_data="empl_send_next_sms-send_doc",
                        ),
                        InlineKeyboardButton(
                            "Отправить ссылку на документ",
                            callback_data="empl_send_next_sms-send_link",
                        ),
                    ]
                ]
                sms = "Что передать?"
                await query.edit_message_text(
                    text=sms, reply_markup=InlineKeyboardMarkup(keyboard)
                )
            elif "empl_send_next_sms" in query.data:
                arr = [
                    "трудовой договор (файл для прочтения, печати и подписи)",
                    "внесена запись в трудовую книгу",
                    "приказ о назначении на должность",
                ]
                triger = query.data.split("-")[1]
                user_triger[user_chat_id]["triger"] = triger
                if triger == "send_doc":
                    sms = (
                        'Жду документ "'
                        + arr[int(user_triger[user_chat_id]["j"])]
                        + '"'
                    )
                elif triger == "send_link":
                    sms = f'Жду ссылку на документ "\
        {arr[int(user_triger[user_chat_id]["j"])]}"'
                await query.edit_message_text(text=sms)
            elif "send_doc" in query.data:
                arr = [
                    "акт технической готовности",
                    "заявку на пропуск, вывоз материалов, контейнера",
                    "заявку на проведение исследований сточных вод",
                    "следующую информацию",
                    "проектную документацию",
                ]
                user_id = query.data.split("-")[1]
                # В данном случае это ID пользователя который отправил запрос
                id_doc = query.data.split("-")[
                    2
                ]  # Это ID документа на который запрос
                j = int(
                    query.data.split("-")[3]
                )  # это номер что из списка что нужно пользователю
                info = pd.read_sql(
                    f"""SELECT name, family_name, tel FROM doc_key_corp
                    WHERE user_id = '{user_id}';""",
                    engine,
                )
                info2: pd.DataFrame = pd.read_sql(
                    f"""SELECT number_doc, short_name FROM documents
                    WHERE id = {id_doc};""",
                    engine,
                )
                text = (
                    "Сотрудник "
                    + str(info.loc[0, "name"])
                    + " "
                    + str(info.loc[0, "family_name"])
                    + ", (тел. "
                    + str(info.loc[0, "tel"])
                    + ") запрашивает "
                    + str(arr[j])
                    + " по Договору "
                    + str(info2.loc[0, "number_doc"])
                    + " ("
                    + str(info2.loc[0, "short_name"])
                    + ")\n\n"
                )
                user_triger[user_chat_id] = {
                    "triger": "send_doc",
                    "num_doc": id_doc,
                    "id": str(user_id),
                    "j": j,
                }
                await query.edit_message_text(
                    text=text + "Загрузите документ, можно его подписать."
                )
            elif "send_link" in query.data or "send_text" in query.data:
                arr = [
                    "акт технической готовности",
                    "заявку на пропуск, вывоз материалов, контейнера",
                    "заявку на проведение исследований сточных вод",
                    "следующую информацию",
                    "проектную документацию",
                ]
                # В данном случае это ID пользователя который отправил запрос
                user_id = query.data.split("-")[1]
                # Это ID документа на который запрос
                id_doc = query.data.split("-")[2]
                j = int(query.data.split("-")[3])
                info = pd.read_sql(
                    f"""SELECT name, family_name, tel FROM doc_key_corp
                    WHERE user_id = '{user_id}';""",
                    engine,
                )
                if id_doc != "999999":
                    info2 = pd.read_sql(
                        f"""SELECT number_doc, short_name FROM documents
                        WHERE id = {id_doc};""",
                        engine,
                    )
                    text = f"""запрашивает {arr[j]} по Договору \
{info2.loc[0, "number_doc"]} ({info2.loc[0, "short_name"]})\n
Отправьте ссылку, она автоматически добавится к этому документу и \
отправится пользователю."""
                else:
                    arr2 = (
                        "запрашивает справки 2НДФЛ",
                        "запрашивает справку о месте работы",
                        "хочет предоставить сведения о детях",
                        "запрашивает выплату за фактически отработанное время",
                        "запрашивает планируемую дату выплаты аванса, \
зарплаты",
                        "запрашивает информацию о окладе \
(структура, сумма, даты выплаты)",
                        "запрашивает сумму за период (структура оклад, \
налоги)",
                        "запрашивает сканы документов (трудовой договор, все \
личные (паспорт и тд), приказ, и другие приказы)",
                        "интересуется, что компания ждет от него, \
профессиональный рост (регистрация в ноприз, нострой, обучение на курсах \
повышения квалификации) и др.",
                    )

                    text = arr2[j]
                if "send_link" in query.data:
                    triger = "send_link"
                else:
                    triger = "send_text"
                user_triger[user_chat_id] = {
                    "triger": triger,
                    "num_doc": id_doc,
                    "user_id": user_id,
                    "j": j,
                }
                await query.edit_message_text(
                    text=f"Сотрудник {info.loc[0, 'name']} \
        {info.loc[0, 'family_name']}, (тел. {info.loc[0, 'tel']}) {text}"
                )
            elif "WorkTime" in query.data:  # Запрос сроков выполнения работ
                short_name = str(
                    pd.read_sql(
                        "SELECT short_name FROM documents WHERE id = %(id)s;",
                        params=({"id": query.data.split("#$#")[1]}),
                        con=engine,
                    ).loc[0, "short_name"]
                )
                info = pd.read_sql_query(
                    """SELECT * FROM doc_date
                    WHERE doc_name in (
                     %(short_name)s,
                     %(short_name_end)s
                    ) ORDER BY id ASC;""",
                    params=(
                        {
                            "short_name": short_name,
                            "short_name_end": str(short_name) + " (завершено)",
                        }
                    ),
                    con=engine,
                )

                text = ""
                i = 0
                for idx, row in info.iterrows():
                    i += 1
                    if "(завершено)" in str(row["doc_name"]):
                        end = " (завершено)"
                    else:
                        end = ""
                    if int(row["noct"]) > 0:

                        text += f'{i}){row["work_name"]}{end}-\
{row["date_end"].strftime("%d.%m.%Y")}\n(Количествл переносов: \
"{row["noct"]}"; Причина переноса: "{row["coment"]}")\n\n'
                    else:
                        text += f'{i}){row["work_name"]}{end}-\
{row["date_end"].strftime("%d.%m.%Y")}\n\n'
                await context.bot.send_message(chat_id=user_chat_id, text=text)
            elif "notification" in query.data:
                num_notification = query.data.split("-")[
                    1
                ]  # В данном случае это номер оповещения
                user_triger[user_chat_id] = {
                    "triger": "notification_link",
                    "num_doc": str(num_notification),
                }
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Отправьте ссылку на документ, с которым сотрудники \
должны ознакомиться.",
                )
                ####################################
            elif "next_send_request" in query.data:
                user_id = query.data.split("-")[1]
                if query.message:
                    await query.message.delete()
                if user_id == "all":
                    info = pd.read_sql(
                        """SELECT user_id, name, family_name FROM doc_key_corp
                        WHERE user_id > 0;""",
                        engine,
                    )
                    for idx, row in info.iterrows():
                        if str(row["user_id"]) != str(user_chat_id):
                            try:
                                await context.bot.send_message(
                                    chat_id=row["user_id"],
                                    text="Тестовое оповещение.",
                                )
                            except Exception:
                                logging.error(
                                    "Не смог отправить сообщение",
                                    f'chat_id={row["user_id"]}',
                                )
                else:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text="Тестовое личное оповещение.",
                    )
            elif "send_request" in query.data:
                # arr = (
                #     "Начисленная зарплата в месяц, дата выплаты",
                #     "ЗП переведена на расчетный счет, дата, время",
                #     "Требования ознакомиться и подписать приказы, заявления",
                # )
                # num = int(query.data.split("-")[1])
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Отправить всем",
                            callback_data="next_send_request-all",
                        )
                    ]
                ]
                info = pd.read_sql(
                    "SELECT user_id, name, family_name \
                    FROM doc_key_corp WHERE user_id > 0;",
                    engine,
                )
                for i in range(len(info)):
                    if str(info.loc[i, "user_id"]) != str(user_chat_id):
                        keyboard += [
                            [
                                InlineKeyboardButton(
                                    text=f"{info.loc[i, 'family_name']} \
        {info.loc[i, 'name']}",
                                    callback_data="next_send_request-"
                                    + str(info.loc[i, "user_id"]),
                                )
                            ]
                        ]
                await query.edit_message_text(
                    "Оповестить всех или кого-то лично?",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "request" in query.data:
                arr = [
                    "запрашивает справки 2НДФЛ",
                    "запрашивает справку о месте работы",
                    "хочет предоставить сведения о детях",
                    "запрашивает выплату за фактически отработанное время",
                    "запрашивает планируемую дату выплаты аванса, зарплаты",
                    "запрашивает информацию о окладе \
(структура, сумма, даты выплаты)",
                    "запрашивает сумму за период (структура оклад, налоги)",
                    "запрашивает сканы документов (трудовой договор, все \
личные (паспорт и тд), приказ, и другие приказы)",
                    "интересуется, что компания ждет от него, \
профессиональный рост (регистрация в ноприз, нострой, обучение на курсах \
повышения квалификации) и др.",
                ]
                num = str(query.data.split("-")[1])
                identification_number = "999999"
                await query.edit_message_text(
                    text="Запрос отправлен, ожидайте ответа."
                )
                info = pd.read_sql(
                    f"SELECT name, family_name, tel \
                    FROM doc_key_corp \
                    WHERE user_id  = '{user_chat_id}';",
                    engine,
                )
                text = (
                    "Сотрудник "
                    + str(info.loc[0, "name"])
                    + " "
                    + str(info.loc[0, "family_name"])
                    + ", (тел. "
                    + str(info.loc[0, "tel"])
                    + ") "
                    + arr[int(num)]
                    + "\n\n"
                )
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Отправить документ",
                            callback_data="send_doc-"
                            + str(user_chat_id)
                            + "-"
                            + str(identification_number)
                            + "-"
                            + str(num),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Отправить ссылку",
                            callback_data="send_link-"
                            + str(user_chat_id)
                            + "-"
                            + str(identification_number)
                            + "-"
                            + str(num),
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Ответить в текстовом виде",
                            callback_data="send_text-"
                            + str(user_chat_id)
                            + "-"
                            + str(identification_number)
                            + "-"
                            + str(num),
                        )
                    ],
                ]
                await context.bot.send_message(
                    chat_id=id_telegram["OK"],
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                # 943180118 456335434 Если выбор пал на проектную документацию
                # и ее нет, то летит запрос Андрею
            elif "write_new_latter" in query.data:
                if query.message:
                    await query.message.delete()
                name = query.data.split("-")[1]
                await num_doc_letters(update, context, name, True)
            elif "cancel" in query.data:
                if query.message:
                    await query.message.delete()
                if user_chat_id in user_triger:
                    user_triger.pop(user_chat_id)
                if user_chat_id in user_supply:
                    user_supply.pop(user_chat_id)
            elif "types" in query.data:
                if query.message:
                    await query.message.delete()
                doc_id = query.data.split("-")[1]
                if user_chat_id in user_supply:
                    user_supply.pop(user_chat_id)
                info = pd.read_sql(
                    f"SELECT link, number_doc, short_name, type_of_building \
                    FROM documents WHERE id = '{doc_id}';",
                    engine,
                )
                user_info: pd.DataFrame = pd.read_sql(
                    f"SELECT name, family_name, tel FROM doc_key_corp \
                    WHERE user_id = '{user_chat_id}';",
                    engine,
                )
                user_supply[user_chat_id] = {
                    "doc_id": str(doc_id),
                    "number_doc": str(info.loc[0, "number_doc"]),
                    "short_name": str(info.loc[0, "short_name"]),
                    "fio": str(user_info.loc[0, "family_name"])
                    + " "
                    + str(user_info.loc[0, "name"]),
                    "tel": str(user_info.loc[0, "tel"]),
                    "type_of_building": "None",
                    "type_of_equipment": "None",
                    "link": "",
                    "brand": "None",
                }
                type_of_building = str(info.loc[0, "type_of_building"]).split(
                    ","
                )
                keyboard = []
                keyboard += [
                    [
                        InlineKeyboardButton(
                            str(type_value),
                            callback_data="next_type_of_the_type-"
                            + str(type_value),
                        )
                    ]
                    for type_value in type_of_building
                ]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Выберите тип сооружения.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "next_type_of_the_type" in query.data:
                if query.message:
                    await query.message.delete()
                    type_of_building = query.data.split("-")
                user_supply[user_chat_id]["type_of_building"] = str(
                    type_of_building[1]
                )
                info = pd.read_sql(
                    f"SELECT type_of_equipment, need_link FROM types \
                    WHERE type_of_building = '{type_of_building[1]}';",
                    engine,
                )
                keyboard = []
                for i in range(len(info)):
                    link = (
                        "-1"
                        if int(str(info.loc[i, "need_link"])) == 1
                        else "-0"
                    )
                    keyboard += [
                        [
                            InlineKeyboardButton(
                                str(info.loc[i, "type_of_equipment"]),
                                callback_data="brand-"
                                + str(info.loc[i, "type_of_equipment"])
                                + str(link),
                            )
                        ]
                    ]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Выберите тип оборудования.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "accepted" in query.data:
                if query.message:
                    await query.message.delete()
                accepted_id: str = query.data.split("-")[1]
                date: str = ""
                accepted: str = ""
                num_answer: int = 0
                if user_chat_id == id_telegram["Boss"]:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "принято",
                                callback_data=f"accepted-{accepted_id}",
                            )
                        ]
                    ]
                    await context.bot.send_message(
                        chat_id=id_telegram["supply"],
                        text=str(query.message.text) if query.message else "",
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                    num_answer = 1
                    date = f", date = '{datetime.now()}'"
                    accepted = "согласована."
                elif user_chat_id == id_telegram["supply"]:
                    num_answer = 2
                    date = ""
                    accepted = "принята."
                await insert_and_update_sql(
                    f"UPDATE saving_query_the_supply \
                    SET answer{num_answer} = 'принято'{date} \
                    WHERE id = '{accepted_id}';"
                )
                text = "Позиция для комплектации объекта {}\n{}".format(
                    accepted, query.message.text if query.message else ""
                )
                await context.bot.send_message(chat_id=user_chat_id, text=text)
            # supply
            elif "supply_short_name" in query.data:
                if query.message:
                    await query.message.delete()
                user_triger[user_chat_id]["triger"] = "link_yandex"
                user_triger[user_chat_id]["short_name"] = query.data.split(
                    "#*&*#"
                )[1]
                reply_keyboard = [["Вернуться в главное меню"]]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Прикрепите ссылку к файлу на яндекс диске",
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard,
                        resize_keyboard=True,
                        one_time_keyboard=False,
                    ),
                )
            elif "brand" in query.data:
                if query.message:
                    await query.message.delete()
                user_supply[user_chat_id]["type_of_equipment"] = (
                    query.data.split("-")[1]
                )
                triger = (
                    "brand"
                    if str(query.data.split("-")[2]) == "0"
                    else "need_link"
                )
                text = (
                    "Введите ссылку на чертеж оборудования"
                    if str(query.data.split("-")[2]) == "1"
                    else "Введите название бренда оборудования"
                )
                user_triger[user_chat_id] = {
                    "triger": triger,
                    "num_doc": "None",
                }
                await context.bot.send_message(chat_id=user_chat_id, text=text)

            elif "location" in query.data:
                user_id = query.data.split("-")[1]
                """location = '{update.edited_message.location['longitude']}:\
        {update.edited_message.location['latitude']}'"""
                info = pd.read_sql(
                    f"SELECT location, name, date_time \
                    FROM user_worker_key_corp \
                    WHERE user_id = '{user_id}' and date_time > '\
        {datetime.now().strftime('%Y-%m-%d')}';",
                    engine,
                )
                try:
                    str_time = "08:00:00"
                    if info.loc[0, "date_time"]:
                        str_time = pd.to_datetime(
                            str(info.loc[0, "date_time"])
                        ).strftime("%H:%M:%S")
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"{info.loc[0, 'name']}. Местоположение была \
актуальна в {str_time}.",
                    )
                    await context.bot.send_location(
                        chat_id=user_chat_id,
                        longitude=float(
                            str(info.loc[0, "location"]).split(":")[0]
                        ),
                        latitude=float(
                            str(info.loc[0, "location"]).split(":")[1]
                        ),
                    )
                except Exception:
                    try:
                        info = pd.read_sql(
                            f"SELECT location, name, date_time \
                            FROM user_worker_key_corp \
                            WHERE user_id = '{user_id}';",
                            engine,
                        )
                        if str(info.loc[0, "location"]) != "None":
                            str_time = "08:00:00"
                            if info.loc[0, "date_time"]:
                                str_time = pd.to_datetime(
                                    str(info.loc[0, "date_time"])
                                ).strftime("%H:%M:%S")
                            await context.bot.send_message(
                                chat_id=user_chat_id,
                                text=f"{info.loc[0,'name']}\nГеопозиции нет. \
Дата последний трансляции геопозиции {str_time}.",
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=user_chat_id, text="Геопозиции нет"
                            )
                    except Exception:
                        await context.bot.send_message(
                            chat_id=user_chat_id, text="Геопозиции нет"
                        )
            elif "reg_worker_next" in query.data:
                u_id = query.data.split("-")[1]
                info = pd.read_sql_query(
                    f"SELECT name, tel FROM user_worker_key_corp \
                    WHERE id = '{u_id}';",
                    engine,
                )  #
                user_triger[user_chat_id] = {
                    "triger": "reg_worker_next",
                    "num_doc": 0,
                    "id": u_id,
                    "num_working_group": 0,
                    "name": info.loc[0, "name"],
                    "tel": info.loc[0, "tel"],
                }
                reply_keyboard = [["Отмена"]]
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"""{info.loc[0,'name']} - {info.loc[0,'tel']}
Напишите в какую бригаду определить данного работника?""",
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard,
                        resize_keyboard=True,
                        one_time_keyboard=False,
                    ),
                )
            elif "send_email_1c_doc" in query.data:
                doc_id = query.data.split("-")[1]
                info = pd.read_sql(
                    f"""SELECT num_doc, contragent, date_doc, num_1c,
                    sum, link, name_file, comment, inn, \"delete\", send_email
                    FROM doc_entera_1c WHERE id = '{doc_id}';""",
                    engine,
                )
                for idx, row in info.iterrows():
                    link = str(row["link"])
                    name_file = str(row["name_file"])
                    table_type, total = service_abc(inn=str(row["inn"]))
                    f_sum_doc = (
                        "{:,}".format(float(str(row["sum"])))
                        .replace(",", "\u00A0")
                        .replace(".", ",")
                    )
                    if not row["delete"]:
                        text = f"Счёт № {row['num_doc']} от \
{row['date_doc']} \
на сумму {f_sum_doc} руб.\n\n{table_type} \
Контрагент: {row['contragent']} ({total} руб.)\n\n\
Комментарий: {row['comment']}"
                        text_for_supply = f"Счёт № {row['num_doc']} \
от {row['date_doc']} на сумму {f_sum_doc} руб.\n\n\
Контрагент: {row['contragent']}\n\n\
Комментарий: {row['comment']}"

                        await query.edit_message_text(text=text)
                        await entera_download(link, name_file)
                        answer = send_email(
                            list_file=[name_file],
                            text=text,
                            working_folder=str(working_folder_1c)
                            + "send_file/",
                        )
                        if "Письмо с документом отправлено!" == answer:
                            await query.edit_message_text(
                                text=text + "\n|| Отправлено на почту. ||"
                            )
                            await context.bot.send_message(
                                chat_id=id_telegram["supply"],
                                text=text_for_supply
                                + "\n|| Cогласован в оплату. ||",
                            )  # supply
                            await context.bot.send_message(
                                chat_id=id_telegram["my"],
                                text=text_for_supply
                                + "\n|| Cогласован в оплату. ||",
                            )  # my
                            await insert_and_update_sql(
                                f"""UPDATE doc_entera_1c SET
                                send_email = 'True'
                                WHERE id = '{doc_id}';"""
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=user_chat_id,
                                text="Ошибка при отправке письма. \
Повторите позже.",
                            )
                            await context.bot.send_message(
                                chat_id=id_telegram["my"],
                                text=answer
                                + "\n\n"
                                + text
                                + "\n|| Cогласован в оплату. ||",
                            )
                    else:
                        text = f"Счёт № {row['num_doc']} от {row['date_doc']} \
на сумму {f_sum_doc} руб.\n\n Данный счёт был удален в 1с ({row['num_1c']})"
                        await query.edit_message_text(text=text)

            elif "item_1c_doc" in query.data:
                doc_id = query.data.split("-")[1]
                info = pd.read_sql(
                    f"""SELECT num_1c, num_doc, contragent, date_doc, sum,
link, name_file FROM doc_entera_1c WHERE id = '{doc_id}';""",
                    engine,
                )
                info2 = pd.read_sql(
                    "SELECT * FROM employee_cards_pricechangelog;",
                    engine2,
                )
                for idx1, row1 in info.iterrows():
                    info_sheta = pd.read_sql(
                        f"""SELECT * FROM invoice_analysis_invoice
                            WHERE number = '{row1['num_1c']}'""",
                        engine2,
                    )
                    f_sum_doc = (
                        "{:,}".format(float(str(row1["sum"])))
                        .replace(",", "\u00A0")
                        .replace(".", ",")
                    )
                    text = f'Состав: Счёт № {info.loc[0,"num_doc"]} \
от {info.loc[0,"date_doc"]} на сумму {f_sum_doc} руб.\n'
                    i = 0
                    for idx, row in info_sheta.iterrows():
                        i += 1
                        nds: str = ""
                        price_analysis: str = ""
                        inaccuracy: int = (
                            11  # разница цены которая не считается
                        )
                        if (
                            str(row["vat_percent"]) == "Без НДС"
                            or str(row["vat_percent"]) == "0%"
                        ):
                            nds = "*** Без НДС ***"
                        df_info_isin = info2[
                            info2["nomenclature"].isin([row["nomenclature"]])
                        ]
                        df_info_isin = df_info_isin[
                            df_info_isin["counterparty_id"].isin(
                                [row["counterparty_id"]]
                            )
                        ]
                        if not df_info_isin.empty:
                            min_price: float = round(
                                float(
                                    min(df_info_isin["min_price"].to_list())
                                ),
                                2,
                            )
                            max_price: float = round(
                                float(
                                    min(df_info_isin["max_price"].to_list())
                                ),
                                2,
                            )
                            price_one: float = round(
                                float(row["total"]) / float(row["amount"]), 2
                            )
                            if price_one < (min_price + inaccuracy):
                                price_analysis = "🟩"
                            elif price_one > (
                                min_price + inaccuracy
                            ) and price_one < (max_price + inaccuracy):
                                f_price = (
                                    "{:,}".format(
                                        round(price_one - min_price, 2)
                                    )
                                    .replace(",", "\u00A0")
                                    .replace(".", ",")
                                )
                                price_analysis = f"- {f_price} 🟨"
                            elif price_one > (max_price + inaccuracy):
                                f_max_price = (
                                    "{:,}".format(max_price)
                                    .replace(",", "\u00A0")
                                    .replace(".", ",")
                                )
                                price_analysis = f"MAX ({f_max_price}) 🟥"
                        else:
                            price_analysis = "❗️"
                        text += f"\n{i}) {row['nomenclature']} - \
{row['amount']} {row['unit']}. ({(row['total'])}  руб. \
{nds}) {price_analysis}\n"
                # хитрая система :) отправляем сообщение
                # и одновременно считываем его id,
                # затем отправляем на удаление через минуту
                if query.message:
                    q_msg_id = await context.bot.send_message(
                        chat_id=user_chat_id, text=text.replace(" nan", "")
                    )
                    asyncio.create_task(
                        timer(update, context, 60, q_msg_id.message_id)
                    )
            elif "update_k_info" in query.data:
                inn = query.data.split("-")[1]
                user_triger[user_chat_id] = {
                    "triger": "update_k_info",
                    "num_doc": "0",
                    "inn": inn,
                    "trade_name": "None",
                    "description": "None",
                    "url": "None",
                    "tel": "None",
                }
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text=f"ИНН:{inn}\nВведите торговое название.",
                )
            elif "explanation_next" in query.data:
                id_entera_1c: int = int(query.data.split("-")[1])
                user_triger[user_chat_id] = {
                    "triger": "explanation_next",
                    "num_doc": "0",
                    "id_entera_1c": id_entera_1c,
                }
                await context.bot.send_message(
                    chat_id=user_chat_id,
                    text="Готов записывать",
                )
            elif "explanation" in query.data:
                id_entera_1c = int(query.data.split("-")[1])
                info = pd.read_sql(
                    f"""SELECT contragent FROM doc_entera_1c
                        WHERE id = '{id_entera_1c}'""",
                    engine,
                )
                for idx, row in info.iterrows():
                    user_triger[user_chat_id] = {
                        "triger": "explanation",
                        "num_doc": "0",
                        "contragent": row["contragent"],
                        "id_entera_1c": id_entera_1c,
                    }
                    await context.bot.send_message(
                        chat_id=user_chat_id,
                        text=f"""Наименование нового контрагента: \
    {row['contragent']}
    Введите его ИНН.""",
                    )
                    break
            elif "verification" in query.data:
                # подтверждение дней рождений сотрудников
                data = query.data.split("-")[1]
                id_user = query.data.split("-")[2]
                if data == "ok":
                    await query.edit_message_text(text="Спасибо.")
                    await insert_and_update_sql(
                        f"UPDATE birthday SET verified = 'true' \
                            WHERE id_user = '{id_user}';"
                    )
                elif data == "wrong":
                    await query.edit_message_text(
                        text="Пожалуйста, опишите что не верно и на что \
заменить."
                    )
                    user_triger[user_chat_id] = {
                        "triger": "verification",
                        "num_doc": "0",
                        "id_user": id_user,
                    }
            else:
                await button_location(update, user_triger)


####################################################
# Выбор запроса по договору
####################################################
async def choice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    choice_query_data: str,
    doc_id: str,
    j: int,
) -> None:
    if update.effective_chat:
        info: pd.DataFrame = pd.read_sql(
            f"SELECT name, family_name, tel FROM doc_key_corp \
            WHERE user_id  = {update.effective_chat.id!r};",
            engine,
        )
        info2: pd.DataFrame = pd.read_sql(
            f"SELECT number_doc, short_name FROM documents \
            WHERE id = {doc_id};",
            engine,
        )
        text = (
            "Сотрудник "
            + str(info.loc[0, "name"])
            + " "
            + str(info.loc[0, "family_name"])
            + ", (тел. "
            + str(info.loc[0, "tel"])
            + ") запрашивает "
            + str(choice_query_data)
            + " по Договору "
            + str(info2.loc[0, "number_doc"])
            + " ("
            + str(info2.loc[0, "short_name"])
            + ")\n\n"
        )
        keyboard = [
            [
                InlineKeyboardButton(
                    "Отправить документ",
                    callback_data="send_doc-"
                    + str(update.effective_chat.id)
                    + "-"
                    + str(doc_id)
                    + "-"
                    + str(j),
                )
            ],
            [
                InlineKeyboardButton(
                    "Отправить ссылку",
                    callback_data="send_link-"
                    + str(update.effective_chat.id)
                    + "-"
                    + str(doc_id)
                    + "-"
                    + str(j),
                )
            ],
        ]
        if j != 4:
            # keyboard = [[InlineKeyboardButton(
            # 'Отправить документ', callback_data='send_doc-' + str(
            # update.effective_chat.id) + '-' + str(id) + '-' + str(j))]]
            await context.bot.send_message(
                chat_id=id_telegram["Pavel"],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )  # 943180118 Все отправляем Павлу
            # Производим запись в БД
            # чтобы при необходимости можно вернуть при необходимости
            await insert_and_update_sql(
                "INSERT INTO request_control (text, callback_data, num) \
                    VALUES({}, '{}-{}',{});".format(
                    text,
                    update.effective_chat.id,
                    doc_id,
                    j,
                )
            )
        else:
            await context.bot.send_message(
                chat_id=id_telegram["Andrei"],
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )  # 943180118 Если выбор пал на проектную документацию и ее нет,
            # то летит запрос Андрею


####################################################
# сохранение контактов к договору
####################################################
async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sms = "Вы хотите получить или добавить контакты?"
    reply_keyboard = [["Получить", "Добавить"], ["Главное меню"]]
    if update.message:
        await update.message.reply_text(
            sms,
            reply_markup=ReplyKeyboardMarkup(
                reply_keyboard, resize_keyboard=True, one_time_keyboard=False
            ),
        )


async def kontragent(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    sms = "Вам показать или Вы хотите заполнить данные о контрагенте?"
    keyboard = [
        [
            InlineKeyboardButton("Показать", callback_data="choice8"),
            InlineKeyboardButton("Заполнить", callback_data="choice9"),
        ]
    ]
    if update.message:
        await update.message.reply_text(
            text=sms,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


####################################################
# поиск договоров с завершением срока по интервалу
####################################################
async def interval(update: Update, num: str) -> None:
    list_doc: str = ""
    text: str = ""
    j: int = 0
    try:
        now = datetime.now()
        info: pd.DataFrame = pd.read_sql_query(
            "SELECT doc_name, work_name, date_end \
            FROM doc_date ORDER BY date_end ASC",
            engine,
        )
        for i in range(len(info)):
            date_end = str(
                pd.to_datetime(str(info.loc[i, "date_end"])) - now
            ).split(" ")[0]
            if date_end != "NaT":
                if abs(int(num)) == 1:
                    days = "дня"
                else:
                    days = "дней"
                if int(date_end) <= int(num) and int(date_end) >= 0:
                    j += 1
                    str_time = "08:00:00"
                    if info.loc[0, "date_end"]:
                        str_time = pd.to_datetime(
                            str(info.loc[0, "date_end"])
                        ).strftime("%d.%m.%Y")
                    list_doc += (
                        str(j)
                        + ") "
                        + str(info.loc[i, "doc_name"])
                        + " "
                        + str(info.loc[i, "work_name"])
                        + ' "'
                        + str(str_time)
                        + '"\n\n'
                    )
                    text = (
                        "Завершение работ в период - меньше "
                        + str(num)
                        + " "
                        + days
                        + "\n\n"
                        + list_doc
                    )
                elif int(date_end) >= int(num) and int(date_end) <= 0:
                    j += 1
                    str_time = "08:00:00"
                    if info.loc[0, "date_end"]:
                        str_time = pd.to_datetime(
                            str(info.loc[0, "date_end"])
                        ).strftime("%d.%m.%Y")
                    list_doc += (
                        str(j)
                        + ") "
                        + str(info.loc[i, "doc_name"])
                        + " "
                        + str(info.loc[i, "work_name"])
                        + ' "'
                        + str(str_time)
                        + '"\n\n'
                    )
                    text = (
                        "Просроченное завершение работ в период - меньше "
                        + str(abs(int(num)))
                        + " "
                        + days
                        + "\n\n"
                        + list_doc
                    )
    except Exception as err:
        logging.error("Error:" + str(err))
        text = "Вы ввели не целочисленное число, повторите попытку"
    try:
        if update.message:
            await update.message.reply_text(text=text)
    except Exception as err:
        logging.error(
            "Error: В запросе получился большой список который \
не умещается в одном СМС"
            + str(err)
        )
        text = "Вы ввели большое количество дней."
        if update.message:
            await update.message.reply_text(text)


# ####################################################
# # функция для запросов
# ####################################################
# async def request(
#     update: Update, i: int
# ) -> None:
#     if i == 1:
#         keyboard = [
#             [
#                 InlineKeyboardButton(
#                     "Запрос справки 2НДФЛ", callback_data="request-" + str(0)
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Запрос о месте работы",
#                     callback_data="request-" + str(1)
#                 )
#             ],
#             # [InlineKeyboardButton('Предоставить сведения о детях',
#             # callback_data='request-' + str(2))],
#             [
#                 InlineKeyboardButton(
#                     "Запросить выплату за фактически отработанное время \
# (при острой необходимости)",
#                     callback_data="request-" + str(3),
#                 )
#             ],
#         ]
#         if update.message:
#             await update.message.reply_text(
#                 text="Можно получить следующие сведения:",
#                 reply_markup=InlineKeyboardMarkup(keyboard),
#             )
#     elif i == 2:
#         keyboard = [
#             [
#                 InlineKeyboardButton(
#                     "Планируемая дата выплаты аванса, зарплаты",
#                     callback_data="request-" + str(4),
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Оклад (структура, сумма, даты выплаты)",
#                     callback_data="request-" + str(5),
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Сумма за период (структура оклад, налоги)",
#                     callback_data="request-" + str(6),
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Сканы документов (трудовой договор, все личные \
# (паспорт и тд), приказ, и другие приказы)",
#                     callback_data="request-" + str(7),
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Что компания ждет от вас, ваш профессиональный рост \
# (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) \
# и др.",
#                     callback_data="request-" + str(8),
#                 )
#             ],
#         ]
#         if update.message:
#             await update.message.reply_text(
#                 text="Можно получить следующие сведения:",
#                 reply_markup=InlineKeyboardMarkup(keyboard),
#             )
#     elif i == 3:
#         keyboard = [
#             # [InlineKeyboardButton(
#             # 'Начисленная зарплата в месяц, дата выплаты',
#             # allback_data='send_request-' + str(0))],
#             [
#                 InlineKeyboardButton(
#                     "ЗП переведена на расчетный счет, дата, время",
#                     callback_data="send_request-" + str(1),
#                 )
#             ],
#             [
#                 InlineKeyboardButton(
#                     "Требования ознакомиться и подписать приказы, заявления",
#                     callback_data="send_request-" + str(2),
#                 )
#             ],
#         ]
#         if update.message:
#             await update.message.reply_text(
#                 text="Можно отправить следующие сведения:",
#                 reply_markup=InlineKeyboardMarkup(keyboard),
#             )


####################################################
# Функция для регистрации КК
####################################################
async def reg_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        if update.message.text and update.effective_chat:
            user_triger.pop(update.effective_chat.id)
            try:
                info: pd.DataFrame = pd.read_sql(
                    f"SELECT id, user_id FROM doc_key_corp \
                    WHERE a_key = '{update.message.text}'",
                    engine,
                )
                doc_key_corp_id = info.loc[0, "id"]
                if str(info.loc[0, "user_id"]) == "0":
                    await insert_and_update_sql(
                        "UPDATE doc_key_corp SET user_id = "
                        + str(update.effective_chat.id)
                        + " WHERE id = "
                        + str(doc_key_corp_id)
                    )
                    await user2(
                        update,
                        context,
                        "Компания ИВЕА приветствует Вас!",
                    )
                    time.sleep(3)  # ждум 7сек
                    await update.message.reply_text(
                        text="Вам открыт доступ к документации.",
                    )
                else:
                    await update.message.reply_text("Этот ключ уже занят.")
            except Exception as err:
                logging.error("Error:" + str(err))
                await update.message.reply_text(
                    text='Совпадений нет, возможно вы ошиблись. \
        Пожалуйста, повторите попытку,повторно нажав на кнопку "Ввести ключ".',
                )


####################################################
# Прием сообщений c файлом(документом)
####################################################
async def send_document(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    arr = (
        "акта технической готовности",
        "пропуска, вывоза материалов, контейнера",
        "проведение исследований сточных вод",
        "следующую информацию",
        "проектную документацию",
    )
    arr2 = (
        "на запрос справки 2НДФЛ",
        "на запрос справки о месте работы",
        "на запрос о предоставлении сведений о детях",
        "на запрос выплаты за фактически отработанное время",
        "на запрос планируемой даты выплаты аванса, зарплаты",
        "на запрос информации о окладе (структура, сумма, даты выплаты)",
        "на запрос суммы за период (структура оклад, налоги)",
        "на запрос сканы документов (трудовой договор, все личные \
(паспорт и тд), приказ, и другие приказы)",
        "на запрос, что компания ждет от Вас, Ваш профессиональный рост \
(регистрация в ноприз, нострой, обучение на курсах повышения квалификации) \
и др.",
    )
    arr3 = [
        "трудовой договор (файл для прочтения, печати и подписи)",
        "внесена запись в трудовую книгу",
        "приказ о назначении на должность",
    ]
    if update.effective_chat and update.message:
        if update.effective_chat.id in user_triger:
            if user_triger[update.effective_chat.id]["triger"] == "send_doc":
                user_id = str(user_triger[update.effective_chat.id]["id"])
                num_doc = str(user_triger[update.effective_chat.id]["num_doc"])
                j = int(user_triger[update.effective_chat.id]["j"])
                user_triger.pop(update.effective_chat.id)

                if num_doc == "empl_send_sms":
                    array = arr3[j]
                elif num_doc != "999999":
                    array = arr[j]
                else:
                    array = arr2[j]

                if str(id_telegram["Pavel"]) == str(update.effective_chat.id):
                    try:
                        await insert_and_update_sql(
                            f"UPDATE request_control SET send ='true' \
                                WHERE callback_data = '{user_id}-{num_doc}'\
                                AND num = '{j}'"
                        )
                    except Exception as err:
                        logging.error(f"def send_document() = {err}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Елисеев Павел направляет Вам файл в ответ на \
запрос "
                        + array
                        + ":",
                    )  # Акт технической готовности по объекту
                elif str(id_telegram["Boss"]) == str(update.effective_chat.id):
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"Войтенко Андрей направляет Вам \
файл в ответ на запрос {array}:",
                    )  # Акт технической готовности по объекту
                elif str(id_telegram["my"]) == str(update.effective_chat.id):
                    try:
                        await insert_and_update_sql(
                            f"UPDATE request_control SET send ='true' \
                                WHERE callback_data = '{user_id}-{num_doc}' \
                                AND num = '{j}'"
                        )
                    except Exception as err:
                        logging.error(f"def send_document() = {err}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="Константин направляет Вам файл в ответ на \
запрос "
                        + array
                        + ":",
                    )  # Акт технической готовности по объекту
                if update.message.document:
                    if update.message.caption:
                        await context.bot.send_document(
                            chat_id=user_id,
                            document=update.message.document,
                            caption=update.message.caption,
                        )
                    else:
                        await context.bot.send_document(
                            chat_id=user_id, document=update.message.document
                        )
                if num_doc != "empl_send_sms":
                    info = pd.read_sql(
                        f"SELECT name, family_name FROM doc_key_corp \
                        WHERE user_id  = '{user_id}';",
                        engine,
                    )
                    text = (
                        "Сотрудник "
                        + str(info.loc[0, "name"])
                        + " "
                        + str(info.loc[0, "family_name"])
                        + " оповещен(а)."
                    )
                else:
                    info = pd.read_sql(
                        "SELECT * FROM doc_employment WHERE user_id = "
                        + str(update.effective_chat.id),
                        engine,
                    )
                    text = (
                        "Кандидат "
                        + str(info.loc[0, "name"])
                        + " тел: "
                        + str(info.loc[0, "tel"])
                        + " оповещен(а)."
                    )
                if update.message:
                    await update.message.reply_text(text)

            elif (
                user_triger[update.effective_chat.id]["triger"]
                == "empl_send_doc"
            ):
                if update.message.document:
                    # file_info = await context.bot.get_file(
                    #     update.message.document.file_id
                    # )

                    num_doc = user_triger[update.effective_chat.id]["num_doc"]
                    name_doc: str = ""
                    if num_doc == "1":
                        name_doc = "заявление"
                    elif num_doc == "2":
                        name_doc = "копия паспорта"
                    elif num_doc == "3":
                        name_doc = "копия трудовой книги"
                    elif num_doc == "4":
                        name_doc = "копия ИНН"
                    elif num_doc == "5":
                        name_doc = "копия снилс"
                    elif num_doc == "6":
                        name_doc = "копия диплома(ов)"
                    elif num_doc == "7":
                        name_doc = "сертификаты курсов"
                    elif num_doc == "8":
                        name_doc = "резюме"
                    current_dttm_str = datetime.now().strftime(
                        "%Y-%m-%d_%H.%M.%S"
                    )
                    if update.message:
                        await update.message.reply_text("Спасибо.")
                    employment_path = "/home/admin/py/employment/\
    {}_{}_{}.pdf".format(
                        name_doc, update.effective_chat.id, current_dttm_str
                    )
                    # TODO Надо разобраться и протестировать скачивания файла.
                    # В новой библиотеке нет старого параметра download
                    # await file_info.save(employment_path)
                    await insert_and_update_sql(
                        f"""UPDATE doc_employment
                        SET link_{str(user_triger[update.effective_chat.id][
                                  'num_doc'])} = '{employment_path}'
                        WHERE user_id ='{str(update.effective_chat.id)}';"""
                    )
                user_triger.pop(update.effective_chat.id)


async def num_doc_letters(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    name: str,
    save: bool = False,
) -> None:
    year: str = str(datetime.now().strftime("%y"))
    month: int = datetime.now().month
    quarter: str = str(((month - 1) // 3) + 1)
    num: int = 1
    info = pd.read_sql(
        f"""SELECT {name}
            FROM numbering_of_official_documents
            WHERE year = '{year}' and quarter = '{quarter}';""",
        engine,
    )
    if not info.empty:
        for idx, row in info.iterrows():
            # numeric letter or contract
            num = int(row[name]) + 1
    else:
        await insert_and_update_sql(
            f"""INSERT INTO numbering_of_official_documents (
                    contracts,
                    letters,
                    quarter,
                    year
                    ) VALUES('0','0','{quarter}','{year}');
                    """
        )
    if save:
        await insert_and_update_sql(
            f"""UPDATE numbering_of_official_documents SET {name} = '{num}'
                WHERE year = '{year}' and quarter = '{quarter}';"""
        )
    else:
        num_for_text: str = str(num)
        if int(num) < 10:
            num_for_text = f"0{num}"
        if name == "letters":
            text: str = f"0{year}/0{quarter}-{num_for_text}"
        else:
            text = f"0{quarter}/{year}-{num_for_text}"

        keyboard = [
            [
                InlineKeyboardButton(
                    text="присвоить номер",
                    callback_data="write_new_latter-" + name,
                ),
                InlineKeyboardButton(text="отмена", callback_data="cancel"),
            ]
        ]
        if update.message:
            await update.message.reply_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            asyncio.create_task(
                timer(update, context, 60, update.message.message_id + 1)
            )


async def timer(
    update: Update, context: ContextTypes.DEFAULT_TYPE, sec: int, msg_id: int
) -> None:
    await asyncio.sleep(sec)
    try:
        if update.effective_chat:
            # Передаем event loop явно
            await context.bot.delete_message(
                chat_id=update.effective_chat.id, message_id=msg_id
            )
    except Exception as err:
        logging.info("Проблема с таймером, возможно сообщение уже удалено")
        logging.error(f"Error_Timer - {err}")


async def send_excel_file(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    info = pd.read_sql(
        "SELECT number_doc, short_name, type_of_building, \
        type_of_equipment, brand, quantity, answer2, date, fio, tel, link, \
        num_account, sum FROM saving_query_the_supply \
        WHERE answer1 = 'принято' ORDER BY id ASC;",
        engine,
    )
    info = info.rename(
        columns={
            "number_doc": "Номер договора",
            "short_name": "Условное название объекта",
            "type_of_building": "Тип сооружения",
            "type_of_equipment": "Тип оборудования",
            "brand": "Марка",
            "quantity": "Количество (шт.)",
            "answer2": "Подтверждение",
            "date": "Дата",
            "fio": "ФИО",
            "tel": "Номер телефона",
            "link": "Ссылка на чертеж",
            "num_account": "Номер счета",
            "sum": "Сумма",
        }
    )
    info.to_excel(str(working_folder) + "report_supply.xlsx", index=False)
    if update.effective_chat:
        with open(str(working_folder) + "report_supply.xlsx", "rb") as file:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=file,
                filename="Отчет_комплектации.xlsx",
            )


async def location_processing(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat:
        if update.message:
            up_msg: Any = update.message
        else:
            up_msg = update.edited_message
        info = pd.read_sql(
            f"SELECT * FROM user_worker_key_corp \
            WHERE user_id = '{update.effective_chat.id}';",
            engine,
        )
        if not info.empty:
            await insert_and_update_sql(
                "UPDATE user_worker_key_corp \
SET location = '{}:{}', date_time = '{}' \
WHERE user_id = '{}';".format(
                    str(up_msg.location["longitude"]),
                    str(up_msg.location["latitude"]),
                    str(datetime.now()),
                    str(update.effective_chat.id),
                )
            )
            await context.bot.send_message(
                chat_id=id_telegram["my"],
                text=f"{info.loc[0,'name']} - бригада \
\"{info.loc[0,'num_working_group']}\"",
            )
            await context.bot.send_message(
                chat_id=id_telegram["Boss"],
                text=f"{info.loc[0,'name']} - бригада \
\"{info.loc[0,'num_working_group']}\"",
            )
            await context.bot.send_location(
                chat_id=id_telegram["my"],
                location=up_msg.location,
            )
            await context.bot.send_location(
                chat_id=id_telegram["Boss"],
                location=up_msg.location,
            )


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.effective_chat and context:
        user_triger[update.effective_chat.id] = {
            "triger": "Entera",
            "num_doc": 0,
        }
        await update.message.reply_text(text="Введите номер документа.")


async def inn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        list_msg: list[str] = [
            "Общество с ограниченной ответственностью «ИВЕА»",
            "ООО «ИВЕА»",
            "ИНН",
            "7716782520",
            "КПП",
            "771601001",
            "ОГРН",
            "1147746928735",
            "ОКПО",
            "16432457",
            "ОКВЭД",
            "70.22",
            "ОКАТО",
            "45280556000",
            "ОКТМО",
            "45351000000",
            "ОКОГУ",
            "4210014",
            "ОКФС",
            "16",
            "ОКОПФ",
            "12165",
            "Юридический адрес",
            "129344, г. Москва, ул. Искры, \
д. 31 Корпус 1, помещение I, офис 521, этаж 5",
        ]
        for msg in list_msg:
            q_msg_id = await update.message.reply_text(text=msg)
            asyncio.create_task(
                timer(update, context, 60, q_msg_id.message_id)
            )


async def timer_call_and_email(
    sec: int,
    text: str,
    text_for_email: str,
    text_for_tel: str,
    index: Any,
) -> None:
    await asyncio.sleep(sec * index)
    try:
        send_email(list_file=[], text=text_for_email, subject=str(text))
        # , addressees="info@ivea-water.ru"
        # #, addressees="kostik55555@yandex.ru"
        # call("89616599948", text_for_tel)
        # call("89253538733", text_for_tel)
        call("89264942722", text_for_tel)
    except Exception:
        logging.info("Проблема с таймером")


async def log_all_open_doc(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log_doc("all")
    await send_report_log_doc(update, context)


async def log_not_bild_doc(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log_doc("not_bild")
    await send_report_log_doc(update, context)


async def send_report_log_doc(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.effective_chat:
        with open(working_folder + "report_log_doc.pdf", "rb") as pdf:
            await context.bot.send_document(
                chat_id=update.effective_chat.id, document=pdf
            )


async def start_log_write_db(
    update: Update,
    doc_id: str,
    url_group: str = "",
) -> None:
    if update.message and update.effective_chat:
        info = pd.read_sql(
            f"SELECT * FROM log_chat_doc \
            WHERE id_chat  = '{update.message.chat.id}';",
            engine,
        )
        if len(info) == 0:
            await insert_and_update_sql(
                f"INSERT INTO log_chat_doc (id_chat, id_doc, name_group) \
                VALUES('{update.message.chat.id}', '{doc_id}', \
'{update.message.chat.title}');"
            )
        else:
            await insert_and_update_sql(
                f"UPDATE log_chat_doc SET id_doc = '{doc_id}', name_group = \
                '{update.message.chat.title}'\
                WHERE id_chat = '{update.message.chat.id}';"
            )
        if url_group != "":
            await insert_and_update_sql(
                f"UPDATE documents SET link_group = '{url_group}'\
                WHERE id = '{doc_id}';"
            )
        user_triger.pop(update.effective_chat.id)


async def start_log(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if update.message:
        await context.bot.delete_message(
            chat_id=update.message.chat.id,
            message_id=update.message.message_id,
        )
        if update.message.chat.type != "private" and update.effective_chat:
            if context.args:
                doc_id = context.args[0]
                url_group = context.args[1] if len(context.args) >= 2 else ""
                await start_log_write_db(
                    update, doc_id=doc_id, url_group=url_group
                )
            else:
                user_triger[update.effective_chat.id] = {
                    "triger": "start_log",
                    "num_doc": "0",
                }
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "ID документа, можно посмотреть тут.",
                            url="https://admin.ivea-water.ru/documents/\
list_documents/",
                        )
                    ]
                ]
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Пожалуйста, введите номер документа в журнал \
которого будет производиться запись.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )


async def resend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message and update.effective_chat and context:
        if str(update.effective_chat.id) == str(id_telegram["Boss"]) or str(
            update.effective_chat.id
        ) == str(id_telegram["my"]):
            info = pd.read_sql(
                "SELECT * FROM doc_entera_1c \
                WHERE \"delete\" = 'false' AND send_email = 'false';",
                engine,
            )
            if info.empty:
                await update.message.reply_text(
                    text="Документов, которые ждут подтверждения, нет.",
                )
            else:
                for idx, row in info.iterrows():
                    await send_msg_sheta(
                        num_1c=row["num_1c"],
                        user_list=[str(update.effective_chat.id)],
                    )
        elif str(update.effective_chat.id) == str(id_telegram["Pavel"]) or str(
            update.effective_chat.id
        ) == str(id_telegram["my"]):
            info = pd.read_sql(
                "SELECT * FROM public.request_control WHERE send = 'false';",
                engine,
            )
            if info.empty:
                await update.message.reply_text(
                    text="Запросов, которые ждут ответа, нет.",
                )
            else:
                for idx, row in info.iterrows():
                    if str(row["num"]) == "3":
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "Отправить документ",
                                    callback_data=f'send_doc-\
    {row["callback_data"]}-3',
                                )
                            ]
                        ]
                    else:
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "Отправить документ",
                                    callback_data=f'send_doc-\
    {row["callback_data"]}-{row["num"]}',
                                )
                            ],
                            [
                                InlineKeyboardButton(
                                    "Отправить ссылку",
                                    callback_data=f'send_link-\
    {row["callback_data"]}-{row["num"]}',
                                )
                            ],
                        ]
                    await update.message.reply_text(
                        text=row["text"],
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )


####################################################
# Прием текстовых сообщений
####################################################
async def handle_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    ####################################################
    # Прием текстовых по тригерам
    ####################################################
    if update.message:
        if update.message.text and update.effective_chat:
            user_text = update.message.text
            if update.effective_chat.id in user_triger:
                user_dict: dict[str, str] = user_triger[
                    update.effective_chat.id
                ]
                triger: str = user_dict["triger"]
                try:
                    num_doc: str | int = user_dict["num_doc"]
                except Exception:
                    num_doc = 0
                if (
                    "отменить" == user_text.lower()
                    or "отмена" == user_text.lower()
                    or "вернуться в главное меню" == user_text.lower()
                ):
                    await user2(
                        update, context, "Возвращаемся в главное меню."
                    )
                elif triger == "C":  # добавление контактов
                    user_triger.pop(update.effective_chat.id)
                    current_dttm_str = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    await insert_and_update_sql(
                        f"""INSERT INTO doc_contact(doc_id, text, datatime)
                            VALUES(
                            '{num_doc}',
                            '{user_text}',
                            '{current_dttm_str}'
                            );"""
                    )
                    await user2(update, context, "Данные добавленны.")
                elif triger == "reg":  # регистрация
                    await reg_user(update, context)
                elif triger == "reg_worker":  # регистрация новых рабочих.
                    text: str = "Случилась ошибка :("
                    # запрос фамилии, имени, отчества, дата рождения,
                    # номер паспорта, марка автомобиля, номер
                    if user_dict["FIO"] == "None":
                        user_dict["FIO"] = user_text
                        text = "Введите номер телефона для связи\
(в случаях необходимости)."
                    elif user_dict["tel"] == "None":
                        user_dict["tel"] = user_text
                        text = "Введите дату рождения."
                    elif user_dict["birthday"] == "None":
                        user_dict["birthday"] = user_text
                        text = "Введите номер паспорта."
                    elif user_dict["num_pasport"] == "None":
                        user_dict["num_pasport"] = user_text
                        text = "Введите марку автомобиля."
                    elif user_dict["brand_car"] == "None":
                        user_dict["brand_car"] = user_text
                        text = "Введите номер автомобиля."
                    elif user_dict["num_car"] == "None":
                        user_dict["num_car"] = user_text
                        person: dict[str, str] = user_dict
                        sms: str = (
                            "Добавлен новый пользователь.\n"
                            f"ФИО: {person['FIO']}\n"
                            f"Дата рождения: {person['birthday']}\n"
                            f"Номер телефона: {person['tel']}\n,"
                            f"Номер паспорта: {person['num_pasport']}\n"
                            f"Марка автомобиля: {person['brand_car']}\n"
                            f"Номер автомобиля: {person['num_car']}"
                        )
                        wh = True
                        key = ""
                        while wh:
                            key = ""
                            for i in range(8):
                                rand_num = randint(0, 9)
                                key += str(rand_num)  # letter[rand_num]
                            info = pd.read_sql_query(
                                f"""SELECT doc_key_corp.name,
                                key_for_people.name, user_worker_key_corp.name
                                FROM doc_key_corp, key_for_people,
                                user_worker_key_corp
                                WHERE doc_key_corp.a_key = '{key}'
                                or key_for_people.a_key = '{key}'
                                or user_worker_key_corp.a_key = '{key}'
                                limit 1;""",
                                engine,
                            )  #
                            if (
                                len(info) == 0
                            ):  # and len(info2) == 0 and len(info3) == 0:
                                wh = False
                        await insert_and_update_sql(
                            f"""INSERT INTO user_worker_key_corp (
                                user_id,
                                a_key,
                                name,
                                birthday,
                                tel,
                                num_pasport,
                                brand_car,
                                num_car,
                                date_time
                            ) VALUES(
                            '{update.effective_chat.id}',
                            '{key}',
                            '{user_dict['FIO']}',
                            '{user_dict['birthday']}',
                            '{user_dict['tel']}',
                            '{user_dict['num_pasport']}',
                            '{user_dict['brand_car']}',
                            '{user_dict['num_car']}',
                            '{datetime.now()}'
                            );"""
                        )
                        # отправляем смс Андрею Дмитриевичу
                        await context.bot.send_message(
                            chat_id=id_telegram["my"], text=sms
                        )
                        # отправляем смс самому пользвоателю
                        await update.message.reply_text(sms)
                        info = pd.read_sql_query(
                            f"SELECT id FROM user_worker_key_corp \
                            WHERE user_id = '{update.effective_chat.id}';",
                            engine,
                        )  #

                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "Определить в бригаду",
                                    callback_data=f"reg_worker_next-\
        {info.loc[0,'id']}",
                                )
                            ]
                        ]
                        await context.bot.send_message(
                            chat_id=id_telegram["Boss"],
                            text=sms,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                        # отправляем смс Михаилу Черкас для распределения
                        # 1726499460
                        user_triger.pop(update.effective_chat.id)
                        text = "Для завершения регистрации осталось отправить \
копию паспорта на почту info@ivea-water.ru"
                        # text2 = f"Ваш, временный, ключ доступа : {key}"
                        await update.message.reply_text(
                            text,
                            reply_markup=ReplyKeyboardMarkup(
                                [["Ввести код доступа"]],
                                resize_keyboard=True,
                                one_time_keyboard=False,
                            ),
                        )
                    if user_dict["num_car"] == "None":
                        await update.message.reply_text(text)
                elif (
                    triger == "filter"
                ):  # работа с фльтром или просто поиск документов по названию
                    user_triger.pop(update.effective_chat.id)
                    await get_filtr_list(update, context)
                elif (
                    triger == "filter_kontragent"
                ):  # работа с фльтром или просто поиск документов по названию
                    num = str(user_dict["num_doc"])
                    user_triger.pop(update.effective_chat.id)
                    await filter_kontragent(update, user_text.lower(), num)
                elif triger == "int":  # Интервал завершения работ по договорам
                    user_triger.pop(update.effective_chat.id)
                    await interval(update, user_text)
                elif triger == "choice6":
                    user_triger.pop(update.effective_chat.id)
                    info = pd.read_sql(
                        f"SELECT name, family_name, tel FROM doc_key_corp \
                        WHERE user_id  = '{update.effective_chat.id}';",
                        engine,
                    )
                    info2 = pd.read_sql(
                        f"SELECT number_doc, short_name FROM documents \
                        WHERE id = {num_doc};",
                        engine,
                    )
                    text = (
                        "Сотрудник "
                        + str(info.loc[0, "name"])
                        + " "
                        + str(info.loc[0, "family_name"])
                        + ", (тел. "
                        + str(info.loc[0, "tel"])
                        + ") запрашивает следующую информацию по Договору "
                        + str(info2.loc[0, "number_doc"])
                        + " ("
                        + str(info2.loc[0, "short_name"])
                        + "):\n\n"
                        + str(user_text)
                    )
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Отправить документ",
                                callback_data="send_doc-"
                                + str(update.effective_chat.id)
                                + "-"
                                + str(num_doc)
                                + "-3",
                            )
                        ]
                    ]
                    # Производим запись в БД
                    # чтобы при необходимости можно было вернуть
                    await insert_and_update_sql(
                        f"""INSERT INTO request_control (
                            text,
                            callback_data,
                            num
                        ) VALUES(
                            '{text}',
                            '{update.effective_chat.id}-{num_doc}',
                            '3'
                        );"""
                    )
                    await context.bot.send_message(
                        chat_id=id_telegram["Pavel"],
                        text=text,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )  # 943180118
                elif triger == "choice_log_write":
                    if user_text.lower() in [
                        "cписок договоров",
                        "контакты",
                        "нумерация официальных документов",
                        "завершение работ в период...",
                        "главное меню",
                        "корпоративный сайт",
                        "счет в оплату",
                        "отменить",
                        "отмена",
                        "вернуться в главное меню",
                    ]:
                        await user2(
                            update, context, "Запись в журнал работ отменена!"
                        )
                    user_triger.pop(update.effective_chat.id)
                    info = pd.read_sql(
                        f"SELECT name, family_name FROM doc_key_corp \
                        WHERE user_id  = '{update.effective_chat.id}';",
                        engine,
                    )
                    msg: str = (
                        str(user_text).replace("%", "%%").replace("'", "''")
                    )
                    await insert_and_update_sql(
                        f"""INSERT INTO log_doc (
                            doc_id,
                            text,
                            date_time,
                            user_name
                        ) VALUES(
                        '{num_doc}',
                        '{msg}',
                        '{datetime.now()}',
                        '{info.loc[0, 'name']} {info.loc[0, 'family_name']}'
                        );"""
                    )
                    await update.message.reply_text(
                        text="Запись успешно сохранена.",
                    )
                    text = ""
                    info_doc_id = pd.read_sql(
                        f"SELECT name, number_doc, date FROM documents \
                        WHERE id = '{num_doc}';",
                        engine,
                    )
                    for idx, row in info_doc_id.iterrows():
                        text += f"Договор № {row['number_doc']} от \
{row['date']} г.\nУсловное название: {row['name']}\n\n"
                        break
                    text += f"\"{msg}\"\n{info.loc[0, 'name']} \
{info.loc[0, 'family_name']}"
                    await context.bot.send_message(
                        chat_id=id_telegram["Boss"], text=text
                    )

                elif triger == "send_text" or triger == "send_link":
                    arr: tuple[str, str, str, str, str] = (
                        "на запрос акта технической готовности",
                        "по запросу заявки на пропуск, вывоз материалов, \
контейнера",
                        "по запросу заявки на проведение исследований \
сточных вод",
                        "на запрос информации",
                        "на запрос проектной документации",
                    )
                    arr2: tuple[
                        str, str, str, str, str, str, str, str, str
                    ] = (
                        "на запрос справки 2НДФЛ",
                        "на запрос справки о месте работы",
                        "на запрос о предоставлении сведений о детях",
                        "на запрос выплаты за фактически отработанное время",
                        "на запрос планируемой даты выплаты аванса, зарплаты",
                        "на запрос информации о окладе (структура, сумма, \
даты выплаты)",
                        "на запрос суммы за период (структура оклад, налоги)",
                        "на запрос сканы документов (трудовой договор, все \
личные (паспорт и тд), приказ, и другие приказы)",
                        "на запрос, что компания ждет от Вас, Ваш \
профессиональный рост (регистрация в ноприз, нострой, \
обучение на курсах повышения квалификации) и др.",
                    )
                    arr3: list[str] = [
                        "трудовой договор (файл для прочтения, печати и \
подписи)",
                        "внесена запись в трудовую книгу",
                        "приказ о назначении на должность",
                    ]
                    st_user_id = user_dict["user_id"]
                    j = int(user_dict["j"])
                    if str(id_telegram["Pavel"]) == str(
                        update.effective_chat.id
                    ):
                        try:
                            await insert_and_update_sql(
                                f"UPDATE request_control SET send ='true' \
                                WHERE callback_data = '{st_user_id}-{num_doc}'\
                                AND num = '{j}'"
                            )
                        except Exception as err:
                            logging.error(f"def send_document() = {err}")
                        name = "Елисеев Павел "
                    elif str(id_telegram["Boss"]) == str(
                        update.effective_chat.id
                    ):
                        name = "Войтенко Андрей "
                    else:
                        try:
                            await insert_and_update_sql(
                                f"UPDATE request_control SET send ='true' \
WHERE callback_data = '{st_user_id}-{num_doc}' AND num = '{j}'"
                            )
                        except Exception as err:
                            logging.error(f"def send_document() = {err}")
                        name = "Константин "
                    if num_doc == "empl_send_sms":
                        array = arr3[j]
                    elif num_doc != "999999":
                        if triger == "send_link":
                            array = arr[j]
                            if j == 4:
                                await insert_and_update_sql(
                                    "UPDATE documents \
                                        SET project_doc_link = '"
                                    + str(user_text)
                                    + "' WHERE id = "
                                    + str(num_doc)
                                    + ";"
                                )
                    else:
                        array = arr2[j]
                    if triger == "send_link":
                        text = "направляет Вам ссылку на файл, в ответ "
                    else:
                        text = "ответил "
                    user_triger.pop(update.effective_chat.id)
                    await context.bot.send_message(
                        chat_id=st_user_id,
                        text=name + text + array + " :\n" + str(user_text),
                    )
                    if num_doc != "empl_send_sms":
                        info = pd.read_sql(
                            f"SELECT name, family_name FROM doc_key_corp \
                            WHERE user_id  = '{st_user_id}';",
                            engine,
                        )
                        text = (
                            "Сотрудник "
                            + str(info.loc[0, "name"])
                            + " "
                            + str(info.loc[0, "family_name"])
                            + " оповещен(а)."
                        )
                    else:
                        info = pd.read_sql(
                            "SELECT * FROM doc_employment WHERE user_id = "
                            + str(update.effective_chat.id),
                            engine,
                        )
                        text = (
                            "Кандидат "
                            + str(info.loc[0, "name"])
                            + " тел: "
                            + str(info.loc[0, "tel"])
                            + " оповещен(а)."
                        )
                    await update.message.reply_text(text=text)
                elif triger == "date":
                    info = pd.read_sql_query(
                        f"SELECT date_end, noct FROM doc_date \
                        WHERE id ={num_doc}",
                        engine,
                    )
                    try:
                        noct: int = 0
                        for idx, row in info.iterrows():
                            noct = int(row["noct"])
                        new_date = str(user_text).split(".")

                        d = new_date[0]
                        m = new_date[1]
                        y = new_date[2]
                        if int(y) >= 2021 and int(y) <= 3021:
                            if int(m) <= 12:
                                if (
                                    (
                                        (int(d) <= 31)
                                        and (int(m) in (1, 3, 5, 7, 8, 10, 12))
                                    )
                                    or (
                                        (int(d) <= 30)
                                        and (int(m) in (4, 6, 9, 11))
                                    )
                                    or ((int(d) <= 29) and (int(m) == 2))
                                ):
                                    if noct > 0:
                                        await insert_and_update_sql(
                                            f"""
UPDATE doc_date
SET date_end = '{y}-{m}-{d} 00:00:00', noct = '{noct + 1}'
WHERE id = {num_doc};
"""
                                        )
                                    else:
                                        await insert_and_update_sql(
                                            f"""
                                        UPDATE doc_date
                                        SET date_end = '{y}-{m}-{d} 00:00:00',
                                        date1 = '{info.loc[0, 'date_end']}',
                                        noct = '1'
                                        WHERE id = {num_doc};"""
                                        )
                                    user_dict["triger"] = "comment"
                                    await update.message.reply_text(
                                        text="Напишите причину переноса \
сроков.",
                                    )
                                else:
                                    await update.message.reply_text(
                                        text="Не правильно указан день.\
Повторите попытку!",
                                    )
                            else:
                                await update.message.reply_text(
                                    text="Не правильно указан месяц.\
Повторите попытку!"
                                )
                        else:
                            await update.message.reply_text(
                                text="Не правильно указан год.\
Повторите попытку!",
                            )
                    except Exception:
                        await update.message.reply_text(
                            text="Повторите попытку!"
                        )
                elif triger == "comment":
                    await insert_and_update_sql(
                        f"UPDATE doc_date SET coment = '{str(user_text)}' \
                        WHERE id = {num_doc}"
                    )
                    user_triger.pop(update.effective_chat.id)
                    await update.message.reply_text(text="Изменения внесены.")
                elif triger == "need_link":
                    user_supply[update.effective_chat.id][
                        "link"
                    ] = user_text  # saving a link in the Data "user_supply"
                    user_dict["triger"] = (
                        "brand"  # saving brand in Data "Triger"
                    )
                    await update.message.reply_text(
                        text="Введите название бренда оборудования",
                    )  # Sending a message to the user
                elif triger == "brand":  # продолжение функции "СНАБЖЕНИЕ"
                    user_supply[update.effective_chat.id][
                        "brand"
                    ] = user_text  # saving a brand in the Data "user_supply"
                    user_dict["triger"] = (
                        "quantity"  # saving quantity in Data "Triger"
                    )
                    await update.message.reply_text(
                        text="Введите необходимое количество шт.",
                    )  # Sending a message to the user
                elif triger == "quantity":  # продолжение функции "СНАБЖЕНИЕ"
                    if user_text.isnumeric():
                        text = f"""Отправитель: \
{user_supply[update.effective_chat.id]['fio']}.\n
Условное  название объекта: \
{user_supply[update.effective_chat.id]['short_name']},\n
Тип сооружения: \
{user_supply[update.effective_chat.id]['type_of_building']},\n
Тип оборудования: \
{user_supply[update.effective_chat.id]['type_of_equipment']},\n
Марка: {user_supply[update.effective_chat.id]['brand']},\n
Количество: {user_text} шт."""  # Collecting a text to send.
                        text += (
                            f"\nСсылка на чертеж: \
{user_supply[update.effective_chat.id]['link']}"
                            if user_supply[update.effective_chat.id]["link"]
                            != ""
                            else ""
                        )
                        local_dict_us: dict[str, str] = user_supply[
                            update.effective_chat.id
                        ]
                        await insert_and_update_sql(
                            f"""INSERT INTO saving_query_the_supply (
                                user_id,
                                number_doc,
                                short_name,
                                type_of_building,
                                type_of_equipment,
                                brand,
                                quantity,
                                fio,
                                tel,
                                link
                            ) VALUES(
                                '{str(update.effective_chat.id)}',
                                '{local_dict_us['number_doc']}',
                                '{local_dict_us['short_name']}',
                                '{local_dict_us['type_of_building']}',
                                '{local_dict_us['type_of_equipment']}',
                                '{local_dict_us['brand']}',
                                '{user_text}',
                                '{local_dict_us['fio']}',
                                '{local_dict_us['tel']}',
                                '{local_dict_us['link']}'
                            );"""
                        )
                        # Saving the collect information in BD
                        info = pd.read_sql(
                            "SELECT id FROM saving_query_the_supply \
                                ORDER BY id ASC;",
                            engine,
                        )  # Looking all the id ...
                        finish_id = info.loc[
                            len(info) - 1, "id"
                        ]  # ...and take final the id
                        keyboard = [
                            [
                                InlineKeyboardButton(
                                    "согласовано",
                                    callback_data=f"accepted-{str(finish_id)}",
                                )
                            ]
                        ]
                        await context.bot.send_message(
                            chat_id=id_telegram["Boss"],
                            text=text,
                            reply_markup=InlineKeyboardMarkup(keyboard),
                        )
                        logging.info(
                            f'Функция "СНАБЖЕНИЕ" chat_id=\
{update.effective_chat.id}:\n{text}'
                        )
                        keyboard_for_user = [
                            [
                                InlineKeyboardButton(
                                    "добавить еще",
                                    callback_data="types-"
                                    + user_supply[update.effective_chat.id][
                                        "doc_id"
                                    ],
                                ),
                                InlineKeyboardButton(
                                    "завершить", callback_data="cancel"
                                ),
                            ]
                        ]
                        await update.message.reply_text(
                            text="Информация записанна и передана.",
                            reply_markup=InlineKeyboardMarkup(
                                keyboard_for_user
                            ),
                        )
                    else:
                        await update.message.reply_text(
                            text="Введите необходимое количество шт. \
                            (используйте только цифры)",
                        )
                elif (
                    triger == "link_yandex"
                ):  # начало функции "Счет в оплату" принимаем ссылку
                    user_dict["link_yandex"] = user_text
                    user_dict["triger"] = "num_account"
                    await update.message.reply_text(
                        text="Прикрепите номер счета"
                    )
                elif (
                    triger == "num_account"
                ):  # продолжение функции "Счет в оплату" принимаем номер счета
                    user_dict["num_account"] = user_text
                    user_dict["triger"] = "sum"
                    await update.message.reply_text(text="Прикрепите сумму")
                elif (
                    triger == "sum"
                ):  # начало функции "Счет в оплату" принимаем сумму.
                    # и выбираем куда записать собранную информацию
                    user_dict["sum"] = user_text
                    user_dict["triger"] = "end_supply"
                    info = pd.read_sql(
                        f"""SELECT id, short_name, type_of_building,
                        type_of_equipment, brand, quantity, link
                        FROM saving_query_the_supply
                        WHERE answer1 = 'принято'
                        and short_name = '{user_dict[
                            'short_name']}'
                        ORDER BY id ASC;""",
                        engine,
                    )
                    text = f"Введите номер комплектации цифрами. \
Можно ввести неслолько значений через запятую.\n{info.loc[0, 'short_name']}:\n"
                    for i in range(len(info)):
                        if (
                            info.loc[i, "link"] is None
                            or info.loc[i, "link"] == ""
                        ):
                            text += f"№{info.loc[i, 'id']} - \
{info.loc[i, 'type_of_building']}, {info.loc[i, 'type_of_equipment']}, \
{info.loc[i, 'brand']}, {info.loc[i, 'quantity']}шт.\n"
                    await update.message.reply_text(text=text)
                elif triger == "end_supply":
                    try:
                        await insert_and_update_sql(
                            f"""UPDATE saving_query_the_supply
                            SET link = '{user_dict[
                                'link_yandex']}',
                            num_account = '{user_dict[
                                'num_account']}',
                            sum = '{user_dict['sum']}'
                            WHERE id in ({user_text})"""
                        )
                        await user2(
                            update,
                            context,
                            f"Изменения внесены. №{user_text}",
                        )
                    except Exception:
                        logging.error(
                            f"Не удалось записать значение в БД\
\n{user_dict}"
                        )
                        logging.error(
                            f"""UPDATE saving_query_the_supply
                            SET link = '{user_dict[
                                'link_yandex']}',
                            num_account = '{user_dict[
                                'num_account']}',
                            sum = '{user_dict['sum']}'
                            WHERE id in ({user_text})"""
                        )
                        user_triger.pop(update.effective_chat.id)
                elif triger == "reg_worker_next":
                    user_dict["num_working_group"] = str(user_text.lower())
                    user_dict["triger"] = "reg_worker_next2"
                    await update.message.reply_text(
                        text=f"Укажите предположительную дату до которого \
{user_dict['name']} будет находиться в бригаде {user_text}",
                    )
                elif triger == "reg_worker_next2":
                    day: str = "01"
                    month: str = "01"
                    year: str = "1990"
                    if "." in user_text:
                        date = str(user_text).split(".")
                        day = date[0]
                        month = date[1]
                        year = date[2]
                    elif "-" in user_text:
                        date = str(user_text).split("-")
                        day = date[2]
                        month = date[1]
                        year = date[0]
                    hours = datetime(int(year), int(month), int(day), 9, 30)

                    await insert_and_update_sql(
                        f"""UPDATE user_worker_key_corp
                        SET num_working_group = '\
{user_dict['num_working_group']}',
                        date_ower_num_group = '{hours}'
                        WHERE id = '{user_dict['id']}';"""
                    )
                    await user2(update, context, "готово.")
                elif triger == "Entera":
                    sms = entera(user_text)
                    if sms:
                        await update.message.reply_text(text=sms)
                elif triger == "update_k_info":
                    num_inn: str = user_dict["inn"]
                    if user_dict["trade_name"] == "None":
                        user_dict["trade_name"] = user_text
                        await update.message.reply_text(
                            text=f"ИНН:{num_inn}\nОпишите контрагента \
(кратко о товарах, услугах).",
                        )
                    elif user_dict["description"] == "None":
                        user_dict["description"] = user_text
                        await update.message.reply_text(
                            text=f"""ИНН:{num_inn}
Введите ссылку на сайт,если такая имеется""",
                        )
                    elif user_dict["url"] == "None":
                        user_dict["url"] = user_text
                        await update.message.reply_text(
                            text=f"""ИНН:{num_inn}
Введите контакты (менеджер, бухгалтер)""",
                        )
                    elif user_dict["tel"] == "None":
                        user_dict["tel"] = user_text
                        await insert_and_update_sql(
                            f"""UPDATE employee_cards_counterparty
                            SET trade_name = '{user_dict[
                                'trade_name']}',
                            description = '{user_dict[
                                'description']}',
                            url = '{user_dict['url']}',
                            tel = '{user_dict['tel']}'
                            WHERE inn = '{user_dict[
                                'inn']}';""",
                            eng=engine2,
                        )
                        await update.message.reply_text(
                            text=f"""ИНН:{num_inn}
Данные заполненны и сохранены.""",
                        )
                        user_triger.pop(update.effective_chat.id)
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id - 1,
                    )
                elif triger == "explanation":
                    name_contragent: str = user_dict["contragent"]
                    id_entera_1c: str = user_dict["id_entera_1c"]
                    msg_inn: str = str(user_text).replace(" ", "")
                    if msg_inn.isnumeric():
                        num_inn = msg_inn
                        check_info: pd.DataFrame = pd.read_sql(
                            f"""SELECT * FROM employee_cards_counterparty
                            WHERE inn = '{num_inn}';""",
                            engine2,
                        )
                        if check_info.empty:
                            await insert_and_update_sql(
                                f"""
                                    INSERT INTO employee_cards_counterparty (
                                            inn,
                                            title,
                                            group_k,
                                            type_k,
                                            total,
                                            load_by_month,
                                            standard_deviation
                                        )
                                    VALUES(
                                            '{num_inn}',
                                            '{name_contragent}',
                                            'Поставщики',
                                            'Юридическое лицо',
                                            '0',
                                            '0',
                                            '0'
                                        );""",
                                eng=engine2,
                            )
                            text = f"""Добавлен новый контрагент
Полное наименование: {name_contragent}
Группа: Поставщики
Вид контрагента: Юридическое лицо
ИНН контрагента: {num_inn}"""
                            keyboard = [
                                [
                                    InlineKeyboardButton(
                                        "Заполнить данные",
                                        callback_data=f"update_k_info-\
{int(num_inn)}",
                                    )
                                ]
                            ]
                            await context.bot.send_message(
                                chat_id=id_telegram["supply"],
                                text=text,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                            )
                            await context.bot.send_message(
                                chat_id=id_telegram["my"],
                                text=text,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                            )
                            await context.bot.send_message(
                                chat_id=id_telegram["Boss"],
                                text=text,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                            )
                            text_explanation: str = (
                                f'Обоснуйте необходимость \
работы с новым контрагентом "{name_contragent}"'
                            )
                            keyboard = [
                                [
                                    InlineKeyboardButton(
                                        "Записать обоснование",
                                        callback_data=f"explanation_next\
-{id_entera_1c}",
                                    )
                                ]
                            ]
                            await context.bot.send_message(
                                chat_id=id_telegram["supply"],
                                text=text_explanation,
                                reply_markup=InlineKeyboardMarkup(keyboard),
                            )
                        else:
                            # Если мы нашли по inn записи, то логично,
                            # что просто произошло переименование в 1с
                            # поэтому делаем update в 2х БД
                            await insert_and_update_sql(
                                f"""UPDATE employee_cards_counterparty
                            SET title = '{name_contragent}'
                            WHERE inn = '{num_inn}';""",
                                eng=engine2,
                            )
                        await insert_and_update_sql(
                            f"""UPDATE doc_entera_1c
                            SET inn = '{num_inn}'
                            WHERE id = '{id_entera_1c}';"""
                        )
                        user_triger.pop(update.effective_chat.id)
                    else:
                        await update.message.reply_text(
                            text="Вы, наверное, опечатались. ИНН должен \
содержать только цифры.\nПопробуйте еще раз.",
                        )

                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id - 1,
                    )
                elif triger == "explanation_next":
                    msg = str(user_text)
                    id_entera_1c = user_dict["id_entera_1c"]
                    await insert_and_update_sql(
                        f"""UPDATE new_kontragent_in_sheta
                    SET explanation = '{msg}'
                    WHERE id_entera_1c = '{id_entera_1c}';"""
                    )
                    info = pd.read_sql(
                        f"""SELECT num_doc, date_doc, sum, contragent, \
                        comment, num_1c, inn
                        FROM doc_entera_1c WHERE id = '{id_entera_1c}';""",
                        engine,
                    )
                    for idx, row in info.iterrows():
                        await send_msg_sheta(
                            num_1c=row["num_1c"],
                            msg="\n\nОбоснование для нового контрагента:\n"
                            + str(msg),
                        )
                        user_triger.pop(update.effective_chat.id)
                        await context.bot.delete_message(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id - 1,
                        )
                        break

                elif triger == "platejka":
                    info = pd.read_sql(
                        f"""SELECT * FROM doc_entera_1c
                        WHERE num_1c LIKE ('%%{user_text}')
                        AND year = '{datetime.now().strftime('%Y')}'
                        ;""",
                        engine,
                    )
                    if len(info) != 0:
                        if bool(info.loc[0, "send_email"]):
                            text = user_dict["text"]
                            text_for_email = f"""{text}
Счёт № {info.loc[0,'num_doc']} от {info.loc[0,'date_doc']} на сумму \
{info.loc[0,'sum']} руб.
Контрагент: {info.loc[0,'contragent']}
Комментарий: {info.loc[0,'comment']}"""
                            text_for_tel = f"Автоматическое \
уведомление..........{str(text).lower()}......Контрагент: \
{info.loc[0,'contragent']}.......Подробнее на электронной почте."
                            time_now: str = datetime.now().strftime("%H:%M:%S")
                            # Время на сервере преобразованное в нужный нам вид
                            if time_now > "09:00:00" and time_now < "19:00:00":
                                send_email(
                                    list_file=[],
                                    text=text_for_email,
                                    subject=str(text),
                                )
                                # , addressees="info@ivea-water.ru"
                                # addressees="kostik55555@yandex.ru"
                                # call("89616599948", text_for_tel)
                                # call("89253538733", text_for_tel)
                                call("89264942722", text_for_tel)
                                await user2(
                                    update,
                                    context,
                                    "Письмо отправлено, ждите ответа от \
бухгалтерии.",
                                )
                            else:
                                try:
                                    with open(
                                        f"{working_folder}dont_call.json"
                                    ) as json_file:
                                        data = json.load(json_file)
                                except Exception:
                                    data = {}
                                date_now: datetime = datetime.now()
                                sec_end: int = 0
                                if time_now > "19:00:00":
                                    date_now = datetime.now() + timedelta(
                                        days=1
                                    )
                                    h = datetime.now().strftime("%H")
                                    m = datetime.now().strftime("%M")
                                    s = datetime.now().strftime("%S")
                                    sec_end = (24 + 9) * 3600 - (
                                        ((int(h) * 60) + int(m)) * 60 + int(s)
                                    )
                                elif time_now < "09:00:00":
                                    date_now = datetime.now()
                                    h = datetime.now().strftime("%H")
                                    m = datetime.now().strftime("%M")
                                    s = datetime.now().strftime("%S")
                                    sec_end = (
                                        (int(h) + 9) * 60 + int(m)
                                    ) * 60 + int(s)
                                if date_now not in data.keys():
                                    data[date_now] = 1
                                else:
                                    data[date_now] += 1
                                with open(
                                    f"{working_folder}dont_call.json", "w"
                                ) as outfile:
                                    json.dump(data, outfile)  # _save
                                asyncio.create_task(
                                    timer_call_and_email(
                                        sec_end,
                                        text,
                                        text_for_email,
                                        text_for_tel,
                                        data[date_now],
                                    )
                                )
                        else:
                            await update.message.reply_text(
                                text="Данный счет еще не согласован.\
\nДождитесь согласования или введите другой номер.",
                            )
                    else:
                        await update.message.reply_text(
                            text='Такого номера нет в базе данных.\
\nПожалуйста, повторите ввод или нажмите "Отмена".',
                        )
                elif triger == "verification":
                    await context.bot.send_message(
                        chat_id=id_telegram["my"],
                        text=f"Ошибочные данные в ДР:\
\nuser_id = {update.effective_chat.id}\
\nid = {user_dict['id_user']}\
\nСообщение пользователя:\n{user_text}",
                    )
                    await update.message.reply_text(text="Спасибо")
                    user_triger.pop(update.effective_chat.id)
                elif triger == "start_log":
                    try:
                        await context.bot.delete_message(
                            chat_id=update.message.chat.id,
                            message_id=update.message.message_id - 1,
                        )
                    except Exception:
                        pass
                    try:
                        await context.bot.delete_message(
                            chat_id=update.message.chat.id,
                            message_id=update.message.message_id,
                        )
                    except Exception:
                        pass
                    await start_log_write_db(update, doc_id=user_text)
                else:
                    await handle_text_location(update, context, user_triger)
            ####################################################
            # Прием текстовых сообщений
            ####################################################
            elif "cписок договоров" == user_text.lower():
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Полный список", callback_data="choice1"
                        ),
                        InlineKeyboardButton(
                            "Использовать фильтр", callback_data="choice2"
                        ),
                    ]
                ]
                text = "Вывести полный список или воспозьзуемся фильтром?"
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
                #########################################
            elif "контакты" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await contact(update, context)
            elif "получить" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await my_doc(update, context, "contact_get")
            elif "добавить" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await my_doc(update, context, "contact_add")
            elif "контрагенты" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await kontragent(update, context)
                ##########################################
            elif "договор" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await user2(update, context, "Эта функция ещё в разработке...")
            elif "акт" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await user2(update, context, "Эта функция ещё в разработке...")
            elif "нумерация официальных документов" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                sms = "Какой документ необходимо пронумеровать?"
                reply_keyboard = [["письма", "договора"], ["главное меню"]]
                await update.message.reply_text(
                    sms,
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard,
                        resize_keyboard=True,
                        one_time_keyboard=False,
                    ),
                )
            elif "письма" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await num_doc_letters(update, context, "letters")
            elif "договора" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await num_doc_letters(update, context, "contracts")
            elif "список комплектаций" == user_text.lower() and (
                update.effective_chat.id == id_telegram["Boss"]
                or update.effective_chat.id == id_telegram["supply"]
            ):
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await send_excel_file(update, context)
            elif "список рабочих" == user_text.lower() and (
                update.effective_chat.id == id_telegram["Boss"]
                or update.effective_chat.id == id_telegram["supply"]
            ):
                info = pd.read_sql(
                    "SELECT name, tel FROM user_worker_key_corp \
                    ORDER BY date_time DESC;",
                    engine,
                )
                text = ""
                for i in range(len(info)):
                    text += f'{i+1}) {info.loc[i,"name"]} - тел: \
{info.loc[i,"tel"]}\n'
                await update.message.reply_text(text)
            elif "посмотреть геопозицию" == user_text.lower() and (
                update.effective_chat.id == id_telegram["Boss"]
                or update.effective_chat.id == id_telegram["supply"]
            ):
                info = pd.read_sql(
                    "SELECT name, user_id FROM user_worker_key_corp \
                    ORDER BY date_time DESC;",
                    engine,
                )
                text = "Выберите рабочего чтобы посмотреть его геолокацию:"
                keyboard = []
                for i in range(len(info)):
                    keyboard += [
                        [
                            InlineKeyboardButton(
                                str(info.loc[i, "name"]),
                                callback_data=f'location-\
{info.loc[i, "user_id"]}',
                            )
                        ]
                    ]
                await update.message.reply_text(
                    text=text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            elif "главное меню" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await user2(update, context, "Возвращаемся в главное меню.")
            elif "завершение работ в период..." == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                await update.message.reply_text(
                    text="Введите желаемый период в колличестве дней \
(цифрами).\n\nБудет создан список договоров, у которых колличество дней до \
завершения работ будет меньше или равно данному числу.",
                )
                user_triger[update.effective_chat.id] = {
                    "triger": "int",
                    "num_doc": "0",
                }
                # ###############################################
            elif "ввести код доступа" == user_text.lower():
                try:
                    info = pd.read_sql(
                        "SELECT user_id FROM doc_key_corp WHERE user_id = "
                        + str(update.effective_chat.id),
                        engine,
                    )
                    user = info.loc[0, "user_id"]
                    if user == update.effective_chat.id:
                        await update.message.reply_text(
                            text="Вы уже зарегистрированы!",
                        )
                except Exception as err:
                    logging.error("Error:" + str(err))
                    await update.message.reply_text(
                        text="Отправьте в сообщении код доступа.",
                    )
                    user_triger[update.effective_chat.id] = {
                        "triger": "reg",
                        "num_doc": "0",
                    }
                    await context.bot.delete_message(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id,
                    )
            elif "счет в оплату" == user_text.lower():
                await context.bot.delete_message(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                )
                # "triger": 'link_yandex',
                user_triger[update.effective_chat.id] = {
                    "triger": "None",
                    "num_doc": "None",
                    "link_yandex": "None",
                    "num_account": "None",
                    "short_name": "None",
                    "sum": "None",
                    "id": "None",
                }
                info = pd.read_sql(
                    """SELECT short_name FROM saving_query_the_supply
                    WHERE answer1 = 'принято' ORDER BY id ASC;""",
                    engine,
                )
                keyboard_for_user = []
                short_name = []
                for i in range(len(info)):
                    if info.loc[i, "short_name"] not in short_name:
                        keyboard_for_user += [
                            [
                                InlineKeyboardButton(
                                    str(info.loc[i, "short_name"]),
                                    callback_data=f'supply_short_name#*&*#\
{info.loc[i, "short_name"]}',
                                )
                            ]
                        ]
                        short_name += [info.loc[i, "short_name"]]
                keyboard_for_user += [
                    [InlineKeyboardButton("Отмена", callback_data="cancel")]
                ]
                await update.message.reply_text(
                    text="Выберите условное название договора из списка",
                    reply_markup=InlineKeyboardMarkup(keyboard_for_user),
                )
            elif "id" == user_text.lower() and (
                update.message.chat.type == "supergroup"
                or update.message.chat.type == "group"
            ):
                await context.bot.send_message(
                    chat_id=id_telegram["my"],
                    text="ID: "
                    + str(update.effective_chat.id)
                    + "\n name: "
                    + str(update.effective_chat.title),
                )
            elif "зарегистрироваться" == user_text.lower():
                # запрос фамилии, имени, отчества, дата рождения,
                # номер паспорта, марка автомобиля, номер
                await update.message.reply_text(text="Введите ФИО.")
                user_triger[update.effective_chat.id] = {
                    "triger": "reg_worker",
                    "num_doc": "None",
                    "FIO": "None",
                    "birthday": "None",
                    "tel": "None",
                    "num_pasport": "None",
                    "brand_car": "None",
                    "num_car": "None",
                }
            elif "объекты" == user_text.lower():
                reply_keyboard = [
                    ["Добавить объект"],
                    ["Показать рабочих на объекте"],
                    ["Редактировать объект"],
                    ["Главное меню"],
                ]
                sms = "В данном меню можно:\n- Добавить новый объект\
\n- Редактировать объект. А именно изменить название обьекта или бригаду, \
или вообще удалить объект\n- Показать рабочих на объекте"
                await update.message.reply_text(
                    text=sms,
                    reply_markup=ReplyKeyboardMarkup(
                        reply_keyboard,
                        resize_keyboard=True,
                        one_time_keyboard=False,
                    ),
                )
            elif "показать рабочих на объекте" == user_text.lower():
                await read_location(update)
            elif "добавить объект" == user_text.lower():
                await my_doc(update, context, flag="doc_montage")
                # write_location(update, context, user_triger)
            elif "редактировать объект" == user_text.lower():
                await edit_location(update)
            elif (
                "запросить платёжку" == user_text.lower()
                or "напоминание" == user_text.lower()
                or "доплатить" == user_text.lower()
            ) and update.effective_chat.id == id_telegram["supply"]:
                if "напоминание" == user_text.lower():
                    text = "СРОЧНО НУЖНА ОПЛАТА. В базе 1С склада счет есть."
                elif "доплатить" == user_text.lower():
                    text = "Требуется доплата по счету."
                else:
                    text = "Требуется платёжное поручение с отметкой банка."
                user_triger[update.effective_chat.id] = {
                    "triger": "platejka",
                    "nun_doc": "0",
                    "text": text,
                }
                await update.message.reply_text(
                    text="Введите номер присвоенный счету в 1С.\
\nПример: 0000-000092 или просто 0092",
                    reply_markup=ReplyKeyboardMarkup(
                        [["Отменить"]],
                        resize_keyboard=True,
                        one_time_keyboard=False,
                    ),
                )
            elif "добавить документ" == user_text.lower() and (
                update.effective_chat.id == id_telegram["Boss"]
                or update.effective_chat.id == id_telegram["Pavel"]
            ):
                await update.message.reply_text(
                    text="Для заполнения информации необходимо пройти по \
ссылке:",
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton(
                                    "Добавить документ в БД",
                                    url=f"https://admin.ivea-water.ru/\
new_document?id={update.effective_chat.id}",
                                )
                            ]
                        ]
                    ),
                )
            elif "корпоративный сайт" == user_text.lower():
                keyboard = [
                    [
                        InlineKeyboardButton(
                            "Корпоративный сайт.",
                            url="https://admin.ivea-water.ru/",
                        )
                    ]
                ]
                await update.message.reply_text(
                    text="Ссылка...",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                )
            else:
                if update.message.chat.type != "private":
                    info = pd.read_sql(
                        f"SELECT * FROM log_chat_doc \
                        WHERE id_chat = '{update.message.chat.id}';",
                        engine,
                    )
                    for idx, row in info.iterrows():
                        if update.message.from_user:
                            info2 = pd.read_sql(
                                f"SELECT name, family_name FROM doc_key_corp \
                                WHERE user_id = '\
{update.message.from_user.id}';",
                                engine,
                            )  # используем update.message.from_user.id
                            # чтобы узналь личный id телеги пользователя
                            for idx2, row2 in info2.iterrows():
                                msg = (
                                    str(user_text)
                                    .replace("%", "%%")
                                    .replace("'", "''")
                                )
                                await insert_and_update_sql(
                                    f"""
                            INSERT INTO log_doc (
                                doc_id,
                                text,
                                date_time,
                                user_name
                            ) VALUES(
                                '{row['id_doc']}',
                                '{msg}',
                                '{datetime.now()}',
                                '{row2['name']} {row2['family_name']} (чат)'
                            );
                                    """
                                )
                else:
                    await update.message.reply_text(
                        text="Команда введена неверно.",
                    )


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    # потключаемся к управлению ботом по токену
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # simple start function
    application.add_handler(CommandHandler("start", start))

    # Add command handler to start the payment invoice
    application.add_handler(CommandHandler("email", email))
    application.add_handler(CommandHandler("inn", inn))
    application.add_handler(CommandHandler("log", log_all_open_doc))
    application.add_handler(CommandHandler("log2", log_not_bild_doc))
    application.add_handler(CommandHandler("start_log", start_log))
    application.add_handler(CommandHandler("resend", resend))

    # Add callback query handler to start the payment invoice
    application.add_handler(CallbackQueryHandler(button))

    application.add_handler(MessageHandler(filters.ALL, handle_text))
    application.add_handler(
        MessageHandler(filters.Document.ALL, send_document)
    )
    application.add_handler(
        MessageHandler(filters.LOCATION, location_processing)
    )

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    if not os.path.isdir(working_folder_1c):
        os.mkdir(working_folder_1c)
        if not os.path.isdir(working_folder_1c + "send_file"):
            os.mkdir(working_folder_1c + "send_file")
    main()
