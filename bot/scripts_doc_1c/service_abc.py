import pandas as pd

from sqlalchemy import create_engine

from work import web_django

engine_django = create_engine(web_django)


def main(inn: str) -> tuple[str, str]:
    info_counterparty: pd.DataFrame = pd.read_sql(
        "SELECT * FROM employee_cards_counterparty;", engine_django
    )
    choice_counterparty = info_counterparty[info_counterparty["inn"] == inn]
    if not choice_counterparty.empty:
        title = str(choice_counterparty["title"].to_list()[0])
        counterparties_data: list[dict[str, str]] = []
        for idx, row in info_counterparty.iterrows():
            dict_x: dict[str, str] = {
                "title": str(row["title"]),
                "tableType": "🟥",
            }
            if row["total"] != "":
                dict_x.update({"total": str(row["total"])})
            else:
                dict_x.update({"total": "0"})
            counterparties_data.append(dict_x)

        # Сортируем список counterpartiesData по полю 'total'
        # в порядке убывания
        sorted_cd: list[dict[str, str]] = sorted(
            counterparties_data, key=lambda x: x["total"], reverse=True
        )

        # Рассчитываем сумму 'total' в списке
        total_sum: float = sum(
            float(counterparty["total"]) for counterparty in sorted_cd
        )

        total_percent: float = 0.0

        # Обновляем значения 'tableType' в соответствии с условиями
        for counterparty in sorted_cd:
            curr_total: float = float(counterparty["total"])

            curr_percent = (curr_total * 100) / total_sum
            total_percent += curr_percent

            if total_percent < 80:
                counterparty["tableType"] = "🟩"
            elif total_percent < 95:
                counterparty["tableType"] = "🟨"
            if title in str(counterparty["title"]):
                return (
                    counterparty["tableType"],
                    f"""{'{:,}'.format(
                        round(
                            float(counterparty['total']), 2
                        )
                    )}""".replace(
                        ",", "\u00A0"
                    ).replace(
                        ".", ","
                    ),
                )
    return ("", "0,00")


if __name__ == "__main__":
    tableType, total = main("7716829024")
    print(tableType)
    print(total)
