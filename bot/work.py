import os

test_url = "postgresql://test:test@test-db:5432/test_db"

login = os.getenv("POSTGRES_USER", "")
ip_server = os.getenv("POSTGRES_HOST", "")
port = os.getenv("POSTGRES_PORT", "")
name_db = os.getenv("POSTGRES_DB", "")
PASSWD_DB = os.getenv("POSTGRES_PASSWORD")
if PASSWD_DB is not None:
    url_engine = f"postgresql://{login}:{PASSWD_DB}@{ip_server}:\
{port}/{name_db}"
else:
    url_engine = test_url

ivea_metrika = url_engine
web_django = url_engine

TELEGRAM_TOKEN: str = str(os.getenv("TELEGRAM_TOKEN_CORP"))
y_token: str = str(os.getenv("Y_TOKEN"))
callapi_token: str = str(os.getenv("CALLAPI_TOKEN"))
space_id: str = str(os.getenv("SPACE_ID"))

working_folder: str = "./"
working_folder_1c: str = f"{working_folder}files_doc_1c/"

id_telegram: dict[str, int | str] = {
    "OK": 232749605,  # -1001378825774#- test group #943180118 #-my
    "Pavel": 82284371,
    "Andrei": 456335434,
    "my": 943180118,
    "Boss": 232749605,
    "supply": 1808145530,
    "Mihail": 1726499460,
    "test_group": "-1001378825774",
}

numbers_telephone: list[str] = [
    "89253538733",
    "89264942722",
]  # Андрей Дмитриевич, Бухгалтерия

datas: dict[str, str] = {
    "login": "info@ivea-water.ru",
    "password": str(os.getenv("CONTROL_1C_DATAS_PASSWD")),
}
header: dict[str, str] = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:86.0) \
Gecko/20100101 Firefox/86.0"
}
data_email: dict[str, str] = {
    "email": "autosserviceivea@yandex.ru",
    "password": str(os.getenv("EMAIL_PASSWORD")),
    "email_send": "102@ivea-water.ru",  # "info@ivea-water.ru"#
}
datas2: dict[str, str] = {
    "login": "autosserviceivea@yandex.ru",
    "password": str(os.getenv("EMAIL_PASSWORD")),
}
