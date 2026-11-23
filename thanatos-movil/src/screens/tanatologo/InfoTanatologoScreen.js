import { useState } from 'react';
import { Text } from 'react-native';
import { api } from '../../api';
import { useAuth } from '../../AuthContext';
import { BotonClaro, BotonRegresar } from '../../components/Botones';
import Fondo from '../../components/Fondo';
import { Campo, Titulo } from '../../components/Visuales';
import { s } from '../../theme';

/** "Información del Tanatólogo": se ve con "Editar" y se modifica con "Guardar". */
export default function InfoTanatologoScreen({ navigation }) {
  const { usuario, refrescar } = useAuth();
  const inicial = { nombre: usuario?.nombre ?? '', correo: usuario?.correo ?? '', telefono: usuario?.telefono ?? '' };
  const [datos, setDatos] = useState(inicial);
  const [editando, setEditando] = useState(false);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState('');
  const cambiar = (campo) => (valor) => setDatos((d) => ({ ...d, [campo]: valor }));

  async function guardar() {
    if (datos.nombre.trim().length < 2) { setError('Escriba su nombre.'); return; }
    setError('');
    setCargando(true);
    try {
      await api.actualizarYo({
        nombre: datos.nombre.trim(),
        correo: datos.correo.trim() || null,
        telefono: datos.telefono.trim() || null,
      });
      await refrescar();
      setEditando(false);
      navigation.navigate('Mensaje', { texto: 'Información modificada con éxito' });
    } catch (e) {
      setError(e.message);
    } finally {
      setCargando(false);
    }
  }

  return (
    <Fondo scroll>
      <BotonRegresar texto="Regresar" onPress={() => navigation.goBack()} style={{ marginLeft: -s(20) }} />
      <Titulo tamano={120} style={{ marginTop: s(10), marginBottom: s(50) }}>Información del Tanatólogo</Titulo>

      <Campo etiqueta="Nombre" value={datos.nombre} onChangeText={cambiar('nombre')} editable={editando} />
      <Campo etiqueta="Dirección de correo electrónico" value={datos.correo} onChangeText={cambiar('correo')}
        editable={editando} keyboardType="email-address" autoCapitalize="none" />
      <Campo etiqueta="Número Telefónico" value={datos.telefono} onChangeText={cambiar('telefono')}
        editable={editando} keyboardType="phone-pad" />

      {error ? <Text style={{ color: '#8A1C1C', fontSize: s(42), marginBottom: s(30) }}>{error}</Text> : null}
      {editando
        ? <BotonClaro texto="Guardar" onPress={guardar} cargando={cargando} />
        : <BotonClaro texto="Editar" onPress={() => setEditando(true)} />}
    </Fondo>
  );
}