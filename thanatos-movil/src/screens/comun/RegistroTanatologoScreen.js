import { useState } from 'react';
import { Text } from 'react-native';
import { api } from '../../api';
import { BotonClaro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Campo, Titulo } from '../../components/Visuales';
import { s } from '../../theme';

/**
 * "Registro del tanatólogo". El correo es también su usuario para iniciar sesión;
 * se agrega la contraseña porque el mockup no la tenía.
 */
export default function RegistroTanatologoScreen({ navigation }) {
  const [datos, setDatos] = useState({ nombre: '', correo: '', telefono: '', password: '', codigo: '' });
  const [pideCodigo, setPideCodigo] = useState(false);
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const cambiar = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }));

  async function guardar() {
    if (datos.nombre.trim().length < 2) return setError('Escriba su nombre.');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(datos.correo.trim())) return setError('Escriba un correo válido: será su usuario para entrar.');
    if (datos.password.length < 8) return setError('La contraseña debe tener al menos 8 caracteres.');
    setError('');
    setCargando(true);
    try {
      await api.registroTanatologo({
        nombre: datos.nombre.trim(),
        password: datos.password,
        correo: datos.correo.trim().toLowerCase(),
        telefono: datos.telefono.trim() || null,
        codigo: datos.codigo.trim() || null,
      });
      navigation.replace('Mensaje', {
        texto: 'Registro exitoso, será redirigido a la pantalla anterior para el inicio de sesión',
        destino: 'Login',
      });
    } catch (e) {
      if (e.status === 403) setPideCodigo(true);
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Titulo tamano={120} style={{ marginTop: s(10), marginBottom: s(50) }}>Registro del tanatólogo</Titulo>

      <Campo etiqueta="Nombre" value={datos.nombre} onChangeText={cambiar('nombre')} autoCapitalize="words" />
      <Campo etiqueta="Dirección de correo electrónico" value={datos.correo} onChangeText={cambiar('correo')}
        keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />
      <Campo etiqueta="Número Telefónico" value={datos.telefono} onChangeText={cambiar('telefono')} keyboardType="phone-pad" />
      <Campo etiqueta="Contraseña" value={datos.password} onChangeText={cambiar('password')} secureTextEntry autoCapitalize="none" />
      {pideCodigo && (
        <Campo etiqueta="Código de registro" value={datos.codigo} onChangeText={cambiar('codigo')} autoCapitalize="none" />
      )}

      {error ? <Text style={{ color: '#8A1C1C', fontSize: s(42), marginBottom: s(30), textAlign: 'center' }}>{error}</Text> : null}
      <BotonClaro texto="Guardar" onPress={guardar} cargando={cargando} />
    </Fondo>
  );
}