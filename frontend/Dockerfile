# Imagen del frontend — construcción con Node, servicio con nginx
#
# Lo que se despliega son archivos estáticos: HTML, CSS y JavaScript ya
# compilados. Node solo hace falta para producirlos, de modo que no viaja en la
# imagen final. Esta queda en unos pocos megabytes y sin un intérprete que
# alguien pudiera aprovechar.
#
# `npm ci` y no `npm install`: respeta package-lock.json al pie de la letra. Con
# `install`, una dependencia transitiva podría subir de versión entre la
# construcción de un integrante y la de otro, y el fallo aparecería en el
# servidor sin que nada en el repositorio hubiera cambiado.

FROM node:22.12.0-alpine AS construccion

WORKDIR /construccion

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# `npm run build` ejecuta primero `tsc --noEmit`: si la interfaz deja de
# coincidir con los tipos del contrato, la construcción falla aquí en lugar de
# producir un paquete que se rompería en ejecución.
RUN npm run build


FROM nginx:1.27.3-alpine AS servicio

COPY --from=construccion /construccion/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
