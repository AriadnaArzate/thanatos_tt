export const API_URL = process.env.EXPO_PUBLIC_API_URL || 'http://192.168.1.100:8000';

// Cuánto se muestra un mensaje ("Emoción registrada...") antes de seguir.
export const ESPERA_MENSAJE_MS = 2800;

// Tope de seguridad para una grabación en "Hablar ahora" (se envía sola al llegar).
export const MAX_GRABACION_MS = 3 * 60 * 1000;