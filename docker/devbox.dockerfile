FROM ubuntu:latest

RUN apt-get update
#RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-pip
RUN python3 -m pip install parse realpython-reader

COPY . /app
WORKDIR /app

RUN python3 -m pip install -r requirements-test.txt
