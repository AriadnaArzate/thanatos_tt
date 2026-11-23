import { useEffect } from 'react';
import { View } from 'react-native';
import { BotonOscuro } from '../../components/Botones';
import Cara from '../../components/Cara';
import Fondo from '../../components/Fondo';
import { TextoMensaje } from '../../components/Visuales';
import { ESPERA_MENSAJE_MS } from '../../config';
import { s } from '../../theme';

/**
 * params:
 *   texto    -> lo que se muestra
 *   detalle  -> segunda línea opcional (por ejemplo, el PIN)
 *   destino  -> pantalla a la que se regresa (con popTo); si falta, goBack()
 *   boton    -> si viene, NO avanza solo: espera a que se toque el botón
 *   espera   -> milisegundos antes de avanzar (por defecto ESPERA_MENSAJE_MS)
 */
export default function MensajeScreen({ navigation, route }) {
  const { texto, destino, boton, espera = ESPERA_MENSAJE_MS, detalle } = route.params ?? {};

  const seguir = () => {
    if (destino) navigation.popTo(destino);
    else navigation.goBack();
  };

  useEffect(() => {
    if (boton) return undefined;
    const t = setTimeout(seguir, espera);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Fondo>
      <View style={{ marginTop: s(160) }}>
        <Cara tipo="ojos" ancho={480} />
      </View>
      <TextoMensaje style={{ marginTop: s(40), paddingHorizontal: s(20) }}>{texto}</TextoMensaje>
      {detalle ? <TextoMensaje style={{ marginTop: s(30), fontSize: s(64) }}>{detalle}</TextoMensaje> : null}
      {boton ? (
        <View style={{ marginTop: s(60) }}>
          <BotonOscuro texto={boton} onPress={seguir} />
        </View>
      ) : null}
    </Fondo>
  );
}