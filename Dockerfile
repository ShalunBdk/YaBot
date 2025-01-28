FROM python:3.11.10-alpine

WORKDIR /app

COPY ./src .
RUN pip install -r requirements.txt

CMD [ "python", "/src/main.py"]
