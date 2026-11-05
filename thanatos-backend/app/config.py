"""
Configuración central del backend de Thanatos.

Todos los valores pueden sobreescribirse con variables de entorno o con un
archivo `.env` en la raíz del proyecto (ver `.env.example`). 
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": si el .env trae variables que no usamos, no truena.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---------- ASR (Whisper vía faster-whisper) ----------
    # Tamaños: tiny < base < small < medium < large-v3 (más grande = más
    # preciso pero más lento). "small" es un buen punto de partida en CPU.
    whisper_model: str = "small"
    whisper_device: str = "cpu"          # "cuda" si tienes GPU NVIDIA
    whisper_compute_type: str = "int8"   # int8 = rápido y ligero en CPU
    whisper_beam_size: int = 5           # 1 = más rápido; 5 = más preciso

    # ---------- LLM (Ollama) ----------
    ollama_host: str = "http://localhost:11434"
    # Modelo de arranque. Hay que COMPARAR contra otros (p. ej. qwen2.5:7b)
    # midiendo español de México y latencia en tu equipo.
    ollama_model: str = "llama3.2:3b"
    ollama_temperature: float = 0.6      # bajo = respuestas más estables
    ollama_max_tokens: int = 160         # tope de longitud (respuestas cortas)
    ollama_keep_alive: str = "30m"       # mantiene el modelo cargado en RAM

    # ---------- Selección de TTS ----------
    tts_proveedor: str = "edge"          # "edge" o "piper"

    # ---------- TTS principal (edge-tts) ----------
    edge_voz: str = "es-MX-DaliaNeural"  # o "es-MX-JorgeNeural"
    edge_velocidad: str = "-10%"         # negativo = más lento

    # ---------- TTS de respaldo (Piper, local) ----------
    piper_voice_path: str = "voices/es_MX-claude-high.onnx"
    # Si está vacío se usa "python -m piper". Si Piper no se instala bien con
    # pip, pon aquí la ruta al piper.exe independiente.
    piper_cmd: str = ""

    # ---------- Conversación y archivos ----------
    max_history_turns: int = 6           # turnos (usuario+asistente) que recuerda
    audio_dir: Path = Path("tmp_audio")  # audios temporales de entrada/salida

    # ---------- Base de datos ----------
    database_url: str = "sqlite:///./thanatos.db"   # relativa a donde corres uvicorn

    # ---------- Autenticación (JWT) ----------
    jwt_secret: str = "CAMBIAR-EN-ENV"              # OBLIGATORIO definirla en .env
    jwt_algoritmo: str = "HS256"
    jwt_expira_minutos: int = 60 * 24 * 7           # 7 días: el adulto mayor no debe loguearse a diario

    # ---------- Ejemplos de estilo (dataset semilla) ----------
    dataset_path: str = "data/dataset_respuestas_empaticas_es_mx_v1.xlsx"
    ejemplos_activos: bool = True        # False = responder sin ejemplos (útil para comparar)
    # Estados de validación del Excel cuyas filas se pueden usar como ejemplos.
    # "pendiente" se incluye porque la tanatóloga revisó una MUESTRA y consideró
    # correcto el dataset (ver data/registro_validacion.md). Las filas "corregir"
    # y "rechazada" NUNCA se usan, aunque se pongan aquí.
    ejemplos_estados_permitidos: str = "aprobada,pendiente"
    ejemplos_k: int = 3                  # cuántos ejemplos se muestran al modelo
    embedding_model: str = "bge-m3"      # modelo de embeddings de Ollama


settings = Settings()