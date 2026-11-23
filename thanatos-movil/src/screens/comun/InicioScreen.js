import { useEffect } from 'react';
import { ImageBackground, Pressable, StyleSheet, Text, View } from 'react-native';
import { colores, fuentes, s } from '../../theme';

const BOSQUE = require('../../../assets/bosque.jpg');

export function saludoDelMomento(fecha = new Date()) {
  const h = fecha.getHours();
  if (h >= 5 && h < 12) return 'Buenos días';
  if (h >= 12 && h < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

/** "Inicio app": bienvenida y, a los pocos segundos, el inicio de sesión. */
export default function InicioScreen({ navigation }) {
  useEffect(() => {
    const t = setTimeout(() => navigation.replace('Login'), 2800);
    return () => clearTimeout(t);
  }, [navigation]);

  return (
    <Pressable style={{ flex: 1 }} onPress={() => navigation.replace('Login')}>
      <ImageBackground source={BOSQUE} style={styles.fondo} resizeMode="cover">
        <View style={styles.bloque}>
          <Text style={styles.titulo}>Bienvenido</Text>
          <Text style={styles.saludo}>{saludoDelMomento()}</Text>
        </View>
      </ImageBackground>
    </Pressable>
  );
}

export const sombraTitulo = {
  textShadowColor: 'rgba(0,0,0,0.55)',
  textShadowOffset: { width: s(4), height: s(6) },
  textShadowRadius: s(8),
};

const styles = StyleSheet.create({
  fondo: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  bloque: {
    width: s(920), backgroundColor: colores.verdeOscuro, borderRadius: s(50),
    paddingBottom: s(36), alignItems: 'center', marginTop: s(60),
  },
  titulo: {
    fontFamily: fuentes.titulo, color: '#EDEBE6', fontSize: s(190), lineHeight: s(200),
    letterSpacing: -s(10), marginTop: -s(120), ...sombraTitulo,
  },
  saludo: { fontFamily: fuentes.accion, color: colores.blanco, fontSize: s(54), marginTop: s(4) },
});