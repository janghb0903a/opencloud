FROM nginx:1.27-alpine

WORKDIR /usr/share/nginx/html

ENV LANG=C.UTF-8

COPY site/ /usr/share/nginx/html/
COPY docker/40-env.sh /docker-entrypoint.d/40-env.sh

RUN chmod +x /docker-entrypoint.d/40-env.sh \
    && chmod -R a+rX /usr/share/nginx/html

EXPOSE 80
