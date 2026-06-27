FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

RUN useradd app && chown -R app:app /code
USER app

ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "app.main:app", "--access-logfile", "-", "--error-logfile", "-", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]