import json
import datetime

import requests

from tkachev.send_email import send_email
from work import *

s = requests.Session()

def registration():
    link = 'https://id.entera.pro/api/v1/login'
    print("logging")
    s.post(link, headers=header, json=datas)

def entera(search=''):
    try:
        url = f"https://app.entera.pro/api/v1/documents"
        site = s.get(url, headers=header, params={'spaceId': "ВАШ spaceId", "search": search, "documentType": ["OFFER","NONSTANDARD","UNKNOWN"]})
        answer = json.loads(site.text)
        list_file = []
        for i in range(len(answer['documents'])):
            if answer['documents'][i]['number'] == search:
                url = f"https://app.entera.pro/api/v1/documents/{answer['documents'][i]['id']}/file"
                print(url)
                entera_download(url, answer['documents'][i]['pages'][0]['file']['name'])
                list_file += [answer['documents'][i]['pages'][0]['file']["name"]]
                text = f"Счёт № {search} от {datetime.datetime.strptime((answer['documents'][i]['date']), '%Y-%m-%d').strftime('%d.%m.%Y')} на сумму {answer['documents'][i]['amount']} руб.\nКонтрагент: {answer['documents'][i]['supplier']['shortName']}"
                print(text)
        if list_file != []:
            print(list_file)
            print(send_email(list_file, text=text, working_folder="\"))
    except Exception as err:
        print(err)
        registration()
        entera(search)
def entera_download(url, name_doc):
    try:
        doc = s.get(url, headers=header)
        if '"result":false' in doc.text and '"errorMessage":"Пользователь не аутентифицирован."' in doc.text:
            registration()
            entera_download(url, name_doc)
        with open(f"{working_folder}send_file/{name_doc}", "wb") as file:#scripts_doc_1c/
            file.write(doc.content)
    except Exception as err:
        print(err)
        # registration()
        # entera_download(url, name_doc)

if __name__ == "__main__":
    pass
    # entera("498/1")
    # entera("485/1")