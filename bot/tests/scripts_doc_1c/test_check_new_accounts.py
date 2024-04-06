# from datetime import datetime
from typing import Any

from models import add_insert_for_check, drop_and_create_db, test_engine

from pytest import mark

from scripts_doc_1c.check_new_accounts_class import CheckNewAccounts

drop_and_create_db()
cna: CheckNewAccounts = CheckNewAccounts(
    engine=test_engine, engine_web_django=test_engine
)


@mark.parametrize(
    "list1, list2, result",
    [
        [
            ["0000-000081", "0000-000082", "0000-000083", "0000-000084"],
            ["0000-000082", "0000-000084"],
            ["0000-000081", "0000-000083"],
        ],
        [
            ["0000-000081", "0000-000082", "0000-000083", "0000-000084"],
            ["0000-000082", "0000-000084", "0000-000083"],
            ["0000-000081"],
        ],
        [[], ["0000-000082", "0000-000084", "0000-000083"], []],
    ],
)
def test_get_list_unique_names(
    list1: list[str], list2: list[str], result: list[str]
) -> None:
    res = cna.get_list_unique_names(list1, list2)
    assert sorted(res) == sorted(result)


@mark.parametrize("not_found, result", [[True, []], [False, ["0000-000154"]]])
def test_find_new_accounts(not_found: bool, result: list[str]) -> None:
    add_insert_for_check(not_found, delete="")
    cna.get_info_doc_entera_1c()
    list_unique_num1c, info_new_accounts = cna.find_new_accounts()
    drop_and_create_db()
    assert (
        sorted(list_unique_num1c) == sorted(result)
        and info_new_accounts["number"].item() == "0000-000154"
    )


@mark.parametrize("delete, result", [["", []], ["Удален", ["0000-000154"]]])
def test_check_delete_accounts(delete: str, result: list[str]) -> None:
    add_insert_for_check(True, delete=delete)
    cna.get_info_doc_entera_1c()
    list_unique_num1c = cna.check_delete_accounts()
    drop_and_create_db()
    assert sorted(list_unique_num1c) == sorted(result)


# Не могу тестировать, так как нет ключа от entera (SPACE_ID)
# @mark.parametrize(
#     "row, result",
#     [
#         [
#             {
#                 "id": 3,
#                 "number": "0000-000154",
#                 "comment": "278,277,237,239",
#                 "date_of_the_incoming_document": datetime(2024, 3, 12),
#                 "incoming_document_number": "2403-250871-37788",
#                 "sum": 6325.0,
#                 "contragent_title": 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"',
#                 "contragent_inn": "7722753969",
#             },
#             {
#                 "num_1c": "0000-000154",
#                 "contragent": 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"',
#                 "inn": "7722753969",
#                 "date_doc": "12.03.2024",
#                 "sum": 6325.0,
#                 "link": "https://app.entera.pro/api/v1/documents/1148ffc5-\
# 543c-4da6-9e6b-592b2e5f8fbd/file",
#                 "comment": "",
#                 "name_file": "2403-250871-37788.pdf",
#                 "num_doc": "2403-250871-37788",
#                 "year": "2024",
#             },
#         ]
#     ],
# )
# def test_generation_text_sql(
#     row: dict[str, Any], result: dict[str, Any]
# ) -> None:
#     add_insert_for_check(False, delete="")
#     text_sql = cna.generation_text_sql("0000-000154", row)
#     compiled_query = text_sql.compile().params
#     drop_and_create_db()
#     assert compiled_query == result


@mark.parametrize(
    "row, result_msg, result_tel",
    [
        [
            {
                "date_doc": "13.03.2024",
                "contragent": 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"',
                "comment": "Валищево к11 КОС50 (237)",
                "sum": 6325.0,
            },
            """Счёт № 0000-000154 от 13.03.2024
Контрагент: 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"'
Комментарий: Валищево к11 КОС50 (237)
Сумма: 6325.0
🚫ОТМЕНА! НЕ ОПЛАЧИВАТЬ!🚫""",
            'ОТМЕНА!....... НЕ ОПЛАЧИВАТЬ!.......\
Контрагент: ...ООО "ВСЕИНСТРУМЕНТЫ.РУ".....\
сумма:...6325.0',
        ]
    ],
)
def test_generation_text_about_del(
    row: dict[str, Any], result_msg: str, result_tel: str
) -> None:
    add_insert_for_check(False, delete="")
    text_msg, text_tel = cna.generation_text_about_del("0000-000154", row)
    assert text_msg == result_msg and text_tel == result_tel


# Не могу тестировать, так как нет ключа от entera (SPACE_ID)
# @mark.parametrize(
#     "search, document_date_to, result_url, result_name_file",
#     [
#         [
#             "00003",
#             "09.01.2024",
#             "5b410266-17a2-4d5c-aae5-e8756a69320b/file",
#             "Счет с печатью и подписью ООО New2-00003.pdf",
#         ],
#         [
#             "п-0017",
#             "14.01.2024",
#             "34d10162-c959-4ab3-ae0b-ef0cf5db3022/file",
#             "Счет с печатью и подписью ООО New2-п-0017.pdf",
#         ],
#         [
#             "16508636/SA",
#             "16.01.2024",
#             "c78cf4d0-19a6-48b5-8bbc-6a46a361f315/file",
#             "16508636 ИВЕА.pdf",
#         ],
#         [
#             "2401-234632-88098",
#             "17.01.2024",
#             "721dc4c1-a40e-42d2-8df2-348083dd4bd6/file",
#             "2401-234632-88098-Счет на оплату.pdf",
#         ],
#     ],
# )
# def test_entera(
#     search: str,
#     document_date_to: str,
#     result_url: str,
#     result_name_file: str
# ) -> None:
#     url, name_file = cna.entera(search, document_date_to)
#     result_url = "https://app.entera.pro/api/v1/documents/" + result_url
#     assert url == result_url and name_file == result_name_file
