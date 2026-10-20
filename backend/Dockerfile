# Imagen del backend — Python 3.12 + FastAPI
#
# El contexto de construcción es la RAÍZ del repositorio, no backend/: la
# imagen necesita también database/seeds para poder sembrar sin Python en la
# máquina anfitriona. Por eso las rutas de COPY empiezan por backend/.
#
# Construcción en dos etapas. La primera instala las dependencias; la segunda
# copia solo lo instalado y el código. La diferencia no es de tamaño: es que el
# compilador y las cabeceras de desarrollo que psycopg necesita para instalarse
# no quedan en la imagen que se despliega.
#
# La versión está fijada (ADR-009). `python:3.12-slim` a secas cambiaría de
# parche entre una construcción y otra sin que nadie lo decidiera.

FROM python:3.12.8-slim AS dependencias

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /instalacion

# Se copia solo requirements.txt antes que el código: así la capa de
# dependencias se reutiliza mientras ese archivo no cambie, y editar una ruta
# no obliga a reinstalar todo.
COPY backend/requirements.txt .
RUN pip install --prefix=/opt/python -r requirements.txt


FROM python:3.12.8-slim AS aplicacion

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # /app además de los paquetes instalados: el guion de siembra vive en
    # /app/database/seeds y necesita importar `app.models` desde allí. Sin
    # esto, `python database/seeds/...` no encontraría los modelos, porque
    # Python antepone el directorio del guion y no el de trabajo.
    PYTHONPATH=/app:/opt/python/lib/python3.12/site-packages \
    PATH=/opt/python/bin:$PATH

# Usuario sin privilegios. Un proceso que corre como root dentro del contenedor
# convierte cualquier escape en acceso de administrador (OWASP A05).
RUN groupadd --system tienda && useradd --system --gid tienda --home /app tienda

COPY --from=dependencias /opt/python /opt/python

WORKDIR /app
COPY --chown=tienda:tienda backend/alembic.ini ./
COPY --chown=tienda:tienda backend/alembic ./alembic
COPY --chown=tienda:tienda backend/app ./app

# La siembra de desarrollo viaja en la imagen para poder poblar la base sin
# instalar Python en la máquina anfitriona. Usa los mismos modelos que la
# aplicación, de modo que no puede desalinearse del esquema.
COPY --chown=tienda:tienda database/seeds ./database/seeds

USER tienda
EXPOSE 8000

# Consulta la base, no solo el proceso: un servicio vivo que no alcanza su
# base de datos no está sano y debe reiniciarse, no recibir tráfico.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,json,sys; \
r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=4)); \
sys.exit(0 if r.get('database')=='ok' else 1)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
