# Next.js UI container (for the local one-command dev stack).
# In production the UI is hosted on Vercel — see docs/DEPLOY.md.
FROM node:20-slim

WORKDIR /app

# NEXT_PUBLIC_* vars are inlined at build time, so pass the API URL as a build arg.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1/query
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npx", "next", "start", "-H", "0.0.0.0", "-p", "3000"]
