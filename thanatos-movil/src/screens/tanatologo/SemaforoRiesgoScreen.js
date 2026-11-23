import { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { api } from '../../api';
import { BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Semaforo, TarjetaRenglones, TextoRenglon, Titulo } from '../../components/Visuales';
import { colores, s } from '../../theme';
import { PastillaPaciente } from './DashboardPacienteScreen';

/**
 * "Semáforo de riesgo": el color y POR QUÉ (categorías detectadas, nunca frases del
 * paciente). El razonamiento ya incluye la tendencia y las alertas sin atender.
 * El tanatólogo no lee las conversaciones por privacidad del paciente.
 */
export default function SemaforoRiesgoScreen({ navigation, route }) {
  const { paciente } = route.params;
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.explicacion(paciente.id).then(setInfo).catch((e) => setError(e.message));
  }, [paciente.id]);

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Titulo tamano={96} style={{ marginTop: s(20), marginBottom: s(30) }}>Semáforo de riesgo</Titulo>

      <View style={styles.zona}>
        <TarjetaRenglones minRenglones={12} style={styles.tarjeta}>
          {!info && !error && <ActivityIndicator color={colores.verdeOscuro} style={{ marginTop: s(40) }} />}
          {!!error && <TextoRenglon>{error}</TextoRenglon>}
          {info && (
            <>
              <TextoRenglon style={styles.encabezado}>El semáforo está en {info.semaforo}</TextoRenglon>
              <TextoRenglon>{info.razonamiento}</TextoRenglon>
              {info.como_se_calculo ? (
                <TextoRenglon style={{ marginTop: s(60), fontSize: s(36) }}>{info.como_se_calculo}</TextoRenglon>
              ) : null}
            </>
          )}
        </TarjetaRenglones>
        <View style={styles.semaforo}><Semaforo nivel={info?.semaforo} tamano={1} /></View>
      </View>

      <PastillaPaciente paciente={paciente} />
    </Fondo>
  );
}

const styles = StyleSheet.create({
  zona: { width: s(960), alignItems: 'flex-end' },
  tarjeta: { width: s(800), marginTop: s(40) },
  semaforo: { position: 'absolute', left: 0, top: 0 },
  encabezado: { textAlign: 'center' },
});