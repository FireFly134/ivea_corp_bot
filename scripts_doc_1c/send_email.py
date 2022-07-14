### эти библиотеки для отправки смс с доками на почту ###
import smtplib
import os
import mimetypes
from email import encoders
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
### эти библиотеки для отправки смс с доками на почту ###

from tkachev.setting import data_email

def send_email(list_file=[], text='', addressees=data_email["email_send"], subject = "Счёт в оплату", working_folder = '', server = ''):
    if server == '':
        server = smtplib.SMTP_SSL("smtp.yandex.ru") #Потключаемся к серверу яндекс.
        try:
            server.login(data_email["email"], data_email["password"])  # Пробуем залогиниться
        except Exception as err:
            return f"{err}\nОшибка при авторизации."
    try:
        msg = MIMEMultipart()
        msg["From"] = data_email["email"] # указываем свою почту в строке от кого.
        msg["To"] = addressees  # указываем кому отправить
        msg["Subject"] = subject # указываем тему письма
        if text:
            msg.attach(MIMEText(text)) # добавляем к письму текст
        if list_file != [] and working_folder != '':  # Проверяем, если лист с документами пуст или не указан путь то мы проходим мимо
            for file in os.listdir(working_folder):  #  в противном случае мы выбираем файлы которые нужно отправить и прикрепляем к сообщени.
                if file in list_file:
                    filename = os.path.basename(file)
                    ftype, encoding = mimetypes.guess_type(file)
                    file_type, subtype = ftype.split("/")
                    path = working_folder+file
                    # идет проверка на тип файла который будет прикреплен к письму.
                    if file_type == "text":
                        with open(path) as f:
                            file = MIMEText(f.read())
                    elif file_type == "image":
                        with open(path, "rb") as f:
                            file = MIMEImage(f.read(), subtype)
                    elif file_type == "audio":
                        with open(path, "rb") as f:
                            file = MIMEAudio(f.read(), subtype)
                    elif file_type == "application":
                        with open(path, "rb") as f:
                            file = MIMEApplication(f.read(), subtype)
                    elif file_type == "vnd.ms-excel":
                        with open(path, "rb") as f:
                            file = MIMEApplication(f.read(), subtype)
                    else:  #  Если не понимаем что за файл , пользуемся шаблоном и прикрепляем по стандарту.
                        with open(path, "rb") as f:
                            file = MIMEBase(file_type, subtype)
                            file.set_payload(f.read())
                            encoders.encode_base64(file)

                    file.add_header('content-disposition', 'attachment', filename=filename)
                    msg.attach(file)
        elif (list_file == [] and working_folder != '') or (list_file != [] and working_folder == ''):  # если что-то не так с ссылкой или со списком файлов то мне дадут об этом знать.
            return f"Документ не найден. list_file = {list_file} and working_folder = {working_folder}"
        server.sendmail(data_email["email"], addressees, msg.as_string()) # Отправляем сформировонное письмо
        return "Письмо с документом отправлено!"
    except Exception as _ex:
        return f"{_ex}\nОшибка при отправке письма."