from datetime import datetime, timedelta

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)
from sqlalchemy import create_engine, insert

from work import test_url


SQL_ECHO = False
test_engine = create_engine(url=test_url, echo=SQL_ECHO)

meta_data_obj = MetaData()
meta_data_obj_user = MetaData()

doc_entera_1c_table = Table(
    "doc_entera_1c",
    meta_data_obj,
    Column("id", Integer, primary_key=True),
    Column("num_doc", String),
    Column("contragent", String),
    Column("date_doc", String, default="13.03.2024"),
    Column("sum", String),
    Column("link", String),
    Column("comment", String),
    Column("name_file", String),
    Column("delete", Boolean, default=False),
    Column("num_1c", String),
    Column("send_email", Boolean, default=False),
    Column("year", Integer),
    Column("inn", String),
)

documents_table = Table(
    "documents",
    meta_data_obj,
    Column("id", Integer, primary_key=True),
    Column("number_doc", String),
    Column("counterparty", String),
    Column("name", String),
    Column("scan", Integer, default="1"),
    Column("note", String),
    Column("date", String),
    Column("short_name", String),
    Column("link", String),
    Column("type_works", String),
    Column("project_doc_link", String),
    Column("type_of_building", String),
    Column("mail", String),
    Column("teg", String),
    Column("text_for_call", String),
    Column("doc_open", Boolean, default=True),
    Column("doc_bild_done", Boolean, default=True),
    Column("link_group", String),
    Column("subject_contract", String),
    Column("flag", Boolean, default=False),
    Column("num_act", String),
    Column("accomplishment", String),
    Column("flag_upd", Boolean, default=False),
    Column("send_sms_new_doc", Boolean, default=False),
)

# Table in Django

invoice_analysis_invoice_table = Table(
    "invoice_analysis_invoice",
    meta_data_obj,
    Column("id", Integer, primary_key=True),
    Column("date", DateTime),
    Column("number", String),
    Column("sum", Numeric),
    Column("pp_created", String),
    Column("payment_status", String),
    Column("entrance", String),
    Column("date_of_the_incoming_document", Date),
    Column("incoming_document_number", String),
    Column("comment", String),
    Column("nomenclature", Text),
    Column("amount", Float),
    Column("unit", String),
    Column("price", Numeric),
    Column("second_sum", Numeric),
    Column("vat_percent", Integer),
    Column("vat", Numeric),
    Column("total", Numeric),
    Column("info", String),
    Column("counterparty_id", Integer),
    Column("alias", String),
    Column("payment", String),
)

# invoice_analysis_contractinvoice_table = Table(
#     "invoice_analysis_contractinvoice",
#     meta_data_obj,
#     Column("id", Integer, primary_key=True),
#     Column("contract_id", Integer),
#     Column("amount", Float),
#     Column("second_sum", Numeric),
#     Column("vat", Numeric),
#     Column("total", Numeric),
#     Column("invoice_id", Integer),
# )

employee_cards_counterparty_table = Table(
    "employee_cards_counterparty",
    meta_data_obj,
    Column("id", Integer, primary_key=True),
    Column("title", String),
    Column("date_time", DateTime),
    Column("description", String),
    Column("group_k", String),
    Column("inn", String),
    Column("tel", String),
    Column("total", Float),
    Column("trade_name", String),
    Column("type_k", String),
    Column("url", String),
    Column("load_by_month", Float),
    Column("standard_deviation", Float),
)


doc_key_corp_table: Table = Table(
    "doc_key_corp",
    meta_data_obj_user,
    Column("id", Integer, primary_key=True),
    Column("a_key", String),
    Column("num_doc", String, default="0"),
    Column("user_id", BigInteger, unique=True, default=0),
    Column("data_time", String, default="0"),
    Column("name", String),
    Column("family_name", String),
    Column("access", Integer, default=0),
    Column("tel", String),
    Column(
        "birthday",
        DateTime,
    ),
    Column("position_at_work", String, default="0"),
)

birthday_table: Table = Table(
    "birthday",
    meta_data_obj_user,
    Column(
        "id_user", Integer, ForeignKey("doc_key_corp.id"), primary_key=True
    ),
    Column("birthday", Date),
    Column("verified", Boolean),
)


def drop_and_create_db(meta_data: MetaData = meta_data_obj) -> None:
    meta_data.drop_all(test_engine)
    meta_data.create_all(test_engine)


def add_insert_for_check(not_found: bool, delete: str) -> None:
    insert_doc_entera_1c_table = insert(doc_entera_1c_table).values(
        {
            "num_doc": "2403-250871-37788",
            "contragent": 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"',
            "sum": "6325.0",
            "link": "https://app.entera.pro/api/v1/documents/1148ffc5-543c-\
    4da6-9e6b-592b2e5f8fbd/file",
            "comment": "Валищево к11 КОС50 (237)",
            "name_file": "2403-250871-37788.pdf",
            "num_1c": "0000-000154",
            "send_email": True,
            "year": datetime.now().strftime("%Y"),
            "inn": "7722753969",
        }
    )
    insert_invoice_analysis_invoice_table = insert(
        invoice_analysis_invoice_table
    ).values(
        [
            {
                "date": "2024-03-12 19:06:47.000 +0300",
                "number": "0000-000154",
                "sum": "6325.00",
                "date_of_the_incoming_document": "2024-03-12",
                "incoming_document_number": "2403-250871-37788",
                "nomenclature": "DKC Маркер для кабеля сечением 0,5-1,5мм \
    символ - 8221,200шт MKSMS1",
                "amount": "1",
                "unit": "шт",
                "price": "186.67",
                "second_sum": "186.67",
                "info": delete,
                "total": "224.00",
                "counterparty_id": "1",
            },
            {
                "date": "2024-03-12 19:06:47.000 +0300",
                "number": "0000-000154",
                "sum": "6325.00",
                "date_of_the_incoming_document": "2024-03-12",
                "incoming_document_number": "2403-250871-37788",
                "nomenclature": "TDM КМН-11210 12А 230B/AC3 1НО SQ0708-0006",
                "amount": "10",
                "unit": "шт",
                "price": "490.83",
                "second_sum": "4908.33",
                "info": delete,
                "total": "5890.00",
                "counterparty_id": "1",
            },
            {
                "date": "2024-03-12 19:06:47.000 +0300",
                "number": "0000-000154",
                "sum": "6325.00",
                "date_of_the_incoming_document": "2024-03-12",
                "incoming_document_number": "2403-250871-37788",
                "nomenclature": "DKC Маркер для кабеля сечением 0,5-1,5мм \
    символ 0 200шт MKF0S1",
                "amount": "1",
                "unit": "шт",
                "price": "175.83",
                "second_sum": "175.83",
                "info": delete,
                "total": "211.00",
                "counterparty_id": "1",
            },
        ]
    )
    insert_employee_cards_counterparty_table = insert(
        employee_cards_counterparty_table
    )
    dict_param = {
        "title": 'ООО "ВСЕИНСТРУМЕНТЫ.РУ"',
        "date_time": "2022-05-18 15:00:00.000 +0300",
        "group_k": "Поставщики",
        "inn": "7722753969",
        "tota": 541710.03,
        "type_k": "Юридическое лицо",
        "load_by_mont": 0.25,
        "standard_deviation": 4384.865831216596,
    }
    with test_engine.connect() as conn:
        conn.execute(insert_invoice_analysis_invoice_table)
        conn.execute(insert_employee_cards_counterparty_table, dict_param)
        if not_found:
            conn.execute(insert_doc_entera_1c_table)
        conn.commit()


def add_insert_for_check_user_and_birthday() -> None:
    now = datetime.now()
    month_and_day = datetime(now.year, now.month, now.day).strftime("%m-%d")
    month_and_tomorrow_day = (now + timedelta(days=+1)).strftime("%m-%d")
    insert_doc_key_corp_table = insert(doc_key_corp_table).values(
        [
            {
                "a_key": "2341351",
                "user_id": 1234567890,
                "name": "Петр",
                "family_name": "Татаренко",
                "tel": "+7 904 999-99-99",
                "birthday": f"1990-{month_and_day} 10:00:00.000",
                "position_at_work": "Тестовый работник 1",
            },
            {
                "a_key": "657346",
                "user_id": 9876543210,
                "name": "Иван",
                "family_name": "Кирпичкин",
                "tel": "+7 999 888-77-66",
                "birthday": f"1994-{month_and_tomorrow_day} 10:00:00.000",
                "position_at_work": "Тестовый работник 2",
            },
        ]
    )
    insert_birthday_table = insert(birthday_table).values(
        [
            {
                "id_user": 1,
                "birthday": f"1990-{month_and_day}",
                "verified": True,
            },
            {
                "id_user": 2,
                "birthday": f"1994-{month_and_tomorrow_day}",
                "verified": True,
            },
        ]
    )

    with test_engine.connect() as conn:
        conn.execute(insert_doc_key_corp_table)
        conn.execute(insert_birthday_table)
        conn.commit()
