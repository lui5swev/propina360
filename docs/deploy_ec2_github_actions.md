# Despliegue en EC2 con GitHub Actions

Este repositorio ya incluye `Dockerfile` y `docker-compose.yml`. El workflow `.github/workflows/deploy-ec2.yml` ejecuta pruebas, copia el bundle de la app a una instancia EC2 por SSH y reinicia el servicio con Docker Compose.

## 1. Preparar la instancia EC2

En una EC2 Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2
sudo usermod -aG docker ubuntu
sudo mkdir -p /opt/propina360
sudo chown -R ubuntu:ubuntu /opt/propina360
```

Cierra y vuelve a abrir la sesion SSH para que el grupo `docker` aplique.

Abre el puerto de la app en el Security Group:

- TCP `18765` desde tu IP o desde el origen que corresponda.

La app quedara disponible en:

```text
http://<IP_PUBLICA_EC2>:18765
```

## 2. Configurar GitHub

En el repositorio de GitHub, agrega estos secrets en `Settings -> Secrets and variables -> Actions -> Secrets`:

```text
EC2_HOST=<IP publica o DNS de la EC2>
EC2_USER=ubuntu
EC2_SSH_KEY=<contenido completo de la llave privada SSH>
PROPINA360_SIGNING_KEY=<clave larga y privada para firmar sesiones>
```

Agrega estas variables opcionales en `Settings -> Secrets and variables -> Actions -> Variables`:

```text
EC2_APP_DIR=/opt/propina360
PROPINA360_PORT=18765
```

## 3. Ejecutar despliegue

Cada push a `main` ejecuta:

1. Instalacion de dependencias backend.
2. Pruebas con `pytest`.
3. Copia de `Dockerfile`, `docker-compose.yml`, `backend-fastapi` y `.env` a la EC2.
4. `docker compose up -d --build --remove-orphans`.
5. Health check contra `/api/health`.

Tambien se puede ejecutar manualmente desde `Actions -> Deploy Propina360 to EC2 -> Run workflow`.

## 4. Operacion en EC2

Comandos utiles dentro de la instancia:

```bash
cd /opt/propina360
docker compose ps
docker compose logs -f
docker compose restart
```

La base SQLite persiste en el volumen Docker `propina360_data`, por lo que no se borra al reconstruir el contenedor.
