-- ============================================================
-- Indicadores desde microdatos (reproduce data/eph_resultados.csv)
-- Regla de oro: toda tasa se calcula con PONDERA.
--   TD = Σ pondera[estado=2] / Σ pondera[estado ∈ {1,2}]
-- Error estándar aproximado: sqrt(p(1-p)/n_eff), n_eff = (Σw)² / Σw² (Kish).
-- ============================================================
SET search_path TO eph;

CREATE OR REPLACE VIEW v_base AS
SELECT f.*,
       n.grupo AS grupo_ed,
       CASE WHEN f.nivel_ed = 6 THEN
            CASE f.ch12 WHEN 6 THEN 'terciario' WHEN 7 THEN 'universitario' WHEN 8 THEN 'posgrado' ELSE 'otro' END
       ELSE '-' END AS tipo_titulo,
       CASE WHEN f.edad < 25 THEN '15-24' WHEN f.edad < 45 THEN '25-44'
            WHEN f.edad < 65 THEN '45-64' ELSE '65+' END AS grupo_edad,
       -- calificación = 5° dígito del CNO (se completan ceros a la izquierda perdidos)
       CASE WHEN length(regexp_replace(f.pp04d_cod, '\D', '', 'g')) BETWEEN 3 AND 5
            THEN substr(lpad(regexp_replace(f.pp04d_cod, '\D', '', 'g'), 5, '0'), 5, 1)
            ELSE '0' END AS calificacion
FROM fact_persona_trimestre f
JOIN dim_nivel_educativo n ON n.nivel_ed = COALESCE(f.nivel_ed, 9)
WHERE f.estado IN (1, 2) AND f.pondera > 0;

-- Función auxiliar: tasa + error estándar de Kish
CREATE OR REPLACE FUNCTION kish_se(p NUMERIC, sw NUMERIC, sw2 NUMERIC)
RETURNS NUMERIC LANGUAGE sql IMMUTABLE AS
$$ SELECT CASE WHEN sw2 > 0 THEN sqrt(p * (1 - p) / (sw * sw / sw2)) END $$;

-- 1. Tasa de desocupación trimestral: total, superior completo (S) y secundario completo (M)
CREATE OR REPLACE VIEW v_td_trimestral AS
WITH g AS (
  SELECT periodo, 'ALL' AS grupo, pondera, estado FROM v_base
  UNION ALL
  SELECT periodo, grupo_ed, pondera, estado FROM v_base WHERE grupo_ed IN ('S','M')
)
SELECT periodo, grupo,
       ROUND(100 * SUM(pondera) FILTER (WHERE estado = 2) / SUM(pondera), 2)                       AS td,
       ROUND(100 * kish_se(SUM(pondera) FILTER (WHERE estado = 2) / SUM(pondera),
                           SUM(pondera), SUM(pondera * pondera)), 2)                                  AS se_pp,
       ROUND(SUM(pondera) FILTER (WHERE estado = 2) / 1000)                                           AS desocupados_miles,
       COUNT(*) FILTER (WHERE estado = 2)                                                             AS n_desocupados
FROM g GROUP BY periodo, grupo;

-- 2. Anual: Gran Mendoza vs. resto del país
CREATE OR REPLACE VIEW v_td_anual_geo AS
SELECT anio,
       CASE WHEN aglomerado = 10 THEN 'Gran Mendoza' ELSE 'Resto' END AS geo,
       grupo_ed,
       ROUND(100 * SUM(pondera) FILTER (WHERE estado = 2) / SUM(pondera), 2) AS td,
       COUNT(*) FILTER (WHERE estado = 2)                                   AS n_desocupados
FROM v_base GROUP BY 1, 2, 3;

-- 3. Graduados por tipo de título y por edad (anual)
CREATE OR REPLACE VIEW v_td_graduados AS
SELECT anio, tipo_titulo, grupo_edad,
       ROUND(100 * SUM(pondera) FILTER (WHERE estado = 2) / SUM(pondera), 2) AS td,
       COUNT(*) FILTER (WHERE estado = 2)                                   AS n_desocupados
FROM v_base WHERE grupo_ed = 'S' GROUP BY 1, 2, 3;

-- 4. Calidad del empleo de los graduados ocupados (trimestral)
CREATE OR REPLACE VIEW v_calidad_empleo AS
SELECT periodo,
       CASE WHEN grupo_ed = 'S' THEN 'S' ELSE 'resto' END AS grupo,
       -- sobrecalificación: graduados en puestos operativos o no calificados
       ROUND(100 * SUM(pondera) FILTER (WHERE calificacion IN ('3','4'))
                 / NULLIF(SUM(pondera) FILTER (WHERE calificacion IN ('1','2','3','4')), 0), 2) AS pct_puesto_operativo_o_no_calif,
       -- informalidad: asalariados sin descuento jubilatorio
       ROUND(100 * SUM(pondera) FILTER (WHERE cat_ocup = 3 AND pp07h = 2)
                 / NULLIF(SUM(pondera) FILTER (WHERE cat_ocup = 3 AND pp07h IN (1,2)), 0), 2)  AS pct_asal_sin_aportes,
       -- subocupación horaria
       ROUND(100 * SUM(pondera) FILTER (WHERE intensi = 1)
                 / NULLIF(SUM(pondera) FILTER (WHERE intensi BETWEEN 1 AND 4), 0), 2)           AS pct_subocupados
FROM v_base WHERE estado = 1 GROUP BY 1, 2;
