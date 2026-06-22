FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund --legacy-peer-deps

FROM node:20-alpine AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ARG NEXT_PUBLIC_WS_URL=ws://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
# public/ may be empty — copy via a wildcard so missing dir doesn't fail the build
RUN mkdir -p ./public
COPY --from=build /app/public/. ./public/
EXPOSE 3000
CMD ["node", "server.js"]
