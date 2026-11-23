import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import * as SecureStore from 'expo-secure-store';
import { api, onSesionExpirada, setToken } from './api';

const CLAVE_TOKEN = 'thanatos_token';
const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(true);

  const cerrarSesion = useCallback(async () => {
    setToken(null);
    setUsuario(null);
    await SecureStore.deleteItemAsync(CLAVE_TOKEN).catch(() => {});
  }, []);

  useEffect(() => {
    onSesionExpirada(() => { cerrarSesion(); });
    (async () => {
      try {
        const guardado = await SecureStore.getItemAsync(CLAVE_TOKEN);
        if (guardado) {
          setToken(guardado);
          setUsuario(await api.yo());
        }
      } catch {
        await cerrarSesion();
      } finally {
        setCargando(false);
      }
    })();
  }, [cerrarSesion]);

  const iniciarSesion = useCallback(async (nombreUsuario, password) => {
    const { access_token: t } = await api.login(nombreUsuario.trim(), password);
    setToken(t);
    const yo = await api.yo();
    await SecureStore.setItemAsync(CLAVE_TOKEN, t);
    setUsuario(yo);
    return yo;
  }, []);

  const refrescar = useCallback(async () => {
    const yo = await api.yo();
    setUsuario(yo);
    return yo;
  }, []);

  const valor = useMemo(
    () => ({ usuario, cargando, iniciarSesion, cerrarSesion, refrescar }),
    [usuario, cargando, iniciarSesion, cerrarSesion, refrescar],
  );
  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);