-- ============================================================
-- Análisis sobre la tabla de indicadores (data/eph_resultados.csv)
-- Carga: \copy eph.indicadores FROM 'data/eph_resultados.csv' WITH (FORMAT csv, HEADER true)
-- ============================================================
SET search_path TO eph;

-- 0. Validación contra cifras oficiales del INDEC (informes de prensa EPH)
SELECT i.periodo, i.pct AS td_microdatos, o.td_oficial, ROUND(i.pct - o.td_oficial, 2) AS dif
FROM indicadores i
JOIN (VALUES ('2019Q2', 10.6), ('2023Q2', 6.2), ('2023Q4', 5.7), ('2024Q2', 7.6),
             ('2025Q2', 7.6), ('2026Q1', 7.8)) AS o(periodo, td_oficial) USING (periodo)
WHERE i.tabla = 'Q' AND i.grupo = 'ALL'
ORDER BY 1;

-- 1. Tasa anual nacional por nivel educativo (Gran Mendoza + resto = total 31 aglomerados)
CREATE OR REPLACE VIEW v_td_anual_nacional AS
SELECT periodo::INT AS anio, grupo,
       SUM(num_miles) AS desoc_miles_suma,
       SUM(den_miles) AS pea_miles_suma,
       ROUND(100.0 * SUM(num_miles) / SUM(den_miles), 2) AS td
FROM indicadores
WHERE tabla IN ('GM', 'RE') AND periodo BETWEEN '2017' AND '2025'   -- años completos
GROUP BY 1, 2;

SELECT * FROM v_td_anual_nacional ORDER BY grupo, anio;

-- 2. ¿Cuánto cambió 2023 → 2025? (absoluto y relativo)
SELECT a.grupo,
       a.td AS td_2023, b.td AS td_2025,
       ROUND(b.td - a.td, 2)                   AS dif_pp,
       ROUND(100 * (b.td - a.td) / a.td, 1)    AS dif_relativa_pct,
       ROUND(a.desoc_miles_suma / 4.0)         AS desoc_prom_2023_miles,
       ROUND(b.desoc_miles_suma / 4.0)         AS desoc_prom_2025_miles
FROM v_td_anual_nacional a
JOIN v_td_anual_nacional b ON b.grupo = a.grupo AND b.anio = 2025
WHERE a.anio = 2023
ORDER BY dif_relativa_pct DESC;

-- 3. "Ventaja del título": cuántas veces más desempleo tiene quien solo terminó el secundario
SELECT m.anio, ROUND(m.td / s.td, 2) AS brecha_sec_vs_sup
FROM v_td_anual_nacional m JOIN v_td_anual_nacional s ON s.anio = m.anio AND s.grupo = 'S'
WHERE m.grupo = 'M' ORDER BY 1;

-- 4. Comparación mismo trimestre (1T) para evitar estacionalidad
SELECT periodo, grupo, pct AS td, se_pp,
       ROUND(pct - 1.96 * se_pp, 2) AS ic95_inf, ROUND(pct + 1.96 * se_pp, 2) AS ic95_sup
FROM indicadores
WHERE tabla = 'Q' AND periodo LIKE '%Q1' AND periodo >= '2019'
ORDER BY grupo, periodo;

-- 5. Graduados: tipo de título y edad
SELECT tabla, periodo, grupo, pct, se_pp, n_muestral
FROM indicadores WHERE tabla IN ('D', 'A') AND periodo IN ('2019', '2023', '2025') AND grupo <> 'otro'
ORDER BY tabla, grupo, periodo;

-- 6. Calidad del empleo de graduados: promedio anual ponderado
SELECT tabla, left(periodo, 4) AS anio, grupo,
       ROUND(100.0 * SUM(num_miles) / SUM(den_miles), 1) AS pct
FROM indicadores
WHERE tabla IN ('CAL', 'INF', 'SUB', 'PRO') AND left(periodo, 4) BETWEEN '2017' AND '2025'
GROUP BY 1, 2, 3
ORDER BY 1, 3, 2;

-- 7. Gran Mendoza vs. total nacional (anual)
SELECT g.periodo AS anio, g.pct AS td_gran_mendoza, g.se_pp, n.td AS td_nacional,
       ROUND(g.pct - n.td, 2) AS dif_pp
FROM indicadores g
JOIN v_td_anual_nacional n ON n.anio = g.periodo::INT AND n.grupo = 'ALL'
WHERE g.tabla = 'GM' AND g.grupo = 'ALL'
ORDER BY 1;
