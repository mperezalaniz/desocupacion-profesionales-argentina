-- ============================================================
-- Desocupación de profesionales en Argentina — modelo de datos
-- Fuente: INDEC, Encuesta Permanente de Hogares (EPH), microdatos
--         usu_individual, 2T2016–1T2026 (40 trimestres)
-- Autor: Emiliano Pérez Alaniz
-- ============================================================
DROP SCHEMA IF EXISTS eph CASCADE;
CREATE SCHEMA eph;
SET search_path TO eph;

-- ---------- MICRODATOS (una fila por persona activa y trimestre) ----------
-- Se carga con etl/procesar_eph.py a partir de usu_individual_TXX.txt
CREATE TABLE fact_persona_trimestre (
    periodo        CHAR(6),          -- '2026Q1'
    anio           SMALLINT,
    trimestre      SMALLINT,
    codusu         VARCHAR(40),
    nro_hogar      SMALLINT,
    componente     SMALLINT,
    region         SMALLINT,         -- 1 GBA, 40 NOA, 41 NEA, 42 Cuyo, 43 Pampeana, 44 Patagonia
    aglomerado     SMALLINT,         -- 10 = Gran Mendoza
    pondera        NUMERIC,          -- ponderador (obligatorio para toda tasa)
    edad           SMALLINT,         -- CH06
    ch12           SMALLINT,         -- nivel más alto cursado
    ch13           SMALLINT,         -- 1 = finalizó ese nivel
    nivel_ed       SMALLINT,         -- 1..7 (6 = superior/universitario completo)
    estado         SMALLINT,         -- 1 ocupado, 2 desocupado
    cat_ocup       SMALLINT,         -- 3 = asalariado
    intensi        SMALLINT,         -- 1 = subocupado
    pp04d_cod      VARCHAR(6),       -- CNO; el 5° dígito es la calificación
    pp07h          SMALLINT          -- 1 con / 2 sin descuento jubilatorio
);

-- ---------- DIMENSIONES ----------
CREATE TABLE dim_nivel_educativo (
    nivel_ed   SMALLINT PRIMARY KEY,
    nombre     VARCHAR(40),
    grupo      CHAR(1)               -- S sup. completo · I sup. incompleto · M sec. completo · B menos que secundario
);
INSERT INTO dim_nivel_educativo VALUES
 (1,'Primario incompleto','B'),(2,'Primario completo','B'),(3,'Secundario incompleto','B'),
 (4,'Secundario completo','M'),(5,'Superior/universitario incompleto','I'),
 (6,'Superior/universitario completo','S'),(7,'Sin instrucción','B'),(9,'Sin dato','B');

CREATE TABLE dim_calificacion (
    digito  CHAR(1) PRIMARY KEY,
    nombre  VARCHAR(20)
);
INSERT INTO dim_calificacion VALUES ('1','Profesional'),('2','Técnica'),('3','Operativa'),('4','No calificada');

CREATE TABLE dim_aglomerado (
    aglomerado SMALLINT PRIMARY KEY,
    nombre     VARCHAR(60)
);
INSERT INTO dim_aglomerado VALUES (10,'Gran Mendoza');

-- ---------- INDICADORES AGREGADOS (resultado publicado en data/) ----------
CREATE TABLE indicadores (
    tabla        VARCHAR(5),   -- Q, RE, GM, GMQ, R, A, D, CAL, INF, SUB, PRO, GCAL, GINF, GSUB
    periodo      VARCHAR(6),   -- '2026Q1' o '2025'
    grupo        VARCHAR(20),
    pct          NUMERIC(6,2), -- indicador en %
    se_pp        NUMERIC(6,2), -- error estándar aproximado (p.p.)
    num_miles    INTEGER,      -- numerador ponderado (miles de personas)
    den_miles    INTEGER,      -- denominador ponderado (miles)
    n_muestral   INTEGER       -- casos en el numerador (sin ponderar)
);

CREATE INDEX idx_fpt_periodo ON fact_persona_trimestre(periodo);
CREATE INDEX idx_fpt_aglo    ON fact_persona_trimestre(aglomerado);
