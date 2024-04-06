from datetime import datetime, timedelta

import birthday

from models import (
    add_insert_for_check_user_and_birthday,
    drop_and_create_db,
    meta_data_obj_user,
    test_engine,
)

from pytest import mark

birthday.engine = test_engine

now = datetime.now()
tomorrow_day = now + timedelta(days=+1)
month_name_today = birthday.month_name[int(now.strftime("%m"))]
month_name_tomorrow_day = birthday.month_name[int(tomorrow_day.strftime("%m"))]


@mark.parametrize(
    "find, results, result_dict",
    [
        [
            True,
            f"{now.strftime('%d')} {month_name_today} - Татаренко \
Петр (Тестовый работник 1)\n{tomorrow_day.strftime('%d')} \
{month_name_tomorrow_day} - Кирпичкин Иван (Тестовый работник 2)\n",
            {
                1234567890: "🎊🎉🎂 Сегодня свой день рождения отмечает \
Татаренко Петр (Тестовый работник 1)🎂🎉🎊",
                9876543210: "🎂 Завтра свой день рождения отмечает \
Кирпичкин Иван (Тестовый работник 2) 🎂",
            },
        ],
        [False, "", {}],
    ],
)
def test_finder(find: bool, results: str, result_dict: dict[int, str]) -> None:
    drop_and_create_db(meta_data=meta_data_obj_user)
    if find:
        add_insert_for_check_user_and_birthday()
    begin_text = ""
    res_list, dict_text = birthday.finder(begin_text=begin_text, testing=True)
    assert res_list == results and dict_text == result_dict
