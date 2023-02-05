#Deriving Python 3.9 image
FROM python:3.9

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

ENTRYPOINT ["python", "src/ticket_sms_alert.py"]
