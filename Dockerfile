From python:3

COPY . .
RUN pip install -r requirements.txt

ENTRYPOINT ["python3","morePing.py"]