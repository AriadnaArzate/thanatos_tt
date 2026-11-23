import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Line } from 'react-native-svg';
import { api } from '../../api';
import { BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { colores, fuentes, s } from '../../theme';

const COLOR_NIVEL = { verde: colores.verdeSemaforo, amarillo: colores.amarillo, rojo: colores.rojo };

/** "Búsqueda de paciente": por número de paciente (o nombre). Solo aparecen sus pacientes. */
export default function BuscarPacienteScreen({ navigation }) {
  const [pacientes, setPacientes] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState('');

  useFocusEffect(useCallback(() => {
    let vigente = true;
    api.pacientesDashboard()
      .then((lista) => { if (vigente) { setPacientes(lista); setError(''); } })
      .catch((e) => { if (vigente) setError(e.message); })
      .finally(() => { if (vigente) setCargando(false); });
    return () => { vigente = false; };
  }, []));

  const resultados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return pacientes;
    return pacientes.filter((p) => p.usuario.toLowerCase().includes(q) || p.nombre.toLowerCase().includes(q));
  }, [busqueda, pacientes]);

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Text style={[styles.etiqueta, { marginTop: s(40) }]}>Ingrese número de paciente</Text>
      <View style={styles.buscador}>
        <TextInput style={styles.entrada} value={busqueda} onChangeText={setBusqueda}
          autoCapitalize="none" autoCorrect={false} accessibilityLabel="Número de paciente" />
        <Svg width={s(80)} height={s(80)} viewBox="0 0 24 24">
          <Circle cx={10} cy={10} r={6.5} stroke="#111" strokeWidth={1.8} fill="none" />
          <Line x1={15} y1={15} x2={21} y2={21} stroke="#111" strokeWidth={1.8} strokeLinecap="round" />
        </Svg>
      </View>

      <Text style={[styles.etiqueta, { alignSelf: 'center', marginTop: s(50) }]}>Resultados</Text>
      {cargando && <ActivityIndicator color={colores.verdeOscuro} size="large" style={{ marginTop: s(40) }} />}
      {!!error && <Text style={styles.vacio}>{error}</Text>}
      {!cargando && !error && resultados.length === 0 && (
        <Text style={styles.vacio}>{pacientes.length ? 'Ningún paciente coincide.' : 'Aún no tiene pacientes registrados.'}</Text>
      )}
      {resultados.map((p) => (
        <Pressable key={p.id} onPress={() => navigation.navigate('DashboardPaciente', { paciente: p })}
          style={({ pressed }) => [styles.resultado, { opacity: pressed ? 0.75 : 1 }]}
          accessibilityRole="button" accessibilityLabel={`Paciente ${p.usuario}, ${p.nombre}`}>
          <View style={[styles.punto, { backgroundColor: COLOR_NIVEL[p.semaforo] ?? colores.verdeSemaforo }]} />
          <Text style={styles.resultadoTexto} numberOfLines={1}>{p.usuario} · {p.nombre}</Text>
          {p.alertas_abiertas > 0 && <Text style={styles.alertas}>{p.alertas_abiertas}</Text>}
        </Pressable>
      ))}
    </Fondo>
  );
}

const styles = StyleSheet.create({
  etiqueta: { fontFamily: fuentes.etiqueta, fontSize: s(48), color: colores.texto, alignSelf: 'flex-start', marginLeft: s(60) },
  buscador: {
    flexDirection: 'row', alignItems: 'center', width: s(800), height: s(130), marginTop: s(16),
    backgroundColor: colores.verdeCampo, borderRadius: s(60), paddingHorizontal: s(36),
  },
  entrada: { flex: 1, fontFamily: fuentes.etiqueta, fontSize: s(54), color: colores.blanco },
  resultado: {
    flexDirection: 'row', alignItems: 'center', width: s(800), minHeight: s(130), marginTop: s(40),
    backgroundColor: colores.verdeClaro, borderRadius: s(60), paddingHorizontal: s(40),
  },
  punto: { width: s(40), height: s(40), borderRadius: s(20), marginRight: s(24) },
  resultadoTexto: { flex: 1, fontFamily: fuentes.etiqueta, fontSize: s(48), color: colores.texto },
  alertas: {
    backgroundColor: colores.rojo, color: colores.blanco, fontFamily: fuentes.etiqueta, fontSize: s(40),
    minWidth: s(60), textAlign: 'center', borderRadius: s(30), paddingHorizontal: s(12), overflow: 'hidden',
  },
  vacio: { fontFamily: fuentes.etiqueta, fontSize: s(46), color: colores.texto, marginTop: s(40), textAlign: 'center' },
});