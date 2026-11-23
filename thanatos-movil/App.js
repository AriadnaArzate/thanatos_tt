import { Delius_400Regular } from '@expo-google-fonts/delius';
import { Fraunces_700Bold, Fraunces_900Black } from '@expo-google-fonts/fraunces';
import { Questrial_400Regular } from '@expo-google-fonts/questrial';
import { Sanchez_400Regular } from '@expo-google-fonts/sanchez';
import { useFonts } from 'expo-font';
import { StatusBar } from 'expo-status-bar';
import { View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { AuthProvider } from './src/AuthContext';
import AppNavigator from './src/navigation/AppNavigator';
import { colores } from './src/theme';

export default function App() {
  const [fuentesListas] = useFonts({
    Fraunces_900Black, Fraunces_700Bold, Sanchez_400Regular, Questrial_400Regular, Delius_400Regular,
  });
  if (!fuentesListas) return <View style={{ flex: 1, backgroundColor: colores.fondo }} />;

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <StatusBar style="dark" />
        <AppNavigator />
      </AuthProvider>
    </SafeAreaProvider>
  );
}