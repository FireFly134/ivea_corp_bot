import requests

from work import callapi_token, header


def call(user_tel: str, user_text: str) -> None:
    url: str = "https://callapi.comagic.ru/v4.0"
    # Определяет тип сообщения.
    # media - файл или tts - текст для услуги синтеза речи Text-to-Speech.
    type_mod: str = "tts"
    data: dict[
        str, str | int | dict[str, str | int | dict[str, str | int]]
    ] = {
        "jsonrpc": "2.0",
        "method": "start.informer_call",
        "id": "req1",
        "params": {
            "access_token": callapi_token,
            "virtual_phone_number": "74951511175",
            "external_id": "34rty567",
            "direction": "in",
            "dialing_timeout": 120,
            "contact": user_tel,
            "contact_message": {"type": type_mod, "value": user_text},
        },
    }
    requests.post(url, headers=header, json=data)
