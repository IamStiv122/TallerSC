# TallerSC — Despliegue en Render

Este repositorio contiene la aplicación Django "TallerSC" preparada para desplegar en Render usando PostgreSQL.

**Archivos importantes**
- [TallerSC/settings.py](TallerSC/settings.py)
- [requirements.txt](requirements.txt)
- [build.sh](build.sh)
- [Procfile](Procfile)

## Pasos para desplegar en Render

1. Subir el proyecto a un repositorio en GitHub.

2. Crear un "Web Service" en Render y conectar el repositorio.

3. Configurar las siguientes variables de entorno en Render (Environment -> Environment Variables):

- SECRET_KEY: Una clave secreta segura.
- DEBUG: False
- ALLOWED_HOSTS: tu-app.onrender.com (o varios separados por coma)
- DATABASE_URL: formulario de conexión PostgreSQL, por ejemplo:
  postgresql://usuario:password@host:puerto/base
- CSRF_TRUSTED_ORIGINS: https://tu-app.onrender.com

> Si tu app usa `ImageField`, necesitas `Pillow`, lo cual ya fue añadido en `requirements.txt`.

4. En la sección de Build & Deploy en Render, configura:

- Build Command:

```bash
./build.sh
```

- Start Command:

```bash
gunicorn TallerSC.wsgi:application
```

- Python Version: asegúrate de usar `python-3.14.3` si Render lo solicita (archivo `runtime.txt`).

5. Opcional: si usas el servicio de PostgreSQL de Render, copia la URL que te entregue y pégala en `DATABASE_URL`.

## Comandos locales útiles

Activar entorno virtual y probar migraciones:

```bash
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver
```

## Notas

- Los archivos estáticos se sirven usando WhiteNoise en producción.
- No comites credenciales ni el archivo `.env` al repositorio público.

Si quieres, puedo crear el repositorio en GitHub desde aquí (necesitaré acceso/token), o puedo preparar el commit y los comandos exactos que debes ejecutar localmente. "
