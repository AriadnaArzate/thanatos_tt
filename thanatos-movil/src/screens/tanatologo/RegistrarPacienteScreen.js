import { useState } from 'react';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { api } from '../../api';
import { BotonClaro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Campo, Etiqueta, Pastilla, Titulo } from '../../components/Visuales';
import { colores, fuentes, s } from '../../theme';

function Casilla({ marcada, onPress, etiqueta }) {
  return (
    <Pressable onPress={onPress} style={styles.casillaFila} accessibilityRole="checkbox"
      accessibilityState={{ checked: marcada }} accessibilityLabel={etiqueta} hitSlop={8}>
      <View style={[styles.casilla, marcada && styles.casillaMarcada]}>
        {marcada ? <Text style={styles.palomita}>✓</Text> : null}
      </View>
    </Pressable>
  );
}

/**
 * "Registro de Paciente". El número de paciente (su usuario) y su PIN de 6 dígitos
 * (su contraseña) los genera el sistema al registrar; se muestran en la siguiente pantalla.
 * La notificación por correo se quitó: solo queda la notificación de la app.
 */
export default function RegistrarPacienteScreen({ navigation }) {
  const [nombre, setNombre] = useState('');
  const [edad, setEdad] = useState('');
  const [telefono, setTelefono] = useState('');
  const [notificacionApp, setNotificacionApp] = useState(true);
  const [guiaAuditiva, setGuiaAuditiva] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');

  async function registrar() {
    if (nombre.trim().length < 2) return setError('Escriba el nombre del paciente.');
    const edadNum = edad ? parseInt(edad, 10) : null;
    if (edad && (Number.isNaN(edadNum) || edadNum < 18 || edadNum > 120)) return setError('Revise la edad.');
    if (guiaAuditiva === null) return setError('Indique si necesita guía auditiva.');
    setError('');
    setCargando(true);
    try {
      const p = await api.registrarPaciente({
        nombre: nombre.trim(),
        edad: edadNum,
        telefono: telefono.trim() || null,
        guia_auditiva: guiaAuditiva,
        notif_app: notificacionApp,
      });
      navigation.replace('Mensaje', {
        texto: `Paciente con número ${p.usuario} registrado correctamente. Recuerde guardar el número de ID del paciente.`,
        detalle: `PIN para entrar: ${p.pin}`,
        boton: 'Listo, ya lo guardé',
        destino: 'MenuTanatologo',
      });
    } catch (e) {
      setError(e.message);
      setCargando(false);
    }
  }

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Titulo tamano={120} style={{ marginTop: s(10), marginBottom: s(40) }}>Registro de Paciente</Titulo>

      <Campo etiqueta="Nombre" value={nombre} onChangeText={setNombre} autoCapitalize="words" />

      <View style={styles.fila}>
        <View>
          <Etiqueta>Edad</Etiqueta>
          <TextInput style={styles.edad} value={edad} onChangeText={(t) => setEdad(t.replace(/\D/g, ''))}
            keyboardType="number-pad" maxLength={3} accessibilityLabel="Edad" />
        </View>
        <View style={{ flex: 1, marginLeft: s(40) }}>
          <Etiqueta>Configuración de Notificaciones:</Etiqueta>
          <View style={styles.casillaFila}>
            <Casilla marcada={notificacionApp} onPress={() => setNotificacionApp((v) => !v)} etiqueta="Notificación de la app" />
            <Pastilla style={styles.pastillaChica} textoStyle={styles.pastillaChicaTexto}>Notificación de la app</Pastilla>
          </View>
        </View>
      </View>

      <View style={[styles.fila, { alignItems: 'center', marginTop: s(30) }]}>
        <Etiqueta style={{ marginBottom: 0 }}>No. de paciente:</Etiqueta>
        <Pastilla style={[styles.pastillaChica, { marginLeft: s(20), flex: 1 }]} textoStyle={styles.pastillaChicaTexto}>
          Se asigna al registrar
        </Pastilla>
      </View>

      <View style={[styles.fila, { marginTop: s(40) }]}>
        <Etiqueta style={{ flex: 1, marginTop: s(10) }}>¿Necesita guía auditiva?:</Etiqueta>
        <View style={{ gap: s(20) }}>
          <View style={styles.casillaFila}>
            <Casilla marcada={guiaAuditiva === true} onPress={() => setGuiaAuditiva(true)} etiqueta="Sí necesita guía auditiva" />
            <Text style={styles.opcion}>Sí</Text>
          </View>
          <View style={styles.casillaFila}>
            <Casilla marcada={guiaAuditiva === false} onPress={() => setGuiaAuditiva(false)} etiqueta="No necesita guía auditiva" />
            <Text style={styles.opcion}>No</Text>
          </View>
        </View>
      </View>

      <Campo etiqueta={'Número telefónico\ndel paciente'} value={telefono} onChangeText={setTelefono}
        keyboardType="phone-pad" style={{ marginTop: s(20) }} />

      {error ? <Text style={styles.error}>{error}</Text> : null}
      <BotonClaro texto="Registrar" onPress={registrar} cargando={cargando} />
    </Fondo>
  );
}

const styles = StyleSheet.create({
  fila: { flexDirection: 'row', width: '100%', marginBottom: s(20) },
  edad: {
    width: s(180), height: s(150), borderRadius: s(40), backgroundColor: colores.verdeCampo,
    fontFamily: fuentes.etiqueta, fontSize: s(60), color: colores.blanco, textAlign: 'center',
  },
  casillaFila: { flexDirection: 'row', alignItems: 'center' },
  casilla: {
    width: s(70), height: s(60), borderWidth: s(5), borderColor: colores.verdeBorde,
    borderRadius: s(8), marginRight: s(20), justifyContent: 'center', alignItems: 'center', backgroundColor: colores.blanco,
  },
  casillaMarcada: { backgroundColor: colores.verdeOscuro },
  palomita: { color: colores.blanco, fontSize: s(44), lineHeight: s(50), fontWeight: 'bold' },
  pastillaChica: { minHeight: s(100), paddingHorizontal: s(26), flexShrink: 1 },
  pastillaChicaTexto: { fontSize: s(38), textAlign: 'center' },
  opcion: { fontFamily: fuentes.etiqueta, fontSize: s(46), color: colores.texto },
  error: { color: '#8A1C1C', fontSize: s(42), marginBottom: s(30), textAlign: 'center' },
});