import { useCallback, useEffect, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { api } from '../../api';
import { modoReproduccion, reproducir } from '../../audio';
import { BotonMenu, BotonRegresar } from '../../components/Botones';
import Cara from '../../components/Cara';
import Fondo from '../../components/Fondo';
import { TarjetaRenglones, TextoMensaje, TextoRenglon } from '../../components/Visuales';
import { s } from '../../theme';

// Título de cada ejercicio, como en los mockups (ids de services/ejercicios.py del backend).
const TITULOS = {
  reminiscencia: 'Compartir un recuerdo',
  cartas_simbolicas: 'Escribir una carta',
  legado_emocional: 'Dejar mi legado',
  expresion_emocional: 'Contar cómo me siento',
};

/**
 * "Ejercicios de desahogo". Cada vez que se abre, el backend elige uno al azar y lo
 * explica en voz; aquí se muestra el texto y se reproduce el audio. Tocar al personaje
 * repite la explicación. El ejercicio se hace fuera de la app.
 */
export default function EjerciciosScreen({ navigation }) {
  const [ejercicio, setEjercicio] = useState(null);
  const [error, setError] = useState('');
  const reproduccion = useRef(null);
  const vigente = useRef(true);

  const escuchar = useCallback(async (audioUrl) => {
    reproduccion.current?.detener();
    await modoReproduccion();
    if (!vigente.current) return;
    reproduccion.current = reproducir(audioUrl);
  }, []);

  useEffect(() => {
    vigente.current = true;
    (async () => {
      try {
        const r = await api.ejercicioDesahogo();
        if (!vigente.current) return;
        setEjercicio(r);
        escuchar(r.audio_url);
      } catch (e) {
        if (vigente.current) setError(e.message);
      }
    })();
    return () => {
      vigente.current = false;
      reproduccion.current?.detener();
    };
  }, [escuchar]);

  if (!ejercicio) {
    return (
      <Fondo>
        <BotonRegresar onPress={() => navigation.goBack()} style={{ marginLeft: s(10) }} />
        <View style={{ marginTop: s(220) }}><Cara tipo="ojos" ancho={480} /></View>
        <TextoMensaje style={{ marginTop: s(50) }}>
          {error || 'Estoy eligiendo un ejercicio para usted…'}
        </TextoMensaje>
      </Fondo>
    );
  }

  const titulo = TITULOS[ejercicio.ejercicio.id] ?? ejercicio.ejercicio.nombre;
  return (
    <Fondo hojas="izquierda">
      <BotonMenu texto={titulo} ancho={680} />
      <TarjetaRenglones alto={1000} style={{ marginTop: s(60) }}>
        <TextoRenglon>{ejercicio.texto}</TextoRenglon>
      </TarjetaRenglones>

      <View style={styles.pie}>
        <BotonRegresar onPress={() => navigation.goBack()} />
        <Cara tipo="ojos" ancho={300} onPress={() => escuchar(ejercicio.audio_url)} />
      </View>
    </Fondo>
  );
}

const styles = StyleSheet.create({
  pie: {
    position: 'absolute', left: s(40), right: s(60), bottom: s(70),
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
});