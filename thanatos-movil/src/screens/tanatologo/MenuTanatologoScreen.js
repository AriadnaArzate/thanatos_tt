import { View } from 'react-native';
import { useAuth } from '../../AuthContext';
import { BotonMenu, BotonOscuro } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { s } from '../../theme';

/** "Menú" del tanatólogo. */
export default function MenuTanatologoScreen({ navigation }) {
  const { cerrarSesion } = useAuth();
  return (
    <Fondo style={{ alignItems: 'flex-start', paddingLeft: s(100) }}>
      <View style={{ gap: s(60), marginTop: s(190) }}>
        <BotonMenu icono="👤" texto="Información del Tanatólogo" ancho={680}
          onPress={() => navigation.navigate('InfoTanatologo')} />
        <BotonMenu icono="🗣️" texto="Registrar paciente" ancho={680}
          onPress={() => navigation.navigate('RegistrarPaciente')} />
        <BotonMenu icono="📊" texto="Dashboard del paciente" ancho={680}
          onPress={() => navigation.navigate('BuscarPaciente')} />
      </View>
      <View style={{ marginTop: s(160), marginLeft: s(30) }}>
        <BotonOscuro texto="Cerrar sesión" ancho={560} onPress={cerrarSesion} />
      </View>
    </Fondo>
  );
}