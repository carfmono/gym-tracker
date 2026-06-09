"""Iron Age CSS — design tokens, component library, Streamlit overrides."""
from __future__ import annotations

GRAIN_SVG = (
    "data:image/svg+xml,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'>"
    "<filter id='n'>"
    "<feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/>"
    "<feColorMatrix type='saturate' values='0'/>"
    "</filter>"
    "<rect width='180' height='180' filter='url(%23n)'/>"
    "</svg>"
)

PALETTES: dict[str, dict[str, str]] = {
    "venice": {
        "--paper":    "#ECDEC2",
        "--card":     "#F5EBD3",
        "--ink":      "#2A1C10",
        "--ink-soft": "#6B5536",
        "--gold":     "#E2A22B",
        "--orange":   "#D2622A",
        "--brick":    "#B0392A",
        "--teal":     "#2E8C82",
        "--magenta":  "#C9456E",
    },
    "neon80s": {
        "--paper":    "#211A2E",
        "--card":     "#2D2040",
        "--ink":      "#E8E0F0",
        "--ink-soft": "#B0A0C8",
        "--gold":     "#00F5D4",
        "--orange":   "#FF6B6B",
        "--brick":    "#FF2D78",
        "--teal":     "#00D4FF",
        "--magenta":  "#FF00CC",
    },
    "leather": {
        "--paper":    "#3D2B1F",
        "--card":     "#4A3328",
        "--ink":      "#F2DEB0",
        "--ink-soft": "#C4A882",
        "--gold":     "#D4A820",
        "--orange":   "#C47A2A",
        "--brick":    "#8B3A2A",
        "--teal":     "#5A9080",
        "--magenta":  "#9A4060",
    },
}

PALETTE_LABELS = {
    "venice":  "Atardecer Venice",
    "neon80s": "Neón 80s",
    "leather": "Cuero & Oro",
}


def build_css(
    palette: str = "venice",
    accent: str | None = None,
    grain_opacity: float = 0.10,
    headline_font: str = "Anton",
) -> str:
    vars_dict = dict(PALETTES.get(palette, PALETTES["venice"]))
    if accent:
        vars_dict["--brick"] = accent
    vars_css = "\n".join(f"    {k}: {v};" for k, v in vars_dict.items())
    display_font = f"'{headline_font}'" if headline_font in ("Anton", "Alfa Slab One") else "'Anton'"

    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Anton&family=Alfa+Slab+One&family=Yellowtail&family=Space+Mono:wght@700&family=Barlow+Semi+Condensed:wght@600;700&display=swap');

:root {{
{vars_css}
    --accent: var(--brick);
    --grad:   linear-gradient(135deg,#F2B33A,#E0612A 52%,#B23A6B);
    --font-display: {display_font}, sans-serif;
    --font-script:  'Yellowtail', cursive;
    --font-mono:    'Space Mono', monospace;
    --font-body:    'Barlow Semi Condensed', sans-serif;
    --grain-opacity:{grain_opacity};
}}

/* ── Hide Streamlit chrome ── */
#MainMenu,
header[data-testid="stHeader"],
footer,
[data-testid="stToolbar"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
.stDeployButton {{ display: none !important; }}

/* ── Base ── */
html, body {{ background: var(--paper) !important; overflow-x: hidden; }}
.stApp {{
    background: var(--paper) !important;
    min-height: 100vh;
    font-family: var(--font-body) !important;
}}

/* ── Grain texture overlay ── */
.stApp::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("{GRAIN_SVG}");
    background-repeat: repeat;
    background-size: 180px 180px;
    mix-blend-mode: multiply;
    opacity: var(--grain-opacity);
    pointer-events: none;
    z-index: 9998;
}}

/* ── Content layout ── */
.block-container {{
    max-width: 430px !important;
    padding: 0 14px 88px 14px !important;
    margin: 0 auto !important;
}}
section[data-testid="stMain"] > div {{ padding-top: 0 !important; }}

/* ── Typography ── */
h1, h2, h3, h4 {{
    font-family: var(--font-display) !important;
    color: var(--ink) !important;
    line-height: 0.92 !important;
    text-transform: uppercase !important;
    letter-spacing: -0.01em !important;
    margin: 8px 0 6px !important;
}}
h1 {{ font-size: 2.0rem !important; }}
h2 {{ font-size: 1.5rem !important; }}
h3 {{ font-size: 1.15rem !important; }}
p, li {{
    font-family: var(--font-body) !important;
    color: var(--ink) !important;
    font-size: 15px !important;
}}
.stMarkdown {{ color: var(--ink) !important; }}
label {{
    font-family: var(--font-body) !important;
    color: var(--ink) !important;
    font-weight: 600 !important;
}}

/* ── Plate button — primary ── */
[data-testid="stButton"] > button {{
    background: linear-gradient(180deg,#F2C94C 0%,var(--gold) 45%,#B07018 100%) !important;
    border: 2.5px solid var(--ink) !important;
    border-radius: 10px !important;
    box-shadow: inset 0 1.5px 0 rgba(255,255,255,0.45), 0 4px 0 var(--ink) !important;
    color: var(--ink) !important;
    font-family: var(--font-display) !important;
    font-size: 14px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    padding: 12px 20px !important;
    min-height: 48px !important;
    width: 100% !important;
    transition: transform 0.08s ease, box-shadow 0.08s ease !important;
    cursor: pointer !important;
}}
[data-testid="stButton"] > button:active {{
    transform: translateY(3px) !important;
    box-shadow: inset 0 1.5px 0 rgba(255,255,255,0.45), 0 1px 0 var(--ink) !important;
}}
[data-testid="stButton"] > button[kind="secondary"] {{
    background: linear-gradient(180deg,#F0EAE0 0%,#C8BCA8 100%) !important;
    color: var(--ink-soft) !important;
    border-color: var(--ink-soft) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 4px 0 var(--ink-soft) !important;
}}
[data-testid="stButton"] > button[kind="secondary"]:active {{
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.3), 0 1px 0 var(--ink-soft) !important;
}}

/* ── Checkbox ── */
[data-testid="stCheckbox"] {{
    background: var(--card) !important;
    border: 2px solid var(--ink) !important;
    border-radius: 8px !important;
    padding: 10px 12px !important;
    margin-bottom: 5px !important;
    min-height: 44px !important;
}}
[data-testid="stCheckbox"] label {{
    font-family: var(--font-body) !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    color: var(--ink) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
}}

/* ── Metrics ── */
[data-testid="metric-container"] {{
    background: var(--card) !important;
    border: 2.5px solid var(--ink) !important;
    border-radius: 12px !important;
    box-shadow: 0 3px 0 var(--ink) !important;
    padding: 12px 14px !important;
}}
div[data-testid="stMetricValue"] {{
    font-family: var(--font-display) !important;
    font-size: 26px !important;
    line-height: 1 !important;
    color: var(--ink) !important;
}}
div[data-testid="stMetricLabel"] > p,
div[data-testid="stMetricLabel"] > div {{
    font-family: var(--font-mono) !important;
    font-size: 9px !important;
    letter-spacing: 0.18em !important;
    text-transform: uppercase !important;
    color: var(--ink-soft) !important;
}}

/* ── Expander ── */
[data-testid="stExpander"] {{
    border: 2.5px solid var(--ink) !important;
    border-radius: 12px !important;
    background: var(--card) !important;
    box-shadow: 0 3px 0 var(--ink) !important;
    margin-bottom: 10px !important;
    overflow: hidden !important;
}}
[data-testid="stExpander"] summary {{
    font-family: var(--font-display) !important;
    font-size: 13px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
    color: var(--ink) !important;
    padding: 12px 14px !important;
}}
[data-testid="stExpander"] > div > div {{
    padding: 0 12px 12px !important;
}}

/* ── Divider ── */
hr {{
    border: none !important;
    border-top: 2px dashed rgba(42,28,16,0.28) !important;
    margin: 10px 0 !important;
}}

/* ── Form inputs ── */
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stDateInput"] input {{
    background: var(--paper) !important;
    border: 2px solid var(--ink) !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
    font-family: var(--font-mono) !important;
    font-size: 13px !important;
    padding: 8px 10px !important;
}}
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    background: var(--paper) !important;
    border: 2px solid var(--ink) !important;
    border-radius: 8px !important;
    color: var(--ink) !important;
    font-family: var(--font-mono) !important;
}}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {{
    font-family: var(--font-mono) !important;
    font-size: 9px !important;
    text-transform: uppercase !important;
    letter-spacing: 0.12em !important;
    color: var(--ink-soft) !important;
    border-radius: 6px 6px 0 0 !important;
    padding: 8px 10px !important;
}}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {{
    color: var(--brick) !important;
    border-bottom: 2px solid var(--brick) !important;
    font-weight: 700 !important;
}}
[data-testid="stTabs"] [role="tablist"] {{
    background: transparent !important;
    border-bottom: 2px solid rgba(42,28,16,0.18) !important;
    overflow-x: auto !important;
    scrollbar-width: none !important;
}}
[data-testid="stTabs"] [role="tablist"]::-webkit-scrollbar {{ display: none !important; }}

/* ── Alerts ── */
[data-testid="stAlert"] {{
    border: 2.5px solid var(--ink) !important;
    border-radius: 12px !important;
    background: var(--card) !important;
    color: var(--ink) !important;
}}
[data-testid="stAlert"] p {{ color: var(--ink) !important; font-family: var(--font-body) !important; }}

/* ── Progress ── */
[data-testid="stProgress"] > div {{
    background: rgba(42,28,16,0.15) !important;
    border: 2px solid var(--ink) !important;
    border-radius: 5px !important;
    height: 16px !important;
    overflow: hidden !important;
    padding: 2px !important;
}}
[data-testid="stProgress"] > div > div {{
    background: linear-gradient(90deg, var(--gold), var(--orange)) !important;
    border-radius: 3px !important;
    height: 100% !important;
}}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {{
    border: 2.5px solid var(--ink) !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}}

/* ── Caption ── */
.stCaption p {{
    font-family: var(--font-mono) !important;
    font-size: 10px !important;
    color: var(--ink-soft) !important;
    letter-spacing: 0.08em !important;
}}

/* ── Form container ── */
[data-testid="stForm"] {{
    border: 2.5px solid var(--ink) !important;
    border-radius: 14px !important;
    background: var(--card) !important;
    padding: 14px !important;
    box-shadow: 0 3px 0 var(--ink) !important;
}}

/* ── Slider ── */
[data-testid="stSlider"] [data-testid="stThumbValue"] {{
    font-family: var(--font-mono) !important;
    font-size: 11px !important;
    color: var(--ink) !important;
}}

/* ─────── Iron Age custom components ─────── */

.ia-label {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: var(--ink-soft);
    margin: 10px 0 6px;
}}
.ia-label::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: var(--ink-soft);
    opacity: 0.3;
}}

.ia-card {{
    background: var(--card);
    border: 2.5px solid var(--ink);
    border-radius: 16px;
    box-shadow: 0 3px 0 var(--ink), 0 8px 20px rgba(42,28,16,0.08);
    padding: 16px;
    margin-bottom: 12px;
    animation: ia-rise .28s ease both;
    opacity: 1;
}}

.ia-hero-card {{
    background: var(--card);
    border: 3px solid var(--ink);
    border-radius: 20px;
    box-shadow: 0 4px 0 var(--ink), 0 12px 32px rgba(42,28,16,0.10);
    padding: 18px 16px 14px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
}}
.ia-hero-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
    background: var(--grad);
}}

.ticket-list {{
    background: var(--card);
    border: 2.5px solid var(--ink);
    border-radius: 16px;
    box-shadow: 0 3px 0 var(--ink);
    overflow: hidden;
    margin-bottom: 12px;
}}
.ticket-row {{
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 14px;
    border-bottom: 2px dashed rgba(42,28,16,0.22);
    min-height: 52px;
}}
.ticket-row:last-child {{ border-bottom: none; }}
.ticket-row.done {{ opacity: 0.58; }}
.ticket-pill {{
    background: var(--ink);
    color: var(--paper);
    font-family: var(--font-mono);
    font-size: 11px;
    font-weight: 700;
    border-radius: 6px;
    padding: 3px 8px;
    min-width: 28px;
    text-align: center;
    white-space: nowrap;
    flex-shrink: 0;
}}
.ticket-body {{ flex: 1; min-width: 0; }}
.ticket-name {{
    font-family: var(--font-body);
    font-weight: 700;
    font-size: 14px;
    color: var(--ink);
    text-transform: uppercase;
    line-height: 1.15;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}}
.ticket-detail {{
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-soft);
    letter-spacing: 0.08em;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-top: 1px;
}}
.ticket-check {{
    width: 30px;
    height: 30px;
    border: 2.5px solid var(--ink);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    font-size: 15px;
    color: var(--ink);
    background: transparent;
}}
.ticket-check.done {{
    background: var(--brick);
    border-color: var(--brick);
    color: #fff;
}}

.ia-stamp {{
    display: inline-block;
    border: 3px solid var(--brick);
    border-radius: 50%;
    color: var(--brick);
    font-family: var(--font-display);
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    padding: 10px 14px;
    transform: rotate(-7deg);
    opacity: 0.9;
    box-shadow: inset 0 0 0 2px var(--brick);
    animation: ia-stamp 0.35s cubic-bezier(0.34,1.56,0.64,1) both;
    line-height: 1.3;
    text-align: center;
}}

.ia-chip {{
    display: inline-flex;
    align-items: center;
    border: 2px solid var(--ink);
    border-radius: 5px;
    background: var(--gold);
    color: var(--ink);
    font-family: var(--font-mono);
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.12em;
    padding: 2px 7px;
    text-transform: uppercase;
    margin: 1px;
    white-space: nowrap;
}}
.ia-chip.brick {{ background: var(--brick); color: #fff; border-color: var(--brick); }}
.ia-chip.teal  {{ background: var(--teal);  color: #fff; border-color: var(--teal); }}
.ia-chip.ink   {{ background: var(--ink);   color: var(--paper); border-color: var(--ink); }}

.xp-strip {{
    background: var(--ink);
    border-radius: 10px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
}}
.xps-level {{
    font-family: var(--font-display);
    font-size: 20px;
    color: var(--gold);
    line-height: 1;
    white-space: nowrap;
}}
.xps-track {{ flex: 1; }}
.xps-bar {{
    background: rgba(255,255,255,0.14);
    border-radius: 3px;
    height: 10px;
    overflow: hidden;
}}
.xps-fill {{
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--gold), var(--orange));
}}
.xps-info {{
    font-family: var(--font-mono);
    font-size: 8px;
    color: rgba(255,255,255,0.45);
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin-top: 3px;
}}
.xps-streak {{
    font-family: var(--font-display);
    font-size: 16px;
    color: var(--brick);
    white-space: nowrap;
}}

.week-boxes {{
    display: flex;
    gap: 4px;
    margin: 8px 0;
}}
.week-box {{
    flex: 1;
    aspect-ratio: 1;
    border: 2.5px solid var(--ink);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: var(--paper);
    gap: 1px;
}}
.wb-day {{
    font-family: var(--font-mono);
    font-size: 7px;
    color: var(--ink-soft);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.wb-icon {{ font-size: 12px; color: var(--ink-soft); }}
.week-box.done {{
    background: var(--brick);
    border-color: var(--brick);
}}
.week-box.done .wb-day,
.week-box.done .wb-icon {{ color: #fff; }}
.week-box.today {{ border-color: var(--gold); border-width: 3px; }}

.ia-progress {{ margin: 5px 0; }}
.ia-progress-label {{
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 9px;
    color: var(--ink-soft);
    letter-spacing: 0.10em;
    text-transform: uppercase;
    margin-bottom: 3px;
}}
.ia-progress-track {{
    background: rgba(42,28,16,0.12);
    border: 2px solid var(--ink);
    border-radius: 5px;
    height: 16px;
    padding: 2px;
    overflow: hidden;
}}
.ia-progress-fill {{
    height: 100%;
    border-radius: 3px;
    background: linear-gradient(90deg, var(--gold), var(--orange));
}}

.ia-logo-bar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 0 2px;
}}
.ia-logo {{
    font-family: var(--font-script);
    font-size: 24px;
    color: var(--ink);
    text-shadow: 1.5px 1.5px 0 var(--ink-soft);
    line-height: 1;
}}
.ia-logo-sub {{
    font-family: var(--font-display);
    font-size: 14px;
    color: var(--brick);
    letter-spacing: 0.08em;
    text-shadow: 1px 1px 0 var(--ink);
}}

.ia-screen-header {{ padding: 12px 0 6px; }}
.ia-mono-row {{
    font-family: var(--font-mono);
    font-size: 10px;
    color: var(--ink-soft);
    letter-spacing: 0.18em;
    text-transform: uppercase;
    margin: 0 0 2px;
}}
.ia-title-row {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
}}
.ia-title {{
    font-family: var(--font-display);
    font-size: 38px;
    color: var(--ink);
    line-height: 0.9;
    text-transform: uppercase;
    letter-spacing: -0.02em;
    margin: 0;
}}

.member-card {{
    background: var(--card);
    border: 3px solid var(--ink);
    border-radius: 18px;
    box-shadow: 0 4px 0 var(--ink), 0 10px 30px rgba(42,28,16,0.12);
    padding: 18px;
    position: relative;
    overflow: hidden;
    margin-bottom: 14px;
}}
.member-card::before {{
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
    background: var(--grad);
}}
.mc-logo {{ font-family: var(--font-script); font-size: 16px; color: var(--brick); text-shadow: 1px 1px 0 var(--ink); }}
.mc-name {{ font-family: var(--font-display); font-size: 28px; line-height: 0.9; text-transform: uppercase; color: var(--ink); margin: 4px 0; }}
.mc-id   {{ font-family: var(--font-mono); font-size: 10px; color: var(--ink-soft); letter-spacing: 0.18em; text-transform: uppercase; }}
.mc-avatar {{
    width: 68px; height: 68px;
    border: 3px solid var(--ink);
    border-radius: 10px;
    background: var(--paper);
    display: flex; align-items: center; justify-content: center;
    font-size: 32px;
    flex-shrink: 0;
}}

.ach-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; }}
.ach-badge {{
    background: var(--card);
    border: 2.5px solid var(--ink);
    border-radius: 12px;
    box-shadow: 0 3px 0 var(--ink);
    padding: 12px 8px;
    text-align: center;
    animation: ia-rise .3s ease both;
    opacity: 1;
}}
.ach-badge.locked {{ opacity: 0.42; filter: grayscale(0.7); box-shadow: 0 2px 0 var(--ink-soft); border-color: var(--ink-soft); }}
.ab-icon  {{ font-size: 26px; line-height: 1; }}
.ab-name  {{ font-family: var(--font-body); font-weight: 700; font-size: 11px; text-transform: uppercase; color: var(--ink); margin: 4px 0 2px; line-height: 1.2; }}
.ab-xp    {{ font-family: var(--font-mono); font-size: 9px; color: var(--gold); font-weight: 700; letter-spacing: 0.08em; }}
.ab-date  {{ font-family: var(--font-mono); font-size: 8px; color: var(--ink-soft); letter-spacing: 0.06em; }}

.pr-row {{
    background: var(--card);
    border: 2.5px solid var(--ink);
    border-radius: 12px;
    box-shadow: 0 3px 0 var(--ink);
    padding: 12px 14px;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 14px;
}}
.pr-num  {{ font-family: var(--font-display); font-size: 32px; line-height: 0.9; color: var(--brick); white-space: nowrap; }}
.pr-unit {{ font-family: var(--font-mono); font-size: 9px; color: var(--ink-soft); letter-spacing: 0.10em; text-transform: uppercase; margin-top: 2px; }}
.pr-exercise {{ font-family: var(--font-body); font-weight: 700; font-size: 14px; text-transform: uppercase; color: var(--ink); line-height: 1.1; }}
.pr-date {{ font-family: var(--font-mono); font-size: 9px; color: var(--ink-soft); letter-spacing: 0.08em; }}

/* ── Fixed bottom tab bar ── */
.iron-tab-bar {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: 68px;
    background: var(--ink);
    border-top: 3px solid var(--gold);
    display: flex;
    align-items: stretch;
    z-index: 99999;
    padding-bottom: env(safe-area-inset-bottom, 6px);
}}
.iron-tab {{
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 2px;
    text-decoration: none !important;
    padding: 5px 2px;
    border-top: 3px solid transparent;
    margin-top: -3px;
}}
.it-icon  {{ font-size: 18px; line-height: 1; color: rgba(236,222,194,0.38); }}
.it-label {{
    font-family: var(--font-mono) !important;
    font-size: 7px !important;
    letter-spacing: 0.15em !important;
    text-transform: uppercase !important;
    color: rgba(236,222,194,0.38) !important;
}}
.iron-tab.active {{ border-top-color: var(--brick); }}
.iron-tab.active .it-icon {{ color: var(--brick); }}
.iron-tab.active .it-label {{ color: var(--brick) !important; }}

/* ── Animations ── */
@keyframes ia-rise  {{ from {{ opacity:0; transform:translateY(12px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes ia-stamp {{ from {{ transform:rotate(-7deg) scale(2.4); opacity:0; }} to {{ transform:rotate(-7deg) scale(1); opacity:0.9; }} }}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        transition-duration: 0.01ms !important;
    }}
}}
</style>"""
