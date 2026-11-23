/**
 * Reproducción de los audios que genera el backend (/audio/...).
 * La grabación vive en la pantalla "Hablar ahora" (hook useAudioRecorder).
 */
import { createAudioPlayer, setAudioModeAsync } from 'expo-audio';
import { urlAudio } from './api';

/** Deja el audio listo para reproducir por la bocina (también en modo silencio en iPhone). */
export async function modoReproduccion() {
  await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
}

export async function modoGrabacion() {
  await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
}

/**
 * Reproduce un audio. Devuelve { terminado, detener }:
 *   terminado -> promesa que se cumple con true al acabar o false si se detuvo antes.
 */
export function reproducir(ruta) {
  const player = createAudioPlayer({ uri: urlAudio(ruta) });
  let listo = false;
  let sub = null;
  let resolver;
  const terminado = new Promise((res) => { resolver = res; });

  const cerrar = (completo) => {
    if (listo) return;
    listo = true;
    try { sub?.remove(); } catch { /* ya liberado */ }
    try { player.pause(); } catch { /* ya liberado */ }
    try { player.remove(); } catch { /* ya liberado */ }
    resolver(completo);
  };

  sub = player.addListener('playbackStatusUpdate', (estado) => {
    if (estado.didJustFinish) cerrar(true);
  });
  player.play();

  return { terminado, detener: () => cerrar(false) };
}

/** Reproduce varios audios uno tras otro (narración del menú). */
export function reproducirEnCadena(rutas) {
  let actual = null;
  let cancelado = false;
  const terminado = (async () => {
    for (const ruta of rutas) {
      if (cancelado) return false;
      actual = reproducir(ruta);
      const ok = await actual.terminado;
      if (!ok) return false;
    }
    return true;
  })();
  return {
    terminado,
    detener: () => { cancelado = true; actual?.detener(); },
  };
}