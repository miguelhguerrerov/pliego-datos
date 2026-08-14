# Estructura de repositorio

Documento 08. Dos repositorios, y la separación no es de orden sino de coste: en repositorios
públicos los minutos de GitHub Actions son ilimitados, y ahí corre todo el cómputo pesado.

---

## 1. `pliego-datos` — público

```
pliego-datos/
├── .github/workflows/
│   ├── ingesta-diaria.yml        cron 09:00 UTC (04:00 ECT) · mes en curso y anterior
│   ├── ingesta-semanal.yml       domingo · últimos 6 meses
│   ├── ingesta-mensual.yml       día 3 · últimos 18 meses
│   ├── ingesta-trimestral.yml    histórico completo + cuadre contra la API
│   ├── publicar-parquet.yml      release mensual con el detalle
│   ├── exportar-suscriptores.yml nocturno · vuelca tablas de usuario al repo privado
│   └── enviar-resumenes.yml      tras la ingesta diaria · Resend
├── src/
│   ├── descarga.py       bulk + reintentos + troceo por method
│   ├── codificacion.py   VALIDA utf-8; detiene la ingesta si la fuente cambia
│   ├── normaliza.py      ZIP → tablas normalizadas
│   ├── entidades.py      unificación por RUC; resolución de nombre por moda
│   ├── clasifica.py      embeddings DeepInfra + agrupamiento + etiquetado de grupos
│   ├── agrega.py         tablas agregadas → COPY a Postgres
│   ├── carga.py          conexión y carga masiva
│   ├── cobertura.py      registro de meses, huecos y % cerrado
│   ├── resumenes.py      arma y envía el correo diario o semanal
│   └── ingesta.py        orquestador con CLI
├── migraciones/
│   ├── 0001_esquema.sql        tablas base
│   ├── 0002_agregados.sql      tablas agregadas e índices
│   ├── 0003_usuarios.sql       suscriptor, perfil, envio_log, lista_espera
│   └── 0004_rls.sql            políticas de acceso por plan
├── pruebas/
│   ├── test_contrato_datos.py  falla si la fuente cambió de esquema
│   ├── test_codificacion.py    los cinco casos de latin-1
│   ├── test_presupuesto.py     falla si Postgres pasa de 420 MB
│   └── test_agregados.py       cifras de control de datos.md §9
├── docs/
│   ├── decisiones.md  datos.md  agregados.md  operacion.md  legal.md
│   └── infraestructura.md  arquitectura.md
├── CLAUDE.md
├── README.md            qué es, cómo correrlo, atribución CC BY 3.0 EC
└── requirements.txt
```

### Interfaz de línea de comandos

```bash
python src/ingesta.py --desde 2015-01 --hasta 2026-08   # backfill completo, ~1 h
python src/ingesta.py --mes 2026-08                     # un mes
python src/ingesta.py --mes 2026-08 --forzar            # reprocesa aunque esté cargado
python src/ingesta.py --incremental                     # mes en curso y anterior
python src/ingesta.py --desde-releases                  # reconstruye desde Parquet, no del SERCOP
python src/agrega.py                                    # recalcula agregados y carga
python src/clasifica.py --pendientes                    # embeddings de lo no clasificado
python src/cobertura.py --informe                       # qué falta o está incompleto
```

---

## 2. `pliego-app` — privado

```
pliego-app/
├── app/
│   ├── page.tsx                    portada
│   ├── radar/page.tsx              embudo en vivo · abierto con 24 h de retardo
│   ├── proveedor/[ruc]/page.tsx    ficha 360 · abierto e indexable
│   ├── entidad/[ruc]/page.tsx      ficha 360 · abierto e indexable
│   ├── buscar/page.tsx             búsqueda de objeto contractual
│   ├── mercado/[cpc]/page.tsx      tamaño y estacionalidad · abierto
│   ├── benchmark/[cpc]/page.tsx    TRAS EL MURO
│   ├── compradores/page.tsx        TRAS EL MURO
│   ├── perfil/page.tsx             TRAS EL MURO · alertas y frecuencia
│   ├── exportar/page.tsx           TRAS EL MURO
│   ├── precio/page.tsx             plan y lista de espera
│   ├── entrar/page.tsx             enlace mágico, sin contraseña
│   ├── legal/                      términos, privacidad, corrección de datos
│   └── api/
├── componentes/
│   ├── Cifra.tsx                   tabular + n de observaciones obligatorio
│   ├── Distribucion.tsx            el gráfico de benchmark
│   ├── FilaOportunidad.tsx
│   ├── NotaCobertura.tsx           la advertencia de datos incompletos, como componente
│   ├── Muro.tsx
│   └── Marca.tsx                   isotipo SVG
├── lib/
│   ├── supabase.ts                 solo lee agregados
│   ├── parquet.ts                  DuckDB en navegador para el detalle fino
│   ├── formato.ts                  moneda, fecha, porcentaje, RUC enmascarado
│   └── enmascarar.ts               reglas de legal.md aplicadas en la capa de datos
├── estilos/tokens.css              la paleta de marca.md
├── CLAUDE.md
└── package.json
```

---

## 3. Convenciones que no son negociables

- **Ninguna estructura se crea desde el panel de Supabase.** Todo pasa por `migraciones/`.
  Es lo que hace que migrar a la cuenta con Pro cueste media jornada y no dos días.
- **Cero referencias a proyecto, URL o claves en el código.** Todo por variables de entorno.
- **Las tablas de usuario se enlazan por correo**, no por la UUID de `auth.users`.
- **Español** en nombres de tabla, columna, función y variable. Inglés solo donde el esquema
  OCDS lo impone: `ocid`, `tag`, `tender`, `award`.
- **Un commit no deja el repositorio en estado no ejecutable.** Las pruebas de contrato y de
  presupuesto corren en cada push.

---

## 4. Secretos

| Secreto | Dónde | Para qué |
|---|---|---|
| `SUPABASE_DB_URL` | pliego-datos | Carga masiva por conexión directa |
| `SUPABASE_SERVICE_KEY` | pliego-datos | Escritura desde Actions |
| `DEEPINFRA_API_KEY` | pliego-datos | Embeddings y etiquetado |
| `RESEND_API_KEY` | pliego-datos | Envío de resúmenes |
| `REPO_PRIVADO_TOKEN` | pliego-datos | Exportación nocturna de suscriptores |
| `NEXT_PUBLIC_SUPABASE_URL` | Vercel | Lectura desde la app |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Vercel | Lectura con RLS |

**Ninguna credencial en texto plano en ningún archivo, nunca.** Las cinco que pasaron por chat
—Supabase (dos), GitHub, Resend (dos), Vercel, DeepInfra— se rotan antes del primer despliegue.

`.gitignore` incluye `.env*`, `cache/`, `*.zip`, `*.parquet` y `SUPABASE_DB_PASSWORD*`.
