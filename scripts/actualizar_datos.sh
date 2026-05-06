#!/usr/bin/env bash
# scripts/actualizar_datos.sh
# ============================================================
# AUTOMATIZACIÓN LOCAL DE ACTUALIZACIÓN DE DATOS
# Ejecuta: bash scripts/actualizar_datos.sh
#
# Flujo completo:
#   1. Genera datos frescos desde la API del MINSAL
#   2. Crea rama chore/actualizar-datos-FECHA
#   3. Commitea el JSON
#   4. Push a GitHub
#   5. Crea PR automático de la rama a develop
#   6. Mergea PR de develop a main
#   7. El deploy se dispara automáticamente
# ============================================================

set -e  # Si cualquier comando falla, el script se detiene

# ============================================================
# CONFIGURACIÓN
# ============================================================
FECHA=$(date '+%Y-%m-%d')
RAMA="chore/actualizar-datos-${FECHA}"
REPO="ceomarin/farmacias-turno-chile"

# Colores para output legible
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # sin color

log()    { echo -e "${GREEN}✅ $1${NC}"; }
warn()   { echo -e "${YELLOW}⚠️  $1${NC}"; }
error()  { echo -e "${RED}❌ $1${NC}"; exit 1; }

# ============================================================
# VERIFICACIONES PREVIAS
# ============================================================

# Verificar que gh CLI está instalado
if ! command -v gh &> /dev/null; then
    error "GitHub CLI (gh) no está instalado. Instálalo desde https://cli.github.com"
fi

# Verificar que estamos autenticados en gh
if ! gh auth status &> /dev/null; then
    error "No estás autenticado en GitHub CLI. Ejecuta: gh auth login"
fi

# Verificar que uv está disponible
if ! command -v uv &> /dev/null; then
    error "uv no está instalado"
fi

log "Verificaciones previas OK"

# ============================================================
# PASO 1 — Asegurarse de estar en develop actualizado
# ============================================================
echo ""
echo "📦 Preparando rama de trabajo..."

git checkout develop
git pull origin develop
log "develop actualizado"

# ============================================================
# PASO 2 — Crear rama de actualización
# ============================================================

# Si la rama ya existe (segunda ejecución del día), la eliminamos
if git show-ref --quiet refs/heads/${RAMA}; then
    warn "Rama ${RAMA} ya existe, eliminando..."
    git branch -D ${RAMA}
fi

git checkout -b ${RAMA}
log "Rama ${RAMA} creada"

# ============================================================
# PASO 3 — Generar datos frescos
# ============================================================
echo ""
echo "🌐 Obteniendo datos frescos del MINSAL..."

uv run python scripts/fetch_farmacias.py

# Verificar que el JSON fue generado
if [ ! -f "src/data/farmacias.json" ]; then
    error "El script Python no generó el JSON"
fi

# Extraer total de farmacias para el mensaje de commit
TOTAL=$(python3 -c "import json; d=json.load(open('src/data/farmacias.json')); print(d['total'])")
log "Datos generados: ${TOTAL} farmacias"

# ============================================================
# PASO 4 — Commit y push
# ============================================================
echo ""
echo "💾 Commiteando datos..."

git add src/data/farmacias.json
git commit -m "chore: actualizar datos farmacias ${FECHA} (${TOTAL} farmacias)"
git push -u origin ${RAMA}
log "Push a origin/${RAMA} OK"

# ============================================================
# PASO 5 — PR de rama a develop
# ============================================================
echo ""
echo "🔀 Creando PR rama → develop..."

PR_RAMA_URL=$(gh pr create \
    --base develop \
    --head ${RAMA} \
    --title "chore: actualizar datos farmacias ${FECHA}" \
    --body "Actualización automática de datos del MINSAL.

- **Fecha:** ${FECHA}
- **Total farmacias:** ${TOTAL}
- **Generado por:** script local \`actualizar_datos.sh\`" \
    --repo ${REPO})

log "PR creado: ${PR_RAMA_URL}"

# Mergear PR automáticamente
gh pr merge ${PR_RAMA_URL} \
    --merge \
    --delete-branch \
    --repo ${REPO}

log "PR rama → develop mergeado"

# ============================================================
# PASO 6 — PR de develop a main
# ============================================================
echo ""
echo "🚀 Creando PR develop → main..."

# Actualizar develop local
git checkout develop
git pull origin develop

PR_DEPLOY_URL=$(gh pr create \
    --base main \
    --head develop \
    --title "release: deploy datos farmacias ${FECHA}" \
    --body "Deploy automático de datos actualizados.

- **Fecha:** ${FECHA}
- **Total farmacias:** ${TOTAL}
- **Trigger:** script local \`actualizar_datos.sh\`

Este PR dispara el deploy automático a GitHub Pages." \
    --repo ${REPO})

log "PR creado: ${PR_DEPLOY_URL}"

# Mergear PR a main — dispara el deploy automático
gh pr merge ${PR_DEPLOY_URL} \
    --merge \
    --repo ${REPO}

log "PR develop → main mergeado — deploy iniciado"

# ============================================================
# RESUMEN
# ============================================================
echo ""
echo "============================================"
echo -e "${GREEN}🎉 Actualización completa${NC}"
echo "============================================"
echo "📊 Farmacias: ${TOTAL}"
echo "📅 Fecha: ${FECHA}"
echo "🌐 Sitio: https://ceomarin.github.io/farmacias-turno-chile"
echo "⚙️  Pipeline: https://github.com/${REPO}/actions"
echo "============================================"