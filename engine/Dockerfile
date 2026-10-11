FROM python:3.12-slim
WORKDIR /app
COPY packages/contracts /packages/contracts
COPY engine/requirements.txt .
RUN pip install --no-cache-dir -e /packages/contracts && pip install --no-cache-dir -r requirements.txt
COPY engine/app ./app
EXPOSE 8200
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8200"]
