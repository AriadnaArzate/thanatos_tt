import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { api } from '../../api';
import { BotonOscuro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { colores, fuentes, s } from '../../theme';

// Mismo orden e ids que CATALOGO_EMOCIONES del backend (services/contexto.py).
const EMOCIONES = [
  { id: 'tristeza', etiqueta: 'Tristeza', emoji: '😢' },
  { id: 'ira_frustracion', etiqueta: 'Ira/\nFrustración', emoji: '😠' },
  { id: 'frustracion', etiqueta: 'Frustración', emoji: '😕' },
  { id: 'calma', etiqueta: 'Calma', emoji: '😌' },
  { id: 'ansiedad_miedo', etiqueta: 'Ansiedad/\nMiedo', emoji: '😟' },
  { id: 'soledad_vacio', etiqueta: 'Soledad/\nVacío', emoji: '🫥' },
];

/** "Registrar emoción": cuadrícula de 2 columnas por 3 filas. */
export default function RegistrarEmocionScreen({ navigation }) {
  const [elegida, setElegida] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  async function confirmar() {
    if (!elegida) { setError('Toque la carita que mejor describa cómo se siente.'); return; }
    setError('');
    setCargando(true);
    try {
      await api.registrarEmocion(elegida);
      navigation.replace('Mensaje', { texto: 'Emoción registrada, regresando al menú', destino: 'MenuPaciente' });
    } catch (e) {
      setError(e.message);
      setCargando(false);
    }
  }

  return (
    <Fondo scroll>
      <BotonRegresar onPress={() => navigation.goBack()} style={{ marginLeft: s(10) }} />
      <View style={styles.cuadricula}>
        {EMOCIONES.map((e) => {
          const activa = elegida === e.id;
          return (
            <Pressable key={e.id} onPress={() => setElegida(e.id)} accessibilityRole="radio"
              accessibilityState={{ selected: activa }} accessibilityLabel={e.etiqueta.replace('\n', ' ')}
              style={({ pressed }) => [styles.caja, activa && styles.cajaActiva, { opacity: pressed ? 0.8 : 1 }]}>
              <Text style={styles.emoji}>{e.emoji}</Text>
              <View style={[styles.etiqueta, activa && styles.etiquetaActiva]}>
                <Text style={[styles.etiquetaTexto, activa && { color: colores.blanco }]}>{e.etiqueta}</Text>
              </View>
            </Pressable>
          );
        })}
      </View>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <View style={{ alignSelf: 'flex-start', marginLeft: s(70), marginTop: s(40) }}>
        <BotonOscuro texto="Confirmar emoción" ancho={560} onPress={confirmar} cargando={cargando} />
      </View>
    </Fondo>
  );
}

const styles = StyleSheet.create({
  cuadricula: {
    flexDirection: 'row', flexWrap: 'wrap', width: s(760), alignSelf: 'flex-start',
    marginLeft: s(60), marginTop: s(70), columnGap: s(120), rowGap: s(70),
  },
  caja: {
    width: s(320), height: s(320), borderWidth: s(7), borderColor: '#2F3E26', borderStyle: 'dotted',
    borderRadius: s(40), justifyContent: 'center', alignItems: 'center',
  },
  cajaActiva: { backgroundColor: colores.verdeClaro, borderStyle: 'solid', borderColor: colores.verdeOscuro },
  emoji: { fontSize: s(150), marginTop: s(30) },
  etiqueta: {
    position: 'absolute', top: -s(40), right: -s(45), backgroundColor: colores.gris,
    borderColor: colores.verdeBorde, borderWidth: s(5), borderRadius: s(40),
    paddingHorizontal: s(18), paddingVertical: s(8), minWidth: s(240), alignItems: 'center',
  },
  etiquetaActiva: { backgroundColor: colores.verdeOscuro },
  etiquetaTexto: { fontFamily: fuentes.etiqueta, fontSize: s(44), color: colores.texto, textAlign: 'center' },
  error: { fontFamily: fuentes.etiqueta, fontSize: s(44), color: '#8A1C1C', marginTop: s(40), textAlign: 'center' },
});