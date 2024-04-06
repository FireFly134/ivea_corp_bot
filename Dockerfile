FROM python:3.11-alpine

ENV PYTHONFAULTHANDLER=1 \
     PYTHONUNBUFFERED=1 \
     PYTHONDONTWRITEBYTECODE=1

WORKDIR /usr/local/app

RUN pip install pipenv
COPY ./Pipfile* ./

RUN pipenv install --system --dev --deploy


COPY ./ ./
CMD ["python", "bot/ivea_corp_bot_v3.py"]