import requests
from setting import header,callapi_token

def call(user_tel,user_text):
    url = "https://callapi.comagic.ru/v4.0"
    type = "tts" # Определяет тип сообщения. media - файл или tts - текст для услуги синтеза речи Text-to-Speech.
    data = {
          "jsonrpc": "2.0",
          "method": "start.informer_call",
          "id": "req1",
          "params": {
                       "access_token": callapi_token,
            "virtual_phone_number": "Ваш номер телефона выданный оператором",
            "external_id": "Ваш ID",
            "direction": "in",
            "dialing_timeout": 120,
            "contact": user_tel,
            "contact_message":
            {
              "type": type,
              "value":user_text
            }}}
    requests.post(url, headers=header, json=data)