FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN apt-get update && apt-get install -y \
    python3-dev \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*
RUN  pip install --upgrade wheel
RUN  pip install --upgrade setuptools
RUN  pip install --upgrade pip
RUN  pip install -r requirements.txt

ARG GIT_TOKEN

RUN pip install --no-cache-dir \
    git+https://${GIT_TOKEN}@github.com/Ravian-Omni/ravian-auth
    
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]