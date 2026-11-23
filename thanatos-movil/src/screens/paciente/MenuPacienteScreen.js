import { useFocusEffect } from '@react-navigation/native';
import { useCallback, useRef, useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { api } from '../../api';
import { modoReproduccion, reproducirEnCadena } from '../../audio';
import { useAuth } from '../../AuthContext';
import { BotonMenu, BotonOscuro } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { colores, s } from '../../theme';

/** "Menú principal" del adulto mayor. */
export default function MenuPacienteScreen({ navigation }) {
  const { usuario, cerrarSesion } = useAuth();
  const [narrando, setNarrando] = useState(false);
  const [contactando, setContactando] = useState(false);
  const narracion = useRef(null);
  const yaNarroAlEntrar = useRef(false);

  const detenerNarracion = useCallback(() => {
    narracion.current?.detener();
    narracion.current = null;
    setNarrando(false);
  }, []);

  const narrarMenu = useCallback(async () => {
    if (narracion.current) { detenerNarracion(); return; }
    setNarrando(true);
    try {
      await modoReproduccion();
      const opciones = await api.guiaMenu();
      const cadena = reproducirEnCadena(opciones.map((o) => o.audio_url));
      narracion.current = cadena;
      await cadena.terminado;
    } catch {
      // Si falla la narración no se interrumpe el uso del menú.
    } finally {
      narracion.current = null;
      setNarrando(false);
    }
  }, [detenerNarracion]);

  // Con "guía auditiva" activada, el menú se narra solo la primera vez que se abre.
  useFocusEffect(useCallback(() => {
    if (usuario?.guia_auditiva && !yaNarroAlEntrar.current) {
      yaNarroAlEntrar.current = true;
      narrarMenu();
    }
    return () => detenerNarracion();
  }, [usuario?.guia_auditiva, narrarMenu, detenerNarracion]));

  const ir = (pantalla) => () => { detenerNarracion(); navigation.navigate(pantalla); };

  async function contactar() {
    detenerNarracion();
    setContactando(true);
    try {
      const r = await api.contactarTanatologo('hablar');
      navigation.navigate('Mensaje', { texto: r.mensaje || 'Ya le avisé a su tanatólogo.', destino: 'MenuPaciente' });
    } catch (e) {
      navigation.navigate('Mensaje', { texto: e.message, destino: 'MenuPaciente' });
    } finally {
      setContactando(false);
    }
  }

  return (
    <Fondo style={{ justifyContent: 'center' }}>
      <View style={styles.opciones}>
        <BotonMenu icono="💬" texto="Hablar ahora" ancho={680} onPress={ir('HablarAhora')} />
        <BotonMenu icono="❤️" texto="Ejercicios de desahogo" ancho={680} onPress={ir('Ejercicios')} />
        <BotonMenu icono="📖" texto="Registrar emoción" ancho={680} onPress={ir('RegistrarEmocion')} />
        <BotonMenu icono="👩‍⚕️" texto="Contactar a mi tanatólogo" ancho={680} onPress={contactar} deshabilitado={contactando} />
      </View>

      <View style={styles.pie}>
        <BotonOscuro texto="Cerrar sesión" ancho={560} onPress={() => { detenerNarracion(); cerrarSesion(); }} />
        <Pressable onPress={narrarMenu} accessibilityRole="button"
          accessibilityLabel={narrando ? 'Detener la guía de voz' : 'Escuchar el menú'}
          style={({ pressed }) => [styles.sonido, narrando && styles.sonidoActivo, { opacity: pressed ? 0.7 : 1 }]}>
          <IconoSonido />
        </Pressable>
      </View>
    </Fondo>
  );
}

function IconoSonido() {
  return (
    <Svg width={s(120)} height={s(120)} viewBox="0 0 24 24" fill="none">
      <Path d="M4 9h3l5-4v14l-5-4H4z" stroke="#EAF0E2" strokeWidth={1.6} strokeLinejoin="round" />
      <Path d="M15 9.5a3.5 3.5 0 0 1 0 5" stroke="#EAF0E2" strokeWidth={1.6} strokeLinecap="round" />
      <Path d="M17.5 7a7 7 0 0 1 0 10" stroke="#EAF0E2" strokeWidth={1.6} strokeLinecap="round" />
      <Path d="M20 4.5a10.5 10.5 0 0 1 0 15" stroke="#EAF0E2" strokeWidth={1.6} strokeLinecap="round" />
    </Svg>
  );
}

const styles = StyleSheet.create({
  opciones: { gap: s(36), alignItems: 'center', marginTop: -s(120) },
  pie: {
    position: 'absolute', bottom: s(140), left: 0, right: 0,
    flexDirection: 'row', justifyContent: 'flex-end', alignItems: 'center', paddingRight: s(30), gap: s(20),
  },
  sonido: {
    width: s(200), height: s(200), borderRadius: s(100), backgroundColor: colores.verde,
    borderWidth: s(12), borderColor: colores.verdeBorde, borderStyle: 'dashed',
    justifyContent: 'center', alignItems: 'center', marginBottom: s(140),
  },
  sonidoActivo: { backgroundColor: colores.verdeOscuro },
});