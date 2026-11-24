FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src src
COPY api api
COPY monitoreo monitoreo
ENV PYTHONPATH=/app OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8000"]
