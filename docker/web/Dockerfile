FROM node:22-alpine

WORKDIR /app

COPY package.json package-lock.json ./
COPY apps/web/package.json ./apps/web/package.json
RUN npm ci

COPY apps/web ./apps/web

EXPOSE 3000

CMD ["npm", "--workspace", "apps/web", "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "3000"]
