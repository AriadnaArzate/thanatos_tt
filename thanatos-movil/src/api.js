/**
 * Cliente del backend de Thanatos. Todas las rutas están en thanatos-backend/app.
 * El token JWT se agrega solo; si el servidor responde 401 se cierra la sesión.
 */
import { File } from 'expo-file-system';
import { API_URL } from './config';

let token = null;
let alExpirar = null;

export const setToken = (t) => { token = t; };
export const onSesionExpirada = (fn) => { alExpirar = fn; };
export const urlAudio = (ruta) => (ruta?.startsWith('http') ? ruta : `${API_URL}${ruta}`);

export class ApiError extends Error {
  constructor(status, mensaje) {
    super(mensaje);
    this.status = status;
  }
}

async function pedir(ruta, { method = 'GET', json, form, urlencoded, timeoutMs = 330000 } = {}) {
  const headers = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  let body;
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(json);
  } else if (urlencoded) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded';
    body = Object.entries(urlencoded)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
  } else if (form) {
    body = form; // fetch pone el Content-Type multipart con su boundary
  }

  const control = new AbortController();
  const temporizador = setTimeout(() => control.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${API_URL}${ruta}`, { method, headers, body, signal: control.signal });
  } catch (e) {
    console.log('[api] falló', ruta, e?.name, e?.message);
    if (e?.name === 'AbortError') {
      throw new ApiError(0, 'El servidor tardó demasiado en responder. Intente de nuevo.');
    }
    throw new ApiError(0, 'No se pudo conectar con el servidor. Revise su conexión.');
  } finally {
    clearTimeout(temporizador);
  }

  if (res.status === 204) return null;
  const datos = await res.json().catch(() => null);
  if (!res.ok) {
    if (res.status === 401 && token && alExpirar) alExpirar();
    let mensaje = datos?.detail;
    if (Array.isArray(mensaje)) mensaje = 'Revise los datos capturados.';
    throw new ApiError(res.status, mensaje || 'Ocurrió un error. Intente de nuevo.');
  }
  return datos;
}

export const api = {
  // --- Sesión ---
  login: (usuario, password) =>
    pedir('/auth/login', { method: 'POST', urlencoded: { username: usuario, password } }),
  registroTanatologo: (datos) => pedir('/auth/registro-tanatologo', { method: 'POST', json: datos }),
  yo: () => pedir('/auth/yo'),
  actualizarYo: (datos) => pedir('/auth/yo', { method: 'PATCH', json: datos }),

  // --- Adulto mayor ---
  conversar: (uriAudio, sessionId) => {
    // En Expo SDK 54+ fetch ya no acepta { uri, name, type } en FormData:
    // el archivo se manda como File de expo-file-system.
    const archivo = new File(uriAudio);
    const form = new FormData();
    form.append('audio', archivo, archivo.name || 'audio.m4a');
    if (sessionId) form.append('session_id', sessionId);
    return pedir('/conversar', { method: 'POST', form });
  },
  ejercicioDesahogo: () => pedir('/ejercicios/desahogo', { method: 'POST' }),
  catalogoEmociones: () => pedir('/emociones/catalogo'),
  registrarEmocion: (emocion) => pedir('/emociones', { method: 'POST', json: { emocion } }),
  contactarTanatologo: (motivo = 'hablar') =>
    pedir('/contacto/tanatologo', { method: 'POST', json: { motivo } }),
  guiaMenu: () => pedir('/guia/menu'),

  // --- Tanatólogo ---
  registrarPaciente: (datos) => pedir('/pacientes', { method: 'POST', json: datos }),
  borrarPaciente: (id) => pedir(`/pacientes/${id}`, { method: 'DELETE' }),
  pacientesDashboard: () => pedir('/dashboard/pacientes'),
  explicacion: (id) => pedir(`/dashboard/pacientes/${id}/explicacion`),
  metricas: (id, dias = 30) => pedir(`/dashboard/pacientes/${id}/resumen?dias=${dias}`),
  generarResumen: (id, dias = 7) =>
    pedir(`/dashboard/pacientes/${id}/resumen-conversaciones?dias=${dias}`, { method: 'POST' }),
};