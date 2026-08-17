-- Pliego · el precio unitario deja de calcularse dividiendo
--
-- **Origen del cambio.** En la ficha de un proceso de obra, la tabla de items daba
-- «Acero de refuerzo, 5.063,22 kg, total $2» y «Excavacion, 827,5 m3, total $4». Los
-- totales sumaban 2.127 USD contra un referencial de 94.102,17. La suma de los renglones
-- no cuadraba con el monto del contrato, y esa es justo la comprobacion que ninguna
-- prueba hacia.
--
-- **La causa.** `unit.value.amount` NO significa lo mismo en todos los metodos:
--
--   Subasta Inversa Electronica -> el TOTAL del renglon
--   todos los demas             -> el PRECIO POR UNIDAD
--
-- Medido contra la fuente en 2025-12 y 2024-06, comparando por proceso `sum(amount)` y
-- `sum(amount*quantity)` contra el referencial (o el adjudicado donde no hay
-- referencial). La fraccion de procesos en que gana cada lectura es 100% o 0%, nunca
-- intermedia: es una regla, no una tendencia. Catalogo electronico no publica items en
-- ninguno de sus 21.623 releases, asi que no entra.
--
-- El proceso de la pantalla lo confirma al centimo: 94.102,18 calculado contra
-- 94.102,17 declarado.
--
-- **Lo que se guardaba mal.** La tabla tenia una sola columna, `monto_linea`, con el
-- `amount` crudo, y la ficha derivaba el precio unitario dividiendo entre la cantidad.
-- Eso es correcto en subasta inversa y falso en todo lo demas. Ahora se guardan las dos
-- cifras ya desglosadas por `normaliza.desglosar_renglon()`, que es el unico sitio del
-- proyecto donde vive la regla.
--
-- No hace falta arreglar las filas existentes aqui: `abiertos.py` reemplaza la tabla
-- entera en cada pasada. Escribir la regla otra vez en SQL seria tener dos copias que
-- se pueden desincronizar, que es como se llego hasta aqui. Ver docs/decisiones.md D-041.

begin;

alter table proceso_item
    add column if not exists precio_unitario numeric;

comment on column proceso_item.precio_unitario is
    'Precio por unidad, ya desglosado. En subasta inversa sale de dividir el total del '
    'renglon entre la cantidad; en el resto de metodos la fuente ya lo da asi. Nunca '
    'dividir ni multiplicar esto en la aplicacion: viene listo.';
comment on column proceso_item.monto_linea is
    'Total del renglon, ya desglosado. En subasta inversa la fuente lo da directo; en el '
    'resto es precio por cantidad. La suma de esta columna sobre un proceso tiene que '
    'aproximarse a su referencial: es la comprobacion que atrapa D-041.';

commit;
