from typing import Any

import pandas as pd

from sqlalchemy import create_engine
from sqlalchemy import text as text_sql

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from work import ivea_metrika

engine = create_engine(ivea_metrika)


async def write_location(
    update: Update,
    user_triger: dict[Any, Any],
) -> None:
    if update:
        if update.effective_chat:
            if update.effective_chat.id:
                user_triger[update.effective_chat.id] = {
                    "triger": "write_location",
                    "num_doc": "0",
                    "name_location": "None",
                }
                if update.message:
                    await update.message.reply_text(
                        text="Введите название места, где проводят работы.",
                    )


async def read_location(
    update: Update,
) -> None:
    info: pd.DataFrame = pd.read_sql(
        "SELECT name_location, work_group FROM location_work_group;", engine
    )
    keyboard: list[list[Any]] = list()
    if len(info) != 0:
        sms = "Выберите интересующий объект."
    else:
        sms = "Объектов нет."
    for i in range(len(info)):
        keyboard += [
            [
                InlineKeyboardButton(
                    str(info.loc[i, "name_location"]),
                    callback_data=f'read_montage-{info.loc[i,"work_group"]}',
                )
            ]
        ]
    if update.message:
        await update.message.reply_text(
            text=sms,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def edit_location(
    update: Update,
) -> None:
    info: pd.DataFrame = pd.read_sql(
        "SELECT id, name_location, work_group FROM location_work_group;",
        engine,
    )
    keyboard: list[list[Any]] = list()
    sms: str = ""
    for i in range(len(info)):
        keyboard += [
            [
                InlineKeyboardButton(
                    f'{info.loc[i, "name_location"]} - бригада "\
{info.loc[i, "work_group"]}"',
                    callback_data=f'edit_montage-{info.loc[i, "id"]}-0',
                )
            ]
        ]
        sms = "Выберите интересующий объект."
    if update.message:
        await update.message.reply_text(
            text=sms,
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


async def button_location(
    update: Update,
    user_triger: dict[Any, Any],
) -> None:
    if update.message and update.callback_query and update.effective_chat:
        query = update.callback_query
        await query.answer()
        if query.data:
            if "read_montage" in query.data:
                if query.message:
                    await query.message.delete()
                work_group = query.data.split("-")[1]
                info2 = pd.read_sql(
                    f"SELECT name FROM user_worker_key_corp \
                    WHERE num_working_group = '{work_group}';",
                    engine,
                )
                sms = f'Состав бригады "{work_group}":\n'
                for i in range(len(info2)):
                    sms += f"{i+1}) {info2.loc[i,'name']}\n"
                await update.message.reply_text(sms)
            elif "edit_montage" in query.data:
                if query.message:
                    await query.message.delete()
                edit_id = query.data.split("-")[1]
                action = query.data.split("-")[2]
                if int(action) in [1, 2]:
                    user_triger[update.effective_chat.id] = {
                        "triger": "edit_montage",
                        "num_doc": 0,
                        "edit_id": edit_id,
                        "action": action,
                    }
                if int(action) == 0:
                    keyboard = [
                        [
                            InlineKeyboardButton(
                                "Изменить название",
                                callback_data=f"edit_montage-{edit_id}-1",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Поменять бригаду",
                                callback_data=f"edit_montage-{edit_id}-2",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                "Удалить объект",
                                callback_data=f"edit_montage-{edit_id}-3",
                            )
                        ],
                    ]
                    sms = "Какое действие будем выполнять?"
                    await update.message.reply_text(
                        text=sms,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                    )
                elif int(action) == 1:
                    await update.message.reply_text(
                        text="Введите новое название объекта",
                    )
                elif int(action) == 2:
                    await update.message.reply_text(
                        text="Введите бригаду которая будет работать \
на данном объекте.",
                    )
                elif int(action) == 3:
                    with engine.connect() as con:
                        con.execute(
                            text_sql(
                                f"DELETE FROM location_work_group\
                            WHERE id = '{edit_id}';"
                            )
                        )
                        con.commit()
                    await update.message.reply_text(text="Объект удален.")
            elif "doc_montage" in query.data:
                if query.message:
                    await query.message.delete()
                info = pd.read_sql(
                    f"SELECT short_name FROM documents \
                    WHERE id = {query.data.split('-')[1]};",
                    engine,
                )
                user_triger[update.effective_chat.id] = {
                    "triger": "write_location",
                    "num_doc": "0",
                    "name_location": str(info.loc[0, "short_name"]),
                }
                await update.message.reply_text(
                    text="Введите бригаду которая будет работать на данном \
объекте.",
                )


async def handle_text_location(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_triger: dict[Any, Any],
) -> None:
    if update:
        if update.effective_chat and update.message:
            if update.effective_chat.id:
                if update.effective_chat.id in user_triger:
                    triger: str = user_triger[update.effective_chat.id][
                        "triger"
                    ]
                    if triger == "write_location":
                        if (
                            user_triger[update.effective_chat.id][
                                "name_location"
                            ]
                            == "None"
                        ):
                            user_triger[update.effective_chat.id][
                                "name_location"
                            ] = update.message.text
                            await context.bot.send_message(
                                chat_id=update.effective_chat.id,
                                text="Введите бригаду которая будет работать \
                                на данном объекте.",
                            )
                        else:
                            with engine.connect() as con:
                                con.execute(
                                    text_sql(
                                        f"""
INSERT INTO location_work_group (name_location, work_group) VALUES(
    '{user_triger[update.effective_chat.id]['name_location']}',
    '{update.message.text}'
    );"""
                                    )
                                )
                                con.commit()

                            user_triger.pop(update.effective_chat.id)
                    elif triger == "edit_montage":
                        edit_id = user_triger[update.effective_chat.id][
                            "edit_id"
                        ]
                        action = user_triger[update.effective_chat.id][
                            "action"
                        ]
                        edit: str = ""
                        if int(action) == 1:
                            edit = "name_location"
                        elif int(action) == 2:
                            edit = "work_group"
                        user_triger.pop(update.effective_chat.id)
                        sql_q: str = (
                            """UPDATE location_work_group
        SET {} = '{}'
        WHERE id = '{}';""".format(
                                edit, update.message.text, edit_id
                            )
                        )
                        with engine.connect() as con:
                            con.execute(text_sql(sql_q))
                            con.commit()
                        await update.message.reply_text(
                            text="Изменения завершены."
                        )
