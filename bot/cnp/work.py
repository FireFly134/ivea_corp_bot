import os

data_email: dict[str, str] = {
    "email": "autosserviceivea@yandex.ru",
    "password": str(os.getenv("EMAIL_PASSWORD")),
    "email_send": "info@ivea-water.ru",
    # "kostik55555@yandex.ru"#"102@ivea-water.ru"#
}

db: str = str(os.getenv("IVEA_WEBSITE"))

discount: float = 0.15  # скидка в итоге будет 15%
