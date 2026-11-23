import { createNativeStackNavigator } from '@react-navigation/native-stack';
import MensajeScreen from '../screens/comun/MensajeScreen';
import EjerciciosScreen from '../screens/paciente/EjerciciosScreen';
import HablarAhoraScreen from '../screens/paciente/HablarAhoraScreen';
import MenuPacienteScreen from '../screens/paciente/MenuPacienteScreen';
import RegistrarEmocionScreen from '../screens/paciente/RegistrarEmocionScreen';
import { opcionesPantalla } from './opciones';

const Stack = createNativeStackNavigator();

/** Vista del adulto mayor. */
export default function PacienteNavigator() {
  return (
    <Stack.Navigator screenOptions={opcionesPantalla}>
      <Stack.Screen name="MenuPaciente" component={MenuPacienteScreen} />
      <Stack.Screen name="HablarAhora" component={HablarAhoraScreen} />
      <Stack.Screen name="Ejercicios" component={EjerciciosScreen} />
      <Stack.Screen name="RegistrarEmocion" component={RegistrarEmocionScreen} />
      <Stack.Screen name="Mensaje" component={MensajeScreen} />
    </Stack.Navigator>
  );
}