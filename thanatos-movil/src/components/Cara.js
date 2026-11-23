import { useEffect, useRef } from 'react';
import { Animated, Pressable } from 'react-native';
import Svg, { Circle, Ellipse, Path } from 'react-native-svg';
import { colores, s } from '../theme';

/**
 * El personaje de los mockups, dibujado en vectores para que se vea nítido.
 *  tipo:
 *   'ojos'      -> ojos abiertos (mensajes, ejercicios, terminar sesión)
 *   'escucha'   -> ojos cerrados sonriendo, verde ("Le escucho")
 *   'habla'     -> ojos cerrados con la boca abierta (cuando responde)
 *  ancho: en px del mockup (480 = tamaño de los mensajes).
 */
export default function Cara({ tipo = 'ojos', ancho = 480, onPress, animada = true }) {
  const escala = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (!animada) return undefined;
    // Respiración suave para que el personaje se sienta vivo, sin distraer.
    const ciclo = Animated.loop(Animated.sequence([
      Animated.timing(escala, { toValue: 1.03, duration: 1800, useNativeDriver: true }),
      Animated.timing(escala, { toValue: 1, duration: 1800, useNativeDriver: true }),
    ]));
    ciclo.start();
    return () => ciclo.stop();
  }, [animada, escala]);

  const w = s(ancho);
  const h = (w * 330) / 480;
  const dibujo = (
    <Animated.View style={{ transform: [{ scale: escala }] }}>
      <Svg width={w} height={h} viewBox="0 -40 480 330">
        {tipo === 'ojos' && <OjosAbiertos />}
        {tipo === 'escucha' && <Escucha />}
        {tipo === 'habla' && <Habla />}
      </Svg>
    </Animated.View>
  );
  return onPress
    ? <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel="Repetir">{dibujo}</Pressable>
    : dibujo;
}

function OjosAbiertos() {
  const negro = colores.negro;
  return (
    <>
      <Path d="M62 6 Q100 -14 150 -10" stroke={negro} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M330 -10 Q380 -12 420 8" stroke={negro} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Circle cx={115} cy={160} r={92} fill="#FFFFFF" />
      <Circle cx={365} cy={160} r={92} fill="#FFFFFF" />
      <Circle cx={140} cy={148} r={60} fill={negro} />
      <Circle cx={393} cy={148} r={60} fill={negro} />
      <Path d="M192 252 Q240 266 284 252" stroke={negro} strokeWidth={22} strokeLinecap="round" fill="none" />
    </>
  );
}

function Escucha() {
  const c = colores.verdeTexto;
  return (
    <>
      <Path d="M70 20 Q100 6 140 8" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M340 8 Q380 6 410 22" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M60 110 Q105 160 150 110" stroke={c} strokeWidth={18} strokeLinecap="round" fill="none" />
      <Path d="M330 110 Q375 160 420 110" stroke={c} strokeWidth={18} strokeLinecap="round" fill="none" />
      <Path d="M220 170 Q240 182 262 170" stroke={c} strokeWidth={18} strokeLinecap="round" fill="none" />
    </>
  );
}

function Habla() {
  const c = '#2E4A24';
  return (
    <>
      <Path d="M80 10 Q120 -8 160 6" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M320 6 Q360 -8 400 14" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M80 100 Q125 140 170 100" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M310 100 Q355 140 400 100" stroke={c} strokeWidth={16} strokeLinecap="round" fill="none" />
      <Path d="M170 130 Q240 120 312 130 Q300 200 240 196 Q180 200 170 130 Z" fill={c} />
      <Ellipse cx={240} cy={180} rx={38} ry={18} fill="#F2B5BE" />
    </>
  );
}