# coding=UTF-8
#
#
import os
### эти библиотеки для отправки смс с доками на почту ###
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
### эти библиотеки для отправки смс с доками на почту ###
import pandas as pd
from sqlalchemy import create_engine
import telegram
import logging

from work import *
from tkachev.send_email import send_email
from tkachev.setting import data_email
from control_1c import download

engine = create_engine(ivea_metrika)  # данные для соединия с сервером

bot = telegram.Bot(TELEGRAM_TOKEN)

logging.basicConfig(filename='information_email.log',
                     filemode='a',
                     level=logging.INFO,
                     format='%(asctime)s %(process)d-%(levelname)s %(message)s',
                     datefmt='%d-%b-%y %H:%M:%S')


def read():
    logging.info("<<============================================================>>")
    """df - dataframe у нас их 2 новый и старый => df = now, df2 = old version """
    """Принцип данноф функции.
    До выполнения функции мы переименовываем старый файл в олд и скачиваем новый файл.
    Открываем 2 файла в данной функции. 
        - Новый файл фильтруем колонку "Оплата" по ["Оплачен частично","Оплачен"]
        - Старый файл фильтруем колонку "Оплата" по 'Не оплачен'
    После чего, мы производим поиск строки из старого файла в новом => находим, то значит это то что нам надо...
    Далее данную информацию помещаем в словарь для дальнейшего сбора инфы... в дальнейшем притопаем к 1 договор = 1 письмо"""
    # mail = False
    # server = smtplib.SMTP_SSL("smtp.yandex.ru")
    # try:
    #     server.login(data_email["email"], data_email["password"])
    #     mail = True
    # except Exception:
    #     logging.error("Не верный логин или пароль, или почта не доступна.")
    df = pd.read_excel(f'{working_folder}Scheta2.xls')[["Контрагент","Сумма","Номер входящего документа","Комментарий","Номенклатура","Количество","Номенклатура.Единица","Оплата"]]
    df2 = pd.read_excel(f'{working_folder}Scheta_old.xls')[["Контрагент","Сумма","Номер входящего документа","Комментарий","Номенклатура","Количество","Номенклатура.Единица","Оплата"]]
    df = df[df['Оплата'].isin(["Оплачен частично","Оплачен"])]
    df2 = df2.loc[df2['Оплата'] == 'Не оплачен']
    data = {}
    for i in range(len(df2)):
        info_df = df[df["Контрагент"].isin([df2.loc[df2.index[i], "Контрагент"]])]
        info_df = info_df[info_df["Сумма"].isin([df2.loc[df2.index[i], "Сумма"]])]
        info_df = info_df[info_df["Номенклатура"].isin([df2.loc[df2.index[i], "Номенклатура"]])]
        info_df = info_df[info_df["Номер входящего документа"].isin([df2.loc[df2.index[i], "Номер входящего документа"]])]
        info_df = info_df[info_df["Количество"].isin([df2.loc[df2.index[i], "Количество"]])]
        info_df = info_df[info_df["Номенклатура.Единица"].isin([df2.loc[df2.index[i], "Номенклатура.Единица"]])]
        if len(info_df) != 0:
            try:
                info = pd.read_sql(f"SELECT short_name, mail FROM documents WHERE id in ({info_df['Комментарий'].item()});", engine)
            except Exception:
                info = pd.read_sql(f"SELECT short_name, mail FROM documents WHERE short_name in ({str(info_df['Комментарий'].item().split('¶')).replace('[', '').replace(']', '')});", engine)
            try:
                comment = str(info["short_name"].tolist()).replace("[", "").replace("]", "").replace("'", "")
                list_i = comment.split(', ')
                for doc_name in list_i:
                    if doc_name not in data:
                        data[doc_name] = {"text":[f'{df2.loc[df2.index[i], "Номенклатура"]} - {df2.loc[df2.index[i], "Количество"]} {df2.loc[df2.index[i], "Номенклатура.Единица"]}.'.replace(" nan","")],
                                                            "doc":[],"comment": ""}
                        if len(list_i) > 1:
                            data[doc_name]["comment"]=str(list_i)
                    else:
                        data[doc_name]["text"].append(f'{df2.loc[df2.index[i], "Номенклатура"]} - {df2.loc[df2.index[i], "Количество"]} {df2.loc[df2.index[i], "Номенклатура.Единица"]}.'.replace(" nan",""))
            except Exception as err:
                print(err)
                logging.info(err)
    for k in data.keys():
        print(k)
        try:
            j=0
            sms=''
            for text in data[k]["text"]:
                j+=1
                sms += f"{j}) {text}\n"
            if len(data[k]["comment"]) > 1:
                sms +=f"\nКомментарий: данный список присутсвует {data[k]['comment'].replace('[','').replace(']','')}."
            subject = f"Оплаченные товары по {k}"
            # if mail:
                # send_email(server=server,text=sms, addressees="kostik55555@yandex.ru", subject=subject)
                # send_email(server=server,text=sms, addressees="info@ivea-water.ru", subject=subject)
                # for email_corp in data[k]["email"].split(";"):
                #     send_email(server=server,text=sms, addressees=email_corp, subject=subject)
                #     print('e-mail:',str(email_corp),' ... Good! Send E-mail!')
                #     logging.info(f'e-mail:{email_corp} ... Good! Send E-mail!')

        except Exception as err:
            text = f"information_email функция read ориентировочно 'ссылка' {err}"
            bot.send_message(chat_id=id_telegram["my"], text=text)

if __name__ == "__main__":
    # try:
    #     if os.path.exists(f'{working_folder}Scheta_old.xls'):
    #         os.remove(f'{working_folder}Scheta_old.xls')
    #     os.rename(f'{working_folder}Scheta2.xls', f'{working_folder}Scheta_old.xls')
    # except Exception:
    #     print("файл Scheta.xls не найден.")
    #     logging.info("файл Scheta.xls не найден.")
    download(name2 = 'Scheta2.xls')
    read()