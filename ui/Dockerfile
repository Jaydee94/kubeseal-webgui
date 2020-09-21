FROM node:lts-alpine AS ui-build-stage
COPY . /ui
WORKDIR /ui
RUN npm install && npm run build

FROM nginx:stable-alpine as ui-production-stage
COPY --from=ui-build-stage /ui/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]