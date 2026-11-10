# Adapted from the SciLifeLab Serve Streamlit reference profile:
# https://github.com/ScilifelabDataCentre/serve-app-template/blob/main/profiles/streamlit/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    USER=appuser \
    HOME=/home/appuser

RUN useradd -m -u 1000 "$USER"

WORKDIR $HOME/app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Core data processing, visualization and public aggregate CSV are all bundled.
COPY --chown=1000:1000 app/app.py app/data_processing.py app/charts.py ./
COPY --chown=1000:1000 app/data/ ./data/
COPY --chown=1000:1000 .streamlit/ ./.streamlit/

USER appuser
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3)" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true", "--browser.gatherUsageStats=false"]
