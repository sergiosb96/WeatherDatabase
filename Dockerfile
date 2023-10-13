FROM python:3.9.16-slim-buster

RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev libmariadb-dev gcc pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


WORKDIR /

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

ENV FLASK_APP=main.py
ENV FLASK_ENV=production

CMD gunicorn --config gunicorn_config.py main:app