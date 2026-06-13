-- consultas_bigquery.sql
-- Consultas de analítica para el proyecto Quincena.
-- Integrante 3: Datos, Pub/Sub y BigQuery ML.
--
-- Dataset usado:
-- quincena-final-2026.quincena_analytics
--
-- Tablas usadas:
-- gastos_eventos: eventos recibidos desde Pub/Sub.
-- pronosticos: tabla para guardar resultados de proyección.
-- anomalias: tabla para guardar gastos inusuales.

-- =========================================================
-- 1. Ver últimos gastos recibidos desde Pub/Sub
-- =========================================================

SELECT
  usuario_id,
  monto,
  categoria,
  fecha,
  created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
ORDER BY created_at DESC
LIMIT 20;


-- =========================================================
-- 2. Gasto total por usuario
-- =========================================================

SELECT
  usuario_id,
  ROUND(SUM(monto), 2) AS gasto_total
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
GROUP BY usuario_id
ORDER BY gasto_total DESC;


-- =========================================================
-- 3. Gasto total por categoría
-- =========================================================

SELECT
  categoria,
  ROUND(SUM(monto), 2) AS gasto_total
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
GROUP BY categoria
ORDER BY gasto_total DESC;


-- =========================================================
-- 4. Gasto diario por usuario
-- =========================================================

SELECT
  usuario_id,
  fecha,
  ROUND(SUM(monto), 2) AS gasto_diario
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
GROUP BY usuario_id, fecha
ORDER BY fecha DESC;


-- =========================================================
-- 5. Detección simple de anomalías
-- Un gasto se considera inusual si supera:
-- promedio del usuario + 2 desviaciones estándar.
-- =========================================================

SELECT
  g.usuario_id,
  g.monto,
  g.categoria,
  g.fecha,
  'Gasto mayor al promedio + 2 desviaciones estándar' AS motivo,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos` AS g
JOIN (
  SELECT
    usuario_id,
    AVG(monto) AS promedio,
    STDDEV(monto) AS desviacion
  FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
  GROUP BY usuario_id
) AS stats
ON g.usuario_id = stats.usuario_id
WHERE g.monto > stats.promedio + 2 * stats.desviacion
ORDER BY g.monto DESC;


-- =========================================================
-- 6. Insertar anomalías detectadas en la tabla anomalias
-- =========================================================

INSERT INTO `quincena-final-2026.quincena_analytics.anomalias`
  (usuario_id, monto, categoria, fecha, motivo, created_at)
SELECT
  g.usuario_id,
  g.monto,
  g.categoria,
  g.fecha,
  'Gasto mayor al promedio + 2 desviaciones estándar' AS motivo,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos` AS g
JOIN (
  SELECT
    usuario_id,
    AVG(monto) AS promedio,
    STDDEV(monto) AS desviacion
  FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
  GROUP BY usuario_id
) AS stats
ON g.usuario_id = stats.usuario_id
WHERE g.monto > stats.promedio + 2 * stats.desviacion;


-- =========================================================
-- 7. Proyección simple mensual por usuario
-- Estima gasto mensual con:
-- gasto acumulado / día actual * días del mes.
-- =========================================================

SELECT
  usuario_id,
  FORMAT_DATE('%Y-%m', CURRENT_DATE()) AS mes,
  ROUND(SUM(monto), 2) AS gastado,
  ROUND(
    SUM(monto) / EXTRACT(DAY FROM CURRENT_DATE())
    * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE())),
    2
  ) AS proyectado,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
WHERE EXTRACT(MONTH FROM fecha) = EXTRACT(MONTH FROM CURRENT_DATE())
  AND EXTRACT(YEAR FROM fecha) = EXTRACT(YEAR FROM CURRENT_DATE())
GROUP BY usuario_id;


-- =========================================================
-- 8. Insertar pronóstico simple en tabla pronosticos
-- Nota: normal_mensual se deja como valor base de demo.
-- En una versión completa puede venir desde Cloud SQL o una tabla de usuarios.
-- =========================================================

INSERT INTO `quincena-final-2026.quincena_analytics.pronosticos`
  (usuario_id, mes, gastado, proyectado, normal_mensual, safe_to_spend, created_at)
SELECT
  usuario_id,
  FORMAT_DATE('%Y-%m', CURRENT_DATE()) AS mes,
  ROUND(SUM(monto), 2) AS gastado,
  ROUND(
    SUM(monto) / EXTRACT(DAY FROM CURRENT_DATE())
    * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE())),
    2
  ) AS proyectado,
  6900.00 AS normal_mensual,
  ROUND(
    GREATEST(
      6900.00 - (
        SUM(monto) / EXTRACT(DAY FROM CURRENT_DATE())
        * EXTRACT(DAY FROM LAST_DAY(CURRENT_DATE()))
      ),
      0
    ),
    2
  ) AS safe_to_spend,
  CURRENT_TIMESTAMP() AS created_at
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
WHERE EXTRACT(MONTH FROM fecha) = EXTRACT(MONTH FROM CURRENT_DATE())
  AND EXTRACT(YEAR FROM fecha) = EXTRACT(YEAR FROM CURRENT_DATE())
GROUP BY usuario_id;


-- =========================================================
-- 9. BigQuery ML: crear modelo ARIMA_PLUS para pronóstico
-- Requiere más datos históricos para ser útil.
-- Con pocos datos sirve como evidencia de integración ML.
-- =========================================================

CREATE OR REPLACE MODEL `quincena-final-2026.quincena_analytics.modelo_gasto_arima`
OPTIONS(
  MODEL_TYPE='ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL='fecha',
  TIME_SERIES_DATA_COL='gasto_diario',
  TIME_SERIES_ID_COL='usuario_id',
  AUTO_ARIMA=TRUE,
  DATA_FREQUENCY='DAILY'
) AS
SELECT
  usuario_id,
  fecha,
  SUM(monto) AS gasto_diario
FROM `quincena-final-2026.quincena_analytics.gastos_eventos`
GROUP BY usuario_id, fecha;


-- =========================================================
-- 10. BigQuery ML: obtener pronóstico con ML.FORECAST
-- Horizonte: 30 días.
-- =========================================================

SELECT
  *
FROM ML.FORECAST(
  MODEL `quincena-final-2026.quincena_analytics.modelo_gasto_arima`,
  STRUCT(30 AS horizon, 0.8 AS confidence_level)
);


-- =========================================================
-- 11. Consultar resultados guardados en pronosticos
-- =========================================================

SELECT
  usuario_id,
  mes,
  gastado,
  proyectado,
  normal_mensual,
  safe_to_spend,
  created_at
FROM `quincena-final-2026.quincena_analytics.pronosticos`
ORDER BY created_at DESC
LIMIT 20;


-- =========================================================
-- 12. Consultar anomalías guardadas
-- =========================================================

SELECT
  usuario_id,
  monto,
  categoria,
  fecha,
  motivo,
  created_at
FROM `quincena-final-2026.quincena_analytics.anomalias`
ORDER BY created_at DESC
LIMIT 20;
