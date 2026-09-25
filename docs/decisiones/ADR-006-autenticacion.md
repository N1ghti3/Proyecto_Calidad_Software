# ADR-006 — Autenticación del administrador mediante token de portador

- **Estado:** **Pendiente** — la decisión de mecanismo está tomada, pero quedan dos puntos abiertos que deben resolverse antes de la iteración I-3
- **Fecha:** 2026-09-25
- **Decide:** Hedixon Cardozo (backend) y Brandon Soto (frontend)
- **Respaldo en el PDF:** parcial. El PDF exige autenticación del administrador y almacenamiento de credenciales con función de derivación de clave (RNF-04), pero **no fija el mecanismo de sesión**: `DECISIÓN PROPUESTA`.

## Contexto

Solo el administrador se autentica; el comprador accede de forma anónima (PDF, apartado 9.3). El frontend es una aplicación de página única servida por C2 y consume la API en el mismo dominio.

## Alternativas consideradas

1. **Token de portador en cabecera `Authorization`**, guardado en memoria de la aplicación.
2. **Cookie de sesión** con marca `HttpOnly` y `SameSite`.
3. **Proveedor de identidad externo** (OAuth/OIDC gestionado).

| Criterio | A1 token | A2 cookie | A3 externo |
| --- | --- | --- | --- |
| Costo (R-03) | Nulo | Nulo | Puede tener costo o cuota |
| Esfuerzo (R-05) | Bajo | Medio (protección contra CSRF) | Medio-alto |
| Exposición a XSS | Media (token accesible por JavaScript si se guarda mal) | Baja | Baja |
| Exposición a CSRF | Nula | Requiere mitigación explícita | Nula |
| Dependencia externa | Ninguna | Ninguna | Alta (contradice la portabilidad de R-01) |

## Decisión

Token de portador emitido por `POST /api/v1/auth/login` (EP-10):

- se envía en `Authorization: Bearer <token>` en todo endpoint `/admin` y en `/auth/me`;
- vigencia de 8 horas, comunicada al cliente en `expiresIn`;
- se guarda **en memoria** de la aplicación durante la sesión, no en almacenamiento persistente del navegador;
- sin refresco automático: al vencer, el usuario vuelve a iniciar sesión;
- las contraseñas se almacenan con función de derivación de clave (RN-20) y el error de inicio de sesión no distingue correo inexistente de contraseña incorrecta;
- límite de 5 intentos por minuto y por cuenta (`RATE_LIMITED`), por OWASP A07.

## Puntos abiertos que mantienen el ADR en estado Pendiente

| # | Pregunta | Fecha límite | Responsable |
| --- | --- | --- | --- |
| 1 | Función de derivación de clave concreta y sus parámetros de costo, según lo que soporte la instancia de capa gratuita | Antes de I-3 | Hedixon |
| 2 | Comportamiento al recargar la página del panel: con token solo en memoria, el administrador debe iniciar sesión de nuevo. ¿Es aceptable para RNF-05 o conviene pasar a cookie `HttpOnly`? | Antes de I-3, con la primera sesión de validación con el propietario | Brandon y Hedixon |

Mientras estén abiertos, la implementación no comienza. Si el punto 2 se resuelve a favor de la cookie, se emitirá un ADR que reemplace a este.

## Consecuencias

**Positivas**

- Sin dependencia externa ni costo, coherente con R-01 y R-03.
- Sin superficie de CSRF.
- El frontend controla explícitamente cuándo hay sesión y cuándo no (`GET /auth/me`).

**Negativas / riesgos**

- Recargar la página cierra la sesión; puede afectar la percepción de operabilidad medida en RNF-05.
- Un token en memoria sigue siendo accesible desde JavaScript de la propia aplicación: la mitigación real es evitar la inyección de contenido no confiable en el panel.

## Verificación

- CP-51: todos los endpoints `/admin` responden 401 sin token.
- CP-82: ninguna contraseña en texto claro; mensajes de error sin información de existencia de cuentas.
- Prueba de usabilidad CP-83: se observa si el vencimiento o la recarga interfieren en la tarea del propietario.
