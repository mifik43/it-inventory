FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt . 
RUN pip install --no-cache-dir -r requirements.txt

COPY ./static/ ./static/
COPY ./templates/ ./templates/

COPY ./*.py .

expose 8000

CMD python ./app.py