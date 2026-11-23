import { useState } from 'react';
import {
  ImageBackground, KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
} from 'react-native';
import { useAuth } from '../../AuthContext';
import { BotonOscuro } from '../../components/Botones';
import { colores, fuentes, s } from '../../theme';
import { sombraTitulo } from './InicioScreen';

const BOSQUE = require('../../../assets/bosque.jpg');

/**
 * "Inicio de sesión". El adulto mayor entra con su número de paciente (usuario)
 * y su PIN de 6 dígitos (contraseña); el tanatólogo con su usuario y contraseña.
 */
export default function LoginScreen({ navigation }) {
  const { iniciarSesion } = useAuth();
  const [usuario, setUsuario] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);

  async function entrar() {
    if (!usuario.trim() || !password) {
      setError('Escriba su usuario y su contraseña.');
      return;
    }
    setError('');
    setCargando(true);
    try {
      await iniciarSesion(usuario, password);
      // AppNavigator cambia solo a la vista del rol.
    } catch (e) {
      setError(e.message);
      setCargando(false);
    }
  }

  return (
    <ImageBackground source={BOSQUE} style={{ flex: 1 }} resizeMode="cover">
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.contenido} keyboardShouldPersistTaps="handled">
          <View style={styles.bloqueTitulo}>
            <Text style={styles.titulo}>Inicio de Sesión</Text>
          </View>

          <View style={styles.formulario}>
            <Text style={styles.etiqueta}>Usuario</Text>
            <TextInput
              style={styles.campo} value={usuario} onChangeText={setUsuario}
              autoCapitalize="none" autoCorrect={false} returnKeyType="next"
              accessibilityLabel="Usuario o número de paciente"
            />
            <Text style={[styles.etiqueta, { marginTop: s(60) }]}>Contraseña</Text>
            <TextInput
              style={styles.campo} value={password} onChangeText={setPassword}
              secureTextEntry autoCapitalize="none" returnKeyType="go" onSubmitEditing={entrar}
              accessibilityLabel="Contraseña o PIN"
            />
          </View>

          {error ? <Text style={styles.error}>{error}</Text> : null}

          <Pressable onPress={() => navigation.navigate('RegistroTanatologo')} style={styles.registro} hitSlop={10}>
            <Text style={styles.registroTexto}>Registrarse como tanatólogo</Text>
          </Pressable>

          <BotonOscuro texto="Iniciar sesión" onPress={entrar} cargando={cargando} ancho={520} />
        </ScrollView>
      </KeyboardAvoidingView>
    </ImageBackground>
  );
}

const styles = StyleSheet.create({
  contenido: { flexGrow: 1, alignItems: 'center', paddingTop: s(300), paddingBottom: s(120) },
  bloqueTitulo: {
    width: s(920), backgroundColor: colores.verdeOscuro, borderRadius: s(50),
    alignItems: 'center', paddingBottom: s(18),
  },
  titulo: {
    fontFamily: fuentes.titulo, color: '#EDEBE6', fontSize: s(140), lineHeight: s(150),
    letterSpacing: -s(8), marginTop: -s(70), ...sombraTitulo,
  },
  formulario: { width: s(800), marginTop: s(150) },
  etiqueta: {
    fontFamily: fuentes.titulo, color: '#EDEBE6', fontSize: s(80), letterSpacing: -s(4),
    marginBottom: -s(18), marginLeft: s(10), zIndex: 1, ...sombraTitulo,
  },
  campo: {
    backgroundColor: colores.verdeCampo, borderColor: '#F1F1EE', borderWidth: s(9), borderRadius: s(40),
    height: s(150), paddingHorizontal: s(36), fontFamily: fuentes.etiqueta, fontSize: s(60), color: colores.blanco,
  },
  error: {
    marginTop: s(30), backgroundColor: 'rgba(255,255,255,0.92)', color: '#8A1C1C', borderRadius: s(24),
    paddingHorizontal: s(30), paddingVertical: s(14), fontFamily: fuentes.etiqueta, fontSize: s(42),
    maxWidth: s(860), textAlign: 'center',
  },
  registro: {
    marginTop: s(60), marginBottom: s(50), backgroundColor: 'rgba(191,210,168,0.85)',
    borderRadius: s(50), paddingHorizontal: s(28), paddingVertical: s(12),
  },
  registroTexto: { fontFamily: fuentes.etiqueta, color: colores.blanco, fontSize: s(46) },
});