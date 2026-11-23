import { useEffect, useRef, useState } from 'react';
import { Animated, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Line, Path } from 'react-native-svg';
import { colores, fuentes, s, sombraTarjeta } from '../theme';

/* ---------- Títulos y textos ---------- */
export function Titulo({ children, tamano = 110, color = colores.verdeTexto, style }) {
  return (
    <Text style={[{
      fontFamily: fuentes.titulo, fontSize: s(tamano), lineHeight: s(tamano * 0.95),
      letterSpacing: -s(tamano * 0.06), color, textAlign: 'center',
    }, style]}>
      {children}
    </Text>
  );
}

/** Texto grande verde de los mensajes ("Cuando esté listo...", "Emoción registrada..."). */
export function TextoMensaje({ children, style }) {
  return <Text style={[styles.mensaje, style]}>{children}</Text>;
}

export function Etiqueta({ children, style }) {
  return <Text style={[styles.etiqueta, style]}>{children}</Text>;
}

/** Campo verde redondeado de los formularios. */
export function Campo({ etiqueta, style, ...props }) {
  return (
    <View style={[{ width: '100%', marginBottom: s(40) }, style]}>
      {etiqueta ? <Etiqueta>{etiqueta}</Etiqueta> : null}
      <TextInput
        placeholderTextColor="#E8EFE0"
        style={[styles.campo, !props.editable && props.editable !== undefined && { opacity: 0.85 }]}
        {...props}
      />
    </View>
  );
}

/* ---------- Tarjeta con renglones punteados (ejercicios, semáforo, resumen) ---------- */
const ALTO_RENGLON = 60;

export function TarjetaRenglones({ children, minRenglones = 14, style, alto }) {
  // Los renglones se dibujan con SVG (en Android un borde punteado de un solo lado no se ve)
  // y se agregan más si el texto es largo. Con `alto`, la tarjeta se desplaza por dentro.
  const [altoTexto, setAltoTexto] = useState(0);
  const renglones = Math.max(minRenglones, Math.ceil(altoTexto / s(ALTO_RENGLON)) + 1);
  const altoLineas = s(ALTO_RENGLON) * renglones;

  const hoja = (
    <View style={{ paddingTop: s(40), paddingHorizontal: s(44), paddingBottom: s(48) }}>
      <View style={[StyleSheet.absoluteFill, { top: s(40), left: s(44), right: s(44) }]} pointerEvents="none">
        <Svg width="100%" height={altoLineas}>
          {Array.from({ length: renglones }).map((_, i) => {
            const y = s(ALTO_RENGLON) * (i + 1) - s(2);
            return (
              <Line key={i} x1="0" x2="100%" y1={y} y2={y}
                stroke="#5B5B5B" strokeWidth={s(3)} strokeDasharray={`${s(14)},${s(6)}`} />
            );
          })}
        </Svg>
      </View>
      <View style={{ minHeight: altoLineas }}>
        <View onLayout={(e) => setAltoTexto(e.nativeEvent.layout.height)}>{children}</View>
      </View>
    </View>
  );

  return (
    <View style={[styles.tarjeta, alto ? { height: s(alto) } : null, style]}>
      {alto ? <ScrollView>{hoja}</ScrollView> : hoja}
    </View>
  );
}

/** Texto que cae sobre los renglones de la tarjeta. */
export function TextoRenglon({ children, style }) {
  return <Text style={[styles.textoRenglon, style]}>{children}</Text>;
}

/* ---------- Onda de voz animada ("Hablar ahora" mientras responde) ---------- */
const ALTURAS = [60, 110, 200, 260, 140, 110, 160, 260, 210, 130, 120, 160, 260, 200, 110, 70, 40];

export function OndaVoz({ activa = true, ancho = 680 }) {
  const valores = useRef(ALTURAS.map(() => new Animated.Value(1))).current;

  useEffect(() => {
    if (!activa) {
      valores.forEach((v) => v.setValue(1));
      return undefined;
    }
    const animaciones = valores.map((v, i) => Animated.loop(Animated.sequence([
      Animated.timing(v, { toValue: 0.35 + ((i * 37) % 50) / 100, duration: 260 + ((i * 53) % 220), useNativeDriver: true }),
      Animated.timing(v, { toValue: 1, duration: 260 + ((i * 29) % 200), useNativeDriver: true }),
    ])));
    animaciones.forEach((a) => a.start());
    return () => animaciones.forEach((a) => a.stop());
  }, [activa, valores]);

  const anchoBarra = s(ancho) / (ALTURAS.length * 2);
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', height: s(280), width: s(ancho), justifyContent: 'space-between' }}>
      {ALTURAS.map((h, i) => (
        <Animated.View key={i} style={{
          width: anchoBarra, height: s(h), borderRadius: anchoBarra,
          backgroundColor: colores.verdeTexto, transform: [{ scaleY: valores[i] }],
        }} />
      ))}
    </View>
  );
}

/* ---------- Semáforo ---------- */
export function Semaforo({ nivel, tamano = 1 }) {
  const luz = (color, activo) => (
    <View style={{
      width: s(96 * tamano), height: s(96 * tamano), borderRadius: s(48 * tamano),
      backgroundColor: color, opacity: nivel && !activo ? 0.22 : 1, marginVertical: s(5 * tamano),
    }} />
  );
  return (
    <View style={{
      backgroundColor: colores.verdeClaro, borderRadius: s(40 * tamano),
      paddingVertical: s(10 * tamano), paddingHorizontal: s(12 * tamano), alignItems: 'center',
    }}>
      {luz(colores.rojo, nivel === 'rojo')}
      {luz(colores.amarillo, nivel === 'amarillo')}
      {luz(colores.verdeSemaforo, nivel === 'verde')}
    </View>
  );
}

/* ---------- Medidor (velocímetro de "Resumen de sesiones") ---------- */
const SEGMENTOS = ['#CDE4A9', '#E2EA7B', '#F8E46F', '#F3A055', '#EA7A78', '#E85F5F'];
const ANGULO_NIVEL = { verde: 160, amarillo: 90, rojo: 22 };

function punto(cx, cy, r, grados) {
  const rad = (grados * Math.PI) / 180;
  return [cx + r * Math.cos(rad), cy - r * Math.sin(rad)];
}

export function Medidor({ nivel, ancho = 300 }) {
  const cx = 150; const cy = 150; const rExt = 120; const rInt = 84;
  const paso = 180 / SEGMENTOS.length;
  const angulo = ANGULO_NIVEL[nivel] ?? 90;
  const [nx, ny] = punto(cx, cy, 98, angulo);
  return (
    <Svg width={s(ancho)} height={s(ancho * 0.62)} viewBox="0 0 300 186">
      {SEGMENTOS.map((color, i) => {
        const a1 = 180 - i * paso; const a2 = 180 - (i + 1) * paso;
        const [x1, y1] = punto(cx, cy, rExt, a1); const [x2, y2] = punto(cx, cy, rExt, a2);
        const [x3, y3] = punto(cx, cy, rInt, a2); const [x4, y4] = punto(cx, cy, rInt, a1);
        return (
          <Path key={color}
            d={`M${x1} ${y1} A${rExt} ${rExt} 0 0 1 ${x2} ${y2} L${x3} ${y3} A${rInt} ${rInt} 0 0 0 ${x4} ${y4} Z`}
            fill={color} stroke="#111" strokeWidth={5} strokeLinejoin="round" />
        );
      })}
      <Line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#111" strokeWidth={11} strokeLinecap="round" />
      <Line x1={cx} y1={cy} x2={nx} y2={ny} stroke="#B9A5DE" strokeWidth={5} strokeLinecap="round" />
      <Circle cx={cx} cy={cy} r={10} fill="#B9A5DE" stroke="#111" strokeWidth={4} />
    </Svg>
  );
}

/* ---------- Tarjeta gris simple y pastilla verde clara ---------- */
export function Tarjeta({ children, style }) {
  return <View style={[styles.tarjeta, styles.tarjetaSimple, style]}>{children}</View>;
}

export function Pastilla({ children, style, textoStyle }) {
  return (
    <View style={[styles.pastilla, style]}>
      <Text style={[styles.pastillaTexto, textoStyle]}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  mensaje: {
    fontFamily: fuentes.boton, color: colores.verdeTexto, fontSize: s(80),
    lineHeight: s(110), textAlign: 'center',
  },
  etiqueta: { fontFamily: fuentes.etiqueta, color: colores.texto, fontSize: s(44), marginBottom: s(16), marginLeft: s(4) },
  campo: {
    backgroundColor: colores.verdeCampo, borderRadius: s(60), minHeight: s(150),
    paddingHorizontal: s(40), fontFamily: fuentes.etiqueta, fontSize: s(54), color: colores.blanco,
  },
  tarjeta: { width: s(860), backgroundColor: colores.gris, borderRadius: s(50), overflow: 'hidden', ...sombraTarjeta },
  tarjetaSimple: { overflow: 'visible', padding: s(40), alignItems: 'center', justifyContent: 'center' },
  textoRenglon: {
    fontFamily: fuentes.etiqueta, fontSize: s(44), lineHeight: s(ALTO_RENGLON), color: colores.texto,
  },
  pastilla: {
    backgroundColor: colores.verdeClaro, borderRadius: s(60), paddingHorizontal: s(40),
    minHeight: s(120), justifyContent: 'center', alignItems: 'center',
  },
  pastillaTexto: { fontFamily: fuentes.etiqueta, fontSize: s(50), color: colores.blanco },
});