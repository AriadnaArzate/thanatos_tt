import { createNativeStackNavigator } from '@react-navigation/native-stack';
import MensajeScreen from '../screens/comun/MensajeScreen';
import BuscarPacienteScreen from '../screens/tanatologo/BuscarPacienteScreen';
import DashboardPacienteScreen from '../screens/tanatologo/DashboardPacienteScreen';
import InfoTanatologoScreen from '../screens/tanatologo/InfoTanatologoScreen';
import MenuTanatologoScreen from '../screens/tanatologo/MenuTanatologoScreen';
import RegistrarPacienteScreen from '../screens/tanatologo/RegistrarPacienteScreen';
import ResumenSesionesScreen from '../screens/tanatologo/ResumenSesionesScreen';
import SemaforoRiesgoScreen from '../screens/tanatologo/SemaforoRiesgoScreen';
import { opcionesPantalla } from './opciones';

const Stack = createNativeStackNavigator();

/** Vista del tanatólogo. */
export default function TanatologoNavigator() {
  return (
    <Stack.Navigator screenOptions={opcionesPantalla}>
      <Stack.Screen name="MenuTanatologo" component={MenuTanatologoScreen} />
      <Stack.Screen name="InfoTanatologo" component={InfoTanatologoScreen} />
      <Stack.Screen name="RegistrarPaciente" component={RegistrarPacienteScreen} />
      <Stack.Screen name="BuscarPaciente" component={BuscarPacienteScreen} />
      <Stack.Screen name="DashboardPaciente" component={DashboardPacienteScreen} />
      <Stack.Screen name="SemaforoRiesgo" component={SemaforoRiesgoScreen} />
      <Stack.Screen name="ResumenSesiones" component={ResumenSesionesScreen} />
      <Stack.Screen name="Mensaje" component={MensajeScreen} />
    </Stack.Navigator>
  );
}