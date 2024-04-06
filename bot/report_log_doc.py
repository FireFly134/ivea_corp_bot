# coding=UTF-8
#
#
from datetime import datetime
from typing import Any

import pandas as pd

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle

from sqlalchemy import create_engine

from work import ivea_metrika, working_folder

engine = create_engine(ivea_metrika)  # данные для соединения с сервером


def main(doc_id: str = "all") -> None:
    pdfmetrics.registerFont(
        TTFont("regular", working_folder + "Lora-Regular.ttf")
    )
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "regular"
    style = styles["Normal"]

    if doc_id == "all" or doc_id == "not_bild":
        if doc_id == "all":
            info: pd.DataFrame = pd.read_sql(
                """SELECT id, name, number_doc, date FROM documents
                WHERE doc_open = 'true' and doc_bild_done = 'true'
                ORDER BY id ASC;""",
                engine,
            )
        else:
            info = pd.read_sql(
                """SELECT id, name, number_doc, date FROM documents
                WHERE doc_bild_done = 'false'
                ORDER BY id ASC;""",
                engine,
            )
        list_num_doc = info["id"].to_list()
        info_log: pd.DataFrame = pd.read_sql(
            f"""SELECT t1.* FROM log_doc t1
                    JOIN (select doc_id, MAX(date_time) AS date_time
                        FROM log_doc
                        WHERE doc_id in (
{str(list_num_doc).replace('[', '').replace(']', '')})
                        GROUP BY doc_id) t2
                    USING (doc_id, date_time);""",
            engine,
        )
        document_title: str = "Отчёт записей по всем договорам."
        text_lines: list[list[str]] = [
            [
                f'Список событий по всем объектам \
{datetime.now().strftime("%d.%m.%Y %H:%M")}'
            ]
        ]
        text_lines.append([f"Количество событый: {len(info_log)}"])
        date_time: str = str(info_log["date_time"].to_list()[-1])[:16]
        text_lines.append([f"Дата последнего события: {date_time}"])
    else:
        info = pd.read_sql_query(
            f"""SELECT log_doc.*, documents.link, documents.number_doc,
            documents.date, documents.counterparty, documents.name,
            documents.short_name
            FROM log_doc INNER JOIN documents ON (log_doc.doc_id=documents.id)
            WHERE documents.id = '{doc_id}' ORDER BY log_doc.date_time ASC;""",
            engine,
        )
        document_title = (
            f'Отчёт записей по номеру договора {info.loc[0, "number_doc"]}.'
        )
        text_lines = [
            [
                f'Список событий по объекту \
{datetime.now().strftime("%d.%m.%Y %H:%M")}'
            ],
            [f'Ссылка на договор: {info.loc[0, "link"]}'],
            [
                f'ООО "ИВЕА" - {info.loc[0,"counterparty"]}, \
{info.loc[0,"number_doc"]} от {info.loc[0,"date"]} г.'
            ],
            [f'Условное название: {info.loc[0, "name"]}'],
            [f"Количество событий: {len(info)}"],
            [
                f'Дата последнего события: \
{str(info["date_time"].to_list()[-1])[:16]}'
            ],
        ]
    elements = list()

    txt = Table(text_lines, 190 * mm)  # Страница в ширину 210мм
    txt.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONT", (0, 0), (-1, -1), "regular"),
            ]
        )
    )
    elements.append(txt)
    elements.append(append_row([("#", "Дата", "Текст", "Имя")]))

    for i in range(len(info)):
        user_name = ""
        date_time = ""
        comment = ""
        text = ""

        if doc_id == "all" or doc_id == "not_bild":
            row_info_log = info_log[info_log["doc_id"] == info.loc[i, "id"]]
            text = f"{info.loc[i, 'number_doc']} от {info.loc[i, 'date']} г.\
            \nУсловное название: {info.loc[i, 'name']}\n\n"
            for idx, row in row_info_log.iterrows():
                comment = str(row["text"])
                user_name = str(row["user_name"])
                date_time = str(row["date_time"])[:16]
        else:
            comment = str(info.loc[i, "text"])
            user_name = str(info.loc[i, "user_name"])
            date_time = str(info.loc[i, "date_time"])[:16]

        if comment != "":
            text += comment

        elements.append(
            append_row(
                [
                    (
                        Paragraph(str(i + 1), style),
                        Paragraph(date_time, style),
                        Paragraph(text.replace("\n", "<br/>"), style),
                        Paragraph(user_name, style),
                    )
                ]
            )
        )

    doc = SimpleDocTemplate(
        working_folder + "report_log_doc.pdf",
        pagesize=A4,
        title=document_title,
        topMargin=10,
        leftMargin=10,
        rightMargin=10,
        bottomMargin=10,
        author="Ткачёв К.Ю.",
    )

    # write the document to disk
    doc.build(elements)


def append_row(info_data: list[tuple[Any, Any, Any, Any]]) -> Table:
    tblrow: Table = Table(
        info_data,
        (10 * mm, 33 * mm, 127 * mm, 35 * mm),
        splitInRow=1,
        emptyTableAction=True,
        normalizedData=1,
        spaceBefore=True,
        spaceAfter=True,
        longTableOptimize=True,
    )
    tblrow.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (1, -1), "CENTER"),
                ("ALIGN", (3, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.black),
                ("BOX", (0, 0), (-1, -1), 0.25, colors.black),
                ("FONT", (0, 0), (-1, -1), "regular"),
            ]
        )
    )
    return tblrow


if __name__ == "__main__":
    main()
