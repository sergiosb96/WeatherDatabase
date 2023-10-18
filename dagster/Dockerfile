FROM python:3.9-slim-buster

RUN apt-get update && \
    apt-get install -y default-libmysqlclient-dev libmariadb-dev gcc pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV DAGIT_PREFERRED_NETWORK_INTERFACE localhost
ENV VIRTUAL_ENV=/venv
ENV DAGSTER_HOME=/dagster_home

RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN mkdir $DAGSTER_HOME

WORKDIR /

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

WORKDIR /my-dagster-project
RUN pip install -e ".[dev]"

EXPOSE 3000

CMD ["dagster", "dev", "-h", "0.0.0.0"]
