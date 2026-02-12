# Usa Node.js (versione Alpine per leggerezza)
FROM node:20-alpine

WORKDIR /app

# Copia i file di configurazione delle dipendenze
COPY package*.json ./

# Installa le dipendenze
RUN npm install

# Copia il resto del codice
COPY . .

# Espone la porta standard di Vite
EXPOSE 5173

# Il comando di avvio è definito nel docker-compose