# coding=UTF-8
#
#
import datetime
import time
from random import randint
import math
import json
import re
import pandas as pd
import logging

from work import *#TELEGRAM_TOKEN, ivea_metrika, OK, Pavel, Andrei, my, Boss,working_folder
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, InputMediaDocument
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from sqlalchemy import create_engine
from threading import Thread

from script_for_montage import button_location, edit_location, read_location, write_location, handle_text_location
from scripts_doc_1c.Entera import entera, entera_download
from tkachev.call_api import call
from tkachev.send_email import send_email

# logging.basicConfig(filename=working_folder + 'errors.log',
#                     filemode='a',
#                     level=logging.INFO,
#                     format='%(asctime)s %(process)d-%(levelname)s %(message)s',
#                     datefmt='%d-%b-%y %H:%M:%S')
engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером

user_triger = {}
user_supply = {} # словарь выделенный специально для функции снабжения. Сюда запишем все необходимые данные.


updater = Updater(token=TELEGRAM_TOKEN, use_context=True)  # потключаемся к управлению ботом по токену

dispatcher = updater.dispatcher

def mega_start(update: Update, context: CallbackContext):
    info = pd.read_sql_query("SELECT user_id FROM doc_key_corp", engine2)
    for i in range(len(info)):
        user_id = int(info.loc[i,"user_id"])
        reply_keyboard = [['Cписок договоров', 'Контакты'], ['Завершение работ в период...']]#,
        if user_id == OK or user_id == my:
            reply_keyboard += [['Оповещение кандидатов', 'Оповещение сотрудников']]
        try:
            context.bot.send_message(chat_id=user_id, text='Компания ИВЕА приветствует Вас!',reply_markup=ReplyKeyboardMarkup(reply_keyboard))
        except Exception:
            logging.info("Чат не найден " + str(user_id))

def start(update: Update, context: CallbackContext):
    try:
        info = pd.read_sql_query("SELECT * FROM doc_key_corp WHERE user_id = " + str(update.effective_chat.id), engine2)
        if len(info) != 0:  # для создания ошибки error если человека нет в списке
            user2(update, context, 'Компания ИВЕА приветствует Вас!')
        else:
            guest(update, context, "Для подключения к системе компании ИВЕА, необходимо ввести код доступа.")
    except Exception:
        guest(update, context, "Для подключения к системе компании ИВЕА, необходимо ввести код доступа.")


def user2(update, context, sms):
    if update.effective_chat.id in user_triger:
        user_triger.pop(update.effective_chat.id)
    if update.effective_chat.id in user_supply:
        user_supply.pop(update.effective_chat.id)
    reply_keyboard = [['Cписок договоров', 'Контакты'], ['Нумерация официальных документов'], ['Завершение работ в период...']]#,
                      #['Запрос документов от работодателя', 'Запрос информации для сотрудника']]
    if update.effective_chat.id == id_telegram['Boss']:
        reply_keyboard += [['Список комплектаций'], ['Список рабочих', 'Посмотреть геопозицию'],['Добавить документ']]
    if update.effective_chat.id == id_telegram['Pavel']:
        reply_keyboard += [['Добавить документ']]
    if update.effective_chat.id == id_telegram['supply']:
        reply_keyboard += [['Список комплектаций', 'Счет в оплату', 'Запросить платёжку']]
    if update.effective_chat.id == id_telegram['Mihail']:
        reply_keyboard += [['Объекты'], ['Список рабочих', 'Посмотреть геопозицию']]
    #if update.effective_chat.id == OK or update.effective_chat.id == my:
        #reply_keyboard += [['Оповещение кандидатов', 'Оповещение сотрудников']]
    # if update.effective_chat.id == OK:
    #     reply_keyboard += [['Оповещение сотрудников']]
    context.bot.send_message(chat_id=update.effective_chat.id, text=sms,
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                              one_time_keyboard=False))


def guest(update, context, sms):
    info = pd.read_sql_query(f"SELECT name FROM user_worker_key_corp WHERE user_id = " + str(update.effective_chat.id), engine2)  #
    if len(info) != 0:
        reply_keyboard = [['Ввести код доступа']]  # , ['Оставить резюме'], ['Подать документы для трудоустройства']]
    else:
        reply_keyboard = [['Ввести код доступа'], ['Зарегистрироваться']]  # , ['Оставить резюме'], ['Подать документы для трудоустройства']]
    update.message.reply_text(sms, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                                    one_time_keyboard=False))


####################################################
############# Вывод списка документов ##############
####################################################
def my_doc(update, context, flag='doc_list', num=0):
    try:
        count = int(pd.read_sql(f"SELECT COUNT(*) FROM documents WHERE scan = 1;", engine2).loc[0,"count"])
        name_doc = []
        num_page = []
        info = []
        # all_doc_num = []
        if flag in ['doc_list','doc_montage']:
            info = pd.read_sql(f"SELECT id, short_name FROM documents WHERE scan = 1 and id > {count - (20 * num)} and id < {count - (20 * (num - 1))} ORDER BY id DESC LIMIT 20;", engine2)
            # all_doc_num = pd.read_sql_query("SELECT COUNT(*) FROM documents WHERE scan = 1;", engine2)
        elif flag == 'contact_get' or flag == 'contact_add':
            info = pd.read_sql(f"SELECT id, short_name FROM documents WHERE id > {count - (20 * num)} and id < {count - (20 * (num - 1))} ORDER BY id DESC LIMIT 20;", engine2)
            # all_doc_num = pd.read_sql_query("SELECT COUNT(*) FROM documents WHERE scan = 1;", engine2)
        for i in range(len(info)):
            name_doc += [[InlineKeyboardButton(str(info.loc[i, 'short_name']),
                                               callback_data=flag + '-' + str(info.loc[i, 'id']))]]
        for i in range(math.ceil(count/20)):
            if num != i:
                num_page += [InlineKeyboardButton("стр."+str(i+1), callback_data=f"choice_answer-{flag}-{i}")]
        keyboard = name_doc+[num_page]
        context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите договор:',
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as err:
        logging.error('Error:' + str(err))


####################################################
############# Фильтрация ################
####################################################
def filter(update, context, flag):  # flag = сообщение от пользователя
    try:
        text = 'Выберите договор:'
        name_doc = []
        j = 0
        if ' ' in flag:
            flag = str(flag).replace(' ', '')
        if ',' in flag:
            flag = flag.split(',')
            j = 1
        info = pd.read_sql(f"SELECT id, name, short_name, type_works FROM documents WHERE scan = 1 ORDER BY id ASC;",
                           engine2)
        for i in range(len(info)):
            if (j == 0) and (flag.lower() in str(info.loc[i, 'name']).lower().replace(' ', '') or flag.lower() in str(
                    info.loc[i, 'short_name']).lower().replace(' ', '')):
                name_doc += [[InlineKeyboardButton(str(info.loc[i, 'short_name']),
                                                   callback_data='doc_list-' + str(info.loc[i, 'id']))]]
            elif (j == 0) and (flag.lower() in str(info.loc[i, 'type_works']).lower().split(',')):  #
                name_doc += [[InlineKeyboardButton(str(info.loc[i, 'short_name']),
                                                   callback_data='doc_list-' + str(info.loc[i, 'id']))]]
            elif j == 1:
                true_or_false = True
                for k in range(len(flag)):
                    if flag[k].lower() in str(info.loc[i, 'type_works']).lower().split(','):  # .split(',')
                        pass
                    else:
                        true_or_false = False
                if true_or_false:
                    name_doc += [[InlineKeyboardButton(str(info.loc[i, 'short_name']),
                                                       callback_data='doc_list-' + str(info.loc[i, 'id']))]]
        keyboard = name_doc
        if keyboard == []:
            text = "Договор не найден, попробуйте еще раз."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as err:
        logging.error('Error:' + str(err))

def filter_kontragent(update, context, filter_word, num):
    try:
        text = 'Выберите контрагент:'
        keyboard = []
        if filter_word.isdigit():
            search = 'inn'
        else:
            search = 'name'
        search_info = pd.read_sql(f"SELECT * FROM kontragent_info WHERE LOWER({search}) LIKE '%%{filter_word}%%';", engine2)

        for i in range(len(search_info)):
            keyboard += [[InlineKeyboardButton(str(search_info.loc[i, 'name']), callback_data=f"filter_kontragent-{num}-{search_info.loc[i, 'inn']}")]]
        if keyboard == []:
            text = "Контрагент не найден, попробуйте еще раз."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as err:
        logging.error('Error:' + str(err))
####################################################
############# Прием данных с кнопки ################
####################################################
def button(update: Update, context: CallbackContext) -> None:  # реагирует на нажатие кнопок.
    query = update.callback_query
    query.answer()
    if 'choice_answer' in query.data:
        update.callback_query.message.delete()
        my_doc(update, context, flag=str(query.data.split('-')[1]), num=int(query.data.split('-')[2]))
    elif 'contact_get' in query.data:
        info = pd.read_sql("SELECT text,datatime FROM doc_contact WHERE doc_id = " + str(query.data.split('-')[1]),
                           engine2)
        if len(info) > 0:
            name_station = pd.read_sql("SELECT short_name FROM documents WHERE id = " + str(query.data.split('-')[1]),
                                       engine2)
            sms = str(name_station.loc[0, 'short_name']) + '\n'
            for i in range(len(info)):
                sms += str(info.loc[i, 'datatime']) + ": " + info.loc[i, 'text'] + "\n"
        else:
            sms = "Для данного договора, контактов нет."
        update.callback_query.message.delete()
        user2(update, context, sms)
    elif 'contact_add' in query.data:
        user_triger[update.effective_chat.id] = {
            'triger': 'C',
            'num_doc': query.data.split('-')[1]
        }
        query.edit_message_text(text="Опишите коротко контакт.")
    elif 'doc_list' in query.data:
        print(query.data)
        update.callback_query.message.delete()
        info = pd.read_sql(f"SELECT link, number_doc, short_name FROM documents WHERE id = {query.data.split('-')[1]};",
                           engine2)
        print(info)
        text = "Документ с номером договора: " + str(info.loc[0, "number_doc"]) + " (" + str(
            info.loc[0, "short_name"]) + ")\n\n" + str(info.loc[0, "link"])
        keyboard = [
            [InlineKeyboardButton('Сроки выполнения работ',
                                          callback_data='WorkTime#$#' + str(query.data.split('-')[1]))],
                    [InlineKeyboardButton('Акт технической готовности',
                                          callback_data='choice3-' + str(query.data.split('-')[1]))],
                    [InlineKeyboardButton('Заявка на пропуск, вывоз материалов, контейнера',
                                          callback_data='choice4-' + str(query.data.split('-')[1]))],
                    [InlineKeyboardButton('Заявка на проведение исследований сточных вод',
                                          callback_data='choice5-' + str(query.data.split('-')[1]))],
                    [InlineKeyboardButton('Проектная документация',
                                          callback_data='choice7-' + str(query.data.split('-')[1]))],
                    [InlineKeyboardButton('Другие обращение',
                                          callback_data='choice6-' + str(query.data.split('-')[1]))]]
        if True:#update.effective_chat.id in [my, Boss]:
            keyboard += [[InlineKeyboardButton('Комплектация', callback_data='types-' + str(query.data.split('-')[1]))]]
        print(str(query.data.split('-')[1]))
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'choice1' == query.data:
        update.callback_query.message.delete()
        my_doc(update, context, 'doc_list')
    elif 'choice2' == query.data:
        user_triger[update.effective_chat.id] = {
            'triger': 'filter',
            'num_doc': '0'
        }
        query.edit_message_text(
            text="Введите слово которое должно содержаться в условном названии.\n\nВиды работ, которые можно указать через запятую:\nпроектирование\nсогласование\nстройка\nпоставка КОС\nпоставка ЛОС\nпоставка\nмонтаж\nПНР\nпоставка КНС")
    elif 'choice3' in query.data:  # Акт технической готовности
        query.edit_message_text(text="Запрос на получение акта технической готовности отправлен.")
        choice(update, context, "акт технической готовности", str(query.data.split('-')[1]),
               0)  # Что запрашиваем, ID документа, номер в матрице
    elif 'choice4' in query.data:  # Заявка на пропуск, вывоз материалов, контейнера
        query.edit_message_text(text="Заявка на пропуск, вывоз материалов, контейнера отправлена.")
        choice(update, context, "заявку на пропуск, вывоз материалов, контейнера", query.data.split('-')[1], 1)
    elif 'choice5' in query.data:  # Заявка на проведение исследований сточных вод
        query.edit_message_text(text="Заявка на проведение исследований сточных вод отправлена.")
        choice(update, context, "заявку на проведение исследований сточных вод", query.data.split('-')[1], 2)
    elif 'choice6' in query.data:  # Другие обращение
        query.edit_message_text(text="Опишите кратко какая помощь вам необходима по Договору")
        user_triger[update.effective_chat.id] = {
            'triger': 'choice6',
            'num_doc': query.data.split('-')[1]
        }
    elif 'choice7' in query.data:  # Проектная документация
        info = pd.read_sql(f"select * from documents where id = {query.data.split('-')[1]};", engine2)
        if info.loc[0, "project_doc_link"] is not None and info.loc[0, "project_doc_link"] != "":
            query.edit_message_text(text=str(info.loc[0, "project_doc_link"]))
        else:
            choice(update, context, "проектную документацию", query.data.split('-')[1], 4)
            query.edit_message_text(text="Запрос отправлен, ожидайте ответа.")
    elif 'choice8' == query.data:
        user_triger[update.effective_chat.id] = {
            'triger': 'filter_kontragent',
            'num_doc': '8'
        }
        query.edit_message_text(text="Введите полное название (можно часть полного названия) или номер ИНН.")
    elif 'choice9' == query.data:
        user_triger[update.effective_chat.id] = {
            'triger': 'filter_kontragent',
            'num_doc': '9'
        }
        query.edit_message_text(text="Введите полное название (можно часть полного названия) или номер ИНН.")
    elif 'filter_kontragent' in query.data:
        num = query.data.split('-')[1]
        inn = query.data.split('-')[2]
        print(num)
        print(inn)
        if num == "8":
            info = pd.read_sql(f"SELECT * FROM kontragent_info WHERE inn = '{inn}';", engine2)
            text = ''
            if str(info.loc[0,'name']) != 'nan':
                text += f"Полное наименование: {info.loc[0,'name']}\n"
            if str(info.loc[0,'group_k']) != 'nan':
                text += f"Группа: {info.loc[0,'group_k']}\n"
            if str(info.loc[0,'type_k']) != 'nan':
                text += f"Вид контрагента: {info.loc[0,'type_k']}\n"
            text += f"ИНН контрагента: {inn}\n"
            if info.loc[0,'trade_name'] is not None:
                text += f"Торговое название: {info.loc[0,'trade_name']}\n"
            if info.loc[0,'description'] is not None:
                text += f"Описание: {info.loc[0,'description']}\n"
            if info.loc[0,'url'] is not None:
                text += f"Ссылка на сайт: {info.loc[0,'url']}\n"
            if info.loc[0,'tel'] is not None:
                text += f"Контактные номера: {info.loc[0,'tel']}\n"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        elif num == "9":
            user_triger[update.effective_chat.id] = {
                "triger": "update_k_info",
                "num_doc": "0",
                "inn": inn,
                "trade_name": "None",
                "description": "None",
                "url": "None",
                "tel": "None"
            }
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"ИНН:{inn}\nВведите торговое название.")
    elif 'go_next_contract' in query.data:
        list = []
        id = query.data.replace('go_next_contract,', '').split(',')
        for i in range(len(id)):
            info = pd.read_sql_query("SELECT doc_name,work_name FROM doc_date WHERE id = " + str(id[i]) + ";", engine2)
            doc = str(i + 1) + ") " + str(info.loc[0, 'doc_name']) + " " + str(info.loc[0, 'work_name'])
            list += [[InlineKeyboardButton(str(doc), callback_data='go_next2,' + str(id[i]))]]
        keyboard = list
        query.edit_message_text(text="В каком договоре будем изменять дату?",
                                reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'go_next2' in query.data:
        id = query.data.replace('go_next2,', '')
        query.edit_message_text(
            text="Введите новую дату.\nПример: " + str(datetime.datetime.now().strftime('%d.%m.%Y')))
        user_triger[update.effective_chat.id] = {
            'triger': 'date',
            'num_doc': id
        }
    elif 'empl_send_doc' in query.data:
        if query.data.split('-')[1] == "go":
            media_group = []
            info = pd.read_sql("SELECT * FROM doc_employment WHERE user_id = " + str(update.effective_chat.id), engine2)
            for i in range(8):
                directory = info.loc[0, "link_" + str(i + 1)]
                if directory is not None:
                    media_group.append(InputMediaDocument(open(directory, 'rb')))
            context.bot.send_message(chat_id=OK, text=str(info.loc[0, "name"]) + " тел: " + str(info.loc[0, "tel"]))
            context.bot.send_media_group(chat_id=OK, media=media_group)
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Документы отправлены в отдел кадров компании ИВЕА. Ожидайте.")
        else:
            user_triger[update.effective_chat.id]['triger'] = "empl_send_doc"
            user_triger[update.effective_chat.id]['num_doc'] = query.data.split('-')[
                1]  # Это будет номер отправленного документа
            print(user_triger[update.effective_chat.id])
            query.edit_message_text(text="Отправьте сюда файл в формате PDF")
    elif 'empl_send_end' in query.data:
        id = query.data.split('-')[1]  # В данном случае это ID пользователя (кандадата на трудоустройства)
        info = pd.read_sql("SELECT name, tel FROM doc_employment WHERE user_id = " + str(id), engine2)
        query.edit_message_text(
            text="Имя кандидата: " + str(info.loc[0, "name"]) + "\nКонтактный номер телефона: " + str(
                info.loc[0, "tel"]))
        user_triger[update.effective_chat.id] = {
            'triger': 'None',
            'num_doc': 'empl_send_sms',
            'id': id,
            'j': 'None'
        }
        keyboard = [[InlineKeyboardButton("трудовой договор (файл для прочтения, печати и подписи)",
                                          callback_data='empl_send_sms-0')],
                    [InlineKeyboardButton("внесена запись в трудовую книгу", callback_data='empl_send_sms-1')],
                    [InlineKeyboardButton("приказ о назначении на должность", callback_data='empl_send_sms-2')]]
        sms = "Что передать?"
        context.bot.send_message(chat_id=update.effective_chat.id, text=sms,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'empl_send_sms' in query.data:
        num_doc = query.data.split('-')[1]
        user_triger[update.effective_chat.id]['j'] = num_doc
        keyboard = [[InlineKeyboardButton("Отправить документ", callback_data='empl_send_next_sms-send_doc'),
                     InlineKeyboardButton("Отправить ссылку на документ",
                                          callback_data='empl_send_next_sms-send_link')]]
        sms = "Что передать?"
        query.edit_message_text(text=sms, reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'empl_send_next_sms' in query.data:
        Arr = ["трудовой договор (файл для прочтения, печати и подписи)", "внесена запись в трудовую книгу",
               "приказ о назначении на должность"]
        triger = query.data.split('-')[1]
        user_triger[update.effective_chat.id]['triger'] = triger
        if triger == "send_doc":
            sms = "Жду документ \"" + Arr[int(user_triger[update.effective_chat.id]['j'])] + "\""
        elif triger == "send_link":
            sms = "Жду ссылку на документ \"" + Arr[int(user_triger[update.effective_chat.id]['j'])] + "\""
        query.edit_message_text(text=sms)
    elif 'send_doc' in query.data:
        Arr = ("акт технической готовности", "заявку на пропуск, вывоз материалов, контейнера",
               "заявку на проведение исследований сточных вод", "следующую информацию", "проектную документацию")
        id = query.data.split('-')[1]  # В данном случае это ID пользователя который отправил запрос
        id_doc = query.data.split('-')[2]  # Это ID документа на который запрос
        j = int(query.data.split('-')[3])  # это номер что из списка что нужно пользователю
        info = pd.read_sql(f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id  = '{id}';", engine2)
        info2 = pd.read_sql(f"SELECT number_doc, short_name FROM documents WHERE id = {id_doc};", engine2)
        text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + ", (тел. " + str(
            info.loc[0, "tel"]) + ") запрашивает " + str(Arr[j]) + " по Договору " + str(
            info2.loc[0, "number_doc"]) + " (" + str(info2.loc[0, "short_name"]) + ")\n\n"
        user_triger[update.effective_chat.id] = {
            'triger': 'send_doc',
            'num_doc': id_doc,
            'id': str(id),
            'j': j
        }
        query.edit_message_text(text=text + "Загрузите документ, можно его подписать.")
    elif 'send_link' in query.data or 'send_text' in query.data:
        Arr = ("акт технической готовности", "заявку на пропуск, вывоз материалов, контейнера",
               "заявку на проведение исследований сточных вод", "следующую информацию", "проектную документацию")
        id = query.data.split('-')[1]  # В данном случае это ID пользователя который отправил запрос
        id_doc = query.data.split('-')[2]  # Это ID документа на который запрос
        j = int(query.data.split('-')[3])
        info = pd.read_sql(f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id  = '{id}';", engine2)
        if id_doc != "999999":
            info2 = pd.read_sql(f"SELECT number_doc, short_name FROM documents WHERE id = {id_doc};", engine2)
            text = "запрашивает " + str(Arr[j]) + " по Договору " + str(info2.loc[0, "number_doc"]) + " (" + str(
                info2.loc[
                    0, "short_name"]) + ")\n\n Отправьте ссылку, она автоматически добавится к этому документу и отправится пользователю."
        else:
            Arr2 = (
                'запрашивает справки 2НДФЛ', 'запрашивает справку о месте работы',
                'хочет предоставить сведения о детях',
                'запрашивает выплату за фактически отработанное время',
                'запрашивает планируемую дату выплаты аванса, зарплаты',
                'запрашивает информацию о окладе (структура, сумма, даты выплаты)',
                'запрашивает сумму за период (структура оклад, налоги)',
                'запрашивает сканы документов (трудовой договор, все личные (паспорт и тд), приказ, и другие приказы)',
                'интересуется, что компания ждет от него, профессиональный рост (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) и др.')

            text = Arr2[j]
        if 'send_link' in query.data:
            triger = 'send_link'
        else:
            triger = 'send_text'
        user_triger[update.effective_chat.id] = {
            'triger': triger,
            'num_doc': id_doc,
            'id': str(id),
            'j': j
        }
        query.edit_message_text(
            text="Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + ", (тел. " + str(
                info.loc[0, "tel"]) + ") " + text)
    elif 'WorkTime' in query.data:  # Запрос сроков выполнения работ
        short_name = pd.read_sql(f"SELECT short_name FROM documents WHERE id = {query.data.split('#$#')[1]};",engine2).loc[0,"short_name"]
        info = pd.read_sql_query(
            "SELECT * FROM doc_date WHERE doc_name in ('" + str(short_name) + "','" + str(short_name) + " (завершено)') ORDER BY id ASC;", engine2)
        text = ''
        for i in range(len(info)):
            if "(завершено)" in str(info.loc[i, 'doc_name']):
                z = " (завершено)"
            else:
                z = ""
            if int(info.loc[i, 'noct']) > 0:
                text += str(i + 1) + ") " + str(info.loc[i, 'work_name']) + z + " - " + str(
                    info.loc[i, 'date_end'].strftime('%d.%m.%Y')) + "\n(Количествл переносов: " + str(
                    info.loc[i, 'noct']) + "; Причина переноса: \"" + str(info.loc[i, 'coment']) + "\")\n\n"
            else:
                text += str(i + 1) + ") " + str(info.loc[i, 'work_name']) + z + " - " + str(
                    info.loc[i, 'date_end'].strftime('%d.%m.%Y')) + "\n\n"
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    elif 'notification' in query.data:
        num_notification = query.data.split('-')[1]  # В данном случае это номер оповещения
        user_triger[update.effective_chat.id] = {
            'triger': 'notification_link',
            'num_doc': str(num_notification)
        }
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Отправьте ссылку на документ, с которым сотрудники должны ознакомиться.")
        ####################################
    elif 'next_send_request' in query.data:
        user_id = query.data.split('-')[1]
        update.callback_query.message.delete()
        if user_id == 'all':
            info = pd.read_sql(f"SELECT user_id, name, family_name FROM doc_key_corp WHERE user_id > 0;", engine2)
            for i in range(len(info)):
                if str(info.loc[i, "user_id"]) != str(update.effective_chat.id):
                    try:
                        context.bot.send_message(chat_id=int(info.loc[i, "user_id"]), text="Тестовое оповещение.")
                    except Exception:
                        print("нет отправки " + str(i))
        else:
            context.bot.send_message(chat_id=int(user_id), text="Тестовое личное оповещение.")
    elif 'send_request' in query.data:
        arr = ("Начисленная зарплата в месяц, дата выплаты", "ЗП переведена на расчетный счет, дата, время",
               "Требования ознакомиться и подписать приказы, заявления")
        num = int(query.data.split('-')[1])
        keyboard = [[InlineKeyboardButton('Отправить всем', callback_data='next_send_request-all')]]
        info = pd.read_sql(f"SELECT user_id, name, family_name FROM doc_key_corp WHERE user_id > 0;", engine2)
        for i in range(len(info)):
            if str(info.loc[i, "user_id"]) != str(update.effective_chat.id):
                keyboard += [[InlineKeyboardButton(info.loc[i, "family_name"] + " " + info.loc[i, "name"],
                                                   callback_data='next_send_request-' + str(info.loc[i, "user_id"]))]]
        query.edit_message_text("Оповестить всех или кого-то лично?", reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'request' in query.data:
        Arr = ('запрашивает справки 2НДФЛ', 'запрашивает справку о месте работы', 'хочет предоставить сведения о детях',
               'запрашивает выплату за фактически отработанное время',
               'запрашивает планируемую дату выплаты аванса, зарплаты',
               'запрашивает информацию о окладе (структура, сумма, даты выплаты)',
               'запрашивает сумму за период (структура оклад, налоги)',
               'запрашивает сканы документов (трудовой договор, все личные (паспорт и тд), приказ, и другие приказы)',
               'интересуется, что компания ждет от него, профессиональный рост (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) и др.')
        num = int(query.data.split('-')[1])
        id = "999999"
        query.edit_message_text(text="Запрос отправлен, ожидайте ответа.")
        info = pd.read_sql(
            f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id  = '{update.effective_chat.id}';", engine2)
        text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + ", (тел. " + str(
            info.loc[0, "tel"]) + ") " + Arr[num] + "\n\n"
        keyboard = [[InlineKeyboardButton('Отправить документ', callback_data='send_doc-' + str(
            update.effective_chat.id) + '-' + id + '-' + str(num))],
                    [InlineKeyboardButton('Отправить ссылку', callback_data='send_link-' + str(
                        update.effective_chat.id) + '-' + id + '-' + str(num))],
                    [InlineKeyboardButton('Ответить в текстовом виде', callback_data='send_text-' + str(
                        update.effective_chat.id) + '-' + id + '-' + str(num))]]
        context.bot.send_message(chat_id=OK, text=text, reply_markup=InlineKeyboardMarkup(
            keyboard))  # 943180118 456335434Если выбор пал на проектную документацию и ее нет, то летит запрос Андрею
    elif 'write_new_latter' in query.data:
        update.callback_query.message.delete()
        name = query.data.split('-')[1]
        num_doc_letters(update, context, name, True)
    elif 'cancel' in query.data:
        update.callback_query.message.delete()
        if update.effective_chat.id in user_triger:
            user_triger.pop(update.effective_chat.id)
        if update.effective_chat.id in user_supply:
            user_supply.pop(update.effective_chat.id)
    elif 'types' in query.data:
        update.callback_query.message.delete()
        doc_id = query.data.split('-')[1]
        if update.effective_chat.id in user_supply:
            user_supply.pop(update.effective_chat.id)
        info = pd.read_sql(f"SELECT link, number_doc, short_name, type_of_building FROM documents WHERE id = '{doc_id}';", engine2)
        user_info = pd.read_sql(f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id = '{update.effective_chat.id}';", engine2)
        user_supply[update.effective_chat.id] = {
            'doc_id': str(doc_id),
            'number_doc': str(info.loc[0, "number_doc"]),
            'short_name': str(info.loc[0, "short_name"]),
            'fio': str(user_info.loc[0, "family_name"]) + ' ' + str(user_info.loc[0, "name"]),
            'tel': str(user_info.loc[0, "tel"]),
            'type_of_building': 'None',
            'type_of_equipment': 'None',
            'link': '',
            'brand': 'None'
        }
        type_of_building = str(info.loc[0, "type_of_building"]).split(',')
        keyboard = []
        keyboard += [[InlineKeyboardButton(str(type), callback_data='next_type_of_the_type-' + str(type))] for type in type_of_building]
        context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите тип сооружения.", reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'next_type_of_the_type' in query.data:
        update.callback_query.message.delete()
        type_of_building = query.data.split('-')[1]
        user_supply[update.effective_chat.id]['type_of_building'] = type_of_building
        info = pd.read_sql(f"SELECT type_of_equipment, need_link FROM types WHERE type_of_building = '{type_of_building}';", engine2)
        keyboard = []
        for i in range(len(info)):
            link = "-1" if int(info.loc[i, "need_link"]) == 1 else "-0"
            keyboard += [[InlineKeyboardButton(str(info.loc[i, "type_of_equipment"]), callback_data='brand-' + str(info.loc[i, "type_of_equipment"]) + str(link))]]
        context.bot.send_message(chat_id=update.effective_chat.id, text="Выберите тип оборудования.",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'accepted' in query.data:
        update.callback_query.message.delete()
        id = query.data.split('-')[1]
        if update.effective_chat.id == id_telegram['Boss']:
            keyboard = [[InlineKeyboardButton("принято", callback_data=f'accepted-{id}')]]
            context.bot.send_message(chat_id=supply, text=query.message.text, reply_markup=InlineKeyboardMarkup(keyboard))
            num_answer = 1
            date = f", date = '{datetime.datetime.now()}'"
            accepted = "согласована."
        elif update.effective_chat.id == supply:
            num_answer = 2
            date = ''
            accepted = "принята."
        engine2.execute(f"UPDATE saving_query_the_supply SET answer{num_answer} = 'принято'{date} WHERE id = '{id}';")
        text = f"Позиция для комплектации объекта {accepted}\n" + query.message.text
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    #################### supply #######################
    elif 'supply_short_name' in query.data:
        update.callback_query.message.delete()
        user_triger[update.effective_chat.id]['triger'] = "link_yandex"
        user_triger[update.effective_chat.id]['short_name'] = query.data.split('#*&*#')[1]
        reply_keyboard = [['Вернуться в главное меню']]
        context.bot.send_message(chat_id=update.effective_chat.id, text='Прикрепите ссылку к файлу на яндекс диске',
                                 reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                                  one_time_keyboard=False))
    elif 'brand' in query.data:
        update.callback_query.message.delete()
        user_supply[update.effective_chat.id]['type_of_equipment'] = query.data.split('-')[1]
        triger = 'brand' if str(query.data.split('-')[2]) == '0' else 'need_link'
        text = 'Введите ссылку на чертеж оборудования' if str(
            query.data.split('-')[2]) == '1' else 'Введите название бренда оборудования'
        user_triger[update.effective_chat.id] = {
            'triger': triger,
            'num_doc': 'None'
        }
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    elif 'location' in query.data:
        user_id = query.data.split('-')[1]
        """location = '{update.edited_message.location['longitude']}:{update.edited_message.location['latitude']}'"""
        info = pd.read_sql(f"SELECT location, name, date_time FROM user_worker_key_corp WHERE user_id = '{user_id}' and date_time > '{datetime.datetime.now().strftime('%Y-%m-%d')}';", engine2)
        try:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"{info.loc[0, 'name']}. Местоположение была актуальна в {info.loc[0,'date_time'].strftime('%H:%M:%S')}.")
            context.bot.send_location(chat_id=update.effective_chat.id, longitude=str(info.loc[0,'location']).split(':')[0], latitude=str(info.loc[0,'location']).split(':')[1])
        except Exception:
            try:
                info = pd.read_sql(f"SELECT location, name, date_time FROM user_worker_key_corp WHERE user_id = '{user_id}';",engine2)
                print(info.loc[0, 'location'])
                if str(info.loc[0, 'location']) != "None":
                    context.bot.send_message(chat_id=update.effective_chat.id, text=f"{info.loc[0,'name']}\nГеопозиции нет. Дата последний трансляции геопозиции {info.loc[0,'date_time'].strftime('%d.%m.%Y %H:%M')}.")
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Геопозиции нет")
            except Exception:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Геопозиции нет")
    elif 'reg_worker_next' in query.data:
        u_id = query.data.split('-')[1]
        info = pd.read_sql_query(f"SELECT name, tel FROM user_worker_key_corp WHERE id = '{u_id}';",engine2)  #
        user_triger[update.effective_chat.id] = {
            "triger": "reg_worker_next",
            "num_doc": 0,
            "id": u_id,
            "num_working_group": 0,
            "name": info.loc[0,'name'],
            "tel": info.loc[0,'tel']
        }
        reply_keyboard = [['Отмена']]
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"{info.loc[0,'name']} - {info.loc[0,'tel']}\nНапишите в какую бригаду определить данного работника?",
                             reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                              one_time_keyboard=False))
    elif 'send_email_1c_doc' in query.data:
        print("Go")
        doc_id = query.data.split('-')[1]
        info = pd.read_sql(f"SELECT num_doc, contragent, date_doc, sum, link, name_file FROM doc_entera_1c WHERE id = '{doc_id}';",engine2)
        link = info.loc[0,'link']
        name_file = info.loc[0,'name_file']
        text = f"Счёт № {info.loc[0,'num_doc']} от {info.loc[0,'date_doc']} на сумму {info.loc[0,'sum']} руб.\nКонтрагент: {info.loc[0,'contragent']}"
        query.edit_message_text(text=text)
        entera_download(link, name_file)
        print("sending...")
        answer = send_email([name_file], text=text,working_folder="C:\\Users\\menac\\Desktop\\работа\\ивеа\\Python\\Новая папка\\новое 21.03.2022\\menace134\\ivea_corp\\scripts_doc_1c\\send_file\\")
        if "Письмо с документом отправлено!" == answer:
            query.edit_message_text(text=text+"\n|| Отправлено на почту. ||")
            # context.bot.send_message(chat_id=id_telegram["supply"], text=text + "\n|| Cогласован в оплату. ||")  # supply
            # engine2.execute(f"UPDATE doc_entera_1c SET send_email = 'True' WHERE id = '{doc_id}';")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text="Ошибка при отправке письма. Повторите позже.")
            context.bot.send_message(chat_id=id_telegram["my"],
                                     text=answer + "\n\n" + text + "\n|| Cогласован в оплату. ||")
    elif 'item_1c_doc' in query.data:
        print("Go")
        doc_id = query.data.split('-')[1]
        info = pd.read_sql(f"SELECT num_1c, num_doc, contragent, date_doc, sum, link, name_file FROM doc_entera_1c WHERE id = '{doc_id}';",engine2)
        df = pd.read_excel(f'{working_folder}scripts_doc_1c/Scheta.xls')
        df = df[df["Номер"].isin([info.loc[0,"num_1c"]])]
        """Счёт № 1644 от 19.04.2022 на сумму 12 136,58 руб."""
        text = f'Состав: Счёт № {info.loc[0,"num_doc"]} от {info.loc[0,"date_doc"]} на сумму {info.loc[0,"sum"]} руб.\n'
        for i in range(len(df)):
            nds=''
            if str(df.loc[df.index[i],'% НДС']) == "Без НДС" or str(df.loc[df.index[i],'% НДС']) == "0%":
                nds='*** Без НДС ***'
            text += f"\n{i+1}) {df.loc[df.index[i],'Номенклатура']} - {df.loc[df.index[i],'Количество']} {df.loc[df.index[i],'Номенклатура.Единица']}. ({(df.loc[df.index[i],'Всего'])}  руб. {nds})\n"
        q_msg_id = context.bot.send_message(chat_id=update.effective_chat.id,text=text.replace(" nan", "")).message_id # хитрая система :) отправляем сообщение и одновременно считываем его id, затем отправляем на удаление через минуту
        Thread(target=Timer, args=(update, context, 60, q_msg_id)).start()
    elif 'update_k_info' in query.data:
        inn = query.data.split('-')[1]
        user_triger[update.effective_chat.id] = {
            "triger": "update_k_info",
            "num_doc": "0",
            "inn": inn,
            "trade_name": "None",
            "description": "None",
            "url": "None",
            "tel": "None"
        }
        context.bot.send_message(chat_id=update.effective_chat.id,text=f"ИНН:{inn}\nВведите торговое название.")

        # engine2.execute(f"UPDATE kontragent_info SET ');")

    else:
        button_location(update, context, user_triger)


####################################################
############# Выбор запроса по договору ################
####################################################
def choice(update, context, choice, id, j):
    info = pd.read_sql(
        f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id  = '{update.effective_chat.id}';", engine2)
    info2 = pd.read_sql(f"SELECT number_doc, short_name FROM documents WHERE id = {id};", engine2)
    text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + ", (тел. " + str(
        info.loc[0, "tel"]) + ") запрашивает " + str(choice) + " по Договору " + str(
        info2.loc[0, "number_doc"]) + " (" + str(info2.loc[0, "short_name"]) + ")\n\n"
    keyboard = [[InlineKeyboardButton('Отправить документ',
                                      callback_data='send_doc-' + str(update.effective_chat.id) + '-' + str(
                                          id) + '-' + str(j))],
                [InlineKeyboardButton('Отправить ссылку',
                                      callback_data='send_link-' + str(update.effective_chat.id) + '-' + str(
                                          id) + '-' + str(j))]]
    if j != 4:
        # keyboard = [[InlineKeyboardButton('Отправить документ', callback_data='send_doc-' + str(update.effective_chat.id) + '-' + str(id) + '-' + str(j))]]
        context.bot.send_message(chat_id=id_telegram['Pavel'], text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))  # 943180118 Все отправляем Елене
    else:
        context.bot.send_message(chat_id=id_telegram['Andrei'], text=text, reply_markup=InlineKeyboardMarkup(
            keyboard))  # 943180118 Если выбор пал на проектную документацию и ее нет, то летит запрос Андрею


####################################################
############# сохранение контактов к договору ################
####################################################
def contact(update, context):
    sms = "Вы хотите получить или добавить контакты?\nТакже имеются данные контрагентов."
    reply_keyboard = [['Получить', 'Добавить'], ['Контрагенты'], ['Главное меню']]
    update.message.reply_text(sms, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,
                                                                    one_time_keyboard=False))
def kontragent(update, context):
    sms = "Вам показать или Вы хотите заполнить данные о контрагенте?"
    keyboard = [[InlineKeyboardButton('Показать', callback_data='choice8'),
                 InlineKeyboardButton('Заполнить', callback_data='choice9')]]
    context.bot.send_message(chat_id=update.effective_chat.id, text=sms,
                             reply_markup=InlineKeyboardMarkup(keyboard))



####################################################
############# поиск договоров с завершением срока по интервалу ################
####################################################
def interval(update, context, num):
    try:
        now = datetime.datetime.now()
        info = pd.read_sql_query("SELECT doc_name, work_name, date_end FROM doc_date ORDER BY date_end ASC", engine2)
        list_doc = ''
        j = 0
        for i in range(len(info)):
            date_end = str(info.loc[i, 'date_end'] - now).split(" ")[0]
            if date_end != "NaT":
                if abs(int(num)) == 1:
                    days = 'дня'
                else:
                    days = 'дней'
                if (int(date_end) <= int(num) and int(date_end) >= 0):
                    j += 1
                    list_doc += str(j) + ") " + str(info.loc[i, 'doc_name']) + " " + str(
                        info.loc[i, 'work_name']) + ' "' + str(info.loc[i, 'date_end'].strftime('%d.%m.%Y')) + '"\n\n'
                    text = 'Завершение работ в период - меньше ' + str(num) + ' ' + days + '\n\n' + list_doc
                elif (int(date_end) >= int(num) and int(date_end) <= 0):
                    j += 1
                    list_doc += str(j) + ") " + str(info.loc[i, 'doc_name']) + " " + str(
                        info.loc[i, 'work_name']) + ' "' + str(info.loc[i, 'date_end'].strftime('%d.%m.%Y')) + '"\n\n'
                    text = 'Просроченное завершение работ в период - меньше ' + str(
                        abs(int(num))) + ' ' + days + '\n\n' + list_doc
    except Exception as err:
        logging.error('Error:' + str(err))
        text = "Вы ввели не целочисленное число, повторите попытку"
    try:
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    except Exception as err:
        logging.error('Error: В запросе получился большой список который не умещается в одном СМС' + str(err))
        text = "Вы ввели большое количество дней."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


####################################################
############# функция для запросов ################
####################################################
def request(update, context, i):
    if i == 1:
        keyboard = [[InlineKeyboardButton('Запрос справки 2НДФЛ', callback_data='request-' + str(0))],
                    [InlineKeyboardButton('Запрос о месте работы', callback_data='request-' + str(1))],
                    # [InlineKeyboardButton('Предоставить сведения о детях', callback_data='request-' + str(2))],
                    [InlineKeyboardButton(
                        'Запросить выплату за фактически отработанное время (при острой необходимости)',
                        callback_data='request-' + str(3))]]
        context.bot.send_message(chat_id=update.effective_chat.id, text="Можно получить следующие сведения:",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif i == 2:
        keyboard = [
            [InlineKeyboardButton('Планируемая дата выплаты аванса, зарплаты', callback_data='request-' + str(4))],
            [InlineKeyboardButton('Оклад (структура, сумма, даты выплаты)', callback_data='request-' + str(5))],
            [InlineKeyboardButton('Сумма за период (структура оклад, налоги)', callback_data='request-' + str(6))],
            [InlineKeyboardButton(
                'Сканы документов (трудовой договор, все личные (паспорт и тд), приказ, и другие приказы)',
                callback_data='request-' + str(7))],
            [InlineKeyboardButton(
                'Что компания ждет от вас, ваш профессиональный рост (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) и др.',
                callback_data='request-' + str(8))]]
        context.bot.send_message(chat_id=update.effective_chat.id, text="Можно получить следующие сведения:",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif i == 3:
        keyboard = [
            # [InlineKeyboardButton('Начисленная зарплата в месяц, дата выплаты', callback_data='send_request-' + str(0))],
            [InlineKeyboardButton('ЗП переведена на расчетный счет, дата, время',
                                  callback_data='send_request-' + str(1))],
            [InlineKeyboardButton('Требования ознакомиться и подписать приказы, заявления',
                                  callback_data='send_request-' + str(2))]]
        context.bot.send_message(chat_id=update.effective_chat.id, text="Можно отправить следующие сведения:",
                                 reply_markup=InlineKeyboardMarkup(keyboard))


####################################################
############# функция для трудоустройства ################
####################################################
def employment(update, context, num_send):
    search_result = engine2.execute(
        "SELECT user_id FROM doc_employment WHERE user_id = " + str(update.effective_chat.id)).fetchall()
    user_triger[update.effective_chat.id] = {
        'triger': 'empl_enter_name',
        'num_doc': "0",  # Это будет номер отправленного документа
        'num_send': str(num_send)  # Это будет номер жействия которое совершаем(пока их 2)
    }
    print(search_result)
    if len(search_result) != 0:
        keyboard = []
        info = pd.read_sql("SELECT * FROM doc_employment WHERE user_id = " + str(update.effective_chat.id), engine2)
        if num_send == 1:
            text = "Для трудоустройства, Вам необхлжимо отправить в формате PDF (1 пункт, 1 файл PDF) следующие документы:"
            if info.loc[0, "link_1"] == None:
                keyboard += [[InlineKeyboardButton('Отправить заявление', callback_data='empl_send_doc-1')]]
            if info.loc[0, "link_2"] == None:
                keyboard += [[InlineKeyboardButton('Отправить копию паспорта', callback_data='empl_send_doc-2')]]
            if info.loc[0, "link_3"] == None:
                keyboard += [[InlineKeyboardButton('Ответить копию трудовой книги', callback_data='empl_send_doc-3')]]
            if info.loc[0, "link_4"] == None:
                keyboard += [[InlineKeyboardButton('Отправить копию ИНН', callback_data='empl_send_doc-4')]]
            if info.loc[0, "link_5"] == None:
                keyboard += [[InlineKeyboardButton('Отправить копию снилс', callback_data='empl_send_doc-5')]]
            if info.loc[0, "link_6"] == None:
                keyboard += [[InlineKeyboardButton('Ответить копию диплома(ов)', callback_data='empl_send_doc-6')]]
            if info.loc[0, "link_7"] == None:
                keyboard += [[InlineKeyboardButton('Отправить сертификаты курсов', callback_data='empl_send_doc-7')]]
            if info.loc[0, "link_8"] == None:
                keyboard += [[InlineKeyboardButton('Отправить резюме', callback_data='empl_send_doc-8')]]
            if info.loc[0, "link_8"] is not None and info.loc[0, "link_1"] is not None and info.loc[
                0, "link_2"] is not None and info.loc[0, "link_3"] is not None and info.loc[0, "link_4"] is not None and \
                    info.loc[0, "link_5"] is not None:
                keyboard += [[InlineKeyboardButton('📨 Отправить документы в отдел кажров 📨',
                                                   callback_data='empl_send_doc-go')]]
        elif num_send == 2:
            text = "Вам необхлжимо отправить в формате PDF (1 пункт, 1 файл PDF) следующие документы:"
            if info.loc[0, "link_8"] == None:
                keyboard += [[InlineKeyboardButton('Отправить резюме', callback_data='empl_send_doc-8')]]
            if info.loc[0, "link_6"] == None:
                keyboard += [[InlineKeyboardButton('Ответить копию диплома(ов)', callback_data='empl_send_doc-6')]]
            if info.loc[0, "link_7"] == None:
                keyboard += [
                    [InlineKeyboardButton('Отправить сертификаты курсов', callback_data='empl_send_doc-7')]]
            if info.loc[0, "link_8"] is not None:
                keyboard += [
                    [InlineKeyboardButton('📨 Отправить в отдел кажров 📨', callback_data='empl_send_doc-go')]]
            print(user_triger[update.effective_chat.id])
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        engine2.execute("INSERT INTO doc_employment (user_id) VALUES('" + str(update.effective_chat.id) + "')")
        text = "Здравствуйте, пожалуйста, введите свое ФИО."
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)


####################################################
########### Функция для регистрации КК #############
####################################################
def reg_user(update, context):
    user_triger.pop(update.effective_chat.id)
    try:
        info = pd.read_sql("SELECT id,user_id FROM doc_key_corp WHERE a_key = '" + str(update.message.text) + "'",
                           engine2)
        id = info.loc[0, 'id']
        if int(info.loc[0, 'user_id']) == 0:
            engine2.execute(
                "UPDATE doc_key_corp SET user_id = " + str(update.effective_chat.id) + " WHERE id = " + str(id))
            # engine2.execute("UPDATE doc_key_corp SET data_time = "+str(update.message.date)+" WHERE id = "+ str(id))
            user2(update, context, """
Компания ИВЕА приветствует Вас!""")
            time.sleep(3)  # ждум 7сек
            context.bot.send_message(chat_id=update.effective_chat.id, text="""
Вам открыт доступ к документации.""")
        else:
            update.message.reply_text("Этот ключ уже занят.")
    except Exception as err:
        logging.error('Error:' + str(err))
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Совпадений нет, возможно вы ошиблись. Пожалуйста, повторите попытку,повторно нажав на кнопку "Ввести ключ".')


####################################################
####### Прием сообщений c файлом(документом) #######
####################################################
def send_document(update, context):
    Arr = (
    "акта технической готовности", "пропуска, вывоза материалов, контейнера", "проведение исследований сточных вод",
    "следующую информацию", "проектную документацию")
    Arr2 = (
        'на запрос справки 2НДФЛ', 'на запрос справки о месте работы',
        'на запрос о предоставлении сведений о детях',
        'на запрос выплаты за фактически отработанное время',
        'на запрос планируемой даты выплаты аванса, зарплаты',
        'на запрос информации о окладе (структура, сумма, даты выплаты)',
        'на запрос суммы за период (структура оклад, налоги)',
        'на запрос сканы документов (трудовой договор, все личные (паспорт и тд), приказ, и другие приказы)',
        'на запрос, что компания ждет от Вас, Ваш профессиональный рост (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) и др.')
    Arr3 = ["трудовой договор (файл для прочтения, печати и подписи)", "внесена запись в трудовую книгу",
            "приказ о назначении на должность"]

    if update.effective_chat.id in user_triger:
        if user_triger[update.effective_chat.id]['triger'] == 'send_doc':
            id = str(user_triger[update.effective_chat.id]['id'])
            num_doc = str(user_triger[update.effective_chat.id]['num_doc'])
            j = int(user_triger[update.effective_chat.id]['j'])
            user_triger.pop(update.effective_chat.id)

            if num_doc == 'empl_send_sms':
                array = Arr3[j]
            elif num_doc != "999999":
                array = Arr[j]
            else:
                array = Arr2[j]

            if str(id_telegram['Pavel']) == str(update.effective_chat.id):
                context.bot.send_message(chat_id=id,
                                         text="Елисеев Павел направляет Вам файл в ответ на запрос " + array + ":")  # Акт технической готовности по объекту
            elif str(id_telegram['Andrei']) == str(update.effective_chat.id):
                context.bot.send_message(chat_id=id,
                                         text="Минеев Андрей направляет Вам файл в ответ на запрос " + array + ":")  # Акт технической готовности по объекту
            elif str(id_telegram['Boss']) == str(update.effective_chat.id):
                context.bot.send_message(chat_id=id,
                                         text="Войтенко Андрей направляет Вам файл в ответ на запрос " + array + ":")  # Акт технической готовности по объекту
            elif str(id_telegram['my']) == str(update.effective_chat.id):
                context.bot.send_message(chat_id=id,
                                         text="Константин направляет Вам файл в ответ на запрос " + array + ":")  # Акт технической готовности по объекту
            if update.message.caption != None:
                context.bot.send_document(chat_id=id, document=update.message.document, caption=update.message.caption)
            else:
                context.bot.send_document(chat_id=id, document=update.message.document)
            if num_doc != 'empl_send_sms':
                info = pd.read_sql(f"SELECT name, family_name FROM doc_key_corp WHERE user_id  = '{id}';", engine2)
                text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + " оповещен(а)."
            else:
                info = pd.read_sql("SELECT * FROM doc_employment WHERE user_id = " + str(update.effective_chat.id),
                                   engine2)
                text = "Кандидат " + str(info.loc[0, "name"]) + " тел: " + str(info.loc[0, "tel"]) + " оповещен(а)."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)

        elif user_triger[update.effective_chat.id]['triger'] == 'empl_send_doc':
            print('PDF')
            file_info = context.bot.get_file(update.message.document.file_id)
            num_doc = user_triger[update.effective_chat.id]['num_doc']
            if num_doc == "1":
                name_doc = 'заявление'
            elif num_doc == "2":
                name_doc = 'копия паспорта'
            elif num_doc == "3":
                name_doc = 'копия трудовой книги'
            elif num_doc == "4":
                name_doc = 'копия ИНН'
            elif num_doc == "5":
                name_doc = 'копия снилс'
            elif num_doc == "6":
                name_doc = 'копия диплома(ов)'
            elif num_doc == "7":
                name_doc = 'сертификаты курсов'
            elif num_doc == "8":
                name_doc = 'резюме'
            current_dttm_str = datetime.datetime.now().strftime('%Y-%m-%d_%H.%M.%S')
            context.bot.send_message(chat_id=update.effective_chat.id, text="Спасибо.")
            employment_path = '/home/admin/py/employment/' + name_doc + "_" + str(
                update.effective_chat.id) + '_' + current_dttm_str + '.pdf'
            file_info.download(employment_path)
            engine2.execute(
                f"UPDATE doc_employment SET link_{str(user_triger[update.effective_chat.id]['num_doc'])} = '{employment_path}' WHERE user_id ='{str(update.effective_chat.id)}'")
            print(user_triger[update.effective_chat.id])
            num_send = user_triger[update.effective_chat.id]['num_send']
            user_triger.pop(update.effective_chat.id)
            employment(update, context, num_send)

def num_doc_letters(update, context,name,save=False):
    if name == "letters":
        month = datetime.datetime.now().month
        xx = ((month - 1) // 3) + 1  # квартал или год...как повезет)
        yy = "015/0"
    else:
        xx = datetime.datetime.now().strftime("%y")
        yy = "07/"

    with open(f"{working_folder}num_doc_{name}.txt", 'r') as txt1:
        save_text = txt1.readlines()

    if str(xx) == str(save_text[0].replace('\n','')):
        num_latter = int(save_text[1]) + 1
    else:
        num_latter = 1

    if save:
        with open(f"{working_folder}num_doc_{name}.txt", "w") as txt:
            txt.write(f"{xx}\n{num_latter}")
    else:
        if num_latter<10:
            num_latter = "0"+str(num_latter)
        keyboard = [[InlineKeyboardButton(text="присвоить номер",callback_data='write_new_latter-'+name),InlineKeyboardButton(text="отмена",callback_data='cancel')]]
        context.bot.send_message(chat_id = update.effective_chat.id, text = f"{yy}{xx}-{num_latter}", reply_markup=InlineKeyboardMarkup(keyboard))
        Thread(target=Timer, args=(update, context, 60, update.message.message_id+1)).start()

def Timer(update, context,sec,msg_id):
    time.sleep(sec)
    try:
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
    except Exception:
        logging.info("Проблема с таймером, возможно сообщение уже удалено")

def send_excel_file (update,context):
    info = pd.read_sql("SELECT number_doc, short_name, type_of_building, type_of_equipment, brand, quantity, answer2, date, fio, tel, link, num_account, sum FROM saving_query_the_supply WHERE answer1 = 'принято' ORDER BY id ASC;",engine2)
    info = info.rename(columns={
        'number_doc': 'Номер договора',
        'short_name': 'Условное название объекта',
        'type_of_building': 'Тип сооружения',
        'type_of_equipment': 'Тип оборудования',
        'brand': 'Марка',
        'quantity': 'Количество (шт.)',
        'answer2': 'Подтверждение',
        'date': "Дата",
        'fio': 'ФИО',
        'tel': 'Номер телефона',
        'link': 'Ссылка на чертеж',
        'num_account': 'Номер счета',
        'sum': 'Сумма'
    })
    info.to_excel(str(working_folder) + 'report_supply.xlsx', index=False)
    with open(str(working_folder) + 'report_supply.xlsx', "rb") as file:
        context.bot.send_document(chat_id=update.effective_chat.id, document=file, filename="Отчет_комплектации.xlsx")

def location_processing(update, context):
    info = pd.read_sql(f"SELECT * FROM user_worker_key_corp WHERE user_id = '{update.effective_chat.id}';",engine2)
    if len(info) != 0:
        try:
            engine2.execute(f"UPDATE user_worker_key_corp SET location = '{update.edited_message.location['longitude']}:{update.edited_message.location['latitude']}', date_time = '{datetime.datetime.now()}' WHERE user_id = '{update.effective_chat.id}';")
        except Exception:
            engine2.execute(f"UPDATE user_worker_key_corp SET location = '{update.message.location['longitude']}:{update.message.location['latitude']}', date_time = '{datetime.datetime.now()}' WHERE user_id = '{update.effective_chat.id}';")
            context.bot.send_message(chat_id=943180118, text=f"{info.loc[0,'name']} - бригада \"{info.loc[0,'num_working_group']}\"")
            context.bot.send_message(chat_id=id_telegram['Boss'], text=f"{info.loc[0,'name']} - бригада \"{info.loc[0,'num_working_group']}\"")
            context.bot.send_location(chat_id=943180118, longitude=update.message.location['longitude'],latitude=update.message.location['latitude'])
            context.bot.send_location(chat_id=id_telegram['Boss'], longitude=update.message.location['longitude'],latitude=update.message.location['latitude'])

####################################################
############ Прием текстовых сообщений #############
####################################################
def handle_text(update, context):
    ####################################################
    ############ Прием текстовых по тригерам #############
    ####################################################
    if update.effective_chat.id in user_triger:
        triger = user_triger[update.effective_chat.id]['triger']
        try:
            num_doc = user_triger[update.effective_chat.id]['num_doc']
        except Exception:
            num_doc = 0
        if 'отменить' == update.message.text.lower() or 'отмена' == update.message.text.lower() or 'вернуться в главное меню' == update.message.text.lower():
            user2(update, context, "Возвращаемся в главное меню.")
        elif triger == 'C':  # длбавление контактов
            user_triger.pop(update.effective_chat.id)
            current_dttm_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            engine2.execute("INSERT INTO doc_contact(doc_id, text, datatime) VALUES(" + str(num_doc) + ",'" + str(
                update.message.text) + "','" + str(current_dttm_str) + "')")
            user2(update, context, "Данные добавленны.")
        elif triger == 'reg':  # регистрация
            reg_user(update, context)
        elif triger == 'reg_worker': # регистрация новых рабочих.
            text = "Случилась ошибка :("
            # запрос фамилии, имени, отчества, дата рождения, номер паспорта, марка автомобиля, номер
            if user_triger[update.effective_chat.id]['FIO'] == 'None':
                user_triger[update.effective_chat.id]['FIO'] = update.message.text
                text = "Введите номер телефона для связи(в случаях необходимости)."
            elif user_triger[update.effective_chat.id]['tel'] == 'None':
                user_triger[update.effective_chat.id]['tel'] = update.message.text
                text = "Введите дату рождения."
            elif user_triger[update.effective_chat.id]['birthday'] == 'None':
                user_triger[update.effective_chat.id]['birthday'] = update.message.text
                text = "Введите номер паспорта."
            elif user_triger[update.effective_chat.id]['num_pasport'] == 'None':
                user_triger[update.effective_chat.id]['num_pasport'] = update.message.text
                text = "Введите марку автомобиля."
            elif user_triger[update.effective_chat.id]['brand_car'] == 'None':
                user_triger[update.effective_chat.id]['brand_car'] = update.message.text
                text = "Введите номер автомобиля."
            elif user_triger[update.effective_chat.id]['num_car'] == 'None':
                user_triger[update.effective_chat.id]['num_car'] = update.message.text
                sms = f"Добавлен новый пользователь.\n" \
                      f"ФИО: {user_triger[update.effective_chat.id]['FIO']}\n" \
                      f"Дата рождения: {user_triger[update.effective_chat.id]['birthday']}\n" \
                      f"Номер телефона: {user_triger[update.effective_chat.id]['tel']}\n" \
                      f"Номер паспорта: {user_triger[update.effective_chat.id]['num_pasport']}\n" \
                      f"Марка автомобиля: {user_triger[update.effective_chat.id]['brand_car']}\n" \
                      f"Номер автомобиля: {user_triger[update.effective_chat.id]['num_car']}"
                wh = True
                key = ''
                while wh:
                    key = ''
                    for i in range(8):
                        rand_num = randint(0, 9)
                        key += str(rand_num)  # letter[rand_num]
                    info = pd.read_sql_query(f"SELECT doc_key_corp.name,key_for_people.name,user_worker_key_corp.name FROM doc_key_corp,key_for_people,user_worker_key_corp WHERE doc_key_corp.a_key = '{key}' or key_for_people.a_key = '{key}' or user_worker_key_corp.a_key = '{key}' limit 1;", engine2)  #
                    if len(info) == 0:# and len(info2) == 0 and len(info3) == 0:
                        wh = False
                engine2.execute(
                    "INSERT INTO user_worker_key_corp (user_id, a_key, name, birthday, tel, num_pasport, brand_car, num_car, date_time) VALUES("
                      f"'{update.effective_chat.id}'," # user_id
                      f"'{key}'," # a_key
                      f"'{user_triger[update.effective_chat.id]['FIO']}'," # ФИО: 
                      f"'{user_triger[update.effective_chat.id]['birthday']}'," # Дата рождения: 
                      f"'{user_triger[update.effective_chat.id]['tel']}'," # номер телефона: 
                      f"'{user_triger[update.effective_chat.id]['num_pasport']}'," # Номер паспорта: 
                      f"'{user_triger[update.effective_chat.id]['brand_car']}'," # Марка автомобиля: 
                      f"'{user_triger[update.effective_chat.id]['num_car']}'," # Номер автомобиля: 
                      f"'{datetime.datetime.now()}'"
                      f");")
                context.bot.send_message(chat_id=id_telegram['Boss'], text=sms)#отправляем смс Андрею Дмитриевичу
                context.bot.send_message(chat_id=update.effective_chat.id, text=sms)#отправляем смс самому пользвоателю
                info = pd.read_sql_query(f"SELECT id FROM user_worker_key_corp WHERE user_id = '{update.effective_chat.id}';",engine2)  #

                keyboard = [[InlineKeyboardButton('Определить в бригаду', callback_data=f"reg_worker_next-{info.loc[0,'id']}")]]
                context.bot.send_message(chat_id=id_telegram['Mihail'], text=sms, reply_markup=InlineKeyboardMarkup(keyboard))#отправляем смс Михаилу Черкас для распределения

                user_triger.pop(update.effective_chat.id)
                text = "Для завершения регистрации осталось отправить копию паспорта на почту info@ivea-water.ru"
                #text2 = f"Ваш, временный, ключ доступа : {key}"
                update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup([['Ввести код доступа']], resize_keyboard=True,one_time_keyboard=False))
            if user_triger[update.effective_chat.id]['num_car'] == 'None':
                context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        elif triger == 'filter':  # работа с фльтром или просто поиск документов по названию
            user_triger.pop(update.effective_chat.id)
            filter(update, context, update.message.text.lower())
        elif triger == 'filter_kontragent':  # работа с фльтром или просто поиск документов по названию
            num = user_triger[update.effective_chat.id]['num_doc']
            user_triger.pop(update.effective_chat.id)
            filter_kontragent(update, context, update.message.text.lower(), num)
        elif triger == 'int':  # Интервал завершения работ по договорам
            user_triger.pop(update.effective_chat.id)
            interval(update, context, update.message.text)
        elif triger == 'choice6':
            user_triger.pop(update.effective_chat.id)
            info = pd.read_sql(
                f"SELECT name, family_name, tel FROM doc_key_corp WHERE user_id  = '{update.effective_chat.id}';",
                engine2)
            info2 = pd.read_sql(f"SELECT number_doc, short_name FROM documents WHERE id = {num_doc};", engine2)
            text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(
                info.loc[0, "family_name"]) + ", (тел. " + str(
                info.loc[0, "tel"]) + ") запрашивает следующую информацию по Договору " + str(
                info2.loc[0, "number_doc"]) + " (" + str(info2.loc[0, "short_name"]) + "):\n\n" + str(
                update.message.text)
            keyboard = [[InlineKeyboardButton('Отправить документ', callback_data='send_doc-' + str(
                update.effective_chat.id) + '-' + num_doc + '-' + str(3))]]
            context.bot.send_message(chat_id=1860023204, text=text,
                                     reply_markup=InlineKeyboardMarkup(keyboard))  # 943180118
        elif triger == 'send_text' or triger == 'send_link':
            Arr = (
            "на запрос акта технической готовности", "по запросу заявки на пропуск, вывоз материалов, контейнера",
            "по запросу заявки на проведение исследований сточных вод", "на запрос информации",
            "на запрос проектной документации")
            Arr2 = (
                'на запрос справки 2НДФЛ', 'на запрос справки о месте работы',
                'на запрос о предоставлении сведений о детях',
                'на запрос выплаты за фактически отработанное время',
                'на запрос планируемой даты выплаты аванса, зарплаты',
                'на запрос информации о окладе (структура, сумма, даты выплаты)',
                'на запрос суммы за период (структура оклад, налоги)',
                'на запрос сканы документов (трудовой договор, все личные (паспорт и тд), приказ, и другие приказы)',
                'на запрос, что компания ждет от Вас, Ваш профессиональный рост (регистрация в ноприз, нострой, обучение на курсах повышения квалификации) и др.')
            Arr3 = ["трудовой договор (файл для прочтения, печати и подписи)", "внесена запись в трудовую книгу",
                    "приказ о назначении на должность"]
            id = user_triger[update.effective_chat.id]['id']
            j = int(user_triger[update.effective_chat.id]['j'])
            if str(id_telegram['Pavel']) == str(update.effective_chat.id):
                name = "Елисеев Павел "
            elif str(id_telegram['Andrei']) == str(update.effective_chat.id):
                name = "Минеев Андрей "
            elif str(id_telegram['Boss']) == str(update.effective_chat.id):
                name = "Войтенко Андрей "
            else:
                name = "Константин "
            if num_doc == 'empl_send_sms':
                array = Arr3[j]
            elif num_doc != "999999":
                if triger == 'send_link':
                    array = Arr[j]
                    if j == 4:
                        engine2.execute("UPDATE documents SET project_doc_link = '" + str(
                            update.message.text) + "' WHERE id = " + str(num_doc) + ";")
            else:
                array = Arr2[j]
            if triger == 'send_link':
                text = "направляет Вам ссылку на файл, в ответ "
            else:
                text = "ответил "
            user_triger.pop(update.effective_chat.id)
            context.bot.send_message(chat_id=id, text=name + text + array + " :\n" + str(update.message.text))
            if num_doc != 'empl_send_sms':
                info = pd.read_sql(f"SELECT name, family_name FROM doc_key_corp WHERE user_id  = '{id}';", engine2)
                text = "Сотрудник " + str(info.loc[0, "name"]) + " " + str(info.loc[0, "family_name"]) + " оповещен(а)."
            else:
                info = pd.read_sql("SELECT * FROM doc_employment WHERE user_id = " + str(update.effective_chat.id),
                                   engine2)
                text = "Кандидат " + str(info.loc[0, "name"]) + " тел: " + str(info.loc[0, "tel"]) + " оповещен(а)."
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        elif triger == 'date':
            info = pd.read_sql_query(f"SELECT date_end, noct FROM doc_date WHERE id ={num_doc}", engine2)
            try:
                new_date = str(update.message.text).split('.')
                d = new_date[0]
                m = new_date[1]
                y = new_date[2]
                if int(y) >= 2021 and int(y) <= 3021:
                    if int(m) <= 12:
                        if ((int(d) <= 31) and (int(m) in (1, 3, 5, 7, 8, 10, 12))) or (
                                (int(d) <= 30) and (int(m) in (4, 6, 9, 11))) or ((int(d) <= 29) and (int(m) == 2)):
                            if int(info.loc[0, 'noct']) > 0:
                                engine2.execute(
                                    f"UPDATE doc_date SET date_end = '{y}-{m}-{d} 00:00:00', noct = '{int(info.loc[0, 'noct']) + 1}' WHERE id = {num_doc}")
                            else:
                                engine2.execute(
                                    f"UPDATE doc_date SET date_end = '{y}-{m}-{d} 00:00:00', date1 = '{info.loc[0, 'date_end']}', noct = '1' WHERE id = {num_doc}")
                            user_triger[update.effective_chat.id]['triger'] = 'comment'
                            context.bot.send_message(chat_id=update.effective_chat.id,
                                                     text="Напишите причину переноса сроков.")
                        else:
                            context.bot.send_message(chat_id=update.effective_chat.id,
                                                     text="Не правильно указан день. Повторите попытку!")
                    else:
                        context.bot.send_message(chat_id=update.effective_chat.id,
                                                 text="Не правильно указан месяц.Повторите попытку!")
                else:
                    context.bot.send_message(chat_id=update.effective_chat.id,
                                             text="Не правильно указан год.Повторите попытку!")
            except Exception:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Повторите попытку!")
        elif triger == 'comment':
            engine2.execute(f"UPDATE doc_date SET coment = '{str(update.message.text)}' WHERE id = {num_doc}")
            user_triger.pop(update.effective_chat.id)
            context.bot.send_message(chat_id=update.effective_chat.id, text="Изменения внесены.")
        elif triger == 'empl_enter_name':  # если человек впервые пишет боту и жмет кнопку трудоустройства... то спрашиваем имя и номер телефона для связи
            info = pd.read_sql(f"SELECT name,tel FROM doc_employment WHERE user_id ='{str(update.effective_chat.id)}'",
                               engine2)
            if num_doc == "0":
                if info.loc[0, "name"] is None:
                    engine2.execute(
                        f"UPDATE doc_employment SET name = '{str(update.message.text)}' WHERE user_id ='{str(update.effective_chat.id)}'")
                    text = "Так же введите свой контактный номер телефона."
                    context.bot.send_message(chat_id=update.effective_chat.id, text=text)
                    user_triger[update.effective_chat.id]['num_doc'] = "1"
                    print(user_triger[update.effective_chat.id])
            else:
                if info.loc[0, "tel"] is None:
                    print(user_triger[update.effective_chat.id])
                    num_send = user_triger[update.effective_chat.id]['num_send']
                    engine2.execute(
                        f"UPDATE doc_employment SET tel = '{str(update.message.text)}' WHERE user_id ='{str(update.effective_chat.id)}'")
                    user_triger.pop(update.effective_chat.id)
                    employment(update, context, num_send)
        elif triger == 'notification_link':  # Оповещение сотрудников
            if 'https://' in update.message.text.lower() or 'http://' in update.message.text.lower():
                Arr3 = ['начисленная зарплата в месяц, дата выплаты.\n',
                        'зп переведена на расчетный счет, дата, время.\n',
                        'необходимо ознакомиться и подписать приказы/заявления.\n']
                info = pd.read_sql("SELECT user_id, name, family_name FROM doc_key_corp", engine2)
                people = 0
                sms = "Здравствуйте, " + Arr3[int(num_doc)] + str(update.message.text)
                for i in range(len(info)):
                    if str(update.effective_chat.id) != str(info.loc[
                                                                i, "user_id"]):  # "1169007263" != str(info.loc[i,"user_id"]) and "1169007263" - это тестовый профель и ему отправлять не надо.
                        try:
                            context.bot.send_message(chat_id=int(info.loc[i, "user_id"]), text=sms)
                            people += 1
                        except Exception:
                            print("Сотрудник " + info.loc[i, "name"] + " " + info.loc[i, "family_name"] + " " + str(
                                info.loc[i, "user_id"]) + " не оповещен.")
                context.bot.send_message(chat_id=update.effective_chat.id, text="Оповещено " + str(
                    people) + " чел.\nОтправленно следующее сообщение: " + sms)
                user_triger.pop(update.effective_chat.id)
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text="Это не похоже на ссылку, попробуйте еще раз.")
        elif triger == 'need_link':
            user_supply[update.effective_chat.id]['link'] = update.message.text # saving a link in the Data "user_supply"
            user_triger[update.effective_chat.id]['triger'] = 'brand' # saving brand in Data "Triger"
            context.bot.send_message(chat_id=update.effective_chat.id, text='Введите название бренда оборудования') # Sending a message to the user
        elif triger == 'brand':  # продолжение функции "СНАБЖЕНИЕ"
            user_supply[update.effective_chat.id]['brand'] = update.message.text # saving a brand in the Data "user_supply"
            user_triger[update.effective_chat.id]['triger'] = 'quantity' # saving quantity in Data "Triger"
            context.bot.send_message(chat_id=update.effective_chat.id, text="Введите необходимое количество шт.") # Sending a message to the user
        elif triger == 'quantity':  # продолжение функции "СНАБЖЕНИЕ"
            if update.message.text.isnumeric():
                text = f"Отправитель: {user_supply[update.effective_chat.id]['fio']}.\n" \
                       f"Условное  название объекта: {user_supply[update.effective_chat.id]['short_name']},\n" \
                       f"Тип сооружения: {user_supply[update.effective_chat.id]['type_of_building']},\n" \
                       f"Тип оборудования: {user_supply[update.effective_chat.id]['type_of_equipment']},\n" \
                       f"Марка: {user_supply[update.effective_chat.id]['brand']},\n" \
                       f"Количество: {update.message.text} шт." # Collecting a text to send.
                text += f"\nСсылка на чертеж: {user_supply[update.effective_chat.id]['link']}" if user_supply[update.effective_chat.id]['link'] != '' else ''
                engine2.execute("INSERT INTO saving_query_the_supply (user_id, number_doc, short_name, type_of_building, type_of_equipment, brand, quantity, fio, tel, link) VALUES("
                                f"'{str(update.effective_chat.id)}',"
                                f"'{user_supply[update.effective_chat.id]['number_doc']}',"
                                f"'{user_supply[update.effective_chat.id]['short_name']}',"
                                f"'{user_supply[update.effective_chat.id]['type_of_building']}',"
                                f"'{user_supply[update.effective_chat.id]['type_of_equipment']}',"
                                f"'{user_supply[update.effective_chat.id]['brand']}',"
                                f"'{update.message.text}',"
                                f"'{user_supply[update.effective_chat.id]['fio']}',"
                                f"'{user_supply[update.effective_chat.id]['tel']}',"
                                f"'{user_supply[update.effective_chat.id]['link']}'"
                                f");")# Saving the collect information in BD
                info = pd.read_sql("SELECT id FROM saving_query_the_supply ORDER BY id ASC;",engine2) #Looking all the id ...
                finish_id = info.loc[len(info)-1,"id"]# ...and take final the id
                keyboard = [[InlineKeyboardButton("согласовано", callback_data=f'accepted-{str(finish_id)}')]]
                context.bot.send_message(chat_id=id_telegram['Boss'], text=text, reply_markup=InlineKeyboardMarkup(keyboard))
                logging.info(f'Функция "СНАБЖЕНИЕ" chat_id={update.effective_chat.id}:\n{text}')
                keyboard_for_user = [[InlineKeyboardButton("добавить еще", callback_data=f'types-{user_supply[update.effective_chat.id]["doc_id"]}'),
                                      InlineKeyboardButton("завершить", callback_data=f'cancel')]]
                context.bot.send_message(chat_id=update.effective_chat.id, text="Информация записанна и передана.", reply_markup=InlineKeyboardMarkup(keyboard_for_user))
            else:
                context.bot.send_message(chat_id=update.effective_chat.id, text="Введите необходимое количество шт. (используйте только цифры)")
        elif triger == 'link_yandex':  # начало функции "Счет в оплату" принимаем ссылку
            user_triger[update.effective_chat.id]['link_yandex'] = update.message.text
            user_triger[update.effective_chat.id]['triger'] = 'num_account'
            context.bot.send_message(chat_id=update.effective_chat.id, text='Прикрепите номер счета')
        elif triger == 'num_account':  # продолжение функции "Счет в оплату" принимаем номер счета
            user_triger[update.effective_chat.id]['num_account'] = update.message.text
            user_triger[update.effective_chat.id]['triger'] = 'sum'
            context.bot.send_message(chat_id=update.effective_chat.id, text='Прикрепите сумму')
        elif triger == 'sum':  # начало функции "Счет в оплату" принимаем сумму. и выбираем куда записать собранную информацию
            user_triger[update.effective_chat.id]['sum'] = update.message.text
            user_triger[update.effective_chat.id]['triger'] = "end_supply"
            info = pd.read_sql(
                "SELECT id, short_name, type_of_building, type_of_equipment, brand, quantity, link FROM saving_query_the_supply WHERE "
                "answer1 = 'принято' and "
                f"short_name = '{user_triger[update.effective_chat.id]['short_name']}' "
                "ORDER BY id ASC;", engine2)
            text = f"Введите номер комплектации цифрами. Можно ввести неслолько значений через запятую.\n{info.loc[0, 'short_name']}:\n"
            for i in range(len(info)):
                if info.loc[i, 'link'] is None or info.loc[i, 'link'] == '':
                    text += f"№{info.loc[i, 'id']} - {info.loc[i, 'type_of_building']}, {info.loc[i, 'type_of_equipment']}, {info.loc[i, 'brand']}, {info.loc[i, 'quantity']}шт.\n"
            context.bot.send_message(chat_id=update.effective_chat.id, text=text)
        elif triger == 'end_supply':
            try:
                engine2.execute(f"UPDATE saving_query_the_supply SET link = '{user_triger[update.effective_chat.id]['link_yandex']}', num_account = '{user_triger[update.effective_chat.id]['num_account']}', sum = '{user_triger[update.effective_chat.id]['sum']}' WHERE id in ({update.message.text})")
                user2(update, context, f'Изменения внесены. №{update.message.text}')
            except Exception:
                logging.error(f"Не удалось записать значение в БД\n{user_triger[update.effective_chat.id]}")
                logging.error(f"UPDATE saving_query_the_supply SET link = '{user_triger[update.effective_chat.id]['link_yandex']}', num_account = '{user_triger[update.effective_chat.id]['num_account']}', sum = '{user_triger[update.effective_chat.id]['sum']}' WHERE id in ({update.message.text})")
                user_triger.pop(update.effective_chat.id)
        elif triger == 'reg_worker_next':
            user_triger[update.effective_chat.id]['num_working_group'] = str(update.message.text.lower())
            user_triger[update.effective_chat.id]['triger'] = 'reg_worker_next2'
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Укажите предположительную дату до которого {user_triger[update.effective_chat.id]['name']} будет находиться в бригаде {update.message.text}")
        elif triger == 'reg_worker_next2':
            if "." in update.message.text:
                date = str(update.message.text).split('.')
                day = date[0]
                month = date[1]
                year = date[2]
            elif "-" in update.message.text:
                date = str(update.message.text).split('-')
                day = date[2]
                month = date[1]
                year = date[0]
            hours = datetime.datetime(int(year), int(month), int(day), 9, 30)

            print(f"num_working_group = '{user_triger[update.effective_chat.id]['num_working_group']}', date_ower_num_group = '{hours}'")
            engine2.execute(f"UPDATE user_worker_key_corp SET num_working_group = '{user_triger[update.effective_chat.id]['num_working_group']}', date_ower_num_group = '{hours}' WHERE id = '{user_triger[update.effective_chat.id]['id']}';")
            user2(update, context, "готово.")
        elif triger == 'Entera':
            sms = entera(update.message.text)
            print(sms)
            context.bot.send_message(chat_id=update.effective_chat.id, text=sms)
        elif triger == 'update_k_info':
            inn = user_triger[update.effective_chat.id]["inn"]
            if user_triger[update.effective_chat.id]["trade_name"] == "None":
                user_triger[update.effective_chat.id]["trade_name"] = update.message.text
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"ИНН:{inn}\nОпишите контрагента (кратко о товарах, услугах).")
            elif user_triger[update.effective_chat.id]["description"] == "None":
                user_triger[update.effective_chat.id]["description"] = update.message.text
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"ИНН:{inn}\nВведите ссылку на сайт,если такая имеется")
            elif user_triger[update.effective_chat.id]["url"] == "None":
                user_triger[update.effective_chat.id]["url"] = update.message.text
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"ИНН:{inn}\nВведите контакты (менеджер, бухгалтер)")
            elif user_triger[update.effective_chat.id]["tel"] == "None":
                user_triger[update.effective_chat.id]["tel"] = update.message.text
                engine2.execute(f"UPDATE kontragent_info SET trade_name = '{user_triger[update.effective_chat.id]['trade_name']}', description = '{user_triger[update.effective_chat.id]['description']}', url = '{user_triger[update.effective_chat.id]['url']}', tel = '{user_triger[update.effective_chat.id]['tel']}' WHERE inn = '{user_triger[update.effective_chat.id]['inn']}';")
                context.bot.send_message(chat_id=update.effective_chat.id,
                                         text=f"ИНН:{inn}\nДанные заполненны и сохранены.")
                user_triger.pop(update.effective_chat.id)
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id - 1)
        elif triger == 'platejka':
            info = pd.read_sql(f"SELECT * FROM doc_entera_1c WHERE num_1c LIKE ('%%{update.message.text}');",engine2)
            if len(info) != 0:
                if bool(info.loc[0,"send_email"]):
                    text = user_triger[update.effective_chat.id]['text']
                    text_for_email = f"{text}\nСчёт № {info.loc[0,'num_doc']} от {info.loc[0,'date_doc']} на сумму {info.loc[0,'sum']} руб.\nКонтрагент: {info.loc[0,'contragent']}\nКомментарий: {info.loc[0,'comment']}"
                    text_for_tel = f"Автоматическое уведомление..........{str(text).lower()}......Контрагент: {info.loc[0,'contragent']}.......Подробнее на электронной почте."
                    time = datetime.datetime.now().strftime('%H:%M:%S')  # Время которое на сервере преобразованное в нужный нам вид
                    if time > "09:00:00" and time < "19:00:00":
                        print(text_for_email)
                        # send_email(text=text_for_email, subject=str(text))#, addressees="info@ivea-water.ru"
                        # call("89616599948", text_for_tel)
                        # call("89253538733", text_for_tel)
                        # call("89264942722", text_for_tel)
                        user2(update,context,"Письмо отправлено, ждите ответа от бухгалтерии.")
                    else:
                        try:
                            with open(f'{working_folder}dont_call.json') as json_file:
                                data = json.load(json_file)
                        except Exception:
                            data = {}
                        if time > "19:00:00":
                            date = datetime.datetime.now() + datetime.timedelta(days=1)
                            h = datetime.datetime.now().strftime('%H')
                            m = datetime.datetime.now().strftime('%M')
                            s = datetime.datetime.now().strftime('%S')
                            sec_end = (24 + 9) * 3600 - (((int(h) * 60) + int(m)) * 60 + int(s))
                        elif time < "09:00:00":
                            date = datetime.datetime.now()
                            h = datetime.datetime.now().strftime('%H')
                            m = datetime.datetime.now().strftime('%M')
                            s = datetime.datetime.now().strftime('%S')
                            sec_end = ((int(h) + 9) * 60 + int(m)) * 60 + int(s)
                        if date not in data.keys():
                            data[date] = 1
                        else:
                            data[date] += 1
                        with open(f'{working_folder}dont_call.json', 'w') as outfile:
                            json.dump(data, outfile)  # _save
                        Thread(target=Timer_call_and_email, args=(update, context, sec_end, text, text_for_email, text_for_tel, data[date])).start()

                else:
                    context.bot.send_message(chat_id=update.effective_chat.id, text="Данный счет еще не согласован.\nДождитесь согласования или введите другой номер.")
            else:
                context.bot.send_message(chat_id=update.effective_chat.id,text="Такого номера нет в базе данных.\nПожалуйста, повторите ввод или нажмите \"Отмена\".")
        else:
            handle_text_location(update, context, user_triger)

    ####################################################
    ############ Прием текстовых сообщений #############
    ####################################################
    elif 'cписок договоров' == update.message.text.lower():
        keyboard = [[InlineKeyboardButton('Полный список', callback_data='choice1'),
                     InlineKeyboardButton('Использовать фильтр', callback_data='choice2')]]
        text = 'Вывести полный список или воспозьзуемся фильтром?'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
        #########################################
    elif 'контакты' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        contact(update, context)
    elif 'получить' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        my_doc(update, context, 'contact_get')
    elif 'добавить' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        my_doc(update, context, 'contact_add')
    elif 'контрагенты' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        kontragent(update, context)
        ##########################################
    elif 'договор' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user2(update, context, 'Эта функция ещё в разработке...')
    elif 'акт' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user2(update, context, 'Эта функция ещё в разработке...')
    elif 'нумерация официальных документов' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        sms = "Какой документ необходимо пронумеровать?"
        reply_keyboard = [['письма', 'договора'], ['главное меню']]
        update.message.reply_text(sms, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True,one_time_keyboard=False))
    elif 'письма' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        num_doc_letters(update, context,"letters")
    elif 'договора' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        num_doc_letters(update, context,"contracts")
    elif 'список комплектаций' == update.message.text.lower() and (update.effective_chat.id == id_telegram['Boss'] or update.effective_chat.id == supply):
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        send_excel_file (update,context)
    elif 'список рабочих' == update.message.text.lower() and (update.effective_chat.id == id_telegram['Boss'] or update.effective_chat.id == supply):
        info = pd.read_sql("SELECT name, tel FROM user_worker_key_corp ORDER BY date_time DESC;", engine2)
        text = ''
        for i in range(len(info)):
            text += f'{i+1}) {info.loc[i,"name"]} - тел: {info.loc[i,"tel"]}\n'
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    elif 'посмотреть геопозицию' == update.message.text.lower() and (update.effective_chat.id == id_telegram['Boss'] or update.effective_chat.id == supply):
        info = pd.read_sql("SELECT name, user_id FROM user_worker_key_corp ORDER BY date_time DESC;", engine2)
        text = 'Выберите рабочего чтобы посмотреть его геолокацию:'
        keyboard = []
        for i in range(len(info)):
            keyboard += [[InlineKeyboardButton(str(info.loc[i, "name"]), callback_data=f'location-{info.loc[i, "user_id"]}')]]
        context.bot.send_message(chat_id=update.effective_chat.id, text=text,
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'главное меню' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user2(update, context, 'Возвращаемся в главное меню.')
    elif 'завершение работ в период...' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Введите желаемый период в колличестве дней (цифрами).\n\nБудет создан список договоров, у которых колличество дней до завершения работ будет меньше или равно данному числу.')
        user_triger[update.effective_chat.id] = {
            'triger': 'int',
            'num_doc': '0'
        }
        ###############################################
    elif 'оповещение сотрудников' == update.message.text.lower():
        keyboard = [[InlineKeyboardButton("требования ознакомиться и подписать приказы, заявления",
                                          callback_data='notification-2')]]
        context.bot.send_message(chat_id=update.effective_chat.id, text="выбирете действие",
                                 reply_markup=InlineKeyboardMarkup(keyboard))
    elif 'запрос документов от работодателя' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user2(update, context, "Эта функция, еще не доступна.")
        #request(update, context, 1)
    elif 'запрос информации для сотрудника' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user2(update, context, "Эта функция, еще не доступна.")
        #request(update, context, 2)
        ################################################
    elif 'подать документы для трудоустройства' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        employment(update, context, 1)
    elif 'оставить резюме' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        employment(update, context, 0)
    elif 'оповещение кандидатов' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        search_result = engine2.execute("SELECT user_id, name, tel FROM doc_employment").fetchall()
        print(search_result)
        if len(search_result) != 0:
            keyboard = []
            # Надо сделать так что если нет кандидатов, то уведомить об этом
            for i in range(len(search_result)):
                keyboard += [[InlineKeyboardButton(str(search_result[i][1]) + " тел.: " + str(search_result[i][2]),
                                                   callback_data='empl_send_end-' + str(search_result[i][0]))]]
            sms = "Все кандидаты на трудоустройства:"
            context.bot.send_message(chat_id=update.effective_chat.id, text=sms,
                                     reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            sms = "Кандидатов нет."
        context.bot.send_message(chat_id=update.effective_chat.id, text=sms)
        ################################################
    elif 'ввести код доступа' == update.message.text.lower():
        try:
            info = pd.read_sql("SELECT user_id FROM doc_key_corp WHERE user_id = " + str(update.effective_chat.id),
                               engine2)
            user = info.loc[0, 'user_id']
            if user == update.effective_chat.id:
                context.bot.send_message(chat_id=update.effective_chat.id, text='Вы уже зарегистрированы!')
        except Exception as err:
            logging.error('Error:' + str(err))
            context.bot.send_message(chat_id=update.effective_chat.id, text='Отправьте в сообщении код доступа.')
            user_triger[update.effective_chat.id] = {
                'triger': 'reg',
                'num_doc': '0'
            }
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
    elif 'счет в оплату' == update.message.text.lower():
        context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        user_triger[update.effective_chat.id] = {
            'triger': 'None',#'link_yandex',
            'num_doc': 'None',
            'link_yandex': 'None',
            'num_account': 'None',
            'short_name': 'None',
            'sum': 'None',
            'id': 'None'
        }
        info = pd.read_sql("SELECT short_name FROM saving_query_the_supply WHERE answer1 = 'принято' ORDER BY id ASC;",
                           engine2)
        keyboard_for_user = []
        short_name = []
        for i in range(len(info)):
            if info.loc[i, 'short_name'] not in short_name:
                keyboard_for_user += [[InlineKeyboardButton(info.loc[i, 'short_name'],
                                                            callback_data=f'supply_short_name#*&*#{info.loc[i, "short_name"]}')]]
                short_name += [info.loc[i, 'short_name']]
        keyboard_for_user += [[InlineKeyboardButton("Отмена", callback_data=f'cancel')]]
        context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите условное название договора из списка',
                                 reply_markup=InlineKeyboardMarkup(keyboard_for_user))
    elif "id" == update.message.text.lower() and (update.message.chat.type == "supergroup" or update.message.chat.type == "group"):
        context.bot.send_message(chat_id=943180118, text="ID: " + str(update.effective_chat.id) + "\n name: " + str(update.effective_chat.title))
    elif 'зарегистрироваться' == update.message.text.lower():
        # запрос фамилии, имени, отчества, дата рождения, номер паспорта, марка автомобиля, номер
        context.bot.send_message(chat_id=update.effective_chat.id, text="Введите ФИО.")
        user_triger[update.effective_chat.id] = {
            'triger': 'reg_worker',
            'num_doc': 'None',
            'FIO': 'None',
            'birthday': 'None',
            'tel': 'None',
            'num_pasport': 'None',
            'brand_car': 'None',
            'num_car': 'None'
        }
    elif "объекты" == update.message.text.lower():
        info = pd.read_sql("SELECT * FROM location_work_group;",engine2)
        sms = ''
        if len(info) != 0:
            sms = 'Список объектов:\n'
            for i in range(len(info)):
                sms += f"{i+1}) {info.loc[i,'name_location']} - бригада \"{info.loc[i,'work_group']}\"\n"
        reply_keyboard = [['Добавить объект'], ['Показать рабочих на объекте'], ['Редактировать объект'], ['Главное меню']]
        sms += '\nВ данном меню можно:\n- Добавить новый объект\n- Редактировать объект. А именно изменить название обьекта или бригаду, или вообще удалить объект\n- Показать рабочих на объекте'
        context.bot.send_message(chat_id=update.effective_chat.id, text=sms, reply_markup=ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False))
    elif "показать рабочих на объекте" == update.message.text.lower():
        read_location(update, context)
    elif "добавить объект" == update.message.text.lower():
        my_doc(update, context, flag='doc_montage')
        #write_location(update, context, user_triger)
    elif "редактировать объект" == update.message.text.lower():
        edit_location(update, context)
    elif ("запросить платёжку" == update.message.text.lower() or "напоминание" == update.message.text.lower() or "доплатить" == update.message.text.lower()) and update.effective_chat.id == id_telegram['my']:
        if "напоминание" == update.message.text.lower():
            text = "СРОЧНО НУЖНА ОПЛАТА. В базе 1С склада счет есть."
        elif "доплатить" == update.message.text.lower():
            text = "Требуется доплата по счету."
        else:
            text = "Требуется платёжное поручение с отметкой банка."
        user_triger[update.effective_chat.id] = {
                "triger": "platejka",
                "nun_doc": "0",
                "text": text
            }
        context.bot.send_message(chat_id=update.effective_chat.id, text="Введите номер присвоенный счету в 1С.\nПример: 0000-000092 или просто 92", reply_markup=ReplyKeyboardMarkup([["Отменить"]], resize_keyboard=True, one_time_keyboard=False))
    elif "добавить документ" == update.message.text.lower() and (update.effective_chat.id == id_telegram['Boss'] or update.effective_chat.id == id_telegram['Pavel']):
        context.bot.send_message(chat_id=update.effective_chat.id, text='Для заполнения информации необходимо пройти по ссылке:',
                                 reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Добавить документ в БД", url=f"http://84.201.175.124:1994/new_document?id={update.effective_chat.id}")]]))
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Команда введена неверно.")

def email(update, context):
    user_triger[update.effective_chat.id]= {
        "triger": "Entera",
        "num_doc": 0
    }
    context.bot.send_message(chat_id=update.effective_chat.id, text="Введите номер документа.")
def inn(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Общество с ограниченной ответственностью «ИВЕА»")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ООО «ИВЕА»")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ИНН")
    context.bot.send_message(chat_id=update.effective_chat.id, text="7716782520")
    context.bot.send_message(chat_id=update.effective_chat.id, text="КПП")
    context.bot.send_message(chat_id=update.effective_chat.id, text="771601001")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОГРН")
    context.bot.send_message(chat_id=update.effective_chat.id, text="1147746928735")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКПО")
    context.bot.send_message(chat_id=update.effective_chat.id, text="16432457")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКВЭД")
    context.bot.send_message(chat_id=update.effective_chat.id, text="70.22")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКАТО")
    context.bot.send_message(chat_id=update.effective_chat.id, text="45280556000")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКТМО")
    context.bot.send_message(chat_id=update.effective_chat.id, text="45351000000")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКОГУ")
    context.bot.send_message(chat_id=update.effective_chat.id, text="4210014")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКФС")
    context.bot.send_message(chat_id=update.effective_chat.id, text="16")
    context.bot.send_message(chat_id=update.effective_chat.id, text="ОКОПФ")
    context.bot.send_message(chat_id=update.effective_chat.id, text="12165")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Юридический адрес")
    context.bot.send_message(chat_id=update.effective_chat.id, text="129344, г Москва, ул. Искры, д. 31 К. 1, помещ. i, офис 521, этаж 5")
    Thread(target=Timer_status, args=(update, context, 60, update.message.message_id)).start()
def Timer_status(update, context,sec,msg_id):
    time.sleep(sec)
    try:
        for i in range(25):
            context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id+i)
    except Exception:
        logging.info("Проблема с таймером")

def Timer_call_and_email(update, context, sec, text, text_for_email, text_for_tel, index):
    time.sleep(sec*index)
    try:
        send_email(text=text_for_email, subject=str(text), addressees="kostik55555@yandex.ru")#, addressees="info@ivea-water.ru"
        call("89616599948", text_for_tel)
        # call("89253538733", text_for_tel)
        # call("89264942722", text_for_tel)
    except Exception:
        logging.info("Проблема с таймером")
def test(update, context):
    print("go")
    context.bot.forward_message(chat_id= -1001378825774, from_chat_id = update.effective_chat.id,  message_id = update.message.message_id)
def test2(update, context):
    context.bot.send_message(chat_id= update.effective_chat.id,text="Я услышал слово \"Костя\"")

####################################################
############# Обьявление заголовков ################
####################################################
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

start2_handler = MessageHandler(Filters.regex(re.compile(r'старт', re.IGNORECASE)), start)
dispatcher.add_handler(start2_handler)

email_handler = CommandHandler('email', email)
dispatcher.add_handler(email_handler)

mega_start_handler = CommandHandler('mega_start', mega_start)
dispatcher.add_handler(mega_start_handler)

inn_handler = CommandHandler('inn', inn)
dispatcher.add_handler(inn_handler)

test_handler = CommandHandler('test', test)
dispatcher.add_handler(test_handler)

dispatcher.add_handler(CallbackQueryHandler(button))

# test2_handler = MessageHandler(Filters.regex(re.compile(r'костя', re.IGNORECASE)), test2)
# dispatcher.add_handler(test2_handler)

text_handler = MessageHandler(Filters.text, handle_text)
dispatcher.add_handler(text_handler)

document_handler = MessageHandler(Filters.document, send_document)
dispatcher.add_handler(document_handler)

photo_handler = MessageHandler(Filters.photo, test)
dispatcher.add_handler(photo_handler)

location_handler = MessageHandler(Filters.location, location_processing)
dispatcher.add_handler(location_handler)

####################################################
############# Обьявление заголовков ################
####################################################


if __name__ == "__main__":
    updater.start_polling()
