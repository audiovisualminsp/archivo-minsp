# Actualización automática del índice

El índice del archivo audiovisual se actualiza solo, todos los días a las 11:00
de Argentina, **en los servidores de GitHub**. No depende de ninguna computadora
encendida.

## Qué hace cada corrida

1. Instala MEGAcmd y entra a la cuenta de MEGA
2. Lee el árbol de carpetas de 2024 en adelante
3. Lee los links públicos ya generados
4. Arma el índice de operativos
5. Lo cruza con la planilla de coberturas de Google Sheets
6. Regenera los dos buscadores
7. Publica los archivos actualizados en este mismo repositorio

Todo corre dentro de `.github/workflows/actualizar-indice.yml`.

## Si algo falla

GitHub manda un mail automáticamente a la cuenta dueña del repositorio cada vez
que una corrida falla. El detalle completo queda en la pestaña **Actions**.

Las fallas más probables:

| Qué dice el log | Qué pasó |
|---|---|
| "Faltan los secrets MEGA_EMAIL..." | No están cargados los secrets |
| "No se pudo iniciar sesion en MEGA" | Contraseña cambiada, o MEGA pidió verificación |
| "Google devolvio una pagina" | La planilla dejó de estar compartida por link |

## Correrlo a mano

Pestaña **Actions** → "Actualizar indice del archivo" → botón **Run workflow**.
Sirve para probar un cambio sin esperar al día siguiente.

## Cambiar la configuración

| Qué | Dónde |
|---|---|
| Hora de la corrida | `cron` en el workflow (está en UTC: 14:00 UTC = 11:00 ART) |
| Años que se indexan | `ANIOS_OK` en `actualizador/actualizar_indice.py` |
| Localidades | `actualizador/localidades.py` |
| Funcionarios y alias | `actualizador/funcionarios.py` |
| Trazas de rutas | `BASE` en `actualizador/rutas_map.py` |
| Planilla de origen | secret `SHEET_ID` |

## Credenciales

Están en Settings → Secrets and variables → Actions. Son dos: `MEGA_EMAIL` y
`MEGA_PASSWORD`. GitHub las guarda encriptadas, no se ven en el código ni en los
registros de ejecución, y se pueden reemplazar en cualquier momento.
