# Thanatos

Prototipo de software de apoyo tanatológico con interfaz de voz para el acompañamiento en procesos de duelo en adultos mayores.

Trabajo Terminal **2026-B126** · ESCOM-IPN
Autora: Ariadna Arzate Rodríguez
Directores: M. en C. César Mújica Ascencio y M. en C. Manuel Portillo Cedillo

> Thanatos es una herramienta complementaria y preventiva. **No sustituye** la atención de un profesional de la salud ni realiza diagnóstico clínico.

## ¿Qué hace?

**Adulto mayor** (entra con su ID de paciente y un PIN de 6 dígitos)
- **Hablar ahora**: conversación por voz con un asistente empático (máx. 20 min por sesión).
- **Ejercicios de desahogo**: reminiscencia, cartas simbólicas, legado emocional y expresión emocional.
- **Registrar emoción**: seis emociones que también orientan al asistente.
- **Contactar a mi tanatólogo**.
- Guía auditiva opcional para el menú.

**Tanatólogo** (entra con su correo y contraseña)
- Registro de pacientes (el sistema genera el ID y el PIN).
- Dashboard por paciente: semáforo de riesgo (verde, amarillo o rojo) con el razonamiento de por qué tiene ese color, y resumen por temas de lo que ha hablado.
- El tanatólogo **nunca lee las conversaciones** del paciente.

Fundamentación teórica: Worden (cuatro tareas del duelo), Kübler-Ross (cinco etapas) y Boss (pérdida ambigua).

## Estructura

```
thanatos-backend/   API en FastAPI + SQLite, motor conversacional (Ollama), voz (Whisper / TTS)
thanatos-movil/     App en Expo / React Native con las vistas de paciente y de tanatólogo
```

## Tecnologías

| Capa | Tecnología |
|---|---|
| App móvil | Expo (React Native), React Navigation, expo-audio |
| API | FastAPI, SQLAlchemy, JWT |
| Base de datos | SQLite |
| Reconocimiento de voz | Whisper (faster-whisper) |
| Modelo de lenguaje | Ollama (llama3.2:3b) |
| Síntesis de voz | edge-tts / Piper |

## Cómo correrlo

### Requisitos
- Python 3.10
- Node.js (LTS)
- [Ollama](https://ollama.com) con el modelo descargado: `ollama pull llama3.2:3b`
- Expo Go en el teléfono, con cuenta de Expo

### 1. Backend
```bash
cd thanatos-backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
La documentación de la API queda en `http://localhost:8000/docs`.

### 2. App
```bash
cd thanatos-movil
npm install
copy .env.example .env
```
En `.env`, pon la IP de la computadora donde corre el backend (en Windows: `ipconfig` → Dirección IPv4):
```
EXPO_PUBLIC_API_URL=http://192.168.X.X:8000
```
Luego:
```bash
npx expo start -c
```
y escanea el código QR con el teléfono. El teléfono y la computadora deben estar en la misma red.

## Datos y privacidad
- La base `thanatos.db`, los archivos `.env` y los audios temporales **no se suben** al repositorio.
- El audio del paciente se borra en cuanto se transcribe.
- El PIN del paciente solo se muestra una vez, al registrarlo; en la base se guarda únicamente su hash.

## Trabajo a futuro
- Versión para iOS (APK solo para Android en esta etapa).
- Verificación de la identidad de los tanatólogos al registrarse.
- Limpieza periódica de los audios de respuesta.
