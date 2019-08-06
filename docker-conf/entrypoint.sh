#!/bin/sh
sed -i -e "s/<<LISTEN_PORT>>/${LISTEN_PORT}/g" /etc/nginx/conf.d/flask-nginx.conf
/usr/bin/supervisord --nodaemon --configuration /etc/supervisord.conf
