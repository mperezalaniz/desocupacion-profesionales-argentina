"""Carrusel LinkedIn (4:5, 1080x1350): desocupación de profesionales en Argentina (EPH-INDEC).
Todas las cifras se calculan desde data/eph_resultados.csv; las únicas cifras externas son
las oficiales del INDEC usadas para validar (informes de prensa EPH) y la TD 2T2026 publicada.
Uso: python etl/graficos_carrusel.py
"""
import os

import img2pdf
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch

FD = "/usr/share/fonts/truetype/google-fonts/"
for f in ["Poppins-Regular.ttf", "Poppins-Medium.ttf", "Poppins-Bold.ttf", "Poppins-Light.ttf"]:
    if os.path.exists(FD + f):
        fm.fontManager.addfont(FD + f)
plt.rcParams["font.family"] = "Poppins"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "img")
os.makedirs(OUT, exist_ok=True)

BG, NAVY, INK2, MUTED, GRID = "#F6F4EF", "#0B2545", "#4A5568", "#8A94A6", "#E3E0D8"
BLUE, ORANGE, RED, PALEBLUE = "#1F5FA8", "#D9731A", "#C0392B", "#C9D8EC"
PALEORANGE = "#F2C9A5"

AUTHOR = "Emiliano Pérez Alaniz"
ROLE = "Data Analytics · SQL · Power BI · Python"
SOURCE = "Fuente: INDEC, EPH microdatos 2T2016-1T2026 · Cálculo propio"
N = 10

# ------------------------------------------------------------------ datos
d = pd.read_csv(os.path.join(ROOT, "data", "eph_resultados.csv"), dtype={"periodo": str})


def anual_nacional(grupo):
    """TD anual total 31 aglomerados = Gran Mendoza + resto (suma de ponderados)."""
    x = d[d.tabla.isin(["GM", "RE"]) & (d.grupo == grupo)].groupby("periodo")[["num_miles", "den_miles"]].sum()
    x = x.loc["2017":"2025"]
    return (100 * x.num_miles / x.den_miles), x.num_miles / 4


def anual_calidad(tabla, grupo="S"):
    x = d[(d.tabla == tabla) & (d.grupo == grupo)].copy()
    x["anio"] = x.periodo.str[:4]
    g = x.groupby("anio")[["num_miles", "den_miles"]].sum().loc["2017":"2025"]
    return 100 * g.num_miles / g.den_miles


def val(tabla, periodo, grupo):
    return float(d[(d.tabla == tabla) & (d.periodo == periodo) & (d.grupo == grupo)].pct.iloc[0])


tdS, desS = anual_nacional("S")
tdM, _ = anual_nacional("M")
tdA, desA = anual_nacional("ALL")
years = [int(y) for y in tdS.index]
cal = anual_calidad("CAL")
inf = anual_calidad("INF")
q1 = lambda g, y: val("Q", f"{y}Q1", g)

gm = d[(d.tabla == "GM") & (d.grupo == "ALL")].set_index("periodo").pct.loc["2017":"2025"]


def f1(v, dec=1):
    return f"{v:.{dec}f}".replace(".", ",")


# chequeos de consistencia con el análisis SQL (fallan si cambian los datos)
assert round(tdS["2023"], 2) == 2.51 and round(tdS["2025"], 2) == 3.17
assert round(tdM["2023"], 2) == 6.93 and round(tdM["2025"], 2) == 7.96
assert round(tdA["2023"], 2) == 6.14 and round(tdA["2025"], 2) == 7.38
rel = lambda s: 100 * (round(s["2025"], 2) - round(s["2023"], 2)) / round(s["2023"], 2)  # sobre tasas publicadas (2 dec.)
REL_S, REL_A, REL_M = rel(tdS), rel(tdA), rel(tdM)
BR23, BR25 = round(tdM["2023"], 2) / round(tdS["2023"], 2), round(tdM["2025"], 2) / round(tdS["2025"], 2)
DES23, DES25 = desS["2023"], desS["2025"]
print(f"rel S {REL_S:.1f}  ALL {REL_A:.1f}  M {REL_M:.1f} | brecha {BR23:.2f}->{BR25:.2f} | desoc S {DES23:.0f}->{DES25:.0f}")


# ------------------------------------------------------------------ helpers
def canvas(bg=BG):
    fig = plt.figure(figsize=(10.8, 13.5), dpi=100)
    fig.patch.set_facecolor(bg)
    return fig


def header(fig, kicker, title):
    fig.text(0.07, 0.935, kicker.upper(), fontsize=17, color=ORANGE, weight="bold")
    fig.text(0.07, 0.905, title, fontsize=37, color=NAVY, weight="bold", va="top", linespacing=1.15)


def footer(fig, n, dark=False):
    c = "#9FB3CC" if dark else MUTED
    fig.text(0.07, 0.035, f"{AUTHOR}  ·  {SOURCE}", fontsize=11.5, color=c)
    fig.text(0.93, 0.035, f"{n}/{N}", fontsize=13, color=c, ha="right")
    if n < N:
        fig.text(0.93, 0.065, "desliza  ›", fontsize=13, color="#F2A65A" if dark else ORANGE,
                 ha="right", weight="medium")


def style_ax(ax):
    ax.set_facecolor(BG)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=14, length=0)
    ax.grid(axis="y", color=GRID, lw=1)
    ax.set_axisbelow(True)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}".replace(".", ",") + "%"))


def takeaway(fig, text, y=0.14):
    fig.patches.append(FancyBboxPatch((0.07, y - 0.04), 0.86, 0.095,
                                      boxstyle="round,pad=0.008,rounding_size=0.015",
                                      transform=fig.transFigure, fc="white", ec=GRID, lw=1.2))
    fig.patches.append(FancyBboxPatch((0.07, y - 0.04), 0.010, 0.095, boxstyle="square,pad=0",
                                      transform=fig.transFigure, fc=ORANGE, ec="none"))
    fig.text(0.10, y + 0.008, text, fontsize=16.5, color=NAVY, va="center", linespacing=1.45)


def subtitle(fig, text, y=0.765):
    fig.text(0.10, y, text, fontsize=15, color=INK2)


def save(fig, n):
    p = os.path.join(OUT, f"slide_{n:02d}.png")
    fig.savefig(p, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return p


def pad23(ax, xs, ys, color, fmt=lambda v: f1(v) + "%", dy=14, size=17, bold=True):
    for x, y in zip(xs, ys):
        ax.annotate(fmt(y), (x, y), xytext=(0, dy), textcoords="offset points", ha="center",
                    fontsize=size, color=color, weight="bold" if bold else "normal")


paths = []

# 1 PORTADA ------------------------------------------------------------------
fig = canvas(NAVY)
fig.text(0.07, 0.87, "ANÁLISIS DE DATOS · ARGENTINA", fontsize=18, color="#F2A65A", weight="bold")
fig.text(0.07, 0.83, "¿Hay más\nprofesionales\ndesocupados?", fontsize=64, color="white",
         weight="bold", va="top", linespacing=1.04)
fig.text(0.07, 0.56, "Lo verifiqué con los microdatos oficiales\ndel INDEC, no con percepciones.",
         fontsize=27, color=PALEBLUE, va="top", linespacing=1.3)
big = [(f"+{REL_S:.0f}%", "desocupación de\ngraduados, 2023-2025"),
       (f"{f1(cal['2025'], 0)}%", "graduados en puestos\nque no piden título"),
       ("927 mil", "registros analizados\n(40 trimestres)")]
for i, (v, l) in enumerate(big):
    x = 0.07 + i * 0.30
    fig.text(x, 0.35, v, fontsize=42, color="white", weight="bold")
    fig.text(x, 0.335, l, fontsize=15, color="#9FB3CC", va="top", linespacing=1.3)
fig.text(0.07, 0.20, "SQL (PostgreSQL)  ·  Python  ·  EPH-INDEC 2016-2026", fontsize=16, color="#9FB3CC")
fig.text(0.07, 0.12, AUTHOR, fontsize=22, color="white", weight="bold")
fig.text(0.07, 0.095, ROLE, fontsize=15, color="#9FB3CC")
fig.text(0.93, 0.065, "desliza  ›", fontsize=15, color="#F2A65A", ha="right", weight="medium")
paths.append(save(fig, 1))

# 2 MÉTODO + VALIDACIÓN --------------------------------------------------------
fig = canvas()
header(fig, "Método", "Primero: ¿los números\nson confiables?")
fig.text(0.07, 0.775, "Procesé 40 trimestres de la Encuesta Permanente de Hogares\n(personas activas, con ponderadores oficiales) y comparé\nmi cálculo con la tasa publicada por el INDEC:",
         fontsize=16, color=INK2, va="top", linespacing=1.45)
rows = [("2T2019", "2019Q2", 10.6), ("2T2023", "2023Q2", 6.2), ("4T2023", "2023Q4", 5.7),
        ("2T2024", "2024Q2", 7.6), ("2T2025", "2025Q2", 7.6), ("1T2026", "2026Q1", 7.8)]
y0 = 0.62
fig.text(0.12, y0 + 0.035, "Trimestre", fontsize=15, color=MUTED, weight="medium")
fig.text(0.45, y0 + 0.035, "Mi cálculo", fontsize=15, color=MUTED, weight="medium", ha="center")
fig.text(0.70, y0 + 0.035, "INDEC oficial", fontsize=15, color=MUTED, weight="medium", ha="center")
for i, (lab, per, of) in enumerate(rows):
    y = y0 - i * 0.052
    fig.patches.append(FancyBboxPatch((0.08, y - 0.02), 0.84, 0.042, boxstyle="round,pad=0.002,rounding_size=0.01",
                                      transform=fig.transFigure, fc="white" if i % 2 == 0 else BG, ec=GRID, lw=0.8))
    mine = val("Q", per, "ALL")
    assert abs(mine - of) < 0.06, (per, mine, of)
    fig.text(0.12, y, lab, fontsize=18, color=NAVY, weight="bold", va="center")
    fig.text(0.45, y, f1(mine, 2) + "%", fontsize=18, color=BLUE, va="center", ha="center")
    fig.text(0.70, y, f1(of) + "%", fontsize=18, color=NAVY, va="center", ha="center")
    fig.text(0.88, y, "✓", fontsize=20, color="#2E8B57", va="center", ha="center", weight="bold",
             family="DejaVu Sans")
takeaway(fig, "Coincide al decimal en todos los casos. Tasas ponderadas, mismo\ntrimestre entre años e intervalos de confianza al 95%.", y=0.21)
footer(fig, 2)
paths.append(save(fig, 2))

# 3 TD GRADUADOS ---------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 1", "La desocupación de\ngraduados sube 2 años seguidos")
ax = fig.add_axes([0.10, 0.28, 0.83, 0.46])
style_ax(ax)
col = [ORANGE if y >= 2023 else BLUE for y in years]
ax.plot(years, tdS.values, color=BLUE, lw=3, zorder=2)
ax.plot(years[-3:], tdS.values[-3:], color=ORANGE, lw=4.5, zorder=3, solid_capstyle="round")
ax.scatter(years, tdS.values, s=70, color=col, zorder=4, edgecolor=BG, lw=2)
for y in [2019, 2023, 2024, 2025]:
    v = tdS[str(y)]
    ax.annotate(f1(v) + "%", (y, v), xytext=(-18 if y == 2019 else 0, 16 if y != 2023 else -30), textcoords="offset points",
                ha="center", fontsize=18, weight="bold", color=ORANGE if y >= 2023 else NAVY)
ax.annotate("pandemia", (2020, tdS["2020"]), xytext=(0, 12), textcoords="offset points",
            ha="center", fontsize=13, color=MUTED)
ax.set_ylim(0, 5.5)
ax.set_xticks(years)
subtitle(fig, "Tasa de desocupación, población con nivel superior completo (promedio anual)")
takeaway(fig, f"De {f1(tdS['2023'], 2)}% (2023) a {f1(tdS['2025'], 2)}% (2025): +{f1(round(tdS['2025'], 2)-round(tdS['2023'], 2), 2)} p.p. Son ~{DES25:.0f} mil graduados\nbuscando trabajo (vs ~{DES23:.0f} mil). Aún por debajo de 2019 ({f1(tdS['2019'], 2)}%).")
footer(fig, 3)
paths.append(save(fig, 3))

# 4 BRECHA ---------------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 2", "El título sigue protegiendo,\npero protege menos")
ax = fig.add_axes([0.10, 0.28, 0.76, 0.46])
style_ax(ax)
ax.plot(years, tdM.values, color=PALEORANGE, lw=3.5)
ax.plot(years, tdS.values, color=BLUE, lw=3.5)
ax.text(2025.25, tdM["2025"], "Secundario\ncompleto", color=ORANGE, fontsize=15, weight="bold", va="center")
ax.text(2025.25, tdS["2025"], "Superior\ncompleto", color=BLUE, fontsize=15, weight="bold", va="center")
for y in [2023, 2025]:
    ax.plot([y, y], [tdS[str(y)], tdM[str(y)]], color=NAVY, lw=1.5, ls=(0, (2, 2)))
    r = tdM[str(y)] / tdS[str(y)]
    ax.text(y + 0.12, (tdS[str(y)] + tdM[str(y)]) / 2, f"{f1(r, 1)}x", fontsize=20, color=NAVY, weight="bold",
            va="center")
ax.set_xlim(2016.6, 2027.2)
ax.set_ylim(0, 13.5)
ax.set_xticks(years)
subtitle(fig, "Tasa de desocupación por máximo nivel educativo (promedio anual)")
takeaway(fig, f"En 2023, quien solo terminó el secundario tenía {f1(BR23, 1)} veces más desempleo\nque un graduado. En 2025, {f1(BR25, 1)} veces: la ventaja del título se achica.")
footer(fig, 4)
paths.append(save(fig, 4))

# 5 VARIACIÓN RELATIVA ------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 3", "Los graduados tuvieron\nla mayor suba relativa")
ax = fig.add_axes([0.10, 0.30, 0.83, 0.42])
style_ax(ax)
labs = ["Superior\ncompleto", "Total\npoblación", "Secundario\ncompleto"]
vals = [REL_S, REL_A, REL_M]
ax.bar(labs, vals, color=[ORANGE, PALEBLUE, PALEBLUE], width=0.55)
for i, v in enumerate(vals):
    ax.text(i, v + 0.8, f"+{f1(v)}%", ha="center", fontsize=26, color=NAVY, weight="bold")
det = [(tdS, "S"), (tdA, "A"), (tdM, "M")]
for i, (s, _) in enumerate(det):
    ax.text(i, 1.5, f"{f1(s['2023'], 2)}% › {f1(s['2025'], 2)}%", ha="center", fontsize=14,
            color="white" if i == 0 else NAVY, weight="medium")
ax.set_ylim(0, 32)
ax.tick_params(axis="x", labelsize=16)
subtitle(fig, "Variación relativa de la tasa de desocupación, 2025 vs. 2023")
takeaway(fig, "En proporción, el desempleo de profesionales creció más que el\ndel resto. Es un cambio de tendencia: venía bajando desde 2020.")
footer(fig, 5)
paths.append(save(fig, 5))

# 6 QUIÉNES ------------------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 4", "Golpea más a jóvenes\ny a terciarios")
ax = fig.add_axes([0.10, 0.28, 0.83, 0.44])
style_ax(ax)
cats = [("A", "25-44", "Graduados\n25-44 años"), ("A", "45-64", "Graduados\n45-64 años"),
        ("D", "terciario", "Título\nterciario"), ("D", "universitario", "Título\nuniversitario")]
import numpy as np
x = np.arange(len(cats))
v23 = [val(t, "2023", g) for t, g, _ in cats]
v25 = [val(t, "2025", g) for t, g, _ in cats]
ax.bar(x - 0.2, v23, 0.38, color=PALEBLUE, label="2023")
ax.bar(x + 0.2, v25, 0.38, color=ORANGE, label="2025")
for i in range(len(cats)):
    ax.text(i - 0.2, v23[i] + 0.08, f1(v23[i], 2), ha="center", fontsize=14, color=INK2)
    ax.text(i + 0.2, v25[i] + 0.08, f1(v25[i], 2), ha="center", fontsize=15, color=NAVY, weight="bold")
ax.set_xticks(x)
ax.set_xticklabels([c[2] for c in cats], fontsize=14.5)
ax.set_ylim(0, 5.2)
ax.legend(frameon=False, fontsize=15, loc="upper right", ncol=2)
subtitle(fig, "Tasa de desocupación de graduados (%), promedio anual")
takeaway(fig, f"Graduados de 25 a 44 años: {f1(v23[0], 2)}% › {f1(v25[0], 2)}%. Terciarios: {f1(v23[2], 2)}% › {f1(v25[2], 2)}%.\nLos más expuestos son quienes están construyendo su carrera.")
footer(fig, 6)
paths.append(save(fig, 6))

# 7 SOBRECALIFICACIÓN ----------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 5", "1 de cada 3 graduados\ntrabaja en puestos operativos")
ax = fig.add_axes([0.10, 0.28, 0.83, 0.46])
style_ax(ax)
cy = [int(y) for y in cal.index]
ax.bar(cy, cal.values, color=[ORANGE if y >= 2023 else PALEBLUE for y in cy], width=0.62)
cal26 = val("CAL", "2026Q1", "S")
ax.bar([2026], [cal26], color="white", edgecolor=ORANGE, lw=2, hatch="//", width=0.62)
for y, v in list(zip(cy, cal.values)) + [(2026, cal26)]:
    ax.text(y, v + 0.6, f1(v), ha="center", fontsize=13.5, color=NAVY,
            weight="bold" if y in (2019, 2025, 2026) else "normal")
ax.set_ylim(20, 37)
ax.set_xticks(cy + [2026])
ax.set_xticklabels([str(y) for y in cy] + ["1T26"])
ax.tick_params(axis="x", labelsize=12.5)
subtitle(fig, "% de graduados ocupados en puestos de calificación operativa o no calificada")
takeaway(fig, f"Subió de {f1(cal['2019'])}% (2019) a {f1(cal['2025'])}% (2025) y {f1(cal26)}% en 1T2026. La sobrecalificación\nno aparece en la tasa de desempleo, pero es parte del mismo problema.")
footer(fig, 7)
paths.append(save(fig, 7))

# 8 INFORMALIDAD ------------------------------------------------------------------------
fig = canvas()
header(fig, "Hallazgo 6", "Más graduados trabajan\nsin aportes jubilatorios")
ax = fig.add_axes([0.10, 0.28, 0.83, 0.46])
style_ax(ax)
iy = [int(y) for y in inf.index]
ax.plot(iy, inf.values, color=BLUE, lw=3.5)
ax.plot(iy[-3:], inf.values[-3:], color=ORANGE, lw=4.5)
ax.scatter(iy, inf.values, s=60, color=[ORANGE if y >= 2023 else BLUE for y in iy], zorder=4, edgecolor=BG, lw=2)
for y in [2019, 2023, 2025]:
    ax.annotate(f1(inf[str(y)]) + "%", (y, inf[str(y)]), xytext=(0, 14), textcoords="offset points",
                ha="center", fontsize=17, weight="bold", color=ORANGE if y == 2025 else NAVY)
inf2q25 = val("INF", "2025Q2", "S")
ax.set_ylim(10, 18.5)
ax.set_xticks(iy)
subtitle(fig, "% de asalariados con título superior sin descuento jubilatorio (promedio anual)")
takeaway(fig, f"{f1(inf['2025'])}% en 2025, el máximo de la serie anual. El 2T2025 marcó {f1(inf2q25)}%,\nel trimestre más alto desde 2016 (1T2026: 16,3%). Más precariedad con título.")
footer(fig, 8)
paths.append(save(fig, 8))

# 9 MENDOZA -------------------------------------------------------------------------------
fig = canvas()
header(fig, "Zoom regional", "Gran Mendoza: de estar\nmejor a igualar al país")
ax = fig.add_axes([0.10, 0.28, 0.76, 0.46])
style_ax(ax)
ax.plot(years, tdA.values, color=PALEBLUE, lw=3.5)
ax.plot(years, gm.values, color=ORANGE, lw=3.5)
ax.scatter([2026.5, 2026.5], [7.9, 8.1], s=90, color=[BLUE, ORANGE], zorder=5, edgecolor=BG, lw=2)
ax.text(2026.5, 8.75, "2T2026\noficial", ha="center", fontsize=12.5, color=NAVY, weight="medium")
ax.text(2026.75, 7.55, "País 7,9%", fontsize=13, color=BLUE, va="center", weight="bold")
ax.text(2026.75, 8.35, "Mza 8,1%", fontsize=13, color=ORANGE, va="center", weight="bold")
ax.text(2021.2, 10.2, "Total 31 aglomerados", color=BLUE, fontsize=14, weight="bold")
ax.text(2017, gm["2017"] - 1.1, "Gran Mendoza", color=ORANGE, fontsize=14, weight="bold")
for y in [2023, 2025]:
    ax.annotate(f1(gm[str(y)]) + "%", (y, gm[str(y)]), xytext=(0, -28) if y == 2023 else (30, -22), textcoords="offset points",
                ha="center", fontsize=16, weight="bold", color=ORANGE)
ax.set_xlim(2016.6, 2028.3)
ax.set_ylim(0, 13)
ax.set_xticks(years + [2026.5])
ax.set_xticklabels(["'" + str(y)[2:] for y in years] + ["2T26"])
subtitle(fig, "Tasa de desocupación total (promedio anual) y último dato oficial")
takeaway(fig, f"Mendoza pasó de {f1(gm['2023'], 1)}% (2023) a {f1(gm['2025'], 1)}% (2025) y en el 2T2026 (8,1%)\nsuperó al promedio nacional (7,9%) por primera vez desde 2021.")
footer(fig, 9)
paths.append(save(fig, 9))

# 10 VEREDICTO ---------------------------------------------------------------------------
fig = canvas(NAVY)
fig.text(0.07, 0.90, "VEREDICTO", fontsize=18, color="#F2A65A", weight="bold")
fig.text(0.07, 0.87, "La percepción es real,\ncon matices.", fontsize=46, color="white", weight="bold",
         va="top", linespacing=1.1)
items = [
    ("Sí", f"Desde 2023 hay más graduados desocupados (+{REL_S:.0f}%), más\nsobrecalificados y más informales."),
    ("Sí", "Afecta sobre todo a menores de 45 y a títulos terciarios.\nMendoza empeoró más rápido que el país."),
    ("Pero", f"La tasa ({f1(tdS['2025'])}%) sigue por debajo de 2019 ({f1(tdS['2019'])}%) y es menos\nde la mitad que la de quien solo terminó el secundario."),
]
for i, (k, t) in enumerate(items):
    y = 0.66 - i * 0.105
    fig.text(0.07, y, k, fontsize=22, color="#F2A65A", weight="bold", va="center")
    fig.text(0.19, y, t, fontsize=16.5, color=PALEBLUE, va="center", linespacing=1.4)
fig.text(0.07, 0.31, "Limitaciones: la EPH cubre 31 aglomerados urbanos; los cambios\ntrimestre a trimestre de graduados no siempre son significativos\n(por eso comparo promedios anuales); Gran Mendoza tiene muestra chica.",
         fontsize=13.5, color="#9FB3CC", va="top", linespacing=1.45)
fig.text(0.07, 0.19, "¿Lo ves en tu entorno? ¿En qué profesión?\nTe leo en comentarios.", fontsize=22,
         color="white", weight="medium", va="top", linespacing=1.3)
fig.text(0.07, 0.085, AUTHOR, fontsize=19, color="white", weight="bold")
fig.text(0.07, 0.062, "Código y datos: github.com/mperezalaniz/desocupacion-profesionales-argentina", fontsize=13, color="#9FB3CC")
fig.text(0.93, 0.035, f"{N}/{N}", fontsize=13, color="#9FB3CC", ha="right")
paths.append(save(fig, 10))

pdf = os.path.join(ROOT, "docs", "Carrusel_Desocupacion_Profesionales_Argentina.pdf")
with open(pdf, "wb") as f:
    f.write(img2pdf.convert(paths))
print(pdf)
