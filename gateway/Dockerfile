FROM python:3.12-slim
WORKDIR /app
COPY packages/contracts /packages/contracts
COPY gateway/requirements.txt .
RUN pip install --no-cache-dir -e /packages/contracts && pip install --no-cache-dir -r requirements.txt
COPY gateway/app ./app
RUN mkdir -p /data/vector
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
