# Usa un'immagine Python leggera
FROM python:3.10-slim

WORKDIR /app

# Installa dipendenze di sistema necessarie per compilare alcune librerie scientifiche
# (Spesso necessario per Scipy/Numpy su architetture specifiche)
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    libffi-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia e installa i requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice (anche se il volume lo sovrascriverà in dev, è buona norma)
COPY . .

# Espone la porta interna
EXPOSE 8000

# Il comando di avvio è definito nel docker-compose