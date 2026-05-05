# 💊 Farmacias de Turno Chile

![Deploy a GitHub Pages](https://github.com/ceomarin/farmacias-turno-chile/actions/workflows/deploy.yml/badge.svg)

![Actualizar datos](https://github.com/ceomarin/farmacias-turno-chile/actions/workflows/update-data.yml/badge.svg)

🌐 **Sitio en producción:** https://ceomarin.github.io/farmacias-turno-chile

Buscador de farmacias de turno por comuna en Chile, con datos oficiales
del MINSAL actualizados automáticamente cada 24 horas. El usuario busca
su comuna y obtiene nombre, dirección, teléfono y horario de cada farmacia
de turno, con indicador visual de si está abierta en este momento.

---

## 🏗️ Arquitectura

API MINSAL → Script Python → farmacias.json → Astro Build → GitHub Pages
↑                                               ↑
GitHub Actions                                  GitHub Actions
(cada 24 horas)                                 (cada push a main)

El proyecto tiene tres capas independientes:

**Capa 1 — Python (ETL):** consume la API del MINSAL, valida y sanitiza
los datos, exporta a `src/data/farmacias.json`.

**Capa 2 — Astro JS (Frontend):** lee el JSON en build time, genera HTML
estático con Tailwind CSS, buscador vanilla JS con sanitización.

**Capa 3 — GitHub Actions (CI/CD):** automatiza la obtención de datos
frescos y el despliegue en cada push o cada 24 horas.

---

## 🚀 Correr localmente

### Requisitos

- Python 3.11+
- Node.js 18+
- uv instalado (`pip install uv`)

### Instalación

```bash
# Clonar el repositorio
git clone <https://github.com/ceomarin/farmacias-turno-chile.git>
cd farmacias-turno-chile

# Copiar variables de entorno
cp .env.example .env

# Instalar dependencias Python
uv sync

# Instalar dependencias Node
npm install
```

### Desarrollo

```bash
# Paso 1: obtener datos frescos de la API
uv run python scripts/fetch_farmacias.py

# Paso 2: levantar el servidor de desarrollo
npm run dev

# El sitio estará en <http://localhost:4321/farmacias-turno-chile/>
```

### Build de producción local

```bash
npm run build
```

---

## ⚙️ Configurar deploy en GitHub Pages

1. Crear el repositorio en GitHub como `farmacias-turno-chile`
2. Ir a **Settings → Pages → Source** y seleccionar **GitHub Actions**
3. Hacer push a `main` — el pipeline se activa automáticamente
4. El sitio estará disponible en `https://TU_USUARIO.github.io/farmacias-turno-chile`

---

## 🔒 Seguridad

### Python

- Variables de entorno via `.env` — nunca hardcodeadas en el código
- Timeout obligatorio en todas las peticiones HTTP (10 segundos)
- Reintentos con espera exponencial via `tenacity` (máximo 3 intentos)
- Validación de estructura del JSON antes de procesarlo
- Sanitización de texto con regex antes de exportar
- Headers `User-Agent` identificados en las peticiones HTTP
- Logging sin datos personales de usuarios finales

### Frontend

- Interpolación de variables con `{}` en Astro — escape automático de XSS
- Buscador usa `textContent` en lugar de `innerHTML`
- `maxlength="100"` en el input del buscador
- Links externos con `rel="noopener noreferrer"`

### Meta tags de seguridad

- `Content-Security-Policy` básico
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: no-referrer`

### GitHub Actions

- Permisos mínimos declarados explícitamente en cada workflow
- `deploy.yml` solo tiene permisos de lectura y publicación en Pages
- `update-data.yml` solo tiene `contents: write` para el commit del JSON
- Versiones de actions fijadas (`@v4`) — no `@latest`

---

## 🪵 Logging

El script Python genera dos archivos de log en `logs/` (excluida de git):

| Archivo | Contenido |
| --- | --- |
| `farmacias_YYYYMMDD.log` | Todas las operaciones desde INFO hacia arriba |
| `errores_YYYYMMDD.log` | Solo WARNING, ERROR y CRITICAL |

Cada línea tiene formato estructurado:
2026-04-09 00:09:21 | INFO | scripts.fetch_farmacias | API respondió — status: 200, tiempo: 2389ms

Los logs se rotan automáticamente al llegar a 5MB y se conservan
los últimos 3 archivos históricos.

En GitHub Actions los logs del script Python se publican como
artefacto descargable por 7 días en cada ejecución del pipeline.

---

## 📡 API

Datos oficiales del Ministerio de Salud de Chile (MINSAL).

- **URL:** `https://midas.minsal.cl/farmacia_v2/WS/getLocalesTurnos.php`
- **Método:** GET
- **Autenticación:** No requerida
- **Actualización:** Diaria

---

## 🛠️ Stack técnico

| Categoría | Tecnología |
| --- | --- |
| Lenguaje backend | Python 3.11 |
| Gestor entorno Python | uv (Astral) |
| HTTP client | requests + tenacity |
| Normalización texto | unidecode |
| Variables de entorno | python-dotenv |
| Framework frontend | Astro JS |
| Estilos | Tailwind CSS v4 |
| Interactividad | JavaScript vanilla |
| CI/CD | GitHub Actions |
| Hosting | GitHub Pages |

---

## 💼 Habilidades demostradas

- **Consumo de APIs REST** con manejo profesional de errores,
timeout y reintentos automáticos
- **ETL (Extract, Transform, Load)** — pipeline de datos desde
API pública hasta sitio estático
- **Logging profesional** con rotación de archivos y niveles de severidad
- **Seguridad en aplicaciones web** — sanitización, CSP, headers de seguridad
- **Static Site Generation (SSG)** con Astro JS
- **CI/CD con GitHub Actions** — deploy automático y actualización programada
- **Monorepo** con dos toolchains independientes (Python + Node.js)
- **Despliegue en producción** en GitHub Pages con dominio público

---

## 👤 Autor

**César Marin**[GitHub](https://github.com/ceomarin)