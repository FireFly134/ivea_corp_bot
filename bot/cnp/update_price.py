# coding=UTF-8
#
#
import datetime
import json
from threading import Thread
from time import sleep
from typing import Any

import pandas as pd

# Без этой записи выдает ошибку по подключению к БД
# ModuleNotFoundError: No module named '_mysql'?
import pymysql

from sqlalchemy import create_engine

from .text import (
    next_main_begin,
    next_main_end,
    next_main_str_time_begin,
    next_main_str_time_end,
    table_h_to_jy,
    table_jy_to_w,
    table_standart_to_h,
    table_w_to_qg,
)
from .work import db, discount

pymysql.install_as_MySQLdb()
engine = create_engine(db, encoding="utf8")


def main() -> None:
    table_standatr: str = ""
    table_h: str = ""
    table_jy: str = ""
    table_w: str = ""
    table_qg: str = ""
    table_price: str = ""
    str_time: str = str(datetime.datetime.now().strftime("%d.%m.%Y, %H:%M"))
    with open(
        f"./ivea_corp/cnp/json_files/{datetime.date.today()}_data.json"
    ) as json_file:
        data = json.load(json_file)
    data_json = pd.DataFrame(data["data"]).fillna(
        "07.10.1994"
    )  # .sort_values(by='Ожидаемая дата поступления', ascending=False)
    data_json["datetime"] = pd.to_datetime(
        data_json["Ожидаемая дата поступления"], dayfirst=True
    )
    data_json = data_json.sort_values(by="datetime", ascending=True)
    exchange = data["rub"]
    info = pd.read_sql_query("SELECT * FROM price;", engine)
    list_write = []
    for item in data_json.itertuples(index=False):
        name = item[1]
        df = info[info["model"] == name]
        if not df.empty:
            for idx, row in df.iterrows():
                list_write.append(name)
                if "QG" in name:
                    break
                else:
                    text_name = create_text_name(name)
                if item[0] == "Будущие поставки":
                    availability = item[4]
                    in_reserve: str = str(int(item[3]) - int(item[4]))
                    expected_date_of_receipt_date = str(
                        datetime.datetime.strptime(item[5], "%d.%m.%Y")
                        - datetime.datetime.now()
                    ).split(" ")[0]
                    try:
                        if int(expected_date_of_receipt_date) > 0:
                            expected_date_of_receipt = f"{item[5]} (\
{int(expected_date_of_receipt_date) + 1})"
                        else:
                            expected_date_of_receipt = "В наличии"
                    except ValueError:
                        print(
                            str(
                                datetime.datetime.strptime(item[5], "%d.%m.%Y")
                                - datetime.datetime.now()
                            )
                        )
                        expected_date_of_receipt = item[5] + " (1)"
                else:
                    availability = item[4]
                    in_reserve = str(int(item[3]) - int(item[4]))
                    expected_date_of_receipt = "В наличии"
                if row["price"] != "по запросу":
                    price = float(
                        str(row["price"]).replace(",", ".").replace(" ", "")
                    ) * float(exchange)
                    price = price - (price * discount)  # Скидка 15%
                    price_text: str = (
                        "%.2f" % price
                    )  # А тут мы округляем до 2х чисел после запятой
                    price_text = "{0:,}".format(float(price_text)).replace(
                        ",", " "
                    )
                else:
                    price_text = "по запросу"
                if row["url"] is None:
                    url = search_url(name, info)
                else:
                    url = row["url"]
                engine.execute(
                    f"UPDATE price SET rub = '{price_text}' \
                    WHERE article = '{row['article']}'"
                )
                table_price += f'          tableNasosyWq.add([ "\
{row["article"]}", "<a href=\'{url}\'>{text_name}", "{availability}", "\
{in_reserve}", "{expected_date_of_receipt}", "по запросу" ]);\n'
                table = f'          tableNasosyWq.add([ "{row["article"]}", "\
{text_name}", "{availability}", "{in_reserve}", "{expected_date_of_receipt}", \
"по запросу", "<button class=\'table-nasosy-order\'>Сделать заказ</button>" \
]);\n'
                Thread(
                    target=page_update,
                    args=(
                        name,
                        table,
                        str_time,
                        exchange,
                        data_json,
                    ),
                ).start()
                Thread(
                    target=update_longtext,
                    args=(
                        name,
                        availability,
                        in_reserve,
                        expected_date_of_receipt,
                        price_text,
                        exchange,
                        data_json,
                    ),
                ).start()
    for i in range(len(info)):
        if info.loc[i, "model"] not in list_write:
            name = info.loc[i, "model"]
            if "QG" in name:
                break
            else:
                text_name = create_text_name(name)
            availability = "1"
            in_reserve = "0"
            expected_date_of_receipt = (
                str(
                    (
                        datetime.datetime.now() + datetime.timedelta(weeks=12)
                    ).strftime("%d.%m.%Y")
                )
                + " (84)"
            )
            if info.loc[i, "price"] != "по запросу":
                price = float(
                    str(info.loc[i, "price"]).replace(",", ".").strip()
                ) * float(exchange)
                price = price - (price * discount)  # Скидка 15%
                # А тут мы округляем до 2х чисел после запятой
                price_text = "%.2f" % price
                price_text = "{0:,}".format(float(price_text)).replace(
                    ",", " "
                )
            else:
                price_text = "по запросу"
            if info.loc[i, "url"] is None:
                url = search_url(name, info)
            else:
                url = str(info.loc[i, "url"])
            if str(info.loc[0, "rub"]) != price_text:
                engine.execute(
                    f"UPDATE price SET rub = '{price_text}' \
                    WHERE article = '{info.loc[i, 'article']}'"
                )
            table_price += f'          tableNasosyWq.add([ "\
{info.loc[i, "article"]}", "<a href=\'{url}\'>{text_name}", "\
{availability}", "{in_reserve}", "{expected_date_of_receipt}", \
"по запросу" ]);\n'
            table = f'          tableNasosyWq.add([ "\
{info.loc[i, "article"]}", "{text_name}", "{availability}", "{in_reserve}", "\
{expected_date_of_receipt}", "по запросу", "<button \
class=\'table-nasosy-order\'>Сделать заказ</button>" ]);\n'
            Thread(
                target=page_update,
                args=(
                    name,
                    table,
                    str_time,
                    exchange,
                    data_json,
                ),
            ).start()

            Thread(
                target=update_longtext,
                args=(
                    name,
                    availability,
                    in_reserve,
                    expected_date_of_receipt,
                    price_text,
                    exchange,
                    data_json,
                ),
            ).start()
    #########################################################
    # Заполняем Технические характеристики насосов марки WQ #
    #########################################################
    info_for_table = pd.read_sql_query(
        """SELECT price.model, price.article, table_pump_wq.flow,
            table_pump_wq.head, table_pump_wq.efficiency, table_pump_wq.power,
            table_pump_wq.motor_power, table_pump_wq.speed, price.url,
            table_pump_wq.weight, table_pump_wq.outlet_bore, price.price
        FROM price INNER JOIN table_pump_wq
        ON (price.model=table_pump_wq.model);""",
        engine,
    )
    for i in range(len(info_for_table)):
        model = str(info_for_table.loc[i, "model"])

        if info_for_table.loc[i, "url"] is None:
            url = search_url(model, info)
        else:
            url = f"{info_for_table.loc[i, 'url']}"

        write = f'          tableNasosyWq.add([ "<a href=\'{url}\'>{model}", "\
{info_for_table.loc[i, "flow"]}", "{info_for_table.loc[i, "head"]}", "\
{info_for_table.loc[i, "efficiency"]}", "{info_for_table.loc[i, "power"]}", "\
{info_for_table.loc[i, "motor_power"]}", "{info_for_table.loc[i, "speed"]}", "\
{info_for_table.loc[i, "outlet_bore"]}", "{info_for_table.loc[i, "weight"]}" \
]);\n'

        if "W(I)" in model:
            table_w += write
        elif "QG" in model:
            table_qg += write
        elif "JY" in model:
            table_jy += write
        elif "H" in model:
            table_h += write
        else:
            table_standatr += write

    #####################################################################
    # Определяем время, подставляем значение в шаблон и записываем в БД #
    #####################################################################
    introtext = next_main(
        table_standatr,
        table_h,
        table_jy,
        table_w,
        table_qg,
        table_price,
        str_time,
    )
    engine.execute(
        "UPDATE u0018321_default.m4szv_content \
        SET introtext = %s WHERE id = '1987';",
        (introtext,),
    )


def next_main(
    table_standatr: str,
    table_h: str,
    table_jy: str,
    table_w: str,
    table_qg: str,
    table_price: str,
    str_time: str,
) -> str:
    return str(
        next_main_begin
        + table_standatr
        + table_standart_to_h
        + table_h
        + table_h_to_jy
        + table_jy
        + table_jy_to_w
        + table_w
        + table_w_to_qg
        + table_qg
        + next_main_str_time_begin
        + str_time
        + next_main_str_time_end
        + table_price
        + next_main_end
    )


def next_main_old(
    table_standatr: str,
    table_h: str,
    table_jy: str,
    table_w: str,
    table_qg: str,
    table_price: str,
    str_time: str,
) -> str:
    ec = (
        """<!--------------------------------------------------------------
    >>> Старт: Слайдер
    --------------------------------------------------------------->
    <p class="cnp-slider">{loadmoduleid 285}</p>
    <!--------------------------------------------------------------
    <<< Конец: Слайдер
    --------------------------------------------------------------->

    <!--------------------------------------------------------------
    >>> Start: Таб презентация
    --------------------------------------------------------------->
    <p>{tab <strong>Презентация</strong>|blue}</p>

    <p>Компания «ИВЕА» является официальным дилером CNP в России \
(Сертификат вы найдете на вкладке <a class="nasosy-redirect" href="/nasosy-\
cnp/wq-pogruzhnye-elektronasosy-dlya-otvoda-stochnykh-vod?tab=documentation" \
tab-name="документация">«Документация»</a>) и специализируется на насосах для \
перекачивания сточных вод (погружные насосы)</p>

    <p>Мы предлагаем инжинириговые услуги по подбору насосов и осуществляем \
их продажу и послегарантийное обслуживание. </p>

    <p>На сайте представлена вся информация, необходимая для покупки насоса. \
Техническое описание, документация, перечень выпускаемых насосов, актуальный \
прайс лист с информацией по наличию.
    </p>

    <p>Вкладка <a class="nasosy-redirect" href="/nasosy-cnp/wq-pogruzhnye-\
elektronasosy-dlya-otvoda-stochnykh-vod?tab=desc" tab-name="описание">\
«Описание»</a> - основная информация по насосам марки WQ. Насосы данной марки \
выполняются в погружном исполнении и предназначены для перекачивания сточной \
воды (канализация, ливневка).</p>

    <em>На вкладке Описание вы найдете основную обзорную информацию по \
насосам марки дабл юкью. Какие бывают серии насосов и их технологические \
отличия. Области применения. Краткая характеристика конструкции позволит \
изучить особенности погружных насосов. Характеристика электродвигателя даст \
представление об этом важном элементе. Условия эксплуатации позволят \
правильно оценить возможности применения для конкретного объекта. Описание \
структуры маркировки насоса позволит быстро ориентироваться при выборе и \
заказе. Также на странице представлены демонстрационные видео. На первом \
видео демонстрируется работа режущего механизма насоса, установленного в \
стеклянный резервуар с водой. В резервуар бросают различные предметы в виде \
пленки, перчатки, пакеты, упаковку. Насос перекачивает жидкость, одновременно \
перемалывая эти предметы, что показывает его надежность при работе в реальных \
условиях при перекачивании сточных вод. На втором видео показана работа \
сальника, предотвращающего попадание воды в камеру электродвигателя. \
Демонстрируется конструкция сальника в три дэ модели насоса, а также показана \
работа на модели со стеклянными стенками.
    </em>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-desc.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-desc.mp3">Скачайте музыку</a>.
    </audio>
    <p>&nbsp;</p>
    <!-- Вкладка «Документы»
    <--==========================================================-->

    <p>Вкладка <a class="nasosy-redirect" href="/nasosy-cnp/wq-pogruzhnye-\
elektronasosy-dlya-otvoda-stochnykh-vod?tab=documentation" tab-name=\
"документация">«Документы»</a> - здесь вы можете скачать паспорта, инструкции \
по эксплуатации, сертификаты и другие файлы, необходимые для работы.</p>

    <em>На вкладке документация собраны документы, которые можно скачать. \
Во-первых это печатный каталог насосов дабл юкью, а также руководство по \
эксплуатации. Рекламный буклет с различными областями применения. В некоторых \
случаях требуется представление декларации о соответствии таможенного союза. \
Ее вы также можете скачать на этой странице. </em>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-docs.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-docs.mp3">Скачайте музыку</a>.
    </audio>
    <p>&nbsp;</p>
    <!-- Вкладка «Насосы WQ»
    <--==========================================================-->

    <p>Вкладка <a class="nasosy-redirect" href="/nasosy-cnp/wq-pogruzhnye-\
elektronasosy-dlya-otvoda-stochnykh-vod?tab=table-nasosy" tab-name="насосы\
-wq">«Насосы WQ»</a> - здесь представлен перечень всех насосов с \
основными характеристиками. Каждый насос можно открыть и просмотреть \
наличие и стоимость, технических характеристики, график и габаритный \
чертеж. На странице есть поиск и возможность выбора группы насосов \
(с режущим механизмом, высокого давления и др.)
    </p>

    <em>На вкладке насосы дабл юкью вы найдете техническую информацию по всем \
насосам. Расход и напор для каждой модели насоса указан в качестве \
оптимального, но может быть отличным от этих значений, в зависимости от \
ваших исходных данных и рабочей характеристики. Которую вы можете \
подробно изучить кликнув по модели насоса. Откроется дополнительная \
страница с основными характеристиками, рабочим графиком и габаритными \
размерами. Также вы найдете информацию по ка пэдэ насоса, его мощности, \
максимальному току и скорости вращения двигателя. Габаритные \
характеристики в таблице указаны только для диаметра напорного патрубка и \
весу. На странице вы можете воспользоваться поиском путем ввода \
произвольного запроса. В результате в таблице будут отображаться только \
те строки, в которых найдено соответствие вашему запросу. Вы можете также \
выбрать список по типу. Например насосы с режущим механизмом, для \
вмучивания или другие. Страница предназначена для представления всего \
перечня поставляемых насосов марки дабл юкью.
    </em>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-nasosy.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-nasosy.mp3">Скачайте музыку</a>.
    </audio>
    <p>&nbsp;</p>
    <!-- Вкладка «Прайс»
    <--==========================================================-->

    <p>Вкладка <a class="nasosy-redirect" href="/nasosy-cnp/wq-pogruzhnye-\
elektronasosy-dlya-otvoda-stochnykh-vod?tab=price" tab-name="прайс">\
«Прайс»</a> -  здесь представлена информация по наличию и стоимости \
насосов. Информация актуализируется в автоматическом режиме каждые 15 \
минут. Вы можете пользоваться этими данными как справочником и быть \
уверены, что информация актуальна. </p>

    <em>На вкладке прайс вы найдете информацию по наличию насосов и их \
стоимости. Актуальность информации подтверждается датой и временем, \
которые указаны выше таблицы. В таблице вы найдете артикул насоса и \
название насоса, дату ожидаемого поступления и стоимость. По наличию \
насосы указаны двумя цифрами. Это общее количество и количество \
зарезервированных насосов.  Дата ожидаемого поступления – это дата, \
когда партия насосов ориентировочно прибудет на центральный склад в \
город челябинск. Данная дата ориентировочная и может быть изменена на \
несколько дней. Зарезервированные насосы могут быть сняты с брони по \
отдельному запросу при стопроцентной оплате. Информация на сайте \
обновляется каждые 15 минут и поэтому всегда является актуальной. \
Наши менеджеры пользуются данной таблицей так же, как и потенциальные \
покупатели. </em>

<em>Поиск на странице работает по всему тексту и по любому произвольному \
запросу. Поэтому вы можете найти по артикулу, названию или по любым \
другим параметрам интересующий вас насос. </em>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-price.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-price.mp3">Скачайте музыку</a>.
    </audio>
    <!--------------------------------------------------------------
    <<< Close: Таб презентация
    --------------------------------------------------------------->

    <!--------------------------------------------------------------
    >>> Старт: Таб - Описание
    --------------------------------------------------------------->
    <p>{tab <strong>Описание</strong>|blue}</p>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-desc.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-desc.mp3">Скачайте музыку</a>.
    </audio>

    <p>Насосы серии WQ являются погружными канализационными (сточно-массными) \
центробежными насосами.</p>
    <p>Серия насосов WQ имеет в своем составе различные исполнения:</p>
    <ul>
      <li>• WQ(I) – классическое исполнение с рабочим колесом закрытого типа;\
      </li>
      <li>• WQX(I) – исполнение с вихревым рабочим колесом Vortex;</li>
      <li>• WQ-W и WQ-QG(I)– исполнение с режущим рабочим колесом;</li>
      <li>• WQ-H(I)– исполнение со спиральным полуоткрытым рабочим колесом;\
      </li>
      <li>• WQ-JY(I) – исполнение с перемешивающим механизмом;</li>
      <li>• WQD – исполнение небольших типоразмеров с однофазным питанием \
электродвигателя.</li>
    </ul>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Применение</h4>

    <ul>
      <li>• Жилищно-коммунальное строительство, сельское хозяйство, \
промышленное строительство;</li>
      <li>• Отвод канализационных стоков, промышленных стоков, дренаж \
затопленных котлованов и болотистой местности;</li>
      <li>• Горная промышленность, шахты и т.д.</li>
    </ul>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Конструкция</h4>

    <p>Насосные агрегаты состоят из двух частей: погружной герметичный \
электродвигатель и насосная часть. Эти две части разделены масляной камерой с \
системой из двух торцевых уплотнений (рабочая среда - масло, масло - \
электродвигатель). В масляной камере предусмотрено отверстие для \
осуществления контроля уровня масла и пополнения при необходимости. \
Смазывание верхнего торцевого уплотнения обеспечивается с помощью специальной \
конструкции маслоподъемника.
    </p>
    <p>В корпусе насоса реализован специальный воздушный клапан, позволяющий \
автоматически выпускать воздух из под торцевого уплотнения.</p>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Электродвигатель</h4>

    <p>Погружной герметичный электродвигатель. Охлаждение осуществляется за \
счет обтекания рабочей среды корпуса. Минимальный уровень перекачиваемой \
среды должен быть не ниже середины корпуса двигателя. Для обеспечения \
герметичности электродвигателя ввод кабеля питания осуществляется при помощи \
гермоввода, изготовленнного методом вулканизации.</p>
    <ul>
      <li>• Степень защиты: IP68;</li>
      <li>• Класс изоляции: F;</li>
      <li>• Стандартное напряжение 50 Гц: 1х220 В (WQD); 3x380 В.</li>
    </ul>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Условия эксплуатации</h4>

    <p>Насосы подходят для перекачивания сред с температурой до +40ºС, \
водородным показателем (pH) от 4 до 10 и плотностью не более 1200 кг/м3. \
Массовая доля содержания твердых механических примесей не должна \
превышать 2%.</p>
    <p>Максимальный диаметр твердых частиц не должен превышать значений \
свободного прохода частиц, указанного в технических характеристиках насосов.\
</p>
    <p>Для перекачивания рабочих сред с большим содержанием волокнистых \
включений рекомендуется использовать насосы серии WQ-W с режущим \
рабочим колесом.</p>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Маркировка</h4>
    <p>&nbsp;</p>

    <img src="images/sdagsadgsadgsadgsdag.png" alt=""/>

    <p>&nbsp;</p>
    <h4 class="article-h4-color">Видео</h4>

    <p>Демонстрация работы насоса серии WQ-W с режущим механизмом:</p>
    <iframe width="100%" height="482" src="https://www.youtube.com/embed/\
aBR9mYJnTa4" title="Работа канализационного насоса WQ-W(I) CNP с режущим \
механизмом" frameborder="0" allow="accelerometer; autoplay; clipboard-write; \
encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

    <p>&nbsp;</p>
    <p>Принцип работы маслоподьемника:</p>
    <iframe width="100%" height="482" src="https://www.youtube.com/embed/\
5yITVncXz_A" title="Смазка торцевого уплотнения" frameborder="0" \
allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; \
picture-in-picture" allowfullscreen></iframe>

    <!--------------------------------------------------------------
    <<< Конец: Таб - Описание
    --------------------------------------------------------------->

    <!--------------------------------------------------------------
    >>> Старт: Таб - Документация
    --------------------------------------------------------------->
    <p>{tab <strong>Документация</strong>|blue}</p>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-docs.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-docs.mp3">Скачайте музыку</a>.
    </audio>

    <p>Полный каталог для подбора насосов можно скачать по ссылке</p>

    <p>
      <a class="btn-nasosy-orange" href="/doc/Catalog_WQ_09.07.2022.pdf" \
download>Скачать каталог</a>
      <a class="btn-nasosy-orange" href="/doc/RE_WQ_07.07.2022.pdf" download>\
Руководство по эксплуатации</a>
    </p>
    <p>
      <a class="btn-nasosy-orange" href="/doc/Buklet_CNP_AIKON_WQ_SSC_Nasosy_\
dlya_otvoda_stochnyh_vod_2020_compressed.pdf" download>Области применения</a>
      <a class="btn-nasosy-orange" href="/doc/Deklaratsiya_nasosy_CNP_Nanfang_\
Pump_do_2026_goda.pdf" download>Декларация о соответствии</a>
    </p>

    <!--------------------------------------------------------------
    <<< Конец: Таб - Документация
    --------------------------------------------------------------->

    <!--------------------------------------------------------------
    >>> Старт: Таб - Насосы WQ
    --------------------------------------------------------------->
    <p>{tab <strong>Насосы WQ</strong>|blue}</p>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-nasosy.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-nasosy.mp3">Скачайте музыку</a>.
    </audio>

    <p>Технические характеристики насосов марки WQ</p>

    <div class="d-flex justify-content-between">
      <select class="filter-nasosy-wq">
        <option value="default" selected disabled>Фильтр по типу насоса\
</option>
        <option value="all">Показать все</option>
        <option value="standard-version">Стандартное исполнение</option>
        <option value="high-pressure">Высоконапорные</option>
        <option value="with-stirring-device">С устройством для взмучивания\
</option>
        <option value="with-cutting-mechanism">С режущим механизмом</option>
        <option value="with-cutting-mechanism-not-russia">С режущим \
механизмом (не поставляется в Россию)</option>
      </select>

      <form action="#" class="search-nasosy-wq">
        <input type="text" class="reset-input" placeholder="Поиск" required>
        <span class="search-nasosy-wq__close hide">×</span>
        <button class="reset-button" type="submit"><i class="fa fa-search">\
</i></button>
      </form>
    </div>

    <!-- Таблица: стандартное исполнение
    =============================================================-->
    <div class="table-nasosy-wq table-nasosy-wq_standard-version">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Модель</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Расход (м3/час)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Напор (м)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">КПД (%)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Мощность (кВт)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ток (А)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Скорость (об/мин)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Диаметр напорного патрубка</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Вес (кг)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( \
$(".table-nasosy-wq_standard-version") );

"""
        + table_standatr
        + """
          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!-- Таблица: высоконапорные
    =============================================================-->
    <div class="table-nasosy-wq table-nasosy-wq_high-pressure">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Модель</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Расход (м3/час)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Напор (м)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">КПД (%)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Мощность (кВт)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ток (А)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Скорость (об/мин)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Диаметр напорного патрубка</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Вес (кг)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( \
$(".table-nasosy-wq_high-pressure") );

"""
        + table_h
        + """
          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!-- Таблица: С устройством для взмучивания
    <--==========================================================-->
    <div class="table-nasosy-wq table-nasosy-wq_with-stirring-device">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Модель</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Расход (м3/час)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Напор (м)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">КПД (%)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Мощность (кВт)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ток (А)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Скорость (об/мин)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Диаметр напорного патрубка</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Вес (кг)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( \
$(".table-nasosy-wq_with-stirring-device") );

"""
        + table_jy
        + """
          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!-- Таблица: С режущим механизмом
    =============================================================-->
    <div class="table-nasosy-wq table-nasosy-wq_with-cutting-mechanism">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Модель</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Расход (м3/час)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Напор (м)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">КПД (%)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Мощность (кВт)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ток (А)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Скорость (об/мин)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Диаметр напорного патрубка</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Вес (кг)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( \
$(".table-nasosy-wq_with-cutting-mechanism") );

"""
        + table_w
        + """
          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!-- Таблица: С режущим механизмом (не поставляется в Россию)
    =============================================================-->
    <div class="table-nasosy-wq \
table-nasosy-wq_with-cutting-mechanism-not-russia">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Модель</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Расход (м3/час)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Напор (м)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">КПД (%)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Мощность (кВт)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ток (А)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Скорость (об/мин)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Диаметр напорного патрубка</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Вес (кг)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( \
$(".table-nasosy-wq_with-cutting-mechanism-not-russia") );

"""
        + table_qg
        + """
          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!--------------------------------------------------------------
    <<< Конец: Таб - Насосы WQ
    --------------------------------------------------------------->

    <!--------------------------------------------------------------
    >>> Старт: Таб - Table price
    --------------------------------------------------------------->
    <p>{tab <strong>Прайс</strong>|blue}</p>

    <!-- Аудио
    <--==========================================================-->
    <audio class="my-2" controls>
      <source src="./audio/audio-price.mp3" type="audio/mpeg">
      Тег audio не поддерживается вашим браузером.
      <a href="./audio/audio-price.mp3">Скачайте музыку</a>.
    </audio>

    <div class="d-flex align-items-center justify-content-between">
      <p>Цены и наличие по насосам актуальные на текущий момент """
        + str_time
        + """ (МСК)</p>

      <form action="#" class="search-nasosy-wq search_price">
        <input type="text" class="reset-input" placeholder="Поиск" required>
        <span class="search-nasosy-wq__close hide">×</span>
        <button class="reset-button" type="submit"><i class="fa fa-search">\
</i></button>
      </form>
    </div>

    <!-- Таблица: Price
    =============================================================-->
    <div class="table-nasosy-wq_price">
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Артикул</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Название</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Наличие</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">В резерве</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Ожидаемая дата поступления \
(осталось дней)</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <div class="table-nasosy-wq__col">
        <div class="table-nasosy-wq__title">Стоимость, руб.</div>
        <div class="table-nasosy-wq__content"></div>
      </div>
      <script>
        jQuery( function($)
        {
          /*--------------------------------------------------------------
          >> Добавить данные в таблицу
          --------------------------------------------------------------*/
          let tableNasosyWq = new TableNasosyWq( $(".table-nasosy-wq_price") );

"""
        + table_price
        + """

          /*--------------------------------------------------------------
          << Добавить данные в таблицу
          --------------------------------------------------------------*/
        });
      </script>
    </div>

    <!--------------------------------------------------------------
    <<< Конец: Таб - Table price
    --------------------------------------------------------------->
    {/tabs}"""
    )
    return ec


def create_text_name(name: str) -> str:
    text_name: str = f"Насос {name}"
    if "WQD" in name:
        text_name += " однофазные"
    elif "WQX" in name:
        text_name += " Vortex колесо"
    if "AC" in name:
        text_name += " с авт. трубной муфтой"
    else:
        text_name += " без авт. трубной муфты"
    if "W(I)" in name:
        text_name += ", с режущим механизмом"
    elif "QG" in name:
        text_name += ", с режущим механизмом (не поставляется в Россию)"
    if "JY" in name:
        text_name += ", с устройством для взмучивания"
    if "H" in name:
        text_name += ", высоконапорные"
    return text_name


def page_update(
    name: str,
    table: str,
    str_time: str,
    exchange: str,
    data: pd.DataFrame,
    price_bool: bool = True,
) -> None:
    count_info = pd.read_sql_query(
        f"SELECT COUNT(*), article FROM price \
        WHERE model = '{name}' AND url is NOT NULL;",
        engine,
    )
    if int(str(count_info.loc[0, "COUNT(*)"])) == 1:
        name2: str = ""
        if "W(I)" in name:
            name2 = name.replace("W(I)", "ACW(I)")
            text_name = create_text_name(name2)
        elif "H" not in name and "QG" not in name:
            name2 = name.replace("(I)", "AC(I)")
            text_name = create_text_name(name2)
        alias = str(count_info.loc[0, "article"]).lower()
        info = pd.read_sql_query(
            f"SELECT introtext FROM m4szv_content WHERE alias = '{alias}';",
            engine,
        )
        if name2 != "":
            info2 = pd.read_sql_query(
                f"SELECT * FROM price WHERE model = '{name2}';", engine
            )
            if not info2.empty:
                if info2.loc[0, "price"] != "по запросу":
                    price = float(
                        str(info2.loc[0, "price"])
                        .replace(",", ".")
                        .replace(" ", "")
                    ) * float(exchange)
                    price = price - (price * discount)  # Скидка 15%
                    # А тут мы округляем до 2х чисел после запятой
                    price_text = "%.2f" % price
                    price_text = "{0:,}".format(float(price_text)).replace(
                        ",", " "
                    )
                else:
                    price_text = "по запросу"
                if str(info2.loc[0, "rub"]) != price_text:
                    engine.execute(
                        f"UPDATE price SET rub = '{price_text}' \
                        WHERE article = '{info2.loc[0, 'article']}'"
                    )
                if name2 in data["Артикул"].to_list():
                    data = data[data["Артикул"] == name2]
                    for item in data.itertuples(index=False):
                        if item[0] == "Будущие поставки":
                            availability = item[4]
                            in_reserve = str(int(item[3]) - int(item[4]))
                            expected_date_of_receipt_date = str(
                                datetime.datetime.strptime(item[5], "%d.%m.%Y")
                                - datetime.datetime.now()
                            ).split(" ")[0]
                            try:
                                if int(expected_date_of_receipt_date) > 0:
                                    expected_date_of_receipt = f"{item[5]} (\
{int(expected_date_of_receipt_date) + 1})"
                                else:
                                    expected_date_of_receipt = "В наличии"
                            except ValueError:
                                print(
                                    str(
                                        datetime.datetime.strptime(
                                            item[5], "%d.%m.%Y"
                                        )
                                        - datetime.datetime.now()
                                    )
                                )
                                expected_date_of_receipt = item[5] + " (1)"
                        else:
                            availability = item[4]
                            in_reserve = str(int(item[3]) - int(item[4]))
                            expected_date_of_receipt = "В наличии"
                        table += f'          tableNasosyWq.add([ "\
{info2.loc[0, "article"]}", "{text_name}", "{availability}", "{in_reserve}", "\
{expected_date_of_receipt}", "по запросу", "<button \
class=\'table-nasosy-order\'>Сделать заказ</button>" ]);\n'

        introtext = str(info.loc[0, "introtext"])
        record_time = introtext.split(
            "<p>Цены и наличие по насосам актуальные на текущий момент "
        )[1].split("</p>")[0]
        introlist = introtext.split(record_time)
        introtext = f"{introlist[0]}{str_time} (МСК){introlist[1]}"
        if price_bool:
            record = introtext.split(
                "let tableNasosyWq = new TableNasosyWq( \
$('.table-nasosy-wq_price') );"
            )[1].split(
                "      /*--------------------------------------------------\
------------"
            )[
                0
            ]
        else:
            record = introtext.split(
                "let tableNasosyWq = new TableNasosyWq( \
$('.table-nasosy-wq') );"
            )[1].split("    });")[0]
        introlist = introtext.split(record)
        write_introtext = f"{introlist[0]}\n{table}\n{introlist[1]}"
        engine.execute(
            f"UPDATE m4szv_content SET introtext = %s \
            WHERE alias = '{alias}';",
            (write_introtext,),
        )


def update_longtext(
    name: str,
    availability: Any,
    in_reserve: str,
    expected_date_of_receipt: str,
    exchange: Any,
    data: pd.DataFrame,
) -> None:
    edfr = expected_date_of_receipt
    text = "Прайс:\nСтоимость без АТМ - по запросу.\n"
    if str(edfr) == "В наличии":
        text += f"- в наличии {availability} шт.\n"
    else:
        text += f"- в наличии нет.\n- в пути 1 шт. {edfr}\n"
    if str(in_reserve) == "0":
        text += "- в резерве нет.\n"
    else:
        text += f"- в резерве {in_reserve}шт.\n"
    name2 = ""
    if "W(I)" in name:
        name2 = name.replace("W(I)", "ACW(I)")
    elif "H" not in name and "QG" not in name:
        name2 = name.replace("(I)", "AC(I)")
    if name2 != "":
        info2 = pd.read_sql_query(
            f"SELECT * FROM price WHERE model = '{name2}';", engine
        )
        if not info2.empty:
            text += "Стоимость с АТМ - по запросу.\n"
            if name2 in data["Артикул"].to_list():
                data = data[data["Артикул"] == name2]
                collect = []
                for item in data.itertuples(index=False):
                    if item[0] == "Будущие поставки":
                        availability = item[4]
                        in_reserve = str(int(item[3]) - int(item[4]))
                        expected_date_of_receipt_date = str(
                            datetime.datetime.strptime(item[5], "%d.%m.%Y")
                            - datetime.datetime.now()
                        ).split(" ")[0]
                        try:
                            if int(expected_date_of_receipt_date) > 0:
                                edfr = f"{item[5]} (\
{int(expected_date_of_receipt_date) + 1})"
                            else:
                                edfr = "В наличии"
                        except ValueError:
                            print(
                                str(
                                    datetime.datetime.strptime(
                                        item[5], "%d.%m.%Y"
                                    )
                                    - datetime.datetime.now()
                                )
                            )
                            edfr = item[5] + " (1)"
                    else:
                        availability = item[4]
                        in_reserve = str(int(item[3]) - int(item[4]))
                        edfr = "В наличии"
                    collect.append(
                        {
                            "availability": availability,
                            "in_reserve": in_reserve,
                            "expected_date_of_receipt": edfr,
                        }
                    )
                availability_text = "- в наличии нет"
                availability = 0
                in_reserve_text = "- в резерве нет."
                on_the_way_text = "- в пути нет."
                one_on_the_way = True
                one_in_reserve = True
                for row in collect:
                    if str(row["expected_date_of_receipt"]) == "В наличии":
                        availability += int(row["availability"])
                        availability_text = f"- в наличии {availability} шт."
                    else:
                        if one_on_the_way:
                            on_the_way_text = f"- в пути \
{row['availability']} шт. {edfr}"
                            one_on_the_way = False
                        else:
                            on_the_way_text += f", {row['availability']} шт. \
{edfr}"
                    if str(row["in_reserve"]) != "0":
                        if one_in_reserve:
                            in_reserve_text = (
                                f"- в резерве {row['in_reserve']}шт."
                            )
                        else:
                            in_reserve_text = f", {row['in_reserve']}шт."
                text += f"""{availability_text}
{on_the_way_text}
{in_reserve_text}
"""
        engine.execute(
            f"UPDATE for_bot SET text = '{text}' WHERE model = '{name}';"
        )
        sleep(1)


def search_url(name: str, info: pd.DataFrame) -> str:
    if "AC" in name:
        name = name.replace("AC", "")
    df = info[info["model"] == name]
    if not df.empty:
        for idx, row in df.iterrows():
            if row["url"] is not None:
                return str(row["url"])
    return "#"


if __name__ == "__main__":
    main()
