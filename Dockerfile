# Dockerfile -- BCG pricing dashboard (read-only Flask) pa Azure App Service
# Monster: MASTER_AZURE §4 (python-slim, non-root, ingen lokal Docker -- byggs
# av ACR Tasks). Byggkontext = repo-roten; .dockerignore slapper ENDAST
# orchestration/ + requirements (AZ.3: verifierad mot faktisk struktur).
# Developer: Jens Palmo (Senior Business Analyst, Evidensia Djursjukvard AB)
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY orchestration/ orchestration/
RUN useradd -m appuser && chown -R appuser /app
USER appuser
ENV PRICINGMODEL_AUTH=key PYTHONUNBUFFERED=1
EXPOSE 8000
# gunicorn importerar app-modulen -> app.run() under __main__ kors aldrig;
# sys.path-bootstrappen i app.py loper vid import, sa blob/story hittas.
CMD ["gunicorn", "-b", "0.0.0.0:8000", "--chdir", "orchestration/webapp", "--timeout", "120", "--keep-alive", "75", "app:app"]
