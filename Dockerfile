FROM python:3.11-slim

WORKDIR /src
COPY . .
RUN pip install --no-cache-dir -e .

ENTRYPOINT ["python"]
