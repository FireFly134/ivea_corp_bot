import asyncio
import json
import os
from datetime import datetime
from typing import Any

import requests

from send_email import send_email

from work import datas, header, space_id, working_folder_1c

from .check_path import check_root_path

s = requests.Session()
path = f"{working_folder_1c}send_file/"


def registration() -> None:
    link = "https://id.entera.pro/api/v1/login"
    print("registration")
    s.post(link, headers=header, json=datas)


def entera(search: str = "") -> str:
    text: str = ""
    try:
        url = "https://app.entera.pro/api/v1/documents"
        site = s.get(
            url,
            headers=header,
            params={
                "spaceId": space_id,
                "search": search,
                "documentType": ["OFFER", "NONSTANDARD", "UNKNOWN"],
            },
        )
        answer: dict[str, Any] = json.loads(site.text)
        list_file: list[str] = list()
        for i in range(len(answer["documents"])):
            answer_doc: dict[str, Any] = answer["documents"][i]
            if answer_doc["number"] == search:
                url = f"https://app.entera.pro/api/v1/documents/\
{answer_doc['id']}/file"
                print(url)
                asyncio.run(
                    entera_download(
                        url, answer["documents"][i]["pages"][0]["file"]["name"]
                    )
                )
                list_file += [
                    answer["documents"][i]["pages"][0]["file"]["name"]
                ]
                date: str = datetime.strptime(
                    answer_doc["date"], "%Y-%m-%d"
                ).strftime("%d.%m.%Y")
                text = f"Счёт № {search} от {date} на сумму \
{answer_doc['amount']} руб.\nКонтрагент: {answer_doc['supplier']['shortName']}"
                print(text)
        if list_file != []:
            print(
                send_email(
                    list_file,
                    text=text,
                    working_folder=path,
                )
            )
    except Exception as err:
        print(err)
        registration()
        entera(search)
    return text


async def entera_download(url: str, name_doc: str) -> None:
    global path
    if not os.path.isdir(path):
        os.mkdir(path)
    try:
        if not os.path.isfile(path + name_doc):
            registration()
            doc = s.get(url, headers=header)
            with open(path + name_doc, "wb") as file:
                file.write(doc.content)
    except Exception as err:
        print(err)


if __name__ == "__main__":
    check_root_path()
    entera()
