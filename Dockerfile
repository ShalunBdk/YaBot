FROM python:3.11.10-alpine

WORKDIR /app

COPY ./src .
RUN pip install -r requirements.txt

RUN echo 1

CMD [ "python", "/app/main.py"]
