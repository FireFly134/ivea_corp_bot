import logging
import mimetypes
import os
import smtplib
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from work import data_email


def send_email(
    list_file: list[str],
    text: str = "",
    addressees: str | None = data_email["email_send"],
    subject: str = "Счёт в оплату",
    working_folder: str = "",
    server: Any = "",
) -> str:
    """Функция для отправки сообщений на почту."""
    if server == "":
        # Потключаемся к серверу яндекс.
        server = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
        try:
            server.login(
                str(data_email["email"]), str(data_email["password"])
            )  # Пробуем залогиниться
        except Exception as err:
            logging.error(f"Send_email(29-35)\nОшибка при авторизации.\n{err}")
            return f"{err}\nОшибка при авторизации."
    try:
        msg = MIMEMultipart()
        msg["From"] = data_email[
            "email"
        ]  # указываем свою почту в строке от кого.
        msg["To"] = addressees  # указываем кому отправить
        msg["Subject"] = subject  # указываем тему письма
        if text:
            msg.attach(MIMEText(text))  # добавляем к письму текст

        # Проверяем, если лист с документами пуст
        # или не указан путь то мы проходим мимо
        if list_file is not None and working_folder != "":
            # Мы выбираем файлы которые нужно отправить
            # и прикрепляем к сообщению.
            for file_name in list_file:
                if file_name in os.listdir(working_folder):
                    filename: str = os.path.basename(file_name)
                    ftype, encoding = mimetypes.guess_type(file_name)
                    # if okay ftype ~= application/pdf
                    if "/" in str(ftype):
                        file_type, subtype = str(ftype).split("/")
                    else:
                        file_type = "None"
                        subtype = "None"
                    path: str = working_folder + file_name
                    # идет проверка на тип файла,
                    # который будет прикреплен к письму.
                    if file_type == "text":
                        with open(path) as f:
                            file: Any = MIMEText(f.read())
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
                    else:
                        #  Если не понимаем что за файл,
                        # пользуемся шаблоном и прикрепляем по стандарту.
                        with open(path, "rb") as f:
                            file = MIMEBase(file_type, subtype)
                            file.set_payload(f.read())
                            encoders.encode_base64(file)

                    file.add_header(
                        "content-disposition", "attachment", filename=filename
                    )
                    msg.attach(file)
        elif (list_file == [] and working_folder != "") or (
            list_file != [] and working_folder == ""
        ):
            # если что-то не так с ссылкой или со списком файлов,
            # то мне дадут об этом знать.
            return f"Документ не найден. list_file = {list_file} \
and working_folder = {working_folder}"
        server.sendmail(
            str(data_email["email"]), addressees, msg.as_string()
        )  # Отправляем сформированное письмо
        return "Письмо с документом отправлено!"
    except Exception as _ex:
        logging.error(
            f"Send_email(38-104)\nОшибка при отправке письма.\n{_ex}"
        )
        return f"{_ex}\nОшибка при отправке письма."


if __name__ == "__main__":
    print(
        send_email(
            list_file=[
                "ИВЕА   аренда счет январь, реализ декабрь.pdf",
                "Счет на оплату № 24 от 10 января 2024 г.pdf",
                "Счет с печатью и подписью ООО New2-00003.pdf",
                "ЛЕРУА Счет № 80 от 09.01.2024г..docx",
            ],
            text="test",
            addressees="kostik55555@yandex.ru",
            working_folder="./ivea_corp/scripts_doc_1c/send_file/",
        )
    )
