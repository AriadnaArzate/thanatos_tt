# Registro de validación del módulo de riesgo

- Módulo: app/services/riesgo.py, reglas versión 1.0
- Casos de prueba: data/casos_riesgo.csv (77 frases escritas por el desarrollador)
- Estado actual: SIN validación formal. Las frases, las categorías y los textos
  (respuesta de nivel rojo, nota de nivel amarillo) los definió el desarrollador.
- Resultado de las pruebas automáticas: 0 discrepancias sobre los casos del CSV y los
  112 mensajes de riesgo bajo del dataset semilla. Las pruebas no demuestran que el
  módulo detecte frases que nadie previó.

## Alcance de uso
- Este módulo es una ayuda para el prototipo, no sustituye el criterio del tanatólogo.
- No se usa con personas reales sin un protocolo humano de respaldo.