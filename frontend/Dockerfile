# WareFlow AI - Frontend Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies first for layer caching
COPY package*.json ./
RUN npm install

# Copy frontend source code
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Start Vite development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
