import { Dimensions } from 'react-native';

// Los mockups miden 1080 x 1920 px. `s()` escala los px a la pantalla del dispositivo, manteniendo la proporción. 
const { width } = Dimensions.get('window');
export const s = (px) => Math.round((px * width) / 1080);

export const colores = {
  fondo: '#F4F6F3',
  verde: '#73933E',          // botones grandes del menú
  verdeBorde: '#4E6E2E',     // borde punteado de los botones
  verdeOscuro: '#496A2F',    // "Cerrar sesión", "Iniciar sesión", triángulo de play
  verdeTexto: '#4A6B2F',     // textos y títulos
  verdeCampo: '#92AC7C',     // campos de texto
  verdeClaro: '#BFD2A8',     // resultados de búsqueda, pastilla "Número de paciente"
  gris: '#ECECED',           // tarjetas y botones "Regresar"
  sombra: '#A9C98A',
  blanco: '#FFFFFF',
  negro: '#000000',
  texto: '#1F2A17',
  rojo: '#FF3434',
  amarillo: '#FFDF5A',
  verdeSemaforo: '#00C060',
};

// Tipografías (Google Fonts vía @expo-google-fonts).
export const fuentes = {
  titulo: 'Fraunces_900Black',      // "Bienvenido", "Inicio de Sesión", "Semáforo de riesgo"
  tituloSlab: 'Fraunces_700Bold',   // "Le escucho"
  boton: 'Sanchez_400Regular',      // botones del menú y mensajes
  etiqueta: 'Questrial_400Regular', // "Regresar al anterior", etiquetas de campos
  accion: 'Delius_400Regular',      // "Cerrar sesión", "Iniciar sesión", "Confirmar emoción"
};

export const sombraTarjeta = {
  shadowColor: colores.sombra,
  shadowOffset: { width: 0, height: s(14) },
  shadowOpacity: 0.55,
  shadowRadius: s(22),
  elevation: 8,
};