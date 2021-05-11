FROM python:3.9.4-slim-buster

WORKDIR /usr/src/app
COPY . /usr/src/app
COPY ./env_sample.json /usr/src/app/env.json

RUN pip install --upgrade pip
RUN pip install -r requirements.txt
