import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { colores, fuentes, s, sombraTarjeta } from '../theme';

const presionado = ({ pressed }) => ({ opacity: pressed ? 0.75 : 1, transform: [{ scale: pressed ? 0.98 : 1 }] });

/** Botón verde grande con borde punteado (menús y títulos de los ejercicios). */
export function BotonMenu({ icono, texto, onPress, ancho = 560, style, deshabilitado }) {
  const contenido = (
    <View style={[styles.menu, { width: s(ancho) }, style]}>
      <Text style={styles.menuTexto}>
        {icono ? `${icono} ` : ''}{texto}
      </Text>
    </View>
  );
  if (!onPress) return contenido;
  return (
    <Pressable onPress={onPress} disabled={deshabilitado} style={presionado}
      accessibilityRole="button" accessibilityLabel={texto}>
      {contenido}
    </Pressable>
  );
}

/** "Regresar al anterior" / "Regresar": gris con borde verde, arriba a la izquierda. */
export function BotonRegresar({ onPress, texto = 'Regresar al anterior', style }) {
  return (
    <Pressable onPress={onPress} style={(e) => [presionado(e), styles.regresarCaja, style]}
      accessibilityRole="button" accessibilityLabel={texto} hitSlop={10}>
      <Text style={styles.regresarTexto}>{texto}</Text>
    </Pressable>
  );
}

/** Botón verde oscuro: "Cerrar sesión", "Iniciar sesión", "Confirmar emoción". */
export function BotonOscuro({ texto, onPress, cargando, ancho = 500, style, textoStyle }) {
  return (
    <Pressable onPress={onPress} disabled={cargando} style={presionado}
      accessibilityRole="button" accessibilityLabel={texto}>
      <View style={[styles.oscuro, { width: s(ancho) }, style]}>
        {cargando
          ? <ActivityIndicator color={colores.blanco} size="large" />
          : <Text style={[styles.oscuroTexto, textoStyle]}>{texto}</Text>}
      </View>
    </Pressable>
  );
}

/** Botón claro con borde: "Guardar", "Editar", "Registrar". */
export function BotonClaro({ texto, onPress, cargando, ancho = 360, style }) {
  return (
    <Pressable onPress={onPress} disabled={cargando} style={presionado}
      accessibilityRole="button" accessibilityLabel={texto}>
      <View style={[styles.claro, { width: s(ancho) }, style]}>
        {cargando
          ? <ActivityIndicator color={colores.verdeOscuro} />
          : <Text style={styles.claroTexto}>{texto}</Text>}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  menu: {
    backgroundColor: colores.verde,
    borderColor: colores.verdeBorde,
    borderWidth: s(12),
    borderStyle: 'dashed',
    borderRadius: s(48),
    minHeight: s(180),
    paddingHorizontal: s(30),
    paddingVertical: s(22),
    justifyContent: 'center',
    alignItems: 'center',
    ...sombraTarjeta,
  },
  menuTexto: {
    fontFamily: fuentes.boton,
    color: colores.blanco,
    fontSize: s(62),
    lineHeight: s(84),
    textAlign: 'center',
  },
  regresarCaja: {
    alignSelf: 'flex-start',
    backgroundColor: colores.gris,
    borderColor: colores.verdeBorde,
    borderWidth: s(5),
    borderRadius: s(60),
    paddingHorizontal: s(36),
    paddingVertical: s(30),
  },
  regresarTexto: { fontFamily: fuentes.etiqueta, color: colores.texto, fontSize: s(42) },
  oscuro: {
    backgroundColor: colores.verdeOscuro,
    borderRadius: s(48),
    minHeight: s(130),
    paddingHorizontal: s(30),
    paddingVertical: s(16),
    justifyContent: 'center',
    alignItems: 'center',
  },
  oscuroTexto: { fontFamily: fuentes.accion, color: colores.blanco, fontSize: s(56), textAlign: 'center' },
  claro: {
    backgroundColor: colores.gris,
    borderColor: colores.verdeBorde,
    borderWidth: s(5),
    borderRadius: s(60),
    minHeight: s(105),
    justifyContent: 'center',
    alignItems: 'center',
  },
  claroTexto: { fontFamily: fuentes.etiqueta, color: colores.texto, fontSize: s(54) },
});