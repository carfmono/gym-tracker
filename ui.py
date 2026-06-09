"""Iron Age UI helpers — pure HTML string generators, no Streamlit calls."""
from __future__ import annotations
import math
import html as _h


def _e(s: str) -> str:
    return _h.escape(str(s))


# ── Logo & headers ──────────────────────────────────────────────────────────

def logo_bar(right_html: str = "") -> str:
    return (
        f'<div class="ia-logo-bar">'
        f'<span class="ia-logo">Iron <span class="ia-logo-sub">Age</span></span>'
        f'{right_html}'
        f'</div>'
    )


def screen_header(context: str, title: str, badge_html: str = "") -> str:
    return (
        f'<div class="ia-screen-header">'
        f'<div class="ia-mono-row">{_e(context)}</div>'
        f'<div class="ia-title-row">'
        f'<div class="ia-title">{_e(title)}</div>'
        f'{badge_html}'
        f'</div>'
        f'</div>'
    )


def label(text: str) -> str:
    return f'<div class="ia-label">{_e(text)}</div>'


# ── Chips & stamps ───────────────────────────────────────────────────────────

def chip(text: str, variant: str = "gold") -> str:
    cls_map = {"gold": "", "brick": " brick", "teal": " teal", "ink": " ink"}
    extra = cls_map.get(variant, "")
    return f'<span class="ia-chip{extra}">{_e(text)}</span>'


def stamp(text: str) -> str:
    return f'<span class="ia-stamp">{_e(text)}</span>'


# ── XP strip ─────────────────────────────────────────────────────────────────

def xp_strip(level: int, pct: float, xp_str: str, streak: int = 0) -> str:
    streak_html = (
        f'<div class="xps-streak">🔥×{streak}</div>' if streak > 1 else ""
    )
    return (
        f'<div class="xp-strip">'
        f'<div class="xps-level">NV.{level}</div>'
        f'<div class="xps-track">'
        f'<div class="xps-bar"><div class="xps-fill" style="width:{min(100,pct):.0f}%"></div></div>'
        f'<div class="xps-info">{_e(xp_str)}</div>'
        f'</div>'
        f'{streak_html}'
        f'</div>'
    )


# ── Ticket rows ───────────────────────────────────────────────────────────────

def ticket_row(
    num: str | int,
    name: str,
    detail: str,
    done: bool = False,
    chips_html: str = "",
) -> str:
    done_cls   = " done" if done else ""
    check_cls  = " done" if done else ""
    check_icon = "✓" if done else ""
    return (
        f'<div class="ticket-row{done_cls}">'
        f'<div class="ticket-pill">{_e(str(num))}</div>'
        f'<div class="ticket-body">'
        f'<div class="ticket-name">{_e(name)}</div>'
        f'<div class="ticket-detail">{_e(detail)}{chips_html}</div>'
        f'</div>'
        f'<div class="ticket-check{check_cls}">{check_icon}</div>'
        f'</div>'
    )


def ticket_list(*rows_html: str) -> str:
    return f'<div class="ticket-list">{"".join(rows_html)}</div>'


# ── Week boxes ────────────────────────────────────────────────────────────────

def week_boxes(days: list[dict]) -> str:
    """days: list of {label, done, today}"""
    boxes = ""
    for d in days:
        cls   = (" done" if d.get("done") else "") + (" today" if d.get("today") else "")
        icon  = "✓" if d.get("done") else "·"
        boxes += (
            f'<div class="week-box{cls}">'
            f'<div class="wb-day">{_e(d.get("label", ""))}</div>'
            f'<div class="wb-icon">{icon}</div>'
            f'</div>'
        )
    return f'<div class="week-boxes">{boxes}</div>'


# ── Progress bar ──────────────────────────────────────────────────────────────

def progress_bar(label_text: str, done: int | float, goal: int | float) -> str:
    pct = min(100.0, (done / goal * 100) if goal else 0)
    return (
        f'<div class="ia-progress">'
        f'<div class="ia-progress-label"><span>{_e(label_text)}</span><span>{int(done)}/{int(goal)}</span></div>'
        f'<div class="ia-progress-track">'
        f'<div class="ia-progress-fill" style="width:{pct:.0f}%"></div>'
        f'</div>'
        f'</div>'
    )


# ── Analog dial SVG ───────────────────────────────────────────────────────────

def _svg_pt(cx: float, cy: float, r: float, deg: float) -> tuple[float, float]:
    rad = math.radians(deg)
    return cx + r * math.cos(rad), cy + r * math.sin(rad)


def _svg_arc(cx: float, cy: float, r: float, start: float, end: float, cw: bool) -> str:
    """Return SVG arc 'd' attribute. cw=True → clockwise (sweep=1)."""
    sx, sy = _svg_pt(cx, cy, r, start)
    ex, ey = _svg_pt(cx, cy, r, end)
    span   = ((end - start) % 360) if cw else ((start - end) % 360)
    large  = 1 if span > 180 else 0
    flag   = 1 if cw else 0
    return f"M {sx:.1f} {sy:.1f} A {r} {r} 0 {large} {flag} {ex:.1f} {ey:.1f}"


def dial_svg(pct: float, label_text: str, value_str: str = "", size: int = 130) -> str:
    """
    240° analogue gauge.
    Start: 210° (7 o'clock in SVG coords, measured CW from right).
    Goes counter-clockwise to 330° (5 o'clock).
    """
    pct    = max(0.0, min(1.0, pct))
    cx = cy = size // 2
    r_outer = size // 2 - 4
    r_bezel = r_outer - 2
    r_track = r_outer - 10

    # Arc geometry: CCW from 210° to 330° spans 240°
    START   = 210.0
    SWEEP   = 240.0
    end_deg = (START - SWEEP * pct + 360) % 360  # CCW end for fill

    track_d = _svg_arc(cx, cy, r_track, START, 330.0, cw=False)  # full 240° track
    fill_d  = _svg_arc(cx, cy, r_track, START, end_deg, cw=False) if pct > 0.005 else ""

    # Ticks (13 points, every 20°, CCW)
    ticks_svg = ""
    for i in range(13):
        t_deg  = (START - (SWEEP / 12) * i + 360) % 360
        major  = (i % 3 == 0)
        r_out  = r_track + 4
        r_in   = r_track + (10 if major else 6)
        ox, oy = _svg_pt(cx, cy, r_out, t_deg)
        ix, iy = _svg_pt(cx, cy, r_in,  t_deg)
        sw     = 2 if major else 1
        ticks_svg += (
            f'<line x1="{ox:.1f}" y1="{oy:.1f}" x2="{ix:.1f}" y2="{iy:.1f}" '
            f'stroke="var(--ink-soft)" stroke-width="{sw}" opacity="0.45"/>'
        )

    # Needle
    needle_deg      = (START - SWEEP * pct + 360) % 360
    nx, ny          = _svg_pt(cx, cy, r_track - 6, needle_deg)
    nb1x, nb1y      = _svg_pt(cx, cy, 5, (needle_deg + 90) % 360)
    nb2x, nb2y      = _svg_pt(cx, cy, 5, (needle_deg - 90) % 360)

    val_display = value_str if value_str else f"{pct*100:.0f}%"

    fill_path = (
        f'<path d="{fill_d}" stroke="var(--brick)" stroke-width="8" '
        f'fill="none" stroke-linecap="round"/>'
        if fill_d else ""
    )

    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" '
        f'xmlns="http://www.w3.org/2000/svg">'
        # Bezel ring
        f'<circle cx="{cx}" cy="{cy}" r="{r_outer}" fill="var(--ink)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r_bezel}" fill="var(--card)" stroke="var(--ink)" stroke-width="1"/>'
        # Track
        f'<path d="{track_d}" stroke="var(--ink-soft)" stroke-width="6" fill="none" stroke-linecap="round" opacity="0.3"/>'
        # Fill arc
        f'{fill_path}'
        # Ticks
        f'{ticks_svg}'
        # Needle
        f'<polygon points="{nx:.1f},{ny:.1f} {nb1x:.1f},{nb1y:.1f} {nb2x:.1f},{nb2y:.1f}" fill="var(--brick)"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="var(--brick)" stroke="var(--ink)" stroke-width="1.5"/>'
        # Value text
        f'<text x="{cx}" y="{cy+10}" text-anchor="middle" '
        f'font-family="\'Space Mono\',monospace" font-size="16" font-weight="700" fill="var(--ink)">'
        f'{_e(val_display)}</text>'
        f'<text x="{cx}" y="{cy+24}" text-anchor="middle" '
        f'font-family="\'Space Mono\',monospace" font-size="7" letter-spacing="0.14em" fill="var(--ink-soft)">'
        f'{_e(label_text.upper())}</text>'
        f'</svg>'
    )


# ── Member card ───────────────────────────────────────────────────────────────

def member_card(
    name: str,
    member_id: str,
    since: str,
    level: int,
    total_xp: int,
    badges: list[str] | None = None,
) -> str:
    badges_html = ""
    if badges:
        chips = "".join(
            f'<span class="ia-chip" style="font-size:9px;">{_e(b)}</span>'
            for b in badges[:6]
        )
        badges_html = f'<div style="margin-top:10px;display:flex;flex-wrap:wrap;gap:4px;">{chips}</div>'

    return (
        f'<div class="member-card">'
        f'<div style="display:flex;gap:14px;align-items:flex-start;">'
        f'<div class="mc-avatar">🏋️</div>'
        f'<div style="flex:1;">'
        f'<div class="mc-logo">Iron Age</div>'
        f'<div class="mc-name">{_e(name)}</div>'
        f'<div class="mc-id">NRO. {_e(member_id)} &nbsp;·&nbsp; SOCIO DESDE {_e(since)}</div>'
        f'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap;">'
        f'{chip(f"NV. {level}", "ink")}'
        f'{chip(f"{total_xp:,} XP", "gold")}'
        f'</div>'
        f'</div>'
        f'</div>'
        f'{badges_html}'
        f'</div>'
    )


# ── Achievement badge ─────────────────────────────────────────────────────────

def ach_badge(icon: str, name: str, xp: int, date_str: str = "", locked: bool = False) -> str:
    locked_cls  = " locked" if locked else ""
    date_html   = f'<div class="ab-date">{_e(date_str[:10])}</div>' if date_str and not locked else ""
    return (
        f'<div class="ach-badge{locked_cls}">'
        f'<div class="ab-icon">{icon}</div>'
        f'<div class="ab-name">{_e(name)}</div>'
        f'<div class="ab-xp">+{xp} XP</div>'
        f'{date_html}'
        f'</div>'
    )


# ── PR row ────────────────────────────────────────────────────────────────────

def pr_row(value: float, unit: str, exercise: str, date_str: str) -> str:
    v_str = f"{value:.1f}".rstrip("0").rstrip(".")
    return (
        f'<div class="pr-row">'
        f'<div style="text-align:center;flex-shrink:0;">'
        f'<div class="pr-num">{_e(v_str)}</div>'
        f'<div class="pr-unit">{_e(unit)}</div>'
        f'</div>'
        f'<div>'
        f'<div class="pr-exercise">{_e(exercise)}</div>'
        f'<div class="pr-date">{_e(date_str)}</div>'
        f'</div>'
        f'<div style="margin-left:auto;">{stamp("PR")}</div>'
        f'</div>'
    )


# ── Tab bar ───────────────────────────────────────────────────────────────────

_TAB_ICONS = {
    "hoy":      ("⊞", "INICIO"),
    "entrenos": ("⚡", "ENTRENOS"),
    "records":  ("★",  "RÉCORDS"),
    "perfil":   ("◉",  "PERFIL"),
}


def tab_bar(current: str) -> str:
    items = ""
    for tid, (icon, label_text) in _TAB_ICONS.items():
        active = " active" if tid == current else ""
        items += (
            f'<a href="?tab={tid}" class="iron-tab{active}">'
            f'<div class="it-icon">{icon}</div>'
            f'<div class="it-label">{label_text}</div>'
            f'</a>'
        )
    return f'<div class="iron-tab-bar">{items}</div>'
