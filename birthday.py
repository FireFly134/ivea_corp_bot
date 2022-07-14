# coding=UTF-8
#
#
import pandas as pd
import logging
from datetime import datetime, timedelta
import telegram


from work import *
from sqlalchemy import create_engine

logging.basicConfig(filename=working_folder + 'birthday.log',
                    filemode='a',
                    level=logging.INFO,
                    format='%(asctime)s %(process)d-%(levelname)s %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S')

bot = telegram.Bot(TELEGRAM_TOKEN)

engine = create_engine(ivea_metrika)  # данные для соединия с сервером

def finder():
    now = datetime.now()
    time = datetime(now.year,now.month, now.day).strftime('%m-%d')# now
    time2 = (now + timedelta(days=+1)).strftime('%m-%d')# +1 day
    birthday_list = "В этом месяце дни рождения у следующих людей:\n"
    month_name = {
        "1": "Января",
        "2": "Февраля",
        "3": "Марта",
        "4": "Апреля",
        "5": "Мая",
        "6": "Июня",
        "7": "Июля",
        "8": "Августа",
        "9": "Сентября",
        "10": "Октября",
        "11": "Ноября",
        "12": "Декабря"
    }
    info = pd.read_sql(f"SELECT * FROM doc_key_corp", engine)# WHERE day ='{time}' or day ='{time2}' or day ='{time3}')
    for i in range(len(info)):
        text=''
        if int(now.strftime('%d')) == 1: #срабатывает каждый первый день месяца и отправляет лист
            if int(info.loc[i, "birthday"].strftime('%m')) == int(now.strftime('%m')):
                birthday_list += f"{str(info.loc[i, 'birthday'].strftime('%d'))} {month_name[str(info.loc[i, 'birthday'].strftime('%m'))]} - {info.loc[i, 'family_name']} {info.loc[i, 'name']} ({info.loc[i, 'position_at_work']})\n"
        if info.loc[i, "birthday"].strftime('%m-%d') == time:
            text=f"🎊🎉🎂 Сегодня свой день рождения отмечает {info.loc[i, 'family_name']} {info.loc[i, 'name']} ({info.loc[i, 'position_at_work']})🎂🎉🎊"
            logging.info(f"Cегодня свой день рождения отмечает {info.loc[i, 'family_name']} {info.loc[i, 'name']} ({info.loc[i, 'position_at_work']})")
        elif info.loc[i, "birthday"].strftime('%m-%d') == time2:
            text=f"🎂 Завтра свой день рождения отмечает {info.loc[i, 'family_name']} {info.loc[i, 'name']} ({info.loc[i, 'position_at_work']}) 🎂"
            logging.info(f"Завтра свой день рождения отмечает {info.loc[i, 'family_name']} {info.loc[i, 'name']} ({info.loc[i, 'position_at_work']})")
        if text != '':
            for j in range(len(info)):
                if int(info.loc[j, "user_id"]) > 0:
                    try:
                        if info.loc[i, "user_id"] != info.loc[j, "user_id"]:
                            logging.info(f'chat_id={info.loc[j, "user_id"]} - "{info.loc[j, "name"]} {info.loc[j, "family_name"]}", text={text}))')
                            bot.send_message(chat_id=int(info.loc[j, "user_id"]), text=text)
                        elif info.loc[j, "birthday"].strftime('%m-%d') == time:
                            logging.info("🎊🎉🎂 С днём рождения!!! 🎂🎉🎊")
                            bot.send_message(chat_id=info.loc[j,"user_id"], text="🎊🎉🎂 С днём рождения!!! 🎂🎉🎊")
                    except Exception:
                        logging.info(f"chat_id={int(info.loc[j,'user_id'])}")
    if birthday_list != "В этом месяце дни рождения у следующих людей:\n":
        logging.info(birthday_list)
        bot.send_message(chat_id=Boss, text=birthday_list)
        bot.send_message(chat_id=Pavel, text=birthday_list)
        bot.send_message(chat_id=my, text=birthday_list)

def send_working():
    info = pd.read_sql(f"SELECT * FROM user_worker_key_corp;", engine)
    for i in range(len(info)):
        try:
            bot.send_message(chat_id=str(info.loc[i,'user_id']), text="Выберите пункт \"Транслировать геопозицию\" и укажите в течение 8 часов")
        except Exception:
            logging.info(f"Не смог отправить смс {info.loc[i,'user_id']}")

if __name__ == '__main__':
    finder()
    if datetime.now().strftime('%w') != '6' and datetime.now().strftime('%w') != '0':# If it's not a weekend, we should ask
        send_working()