# scripts/logger_config.py
# ============================================================
# CONFIGURACIÓN CENTRALIZADA DE LOGGING
# ============================================================
# Este módulo se importa al inicio de cualquier script Python
# del proyecto. Configura todos los handlers una sola vez y
# devuelve un logger listo para usar.
#
# Patrón profesional: logging centralizado en módulo dedicado.
# Cualquier script del proyecto hace:
#   from logger_config import get_logger
#   logger = get_logger(__name__)
# ============================================================

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# ============================================================
# CONSTANTES DE CONFIGURACIÓN
# ============================================================

# Carpeta donde se guardan los archivos de log
# os.path.dirname(__file__) = carpeta donde está este archivo (scripts/)
# os.path.join(..., '..', 'logs') = sube un nivel y entra a logs/
LOGS_DIR = os.path.join(os.path.dirname(__file__), "..", "logs")

# Tamaño máximo de cada archivo de log antes de rotar: 5 MB
MAX_BYTES = 5 * 1024 * 1024

# Cuántos archivos históricos conservar (además del actual)
BACKUP_COUNT = 3

# Formato estándar para todos los mensajes de log
# %(asctime)s    → timestamp: "2026-04-06 03:15:42"
# %(levelname)s  → nivel: "INFO", "ERROR", etc.
# %(name)s       → nombre del módulo que generó el log
# %(message)s    → el mensaje real
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ============================================================
# FUNCIÓN DE CONFIGURACIÓN PRINCIPAL
# ============================================================


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configura el sistema de logging completo del proyecto.

    Crea tres destinos simultáneos para los logs:
    1. Consola (stdout) — visible en GitHub Actions en tiempo real
    2. Archivo rotativo general — todos los niveles desde INFO
    3. Archivo rotativo de errores — solo WARNING, ERROR y CRITICAL

    Args:
        log_level: Nivel mínimo de logging. "DEBUG" en desarrollo,
                   "INFO" en producción (GitHub Actions).
    """

    # Crear la carpeta de logs si no existe
    # exist_ok=True evita error si ya existe
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Nombre del archivo de log con fecha para identificarlo fácilmente
    fecha_hoy = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOGS_DIR, f"farmacias_{fecha_hoy}.log")
    error_log_file = os.path.join(LOGS_DIR, f"errores_{fecha_hoy}.log")

    # Convertir el string del nivel a la constante de logging
    # "DEBUG" → logging.DEBUG (10), "INFO" → logging.INFO (20), etc.
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # --------------------------------------------------------
    # FORMATTER — formato idéntico para todos los handlers
    # --------------------------------------------------------
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    # --------------------------------------------------------
    # HANDLER 1: Consola
    # Muestra logs en tiempo real en la terminal y en GitHub Actions
    # --------------------------------------------------------
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)

    # --------------------------------------------------------
    # HANDLER 2: Archivo rotativo general
    # Guarda TODOS los logs desde INFO hacia arriba
    # Rota cuando llega a 5MB, conserva los últimos 3 archivos
    # --------------------------------------------------------
    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",  # Importante: el JSON tiene caracteres en español
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # --------------------------------------------------------
    # HANDLER 3: Archivo separado solo para errores críticos
    # Útil para monitoreo: si este archivo tiene contenido, algo falló
    # --------------------------------------------------------
    error_handler = RotatingFileHandler(
        filename=error_log_file,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.WARNING)  # WARNING, ERROR y CRITICAL
    error_handler.setFormatter(formatter)

    # --------------------------------------------------------
    # ROOT LOGGER — configuración global que afecta a todo el proyecto
    # --------------------------------------------------------
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Evitar agregar handlers duplicados si setup_logging() se llama más de una vez
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.addHandler(error_handler)


# ============================================================
# FUNCIÓN DE ACCESO AL LOGGER
# ============================================================


def get_logger(name: str) -> logging.Logger:
    """
    Devuelve un logger con el nombre del módulo que lo solicita.

    Uso en cualquier script del proyecto:
        from scripts.logger_config import get_logger
        logger = get_logger(__name__)
        logger.info("Iniciando proceso...")

    Args:
        name: Nombre del módulo. Usar siempre __name__ para que
              el log muestre de dónde viene el mensaje.

    Returns:
        Logger configurado y listo para usar.
    """
    return logging.getLogger(name)


# ============================================================
# SCRIPT DE PRUEBA — solo se ejecuta si corres este archivo directamente
# ============================================================

if __name__ == "__main__":
    # Leer nivel de log desde variable de entorno (con fallback a DEBUG)
    nivel = os.getenv("LOG_LEVEL", "DEBUG")
    setup_logging(nivel)

    logger = get_logger(__name__)

    logger.debug("Mensaje DEBUG — solo visible en desarrollo")
    logger.info("Mensaje INFO — operación normal completada")
    logger.warning("Mensaje WARNING — algo inusual pero no fatal")
    logger.error("Mensaje ERROR — algo falló pero el programa sigue")
    logger.critical("Mensaje CRITICAL — fallo total del sistema")

    print(f"\n✅ Logs escritos en: {LOGS_DIR}")
    print("Abre la carpeta logs/ para ver los archivos generados")
