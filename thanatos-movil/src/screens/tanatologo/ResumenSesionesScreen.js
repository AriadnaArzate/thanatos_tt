import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { api } from '../../api';
import { BotonClaro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Etiqueta, TarjetaRenglones, TextoRenglon, Titulo } from '../../components/Visuales';
import { colores, fuentes, s, sombraTarjeta } from '../../theme';
import { EMOCIONES, fechaCorta, nombreEmocion } from '../../util';
import { PastillaPaciente } from './DashboardPacienteScreen';

/**
 * "Resumen de sesiones": últimas emociones registradas y lo detectado en lo que habló.
 * El backend NO guarda frases para el tanatólogo: en "Palabras/Frases clave detectadas"
 * se muestran las categorías de riesgo detectadas y el resumen por temas (sin citas).
 */
export default function ResumenSesionesScreen({ navigation, route }) {
  const { paciente } = route.params;
  const [metricas, setMetricas] = useState(null);
  const [info, setInfo] = useState(null);
  const [resumen, setResumen] = useState(null);
  const [generando, setGenerando] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.metricas(paciente.id, 30).then(setMetricas).catch((e) => setError(e.message));
    api.explicacion(paciente.id).then((r) => { setInfo(r); setResumen(r.resumen); }).catch((e) => setError(e.message));
  }, [paciente.id]);

  async function generar() {
    setGenerando(true);
    setError('');
    try {
      setResumen(await api.generarResumen(paciente.id, 7));
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerando(false);
    }
  }

  const ultimas = (metricas?.emociones_linea_de_tiempo ?? []).slice(-5).reverse();
  const categorias = info?.detalle ?? [];

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Titulo tamano={96} style={{ marginTop: s(20), marginBottom: s(20) }}>Resumen de sesiones</Titulo>

      <Etiqueta style={styles.subtitulo}>Últimas emociones registradas:</Etiqueta>
      <View style={styles.tabla}>
        <View style={styles.filaTabla}>
          <Text style={[styles.celda, styles.encabezado]}>Emoción</Text>
          <View style={styles.divisor} />
          <Text style={[styles.celda, styles.encabezado]}>Fecha</Text>
        </View>
        {ultimas.length === 0 && (
          <Text style={[styles.celda, { textAlign: 'center', paddingVertical: s(30) }]}>
            {metricas ? 'Sin registros en los últimos 30 días' : '…'}
          </Text>
        )}
        {ultimas.map((e, i) => (
          <View key={i} style={styles.filaTabla}>
            <Text style={styles.celda}>{EMOCIONES[e.emocion]?.emoji ?? ''} {nombreEmocion(e.emocion)}</Text>
            <View style={styles.divisor} />
            <Text style={styles.celda}>{fechaCorta(e.creado_en)}</Text>
          </View>
        ))}
      </View>

      <Etiqueta style={[styles.subtitulo, { marginTop: s(60) }]}>Palabras/Frases clave detectadas:</Etiqueta>
      <TarjetaRenglones minRenglones={10}>
        {info && categorias.length === 0 && <TextoRenglon>No se detectaron señales de riesgo.</TextoRenglon>}
        {categorias.map((d) => (
          <TextoRenglon key={d.categoria}>• {d.descripcion} ({d.veces})</TextoRenglon>
        ))}
        {resumen?.texto ? (
          <>
            <TextoRenglon style={styles.negritas}>Lo que ha hablado:</TextoRenglon>
            <TextoRenglon>{resumen.texto}</TextoRenglon>
            {resumen.desactualizado && <TextoRenglon>(Habló después de este resumen.)</TextoRenglon>}
          </>
        ) : null}
      </TarjetaRenglones>

      {error ? <Text style={styles.error}>{error}</Text> : null}
      <BotonClaro texto={generando ? 'Generando…' : resumen ? 'Actualizar resumen' : 'Generar resumen'}
        onPress={generar} cargando={generando} ancho={600} style={{ marginTop: s(50) }} />
      {generando && <Text style={styles.nota}>Esto puede tardar un par de minutos.</Text>}

      <PastillaPaciente paciente={paciente} />
    </Fondo>
  );
}

const styles = StyleSheet.create({
  subtitulo: { alignSelf: 'flex-start', marginLeft: s(30) },
  tabla: {
    width: s(830), backgroundColor: colores.gris, borderRadius: s(50), paddingVertical: s(10),
    paddingHorizontal: s(20), ...sombraTarjeta,
  },
  filaTabla: { flexDirection: 'row', alignItems: 'stretch', minHeight: s(80) },
  divisor: { width: s(5), backgroundColor: '#111' },
  celda: { flex: 1, fontFamily: fuentes.etiqueta, fontSize: s(40), color: colores.texto, paddingHorizontal: s(16), paddingVertical: s(10) },
  encabezado: { fontFamily: fuentes.boton, fontSize: s(50), textAlign: 'center' },
  negritas: { fontFamily: fuentes.boton },
  error: { color: '#8A1C1C', fontSize: s(42), marginTop: s(30), textAlign: 'center' },
  nota: { fontFamily: fuentes.etiqueta, fontSize: s(38), color: colores.texto, marginTop: s(16) },
});