import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colores, s } from '../theme';

const HOJAS = require('../../assets/hojas.png');
const HOJAS_IZQ = require('../../assets/hojas_izquierda.png');

/**
 * Fondo verde claro con las hojas abajo, como en todos los mockups.
 *  hojas: 'completas' | 'izquierda' | 'ninguna'
 *  scroll: true para formularios (sube con el teclado).
 */
export default function Fondo({ children, hojas = 'completas', scroll = false, style }) {
  const insets = useSafeAreaInsets();
  const relleno = { paddingTop: insets.top + s(40), paddingBottom: insets.bottom + s(40) };

  return (
    <View style={styles.contenedor}>
      {hojas === 'completas' && <Image source={HOJAS} style={styles.hojas} resizeMode="cover" />}
      {hojas === 'izquierda' && <Image source={HOJAS_IZQ} style={styles.hojasIzq} resizeMode="cover" />}
      {scroll ? (
        <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <ScrollView
            contentContainerStyle={[styles.contenido, relleno, { paddingBottom: s(380) }, style]}
            keyboardShouldPersistTaps="handled"
          >
            {children}
          </ScrollView>
        </KeyboardAvoidingView>
      ) : (
        <View style={[styles.contenido, relleno, { flex: 1 }, style]}>{children}</View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  contenedor: { flex: 1, backgroundColor: colores.fondo },
  contenido: { paddingHorizontal: s(60), alignItems: 'center' },
  hojas: { position: 'absolute', left: 0, right: 0, bottom: 0, width: '100%', height: s(450) },
  hojasIzq: { position: 'absolute', left: 0, bottom: 0, width: s(500), height: s(450) },
});