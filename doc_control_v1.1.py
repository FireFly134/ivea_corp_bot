# coding=UTF-8
#
#
import telegram
import pandas as pd
import datetime
import logging

from work import TELEGRAM_TOKEN, ivea_metrika
from sqlalchemy import create_engine
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ReplyKeyboardRemove

engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером
bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(filename='/home/menace134/py/ivea_corp/doc_control.log',
                     filemode='a',
                     level=logging.INFO,
                     format='%(asctime)s %(process)d-%(levelname)s %(message)s',
                     datefmt='%d-%b-%y %H:%M:%S')

def main():
    try:
        now = datetime.datetime.now()
        info = pd.read_sql_query("SELECT * FROM doc_date ORDER BY date_end ASC", engine2)
        list_doc = ''
        text = ''
        id = ''
        j=0
        for i in range(len(info)):
            date_end = str(info.loc[i, 'date_end'] - now).split(" ")[0]
            if date_end == "0":
                j+=1
                if info.loc[i, 'noct'] > 0:
                    id += "," + str(info.loc[i, 'id'])
                    days = str(info.loc[i, 'date_end'] - info.loc[i, 'date1']).split(" ")[0]
                    list_doc += str(j) + ") " + str(info.loc[i, 'doc_name']) + " " + str(info.loc[i, 'work_name']) + "\nВыполнение задачи переносилось " + str(info.loc[i, 'noct']) + " раз(а) на общее количество " + days + " дн. Причина: " + str(info.loc[i, 'coment'])+"\n\n"
                else:
                    id += "," + str(info.loc[i, 'id'])
                    list_doc += str(j)+") "+str(info.loc[i, 'doc_name']) + " " + str(info.loc[i, 'work_name']) + "\n\n"
                text = 'Завершение работ в период - 1 день - "' + str(info.loc[i, 'date_end'].strftime('%d.%m.%Y')) + '"\n\n' + list_doc
        if text != '':
                info = pd.read_sql("SELECT user_id FROM key_for_people WHERE access > 0;", engine2)
                keyboard = [[InlineKeyboardButton("Перенести срок договора", callback_data='go_next_contract'+id)]]
                for i in range(len(info)):
                    if str(info.loc[i, 'user_id']) != "127522234":
                        try:
                            if str(info.loc[i, 'user_id']) == "232749605" or str(info.loc[i, 'user_id']) == "1860023204" or str(info.loc[i, 'user_id']) == "943180118":
                                bot.send_message(chat_id=str(info.loc[i, 'user_id']), text=text, reply_markup=InlineKeyboardMarkup(keyboard))
                            else:
                                bot.send_message(chat_id=str(info.loc[i, 'user_id']), text=text)
                        except Exception as err:
                            logging.error('Error2: doc_control_v1.1(53) - Не удалось отправить сообщение пользователю!  - ' + str(err)+"\n")
    except Exception as err:
        logging.error('Error: doc_control_v1.1(55) - Не удалось отправить сообщение пользователю!  - ' + str(err))

main()
