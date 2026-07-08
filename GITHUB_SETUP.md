# Guia para publicar en GitHub

Desde esta carpeta:

```bash
git init
git status
git add .
git commit -m "Initial Propina360 package"
git branch -M main
git remote add origin <URL_DEL_REPOSITORIO>
git push -u origin main
```

Antes de publicar:

```bash
find . -name '__pycache__' -o -name '*.db' -o -name '.coverage'
```

El comando anterior no deberia listar archivos versionables dentro del paquete.
