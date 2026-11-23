import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { View } from 'react-native';
import { useAuth } from '../AuthContext';
import InicioScreen from '../screens/comun/InicioScreen';
import LoginScreen from '../screens/comun/LoginScreen';
import MensajeScreen from '../screens/comun/MensajeScreen';
import RegistroTanatologoScreen from '../screens/comun/RegistroTanatologoScreen';
import { colores } from '../theme';
import PacienteNavigator from './PacienteNavigator';
import TanatologoNavigator from './TanatologoNavigator';
import { opcionesPantalla } from './opciones';

const Stack = createNativeStackNavigator();

function SinSesion() {
  return (
    <Stack.Navigator screenOptions={opcionesPantalla}>
      <Stack.Screen name="Inicio" component={InicioScreen} />
      <Stack.Screen name="Login" component={LoginScreen} />
      <Stack.Screen name="RegistroTanatologo" component={RegistroTanatologoScreen} />
      <Stack.Screen name="Mensaje" component={MensajeScreen} />
    </Stack.Navigator>
  );
}

/** Elige la vista según el rol del usuario (AppNavigator -> Paciente o Tanatólogo). */
export default function AppNavigator() {
  const { usuario, cargando } = useAuth();
  if (cargando) return <View style={{ flex: 1, backgroundColor: colores.fondo }} />;

  let contenido = <SinSesion />;
  if (usuario?.rol === 'tanatologo') contenido = <TanatologoNavigator />;
  else if (usuario?.rol === 'adulto_mayor') contenido = <PacienteNavigator />;

  return <NavigationContainer>{contenido}</NavigationContainer>;
}