import { usePreventRemove } from '@react-navigation/native';
import { AudioModule, RecordingPresets, useAudioRecorder } from 'expo-audio';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import Svg, { Polygon } from 'react-native-svg';
import { api } from '../../api';
import { modoGrabacion, modoReproduccion, reproducir } from '../../audio';
import { BotonOscuro, BotonRegresar } from '../../components/Botones';
import Cara from '../../components/Cara';
import Fondo from '../../components/Fondo';
import { OndaVoz, TextoMensaje } from '../../components/Visuales';
import { MAX_GRABACION_MS } from '../../config';
import { colores, fuentes, s } from '../../theme';

/**
 * "Hablar ahora". Fases (cada una corresponde a un mockup):
 *   inicio     -> "Cuando esté listo puede oprimir el botón de abajo..." + triángulo
 *   escuchando -> "Le escucho" con ojos cerrados (se está grabando)
 *   pensando   -> el backend transcribe y genera la respuesta (puede tardar)
 *   hablando   -> cara hablando + onda de voz mientras suena la respuesta
 *   confirmar  -> "¿Desea terminar la sesión?"
 * Al terminar de sonar la respuesta vuelve a escuchar sola, como una conversación.
 */
export default function HablarAhoraScreen({ navigation }) {
  const grabadora = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const [fase, setFase] = useState('inicio');
  const [aviso, setAviso] = useState('');
  const [saliendo, setSaliendo] = useState(false);

  const sesionId = useRef(null);
  const reproduccion = useRef(null);
  const grabando = useRef(false);
  const turno = useRef(0);       // invalida respuestas que llegan después de salir o pausar
  const tope = useRef(null);

  const detenerTodo = useCallback(async () => {
    turno.current += 1;
    clearTimeout(tope.current);
    reproduccion.current?.detener();
    reproduccion.current = null;
    if (grabando.current) {
      grabando.current = false;
      try { await grabadora.stop(); } catch { /* ya detenida */ }
    }
  }, [grabadora]);

  useEffect(() => () => { detenerTodo(); }, [detenerTodo]);

  // Si hay una sesión en curso, "regresar" (botón o gesto) pregunta antes de salir.
  const sesionActiva = fase !== 'inicio';
  usePreventRemove(sesionActiva && !saliendo, () => { pedirConfirmacion(); });
  useEffect(() => { if (saliendo) navigation.goBack(); }, [saliendo, navigation]);

  async function escuchar() {
    turno.current += 1;
    const miTurno = turno.current;
    setAviso('');
    try {
      const permiso = await AudioModule.requestRecordingPermissionsAsync();
      if (!permiso.granted) {
        setAviso('Para conversar necesito permiso para usar el micrófono.');
        setFase('inicio');
        return;
      }
      await modoGrabacion();
      await grabadora.prepareToRecordAsync();
      if (miTurno !== turno.current) return;
      grabadora.record();
      grabando.current = true;
      setFase('escuchando');
      tope.current = setTimeout(() => { terminarDeHablar(); }, MAX_GRABACION_MS);
    } catch {
      setAviso('No pude encender el micrófono. Intente de nuevo.');
      setFase('inicio');
    }
  }

  async function terminarDeHablar() {
    if (!grabando.current) return;
    clearTimeout(tope.current);
    const miTurno = turno.current;
    grabando.current = false;
    setFase('pensando');
    try {
      await grabadora.stop();
      const uri = grabadora.uri;
      await modoReproduccion();
      const r = await api.conversar(uri, sesionId.current);
      if (miTurno !== turno.current) return;
      sesionId.current = r.session_id;

      setFase('hablando');
      const rep = reproducir(r.audio_url);
      reproduccion.current = rep;
      const completo = await rep.terminado;
      reproduccion.current = null;
      if (miTurno !== turno.current || !completo) return;

      if (r.limite_alcanzado) setSaliendo(true);   // se llegó a los 20 minutos
      else escuchar();
    } catch (e) {
      if (miTurno !== turno.current) return;
      setAviso(e.message || 'Algo falló. Oprima el botón para intentarlo otra vez.');
      setFase('inicio');
    }
  }

  function pedirConfirmacion() {
    detenerTodo();
    setFase('confirmar');
  }

  const regresar = () => (sesionActiva ? pedirConfirmacion() : navigation.goBack());

  return (
    <Fondo style={{ alignItems: 'center' }}>
      {fase !== 'confirmar' && <BotonRegresar onPress={regresar} style={{ marginLeft: s(10) }} />}

      {fase === 'inicio' && (
        <>
          <TextoMensaje style={{ marginTop: s(120) }}>
            Cuando esté listo puede oprimir el botón de abajo para iniciar la sesión
          </TextoMensaje>
          <Pressable onPress={escuchar} accessibilityRole="button" accessibilityLabel="Iniciar la conversación"
            style={({ pressed }) => ({ marginTop: s(70), opacity: pressed ? 0.7 : 1 })} hitSlop={20}>
            <Svg width={s(200)} height={s(260)} viewBox="0 0 200 260">
              <Polygon points="0,0 200,130 0,260" fill={colores.verdeOscuro} />
            </Svg>
          </Pressable>
          {aviso ? <Text style={styles.aviso}>{aviso}</Text> : null}
        </>
      )}

      {fase === 'escuchando' && (
        <>
          <Text style={styles.escucho}>Le escucho</Text>
          <Cara tipo="escucha" ancho={460} />
          <View style={{ marginTop: s(90) }}>
            <BotonOscuro texto="Ya terminé de hablar" ancho={700} onPress={terminarDeHablar} />
          </View>
        </>
      )}

      {fase === 'pensando' && (
        <>
          <View style={{ marginTop: s(160) }}><Cara tipo="ojos" ancho={460} /></View>
          <TextoMensaje style={{ marginTop: s(60) }}>Déjeme pensar un momento…</TextoMensaje>
        </>
      )}

      {fase === 'hablando' && (
        <>
          <View style={{ marginTop: s(110) }}><Cara tipo="habla" ancho={430} /></View>
          <View style={{ marginTop: s(60) }}><OndaVoz activa /></View>
        </>
      )}

      {fase === 'confirmar' && (
        <>
          <View style={{ marginTop: s(220) }}><Cara tipo="ojos" ancho={480} /></View>
          <TextoMensaje style={{ marginTop: s(80) }}>¿Desea terminar la sesión?</TextoMensaje>
          <View style={styles.opciones}>
            <BotonOscuro texto="Sí, regresar al menú principal" ancho={330} onPress={() => setSaliendo(true)}
              textoStyle={styles.opcionTexto} style={styles.opcion} />
            <BotonOscuro texto="No, seguir la sesión." ancho={330} onPress={escuchar}
              textoStyle={styles.opcionTexto} style={styles.opcion} />
          </View>
        </>
      )}
    </Fondo>
  );
}

const styles = StyleSheet.create({
  escucho: {
    fontFamily: fuentes.tituloSlab, color: colores.verdeTexto, fontSize: s(130),
    marginTop: s(130), marginBottom: s(50), textAlign: 'center',
  },
  aviso: {
    marginTop: s(50), fontFamily: fuentes.etiqueta, fontSize: s(46), color: '#8A1C1C', textAlign: 'center',
  },
  opciones: { flexDirection: 'row', gap: s(50), marginTop: s(60) },
  opcion: { borderRadius: s(40), minHeight: s(200) },
  opcionTexto: { fontSize: s(54), lineHeight: s(66) },
});