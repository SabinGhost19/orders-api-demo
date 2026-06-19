FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN addgroup --system --gid 10001 appgroup \
    && adduser --system --uid 10001 --ingroup appgroup --home /app appuser

COPY requirements.txt .
# Install via pip — intentionally fetches the pinned-vulnerable versions.
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .

RUN chown -R 10001:10001 /app
USER 10001:10001
CMD ["python", "main.py"]
