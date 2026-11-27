import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text } from 'react-native';
import { api } from '../../api';
import { BotonClaro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Medidor, Pastilla, Semaforo, Tarjeta, Titulo } from '../../components/Visuales';
import { colores, fuentes, s } from '../../theme';

/** Pastilla "Número de paciente" que va abajo a la derecha en las pantallas del dashboard. */
export function PastillaPaciente({ paciente }) {
  return <Pastilla style={styles.pastilla}>Paciente {paciente.usuario}</Pastilla>;
}

/** "Dashboard": semáforo de riesgo y resumen de sesiones; cada tarjeta abre su detalle. */
export default function DashboardPacienteScreen({ navigation, route }) {
  const { paciente } = route.params;
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');

  useFocusEffect(useCallback(() => {
    let vigente = true;
    api.explicacion(paciente.id)
      .then((r) => { if (vigente) setInfo(r); })
      .catch((e) => { if (vigente) setError(e.message); });
    return () => { vigente = false; };
  }, [paciente.id]));

  const nivel = info?.semaforo ?? paciente.semaforo;
  const abrir = (pantalla) => () => navigation.navigate(pantalla, { paciente });
    const [borrando, setBorrando] = useState(false);
  function confirmarBorrado() {
    Alert.alert(
      'Borrar paciente',
      `¿Borrar a ${paciente.nombre} y todos sus datos (emociones, sesiones, alertas)? No se puede deshacer.`,
      [
        { text: 'Cancelar', style: 'cancel' },
        {
          text: 'Borrar', style: 'destructive',
          onPress: async () => {
            setBorrando(true);
            try {
              await api.borrarPaciente(paciente.id);
              navigation.navigate('Mensaje', { texto: 'Paciente borrado', destino: 'BuscarPaciente' });
            } catch (e) {
              setError(e.message);
              setBorrando(false);
            }
          },
        },
      ],
    );
  }

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Text style={styles.nombre}>{paciente.nombre}</Text>

      <Titulo tamano={92} style={styles.titulo}>Semáforo de riesgo</Titulo>
      <Pressable onPress={abrir('SemaforoRiesgo')} accessibilityRole="button" accessibilityLabel="Ver semáforo de riesgo">
        <Tarjeta style={styles.tarjeta}>
          {info || nivel ? <Semaforo nivel={nivel} tamano={1.05} /> : <ActivityIndicator color={colores.verdeOscuro} />}
        </Tarjeta>
      </Pressable>

      <Titulo tamano={92} style={[styles.titulo, { marginTop: s(60) }]}>Resumen de sesiones</Titulo>
      <Pressable onPress={abrir('ResumenSesiones')} accessibilityRole="button" accessibilityLabel="Ver resumen de sesiones">
        <Tarjeta style={styles.tarjeta}>
          <Medidor nivel={nivel} ancho={320} />
        </Tarjeta>
      </Pressable>

            {error ? <Text style={styles.error}>{error}</Text> : null}
      <BotonClaro texto="Borrar paciente" onPress={confirmarBorrado} cargando={borrando} ancho={560}
        style={{ marginTop: s(60), borderColor: '#8A1C1C' }} />
      <PastillaPaciente paciente={paciente} />
    </Fondo>
  );
}

const styles = StyleSheet.create({
  nombre: { fontFamily: fuentes.etiqueta, fontSize: s(46), color: colores.texto, marginTop: s(10) },
  titulo: { marginTop: s(20), marginBottom: -s(30), zIndex: 1 },
  tarjeta: { width: s(770), height: s(420) },
  pastilla: { alignSelf: 'flex-end', marginTop: s(70), marginRight: -s(20) },
  error: { color: '#8A1C1C', fontSize: s(42), marginTop: s(30), textAlign: 'center' },
});