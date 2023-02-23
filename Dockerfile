FROM python:3.10.4-slim-buster
RUN mkdir -p /app
WORKDIR /app
COPY pip.conf /root/.pip/pip.conf
COPY requirements.txt /app
COPY . /app


EXPOSE 8001
RUN pip install -r /app/requirements.txt
CMD python main.py
