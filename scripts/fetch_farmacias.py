# scripts/fetch_farmacias.py
# ============================================================
# SCRIPT PRINCIPAL — Obtención y procesamiento de farmacias
# ============================================================
# Flujo:
#   1. Lee configuración desde .env
#   2. Llama a la API del MINSAL con timeout y reintentos
#   3. Valida la estructura del JSON recibido
#   4. Limpia y normaliza los datos
#   5. Exporta a src/data/farmacias.json
#
# Puede correrse manualmente o desde GitHub Actions.
# Sin argumentos requeridos — toda la configuración viene del .env
# ============================================================

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from unidecode import unidecode

# Importamos nuestro sistema de logging centralizado
# sys.path asegura que Python encuentre el módulo aunque se corra
# desde distintas carpetas
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.logger_config import get_logger, setup_logging

# ============================================================
# INICIALIZACIÓN
# ============================================================

# Cargar variables de entorno desde .env (si existe)
# En GitHub Actions no existe .env — las variables vienen
# del entorno del runner directamente
load_dotenv()

# Configurar logging antes de cualquier otra operación
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(LOG_LEVEL)
logger = get_logger(__name__)

# ============================================================
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ============================================================

API_URL = os.getenv(
    "API_URL", "https://midas.minsal.cl/farmacia_v2/WS/getLocalesTurnos.php"
)
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "10"))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", "3"))

# Ruta de salida del JSON — relativa a la raíz del proyecto
OUTPUT_PATH = Path(__file__).parent.parent / "src" / "data" / "farmacias.json"

# Headers HTTP — identificamos nuestro cliente correctamente
# Algunas APIs bloquean requests sin User-Agent
HEADERS = {
    "User-Agent": "farmacias-turno-chile/1.0 (github.com/ceomarin/farmacias-turno-chile)",
    "Accept": "application/json",
}

# ============================================================
# CAMPOS REQUERIDOS — estructura mínima que debe tener cada registro
# Si la API cambia y elimina un campo, lo detectamos antes de fallar
# ============================================================

CAMPOS_REQUERIDOS = {
    "local_nombre",
    "local_direccion",
    "local_telefono",
    "comuna_nombre",
    "localidad_nombre",
    "funcionamiento_hora_apertura",
    "funcionamiento_hora_cierre",
    "funcionamiento_dia",
    "fecha",
}

# ============================================================
# CAPA DE LLAMADA A LA API — con reintentos automáticos
# ============================================================


@retry(
    # Cuántas veces intentar antes de rendirse
    stop=stop_after_attempt(API_MAX_RETRIES),
    # Espera exponencial entre reintentos: 2s, 4s, 8s...
    # Evita bombardear la API si está caída
    wait=wait_exponential(multiplier=1, min=2, max=10),
    # Solo reintenta en errores de conexión/timeout, no en errores de lógica
    retry=retry_if_exception_type(
        (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        )
    ),
    # Loguea un warning antes de cada reintento
    before_sleep=before_sleep_log(logger, 20),  # 20 = logging.INFO
)
def llamar_api() -> list:
    """
    Llama a la API del MINSAL y retorna la lista de farmacias.

    Incluye timeout obligatorio y reintentos automáticos con
    espera exponencial en caso de fallos de conexión.

    Returns:
        Lista de diccionarios con los datos de cada farmacia.

    Raises:
        requests.exceptions.HTTPError: Si el servidor responde con error 4xx/5xx.
        ValueError: Si la respuesta no es JSON válido o no es una lista.
    """
    logger.info(f"Consultando API del MINSAL: {API_URL}")
    inicio = time.time()

    response = requests.get(API_URL, headers=HEADERS, timeout=API_TIMEOUT)

    # Tiempo de respuesta en milisegundos — útil para detectar APIs lentas
    tiempo_ms = int((time.time() - inicio) * 1000)

    # raise_for_status() lanza HTTPError si el código es 4xx o 5xx
    response.raise_for_status()

    logger.info(
        f"API respondió correctamente — status: {response.status_code}, tiempo: {tiempo_ms}ms"
    )

    # Verificar que la respuesta es JSON válido
    try:
        data = response.json()
    except ValueError as e:
        logger.critical(f"La API no devolvió JSON válido: {e}")
        raise

    # Verificar que es una lista (no un dict de error)
    if not isinstance(data, list):
        logger.critical(
            f"Estructura inesperada: se esperaba lista, llegó {type(data).__name__}"
        )
        raise ValueError("Estructura inesperada en respuesta de API")

    logger.info(f"Registros recibidos de la API: {len(data)}")
    return data


# ============================================================
# VALIDACIÓN DE ESTRUCTURA
# ============================================================


def validar_registro(registro: dict, indice: int) -> bool:
    """
    Verifica que un registro tiene todos los campos requeridos.

    Args:
        registro: Diccionario con los datos de una farmacia.
        indice: Posición en la lista (para logs útiles).

    Returns:
        True si el registro es válido, False si debe descartarse.
    """
    campos_faltantes = CAMPOS_REQUERIDOS - set(registro.keys())

    if campos_faltantes:
        logger.warning(
            f"Registro #{indice} descartado — campos faltantes: {campos_faltantes}"
        )
        return False

    return True


# ============================================================
# LIMPIEZA Y NORMALIZACIÓN DE DATOS
# ============================================================


def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto para búsqueda:
    - Convierte a minúsculas
    - Elimina tildes y caracteres especiales (unidecode)
    - Elimina espacios extra

    Ejemplo: "ÑUÑOA" → "nunoa"
    """
    if not texto:
        return ""
    return unidecode(texto.strip().lower())


def sanitizar_texto_display(texto: str, max_largo: int = 200) -> str:
    """
    Limpia un texto para mostrarlo en el frontend:
    - Elimina caracteres de control
    - Normaliza espacios múltiples
    - Trunca si es demasiado largo
    - Convierte a title case (Primera Letra Mayúscula)

    Args:
        texto: Texto original de la API.
        max_largo: Longitud máxima permitida.

    Returns:
        Texto limpio listo para mostrar.
    """
    if not texto:
        return ""

    # Eliminar caracteres de control (tabs, newlines, etc.)
    texto = re.sub(r"[\x00-\x1f\x7f]", "", texto)

    # Normalizar espacios múltiples a uno solo
    texto = re.sub(r"\s+", " ", texto).strip()

    # Truncar si excede el máximo
    if len(texto) > max_largo:
        logger.warning(f"Texto truncado de {len(texto)} a {max_largo} caracteres")
        texto = texto[:max_largo]

    # Title case: "CRUZ VERDE" → "Cruz Verde"
    return texto.title()


def limpiar_telefono(telefono: str) -> str:
    """
    Limpia el número de teléfono:
    - Elimina caracteres no numéricos excepto el +
    - Retorna string vacío si no hay teléfono válido
    """
    if not telefono or not telefono.strip():
        return ""

    # Solo dígitos y el signo +
    limpio = re.sub(r"[^\d+]", "", telefono.strip())

    # Si quedó vacío después de limpiar, no hay teléfono
    if not limpio:
        return ""

    return limpio


def procesar_farmacia(raw: dict) -> dict:
    """
    Transforma un registro crudo de la API en el formato
    limpio que Astro necesita para renderizar.

    Args:
        raw: Diccionario tal como viene de la API.

    Returns:
        Diccionario con datos limpios y normalizados.
    """
    nombre = sanitizar_texto_display(raw.get("local_nombre", ""))
    comuna = sanitizar_texto_display(raw.get("comuna_nombre", ""))
    telefono = limpiar_telefono(raw.get("local_telefono", ""))

    # Si el teléfono viene vacío, logueamos un warning informativo
    if not telefono:
        logger.debug(f"Farmacia sin teléfono: {nombre} — {comuna}")

    return {
        # Datos de display — en title case para mostrar al usuario
        "nombre": nombre,
        "direccion": sanitizar_texto_display(raw.get("local_direccion", "")),
        "telefono": telefono,
        "comuna": comuna,
        "localidad": sanitizar_texto_display(raw.get("localidad_nombre", "")),
        "hora_apertura": raw.get("funcionamiento_hora_apertura", ""),
        "hora_cierre": raw.get("funcionamiento_hora_cierre", ""),
        "dia": sanitizar_texto_display(raw.get("funcionamiento_dia", "")),
        "fecha": raw.get("fecha", ""),
        # Versión normalizada para el buscador frontend (sin tildes, minúsculas)
        # El JS del buscador compara contra este campo
        "comuna_busqueda": normalizar_texto(raw.get("comuna_nombre", "")),
        "nombre_busqueda": normalizar_texto(raw.get("local_nombre", "")),
    }


# ============================================================
# FUNCIÓN PRINCIPAL
# ============================================================


def main() -> int:
    """
    Orquesta el flujo completo:
    1. Llama a la API
    2. Valida y procesa cada registro
    3. Exporta el JSON final

    Returns:
        0 si todo salió bien, 1 si hubo error crítico.
        GitHub Actions usa este código para marcar el job como
        exitoso o fallido.
    """
    logger.info("=" * 60)
    logger.info("INICIO — Script de obtención de farmacias de turno")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # --------------------------------------------------------
    # PASO 1: Llamar a la API
    # --------------------------------------------------------
    try:
        datos_crudos = llamar_api()
    except requests.exceptions.HTTPError as e:
        logger.critical(f"Error HTTP irrecuperable: {e}", exc_info=True)
        return 1
    except requests.exceptions.Timeout:
        logger.critical(f"Timeout después de {API_MAX_RETRIES} intentos", exc_info=True)
        return 1
    except Exception as e:
        logger.critical(f"Error inesperado al llamar la API: {e}", exc_info=True)
        return 1

    # --------------------------------------------------------
    # PASO 2: Validar y procesar registros
    # --------------------------------------------------------
    farmacias_procesadas = []
    descartados = 0

    for i, registro in enumerate(datos_crudos):
        if not validar_registro(registro, i):
            descartados += 1
            continue

        try:
            farmacia = procesar_farmacia(registro)
            farmacias_procesadas.append(farmacia)
        except Exception as e:
            # Un error en un registro no detiene el proceso completo
            logger.error(f"Error procesando registro #{i}: {e}", exc_info=True)
            descartados += 1

    logger.info(f"Registros procesados: {len(farmacias_procesadas)}")

    if descartados > 0:
        logger.warning(f"Registros descartados: {descartados}")

    # Si no hay ninguna farmacia, algo está muy mal
    if not farmacias_procesadas:
        logger.critical("No se procesó ninguna farmacia — abortando exportación")
        return 1

    # --------------------------------------------------------
    # PASO 3: Exportar JSON
    # --------------------------------------------------------
    # Metadata útil para el frontend
    output = {
        "generado_en": datetime.now().isoformat(),
        "total": len(farmacias_procesadas),
        "farmacias": farmacias_procesadas,
    }

    try:
        # Crear carpeta si no existe (por si acaso)
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON exportado: {OUTPUT_PATH}")
        logger.info(f"Total farmacias en el archivo: {len(farmacias_procesadas)}")

    except OSError as e:
        logger.critical(f"No se pudo escribir el archivo JSON: {e}", exc_info=True)
        return 1

    logger.info("=" * 60)
    logger.info("FIN — Script completado exitosamente")
    logger.info("=" * 60)

    return 0


# ============================================================
# PUNTO DE ENTRADA
# ============================================================

if __name__ == "__main__":
    # sys.exit() comunica el código de retorno a GitHub Actions
    # 0 = éxito (job verde), 1 = fallo (job rojo)
    sys.exit(main())
