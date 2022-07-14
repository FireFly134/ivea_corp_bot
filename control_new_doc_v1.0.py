# coding=UTF-8
#
#
import datetime

import telegram
import pandas as pd
import logging

from work import *
from sqlalchemy import create_engine

engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером
bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(filename=str(working_folder) + 'doc_control.log',
                     filemode='a',
                     level=logging.INFO,
                     format='%(asctime)s %(process)d-%(levelname)s %(message)s',
                     datefmt='%d-%b-%y %H:%M:%S')

def main():
    try:
        logging.info('Проверка на наличее новых документов')
        # print('Проверка на наличее новых документов')
        list_doc = ''
        j = 0
        try:
            with open(str(working_folder) + "save_end_id.txt", 'r') as txt1:
                save_text = txt1.read()
        except Exception as err:
            logging.error('Error: Нет файла "save_end_id.txt" или не удалось прочесть - ' + str(err))
            # print('Error: Нет файла "save_end_id.txt" или не удалось прочесть - ' + str(err))
            save_text = 98
        info = pd.read_sql_query("SELECT id, short_name FROM documents ORDER BY id ASC", engine2)
        if int(save_text) < int(info.loc[len(info)-1, 'id']):
            with open(str(working_folder) + "save_end_id.txt", "w") as txt:
                txt.write(str(info.loc[len(info)-1, 'id']))
            txt.close()
            for i in range(len(info)):
                if int(info.loc[i, 'id']) > int(save_text):
                    j += 1
                    list_doc += str(j)+") "+str(info.loc[i, 'short_name']) + "\n\n"
                    if j == 1:
                        text = 'В работу добавлен новый договор:\n\n' + str(list_doc)
                    else:
                        text = 'В работу добавлены новые договора:\n\n' + str(list_doc)
            if list_doc != '': 
                #bot.send_message(chat_id=232749605, text=text)
                #bot.send_message(chat_id=943180118, text=text)
                info = pd.read_sql("SELECT user_id FROM doc_key_corp WHERE access > 0;", engine2)
                for i in range(len(info)):
                    if str(info.loc[i, 'user_id']) != "127522234":
                        try:
                            bot.send_message(chat_id=str(info.loc[i, 'user_id']), text=text)
                        except Exception as err:
                            logging.error('Error2: Не удалось отправить сообщение пользователю!  - ' + str(err)+"\n")
                            # print('Error2: Не удалось отправить сообщение пользователю!  - ' + str(err)+"\n")
                logging.info(str(text))
            else:
                logging.info('документов которые скоро закроются нет\n')
                # print('документов которые скоро закроются нет\n')
    except Exception as err:
        logging.error('Error: Не удалось отправить сообщение пользователю!  - ' + str(err)+"\n")
        # print('Error: Не удалось отправить сообщение пользователю!  - ' + str(err)+"\n")

def check_date_work_group():
    info = pd.read_sql_query(f"SELECT * FROM user_worker_key_corp WHERE date_ower_num_group < '{datetime.datetime.now()}';",engine2)  #
    for i in range(len(info)):
        sms = f"Время нахождения в бригаде вышло, пожалуйста обновите информацию.\n" \
              f"ФИО: {info.loc[i,'name']}\n" \
              f"Номер телефона: {info.loc[i,'tel']}\n"
        keyboard = [[telegram.InlineKeyboardButton('Определить в бригаду', callback_data=f"reg_worker_next-{info.loc[i, 'id']}")]]
        bot.send_message(chat_id=id_telegram['Boss'], text=sms, reply_markup=telegram.InlineKeyboardMarkup(keyboard))  # отправляем смс Михаилу Черкас для распределения 1726499460
        bot.send_message(chat_id=943180118, text=sms, reply_markup=telegram.InlineKeyboardMarkup(keyboard))  # отправляем смс Михаилу Черкас для распределения 1726499460
def check_open_location_today():
    info = pd.read_sql_query(f"SELECT name FROM user_worker_key_corp WHERE date_time > '{datetime.datetime.now().strftime('%Y-%m-%d 01:00:00.000')}';",engine2)  #
    good_boys = info['name'].tolist()
    info = pd.read_sql_query(f"SELECT name FROM user_worker_key_corp;",engine2)
    bad_boys = info['name'].tolist()
    sms = ''
    if good_boys != []:
        sms = "Сегодня включили геолокацию:"# {', '.join(good_boys)}\nГеолокацию не включили: {', '.join(bad_boys)}"
        for name in good_boys:
            if name in bad_boys:
                bad_boys.remove(name)
        for i in range(len(good_boys)):
            sms += f"\n{i+1}) {good_boys[i]}"
    sms += "\nГеолокацию не включили:"
    for i in range(len(bad_boys)):
        sms += f"\n{i+1}) {bad_boys[i]}"
    bot.send_message(chat_id=id_telegram['Boss'], text=sms)
    # bot.send_message(chat_id=943180118, text=sms)
    # print("good_boys:", ', '.join(good_boys))
    # print("bad_boys:", ', '.join(bad_boys))
if __name__ == "__main__":
    main()
    time = datetime.datetime.now().strftime('%H:%M:00')  # Время которое на сервере преобразованное в нужный нам вид
    print(time)
    if str(time) == "09:30:00" and datetime.datetime.now().strftime('%w') not in ['0', '6']:
        check_date_work_group()
    if str(time) == "10:00:00" and datetime.datetime.now().strftime('%w') not in ['0', '6']:
        print("go")
        check_open_location_today()
