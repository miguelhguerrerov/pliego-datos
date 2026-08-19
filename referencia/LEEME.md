# Datos de referencia

Ficheros que no salen de la ingesta: se obtuvieron una vez del SERCOP y cambian
raramente. Son datos públicos.

| Fichero | Origen | Obtenido | Codificación |
|---|---|---|---|
| `cpc_clasificacion.csv` | Navegador del clasificador CPC v1, `compraspublicas.gob.ec/ProcesoContratacion/compras/CPC/index.cpe`, navegando los 5 niveles completos | 18-08-2026 | UTF-8 con BOM |
| `umbral_vae.csv` | «Umbral VAE Descarga» del portal del SERCOP (corte del umbral: 29-12-2025) | 17-08-2026 | **latin-1** — la única fuente del proyecto que no es UTF-8; `src/cpc.py` lo declara explícito |

**Validación antes de entrar aquí** (18-08-2026, ver D-045):

- `cpc_clasificacion.csv`: 3 725 nodos (10 secciones, 73 divisiones, 313 grupos,
  1 192 clases, 2 137 subclases). Cero problemas de integridad (todo padre existe y es
  el prefijo del hijo). Contrastado contra el HTML del navegador oficial: 55 de 55
  nodos coinciden. Las 2 025 subclases usadas por productos del catálogo VAE existen
  todas.
- `umbral_vae.csv`: 30 098 productos con nombre oficial y umbral VAE. Cubre el 97,7 %
  de los CPC en uso y el 98,9 % del monto.

Se cargan con `python src/cpc.py` (flujo `referencia.yml`).
