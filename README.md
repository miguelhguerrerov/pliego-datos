# pliego-datos

Ingesta, normalización y publicación de la contratación pública del Ecuador a partir de
los datos abiertos OCDS del SERCOP.

Este repositorio es **público a propósito**: es donde corre todo el cómputo pesado —en
repositorios públicos los minutos de GitHub Actions son ilimitados— y donde se publica el
histórico limpio en Parquet, que queda disponible para cualquiera.

---

## Qué hay aquí

- **2 774 265 procedimientos** entre 2015 y agosto de 2026.
- Normalizados, con las entidades unificadas por RUC y los montos tipados.
- Publicados como Parquet mensual en los *releases* de este repositorio.
- Actualizados cada madrugada.

## Por qué existe

El portal del SERCOP publica los datos, pero recorrerlos por su API paginada son 60
peticiones por minuto y 10 registros por página: **77 horas para el histórico**. La
descarga masiva mensual lo resuelve en menos de una hora. Este repositorio automatiza esa
descarga y deja el resultado limpio y consultable.

## Uso

```bash
pip install -r requirements.txt

python src/ingesta.py --mes 2026-08 --seco       # valida el parseo, sin base de datos
python src/ingesta.py --incremental              # mes en curso y anterior
python src/ingesta.py --desde 2015-01 --hasta 2026-08
python src/cobertura.py --informe                # qué meses faltan o están incompletos

python -m pytest pruebas/ -q                     # falla si la fuente cambió de esquema
```

`--seco` no requiere Postgres ni dependencias binarias: sirve para comprobar que la
fuente sigue entregando lo que este código espera.

## Cómo está construido

```
FUENTE  →  GitHub Actions  →  ┬→  releases (Parquet, detalle íntegro)
                              └→  Postgres (solo agregados, ~460 MB)
```

El detalle **no** entra en la base de datos: vive como Parquet servido por CDN. La base
guarda solo lo que la aplicación consulta en cada carga de página. Es lo que permite
sostener once años de historia en el plan gratuito.

Las decisiones de diseño y su motivo están en [`docs/decisiones.md`](docs/decisiones.md).
El esquema exacto de la fuente, con sus huecos declarados, en
[`docs/datos.md`](docs/datos.md).

## Advertencias sobre los datos

- **Un mes tarda 4 o 5 meses en cerrar.** Los registros no solo se añaden, se completan.
  Las estadísticas de mercado excluyen los últimos 4 meses.
- **La subasta inversa electrónica no trae presupuesto referencial en el CSV**: llega
  vacío en los 24 060 casos de 2024. Sí está en la descarga JSON.
- **La descarga falla a menudo.** De 24 meses cargados en las pruebas, 10 necesitaron
  reintentos. El registro de cobertura declara qué meses están incompletos.

## Fuente y licencia

Datos del **Servicio Nacional de Contratación Pública del Ecuador**, publicados en
[Contrataciones Abiertas Ecuador](https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA)
bajo licencia **CC BY 3.0 EC**.

Pliego no está afiliado al SERCOP ni al Gobierno del Ecuador.

El código de este repositorio es de Darkmelon. Los datos derivados publicados en los
releases se distribuyen bajo la misma licencia CC BY 3.0 EC que la fuente.
