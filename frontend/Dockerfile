# Dev-oriented image running the Vite dev server. The shared package is
# resolved from ../packages/shared via the Vite alias, so the build context is
# the repo root (see docker-compose.yml).
FROM node:20-slim

WORKDIR /repo

# Install workspace deps using the root manifest + lockfile for cache reuse.
COPY package.json package-lock.json ./
COPY packages/shared/package.json packages/shared/package.json
COPY frontend/package.json frontend/package.json
RUN npm install

COPY . .

WORKDIR /repo/frontend
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
