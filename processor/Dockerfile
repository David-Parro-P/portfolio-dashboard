FROM python:3.12-slim

WORKDIR /app
RUN pip install poetry
ENV PATH="/root/.local/bin:$PATH"
COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false
RUN poetry install --no-root
ENV PYTHONPATH=/app/src
COPY . .
EXPOSE 5000
CMD ["python", "src/app.py"]