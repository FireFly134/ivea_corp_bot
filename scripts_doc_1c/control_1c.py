import json
from datetime import datetime, timedelta
### эти библиотеки для отправки смс с доками на почту ###
import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
### эти библиотеки для отправки смс с доками на почту ###

import requests
from urllib.parse import urlencode
import pandas as pd
from sqlalchemy import create_engine
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

from work import *
from tkachev.call_api import call
from tkachev.send_email import send_email
from tkachev.setting import data_email, header

engine2 = create_engine(ivea_metrika)  # данные для соединия с сервером

bot = telegram.Bot(TELEGRAM_TOKEN)

s = requests.Session()
link = 'https://id.entera.pro/api/v1/login'
s.post(link, headers=header, json=datas)
link = "https://passport.yandex.com/auth"

e = requests.Session()
datas2 = {
    'login': data_email['email'],
    'password': data_email['password']
}
e.post(link, data=datas2, headers=header)

# logging.basicConfig(filename=str(working_folder) + 'doc_control.log',
#                      filemode='a',
#                      level=logging.INFO,
#                      format='%(asctime)s %(process)d-%(levelname)s %(message)s',
#                      datefmt='%d-%b-%y %H:%M:%S')
def download(name1 = 'downloaded_file.csv',name2 = 'Scheta.xls',name3 = 'Kontragent.csv'):
    base_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
    public_key = ['https://disk.yandex.ru/d/3QqZrBaagLESoA','https://disk.yandex.ru/i/rmBYHkNM4F7_kQ', 'https://disk.yandex.ru/d/ZgTslH1SlDzGpA']#'https://disk.yandex.ru/d/Obh6xQ77HXI16A']  # Сюда вписываете вашу ссылку
    dist = {'downloaded_file.csv': {'link': 'https://disk.yandex.ru/d/gSYISs5gXfIm6w',
                                   'download_url': ''},
            'Scheta.csv': {'link': 'https://disk.yandex.ru/d/6sxYy6TKF88Y3A',
                                    'download_url': ''}}
    download_url = []
    for url in public_key:
        try:
        # Получаем загрузочную ссылку
            final_url = base_url + urlencode(dict(public_key=url))
            response = e.get(final_url)
            download_url += [response.json()['href']]# 'парсинг' ссылки на скачивание
        except Exception:
            download_url += ["Error"]  # 'парсинг' ссылки на скачивание
    name_file = [name1,name2, name3]#'Scheta.csv']
    for i in range(len(download_url)):
    # Загружаем файл и сохраняем его
        if "Error" != download_url[i]:
            download_response = requests.get(download_url[i])
            with open(working_folder+name_file[i], 'wb') as f:   # Здесь укажите нужный путь к файлу
                f.write(download_response.content)
        else:
            logging.error(f"does not download \"{name_file[i]}\"")
            logging.error(f"Bad url: {public_key[i]}")
            bot.send_message(chat_id=id_telegram["my"], text= f"does not download \"{name_file[i]}\"\nBad url: {public_key[i]}")

def download_one(name = 'Kontragent.csv', url = 'https://disk.yandex.ru/d/ZgTslH1SlDzGpA'):
    base_url = 'https://cloud-api.yandex.net/v1/disk/public/resources/download?'
    try:
        # Получаем загрузочную ссылку
            final_url = base_url + urlencode(dict(public_key=url))
            response = e.get(final_url)
            download_url = [response.json()['href']]# 'парсинг' ссылки на скачивание
    except Exception:
            download_url = ["Error"]  # 'парсинг' ссылки на скачивание
    # Загружаем файл и сохраняем его
    if "Error" != download_url:
        download_response = requests.get(download_url)
        with open(working_folder+name, 'wb') as f:   # Здесь укажите нужный путь к файлу
            f.write(download_response.content)
    else:
        logging.error(f"does not download \"{name}\"")
        logging.error(f"Bad url: {url}")
        bot.send_message(chat_id=id_telegram["my"], text= f"does not download \"{name}\"\nBad url: {url}")

def read_csv1():
    df = pd.read_csv('downloaded_file.csv', delimiter='\t')
    with open(f'{working_folder}data.json') as json_file:
        data = json.load(json_file)
    if datetime.now().strftime('%w') in ['0', '1', '6']:
        week = datetime.now().strftime('%w')
        day = 1
        if week == '0':
            day = 2
        elif week == '1':
            day = 3
        df = df.dropna().replace("Основной", "Основной договор")
        df = df[df['Дата'].isin([str((datetime.now() - timedelta(days=day)).strftime("%d.%m.%Y"))])]

    else:
        df = df.dropna().replace("Основной", "Основной договор")
        df = df[df['Дата'].isin([str((datetime.now() - timedelta(days=6)).strftime("%d.%m.%Y")),str((datetime.now() - timedelta(days=5)).strftime("%d.%m.%Y")),str((datetime.now() - timedelta(days=4)).strftime("%d.%m.%Y")),str((datetime.now() - timedelta(days=3)).strftime("%d.%m.%Y")),str((datetime.now() - timedelta(days=2)).strftime("%d.%m.%Y")), str((datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")), str(datetime.now().strftime("%d.%m.%Y"))])]
    df = df.loc[df['Ссылка'] == 'Поступление на расчетный счет']
    list_df = df["Договор"].tolist()
    list_df2 = df["Сумма документа"].tolist()
    list_df_data = df["Дата"].tolist()
    list_df_info = df["Платильщик"].tolist()

    print(len(list_df), "==", len(list_df2)," and ",len(list_df),"!= 0")
    if len(list_df) == len(list_df2) and len(list_df) != 0:
        sms = 'Новые оплаты:\n'
        sms_osnov = 'По договору "Основной" поступила оплата:\n'
        summa = 0
        summa_osnov = 0
        q = 0
        q_osnov = 0
        for i in range(len(list_df)):
            if list_df_data[i] not in data:#_save
                data[list_df_data[i]] = []#_save
            text1 = str(list_df[i])\
                .replace("договор", "")\
                .replace("Договор", "") \
                .replace("ДОГОВОР", "") \
                .replace("№", "")\
                .replace("поставки", "")\
                .replace("счет", "")\
                .replace("Счет", "")\
                .replace("счету", "")\
                .replace("СЧЕТУ", "")\
                .replace("сч", "")\
                .replace("Сч", "")\
                .replace("СЧ", "")\
                .replace("-", "")\
                .replace("подряда", "")\
                .replace("на сервисное обслуживание очистных сооружений", "")
            if "специф" in text1:
                text1 = text1.split("специф")[1].split("от")[0].replace(" ", "")
            elif "спец" in text1:
                text1 = text1.split("спец")[1].split("от")[0].replace(" ", "")
            else:
                text1 = text1.split("от")[0].replace(" ", "")
            if "_" in text1:
                text1 = text1.split("_")[0]
            if list_df_data[i] not in data:
                data[list_df_data[i]] = []
            price = float(list_df2[i].replace("\xa0", "").replace(",", "."))
            if text1 + str(price) not in data[list_df_data[i]]:
                data[list_df_data[i]].append(text1 + str(price))  # _save
                if "основной" in text1.lower():
                    q_osnov += 1
                    sms_osnov += f'{q_osnov}) {list_df_info[i]} - {price} руб.\n'
                    summa_osnov += price
                else:
                    q += 1
                    text2 = pd.read_sql(f"SELECT short_name FROM documents WHERE number_doc LIKE ('%%{text1}%%') ",
                                        engine2)
                    try:
                        sms += f'{q}) {text2.loc[0, "short_name"]} ("{list_df_info[i]}") - {price} руб.\n'
                    except Exception:
                        logging.info("Не удалось найти краткое название договора.")
                        sms += f'{q}) {list_df[i]} ("{list_df_info[i]}") - {price} руб.\n'
                    summa += price
                print(text1)
                print(list_df2[i].replace("\xa0", ""))
                print()

        if sms != 'Новые оплаты:\n' or sms_osnov != 'По договору "Основной" поступила оплата:\n':
            if sms != 'Новые оплаты:\n':
                if "2)" in sms and "1)" in sms:
                    sms += f"на общую сумму {summa} руб."
                # bot.send_message(chat_id=id_telegram["Boss"], text=sms)
                bot.send_message(chat_id=id_telegram["my"], text=sms)
                call("8961*****14", "Автоматическое оповещение. . . . . . . . . ." + sms)
            if sms_osnov != 'По договору "Основной" поступила оплата:\n':
                if "2)" in sms_osnov and "1)" in sms_osnov:
                    sms_osnov += f"на общую сумму {summa_osnov} руб."
                # bot.send_message(chat_id=id_telegram["Boss"], text=sms_osnov)
                bot.send_message(chat_id=id_telegram["my"], text=sms_osnov)
                call("8961*****14", "Автоматическое оповещение. . . . . . . . . ." + sms_osnov)
            with open(f'{working_folder}data.json', 'w') as outfile:
                json.dump(data, outfile)#_save
        # logging.info(sms)

    """№ п/п 0
        Дата 1
        Ссылка 2
        Номер	3
        Вх. дата	4
        Вх. номер	5
        Информация	6
        Платильщик	7
        Договор	8
        Счет на оплату	9
        Сумма документа	10
        Валюта документа 11"""

def read_csv2():
    df = pd.read_excel(f'{working_folder}Scheta.xls')
    new_write = False
    # mail=False
    info = pd.read_sql("SELECT * FROM doc_entera_1c;", engine2)
    list_info = info["num_1c"].tolist()
    list_save = {}
    list_del = {}
    # server = smtplib.SMTP_SSL("smtp.yandex.ru")
    # try:
        # server.login(email["email"], email["password"])
    #     mail = True
    # except Exception:
    #     logging.error("Не верный логин или пароль, или почта не доступна.")
    df = df[["Номер","Контрагент","Сумма","Комментарий","Дата входящего документа","Номер входящего документа","Доп информация"]]
    for i in range(len(df)):
        if df.loc[i,'Номер'] not in list_info and df.loc[i,'Доп информация'] != "Удален":# or df.loc[i,'Номер'] == "0000-000148": # Используем при необходимости повторно прислать документ !!! НО НЕ ЗАБУДЬ ЗАКОМЕНТИРОВАТЬ ЗАПИСЬ В БД!!!
            list_info +=[df.loc[i,'Номер']]
            list_save.update({df.loc[i,'Номер']: {
                "Контрагент": df.loc[i, 'Контрагент'],
                "Дата входящего документа": df.loc[i, 'Дата входящего документа'],
                "Сумма": df.loc[i, 'Сумма'],
                "Комментарий": df.loc[i, 'Комментарий'],
                "Номер входящего документа": df.loc[i,'Номер входящего документа'],
                "Ссылка": ''}})
            new_write = True
        elif df.loc[i,'Номер'] in list_info and df.loc[i,'Доп информация'] == "Удален":
                info2 = info[info['num_1с'].isin([df.loc[i,'Номер']])]
                if info2['delete'].bool() == False and df.loc[i,'Номер'] not in list_del:
                    list_del.update({df.loc[i, 'Номер']: {
                        "Контрагент": df.loc[i, 'Контрагент'],
                        "Дата входящего документа": df.loc[i, 'Дата входящего документа'],
                        "Сумма": df.loc[i, 'Сумма'],
                        "Комментарий": df.loc[i, 'Комментарий'],
                        "Номер входящего документа": df.loc[i, 'Номер входящего документа'],
                        "Ссылка": ''}})
                    k=str(info2['num_doc'].item())
                    text = f"Счёт № {k} от {list_del[k]['Дата входящего документа']}\nКонтрагент: {list_del[k]['Контрагент']}\nКомментарий: {list_del[k]['Комментарий']}\n🚫ОТМЕНА! НЕ ОПЛАЧИВАТЬ!🚫"
                    text2 = f"ОТМЕНА!....... НЕ ОПЛАЧИВАТЬ!....... Счёт № {k}.....Контрагент: {list_del[k]['Контрагент']}"
                    # engine2.execute(f"UPDATE doc_entera_1c SET delete = True WHERE id = '{info2['id'].item()}';")
                    # bot.send_message(chat_id=id_telegram["Boss"], text=text)
                    bot.send_message(chat_id=id_telegram["my"], text=text)
                    # call("8925*****33", "Автоматическое оповещение.........." + text2)
                    # call("8961*****14", "Автоматическое оповещение.........." + text2)
                    # call("8925*****22", "Автоматическое оповещение.........." + text2) # Звонок Бухгалтеру.
                    # if mail:
                    #     try:
                            # answer = send_email(server=server, text=text, subject=f"ОТМЕНА! НЕ ОПЛАЧИВАТЬ! Счёт № {k} от {list_del[k]['Дата входящего документа']}")
                            # if "Письмо с документом отправлено!" != str(answer):
                            #     bot.send_message(chat_id=id_telegram["my"], text=answer + "\n\n" + text)
                        # except Exception:
                        #     logging.error("Не удалось отправить сообщение на почту.")
    if new_write:
        for k in list_save.keys():
            try:
                list_save[k]['Ссылка'], name_file = entera(search=list_save[k]['Номер входящего документа'], documentDateFrom=list_save[k]['Дата входящего документа'],documentDateTo=list_save[k]['Дата входящего документа'])
                try:
                    id_list = list_save[k]['Комментарий']
                    info = pd.read_sql(f"SELECT short_name FROM documents WHERE id in ({id_list});", engine2)
                    comment = str(info["short_name"].tolist()).replace("[","").replace("]","").replace("'","")
                except Exception:
                    comment = list_save[k]['Комментарий']
                # engine2.execute(f"INSERT INTO doc_entera_1c (num_1c,contragent,date_doc,sum,link, comment, name_file, num_doc) "
                #        f"VALUES('{k}','{list_save[k]['Контрагент']}','{list_save[k]['Дата входящего документа']}','{list_save[k]['Сумма']}','{list_save[k]['Ссылка']}','{comment}','{name_file}','{list_save[k]['Номер входящего документа']}');")
                print(f"INSERT INTO doc_entera_1c (num_1c,contragent,date_doc,sum,link, comment, name_file, num_doc) "
                    f"VALUES('{k}','{list_save[k]['Контрагент']}','{list_save[k]['Дата входящего документа']}','{list_save[k]['Сумма']}','{list_save[k]['Ссылка']}','{comment}','{name_file}','{list_save[k]['Номер входящего документа']}');")
                info = pd.read_sql(f"SELECT id FROM doc_entera_1c WHERE num_1c = '{k}' and contragent = '{list_save[k]['Контрагент']}' and date_doc = '{list_save[k]['Дата входящего документа']}' and sum = '{list_save[k]['Сумма']}' and link = '{list_save[k]['Ссылка']}';", engine2)
                text = f"Счёт № {list_save[k]['Номер входящего документа']} от {list_save[k]['Дата входящего документа']} на сумму {list_save[k]['Сумма']} руб.\nКонтрагент: {list_save[k]['Контрагент']}\nКомментарий: {comment}"
                keyboard = [[InlineKeyboardButton("Отправить", callback_data=f"send_email_1c_doc-{info.loc[0,'id']}"),InlineKeyboardButton("Состав", callback_data=f"item_1c_doc-{info.loc[0,'id']}")]]
                bot.send_message(chat_id=id_telegram["Boss"], text=text,reply_markup=InlineKeyboardMarkup(keyboard))
                bot.send_message(chat_id=id_telegram["my"], text=text,reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                text = f"Entera ошибка поиска {k}. счет № {list_save[k]['Номер входящего документа']}, documentDateFrom={list_save[k]['Дата входящего документа']}"
                logging.error(text)
                bot.send_message(chat_id=id_telegram["my"], text=text)

def read_csv3():
    df = pd.read_csv(f'{working_folder}Kontragent.csv', delimiter='\t', lineterminator='\n')
    list_info = pd.read_sql("SELECT inn FROM kontragent_info;", engine2)["inn"].tolist()
    list_save = {}
    print(list_info)
    for i in range(len(df)):
        if str(df.loc[i, 'ИНН']) != 'nan':
            if str(int(df.loc[i, 'ИНН'])) not in list_info:
                list_info += [int(df.loc[i, 'ИНН'])]
                list_save.update({int(df.loc[i, 'ИНН']): {
                    "name": df.loc[i, 'Полное наименование'],
                    "group": df.loc[i, 'Группа'],
                    "type": df.loc[i, 'Вид контрагента']}})
    print(list_save)
    for k in list_save.keys():
        try:
            # engine2.execute(f"INSERT INTO kontragent_info (inn,name,group_k,type_k) VALUES('{int(k)}','{list_save[k]['name']}','{list_save[k]['group']}','{list_save[k]['type']}');")
            text = 'Добавлен новый контрагент\n'
            if str(list_save[k]['name']) != 'nan':
                text += f"Полное наименование: {list_save[k]['name']}\n"
            if str(list_save[k]['group']) != 'nan':
                text += f"Группа: {list_save[k]['group']}\n"
            if str(list_save[k]['type']) != 'nan':
                text += f"Вид контрагента: {list_save[k]['type']}\n"
            text += f"ИНН контрагента: {k}\n"
            keyboard = [[InlineKeyboardButton("Заполнить данные", callback_data=f"update_k_info-{int(k)}")]]
            bot.send_message(chat_id=id_telegram["my"], text=text,reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as err:
            text = f"script_doc_1c функция read_csv3 ориентировочно 'ссылка' {err}"
            bot.send_message(chat_id=id_telegram["my"], text=text)

def read_csv4():
    list_df = pd.read_excel(f'{working_folder}Scheta.xls')["Номенклатура"].tolist()
    list_info = pd.read_sql("SELECT name FROM main_accounting_for_purchased_equipment;", engine2)["name"].tolist()
    for name in list_df:
        print(list_info)
        try:
            if name not in list_info:
                engine2.execute(f"INSERT INTO main_accounting_for_purchased_equipment (name)VALUES('{str(name).replace('%','%%')}');")
                list_info.append(name)
        except Exception:
            print(f"INSERT INTO main_accounting_for_purchased_equipment (name) VALUES('{str(name).replace('%','%%')}');")

def read_csv_sostav(d_id):
    info = pd.read_sql(f"SELECT * FROM doc_entera_1c WHERE id = {d_id};", engine2)
    df = pd.read_csv(f'{working_folder}Scheta.csv', delimiter='\t')
    '''Номенклатура	Количество	Номенклатура.Единица	Цена	Сумма	% НДС	НДС	Всего'''
    df = df[df['Номер входящего документа'].isin(info.loc[0,"num_doc"])]
    df = df[["Дата входящего документа","Номенклатура", "Количество", "Номенклатура.Единица", "Цена", "Сумма", "% НДС", "НДС", "Всего"]]
    """Счёт № 1644 от 19.04.2022 на сумму 12 136,58 руб.
1. Поплавок (пласт.) плоский D90mm с резьбой для крепл.(для FARG мод.510), Tmax-80C - 1 шт. (47,42 руб.)
2. Поплавковый мех. регулятор уровня (5 осей) 1/2" штанга диам.5мм, 175мм-латунь, усил., седло-латунь,  - 1 шт. (526,53 руб.)"""
    text =''
    # text = f"Счёт № {num_doc} от {df.loc[0,'Дата входящего документа']} на сумму {list_save[k]['Сумма']} руб.\nКонтрагент: {list_save[k]['Контрагент']}\nКомментарий: {list_save[k]['Комментарий']}"
    print(df)

def entera(search='', documentDateFrom='', documentDateTo=''):
    url = f"https://app.entera.pro/api/v1/documents"
    site = s.get(url, headers=header, params={'spaceId': "8d29235e-393d-408a-82c9-b67607152e10", "search": search, "documentDateFrom":documentDateFrom, "documentDateTo":documentDateTo, "documentType": ["OFFER", "NONSTANDARD", "UNKNOWN", "CERTIFICATE"]})
    answer = json.loads(site.text)
    for i in range(len(answer['documents'])):
        if answer['documents'][i]['number'] == search:
            url = f"https://app.entera.pro/api/v1/documents/{answer['documents'][i]['id']}/file"
            name_file = answer['documents'][i]['pages'][0]['file']['name']
            return url, name_file

# def send_email(server, text='', addressees=email["email_send"]):
#     try:
#         msg = MIMEMultipart()
#         msg["From"] = email["email"]
#         msg["To"] = addressees
#         msg["Subject"] = "ОТМЕНА! НЕ ОПЛАЧИВАТЬ! Счёт..."
#         if text:
#             msg.attach(MIMEText(text))
#         server.sendmail(email["email"], addressees, msg.as_string())
#         logging.info("Письмо отправлено!")
#     except Exception as _ex:
#         logging.info(f"{_ex}\nОшибка при отправке письма.")
#     # return "Документ не найден."

def test():
    time = datetime.now().strftime('%H:%M:%S')  # Время которое на сервере преобразованное в нужный нам вид
    if time > "09:00:00" and time < "15:00:00":
        print(time)
    else:
        # try:
        #     with open(f'{working_folder}dont_call.json') as json_file:
        #         data = json.load(json_file)
        # except Exception:
        #     data = {}
        if time > "15:00:00":
            print("""дата = Дата+1день
            время = 24ч - время + 9ч
            """)
            date = datetime.now() + timedelta(days=1)
            print(date)
            h = datetime.now().strftime('%H')
            m = datetime.now().strftime('%M')
            s = datetime.now().strftime('%S')
            sec_end = (24 + 9)*3600 - (((int(h)*60) + int(m))*60 +int(s))

            print(sec_end)
        elif time < "09:00:00":
            print("""дата = Дата
            время = время + 9ч
            """)
            date = datetime.now()
            print(date)
            h = datetime.now().strftime('%H')
            m = datetime.now().strftime('%M')
            s = datetime.now().strftime('%S')
            sec_end = ((int(h)+9)*60 + int(m))*60+int(s)
            # datetime.now() - timedelta(day)
        # time1h = datetime.datetime.strptime(time, "%H:%M:%S") - datetime.datetime.strptime("01:00:00",
        #                                                                                    "%H:%M:%S")  # -1 чвс
        # if datetime.datetime.now().strftime("%H:%M:%S"):
if __name__ == "__main__":
    # download()
    # download_one()
    # read_csv1()
    # read_csv2()
    # read_csv3()
    # read_csv4()
    test()
    # print(entera(search="74", documentDateTo='12.04.2022'))

