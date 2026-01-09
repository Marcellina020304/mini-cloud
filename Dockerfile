FROM python:3.10-slim

WORKDIR /app

# salin requirement dulu agar cache pip lebih efisien
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# salin seluruh app
COPY app/ /app/

EXPOSE 5000

# jalankan gunicorn (lebih stabil di container)
CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
