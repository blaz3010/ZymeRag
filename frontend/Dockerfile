# ---- Frontend Dev Container ----
FROM node:20-slim

WORKDIR /app

# Install dependencies first (cached layer)
COPY package.json package-lock.json ./
RUN npm ci

# Copy source code
COPY . .

EXPOSE 5173

# Run Vite dev server (host=true already set in vite.config.js)
CMD ["npm", "run", "dev"]
