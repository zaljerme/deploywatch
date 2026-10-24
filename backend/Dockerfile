FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml .
COPY app ./app
RUN pip install --no-cache-dir .
COPY . .
RUN useradd --uid 10001 --create-home deploywatch
USER deploywatch
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
