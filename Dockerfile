# Déploiement hors Streamlit Cloud (Render, Railway, Fly.io, Hugging Face Spaces,
# Scaleway, etc.). Voir DEPLOY_ALTERNATIF.md.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HYMPYR_DATA_DIR=/tmp/hympyr

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app.py script.py ./

# Moindre privilège : le conteneur ne tourne pas en root.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser /app
USER appuser

# Le port est imposé par la plupart des hébergeurs via $PORT.
EXPOSE 8501
CMD ["sh", "-c", "exec streamlit run app.py --server.port=${PORT:-8501} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
