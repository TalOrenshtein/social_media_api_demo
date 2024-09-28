FROM python:3.12.4-slim-bullseye

RUN apt-get update\
    &&apt-get install -y --no-install-recommends --no-install-suggests \
    build-essential && apt install libpq-dev -y && pip install --no-cache-dir pip && apt-get clean

WORKDIR /server
COPY requirements.txt /server
RUN pip install --no-cache-dir -r requirements.txt 
COPY . /server

CMD ["uvicorn","server:app","--host","0.0.0.0","--port","8000"]
