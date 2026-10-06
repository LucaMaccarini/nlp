# nb_export.py
import re
import copy
import pandas as pd
from IPython import get_ipython
from pandas.io.formats.style import Styler

_TEX = {
    "\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#",
    "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
}
_TEX_RE = re.compile("|".join(re.escape(k) for k in _TEX))

# nomi colore che xcolor conosce senza opzioni aggiuntive
_XCOLOR_NAMES = {"black", "blue", "brown", "cyan", "darkgray", "gray", "green", "lightgray",
                 "lime", "magenta", "olive", "orange", "pink", "purple", "red", "teal",
                 "violet", "white", "yellow"}

TABLE_FONT = r"\ttfamily\small"
LINE_WIDTH = 150                  # None -> usa pd.get_option("display.width"); modificalo per adattarlo alla pagina
COL_SEP = 3                       # spazio (in caratteri) tra colonne: tiene conto di \tabcolsep
WRAP_MARK = r"\textbackslash{}"   # segno "continua nel blocco successivo"; None per disattivarlo


# ---------------------------------------------------------------- escape e colori

def _tex_escape(s):
    return _TEX_RE.sub(lambda m: _TEX[m.group()], str(s))


def _wrap(f):
    return lambda v: _tex_escape(f(v))


def _color_spec(c):
    """Colore CSS -> argomenti di xcolor, oppure None se non riconosciuto."""
    c = (c or "").strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{6})", c) or re.fullmatch(r"#([0-9a-f]{3})", c)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return f"[HTML]{{{h.upper()}}}"
    if c in _XCOLOR_NAMES:
        return f"{{{c}}}"
    return None


def _paint(f, css):
    """Avvolge la funzione di formato f applicando sfondo, colore del testo e grassetto.
    (Al momento non usata: gli stili vengono ignorati in _render.)"""
    d = {str(k).strip().lower(): str(v).strip() for k, v in css}
    bg = _color_spec(d.get("background-color"))
    fg = _color_spec(d.get("color"))
    bold = d.get("font-weight") in ("bold", "700", "800", "900")
    if not (bg or fg or bold):
        return f

    def g(v):
        t = f(v)
        if bold:
            t = rf"\textbf{{{t}}}"
        if fg:
            t = rf"\textcolor{fg}{{{t}}}"
        if bg:
            t = rf"\colorbox{bg}{{{t}}}"
        return t

    return g


# ---------------------------------------------------------------- larghezze e blocchi

def _col_widths(s):
    """Larghezza (in caratteri) dell'indice e di ogni colonna, come verrebbe stampata."""
    data = s.data
    n_rows, n_cols = data.shape

    # indice
    idx_w = 0
    for lvl in range(data.index.nlevels):
        level_values = data.index.get_level_values(lvl)
        w = max(
            (len(str(s._display_funcs_index[(i, lvl)](level_values[i])))
             for i in range(n_rows)),
            default=0,
        )
        idx_w += w + (1 if lvl else 0)
    idx_w = max(idx_w, max((len(str(n)) for n in data.index.names if n is not None), default=0))

    # colonne
    widths = []
    for j in range(n_cols):
        label = data.columns[j]
        labels = label if isinstance(label, tuple) else (label,)
        w = max(len(str(x)) for x in labels)
        for i in range(n_rows):
            w = max(w, len(str(s._display_funcs[(i, j)](data.iat[i, j]))))
        widths.append(w)
    return idx_w, widths


def _chunks(idx_w, widths, line_width):
    """Raggruppa le colonne in blocchi che stanno in line_width (come fa pandas)."""
    out, cur, used = [], [], idx_w
    for j, w in enumerate(widths):
        need = w + COL_SEP
        if cur and used + need > line_width:
            out.append(cur)
            cur, used = [], idx_w
        cur.append(j)
        used += need
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- rendering

def _add_wrap_mark(tex):
    """Aggiunge una colonna finale con il segno di continuazione a ogni riga della tabella."""
    tex = re.sub(r"(\\begin\{tabular\}\{[^}]*)\}", r"\1l}", tex, count=1)
    out = []
    for line in tex.splitlines():
        if line.rstrip().endswith(r"\\"):
            line = line.rstrip()[:-2].rstrip() + f" & {WRAP_MARK} \\\\"
        out.append(line)
    return "\n".join(out)


def _render(s, keep=None, cont=False):
    """Una singola tabella LaTeX; keep = posizioni delle colonne da mostrare (None = tutte).
    cont=True aggiunge il segno di continuazione a destra."""
    s = copy.deepcopy(s)
    if keep is not None:
        keep = set(keep)
        hidden = [c for j, c in enumerate(s.data.columns) if j not in keep]
        if hidden:
            s.hide(subset=hidden, axis=1)
    s._compute()  # applica gli stili "pigri" (gradient, apply, map)
    s.ctx.clear(); s.ctx_index.clear(); s.ctx_columns.clear(); s._todo.clear()  # ignora i colori

    n_rows, n_cols = s.data.shape
    for i in range(n_rows):
        for j in range(n_cols):
            s._display_funcs[(i, j)] = _wrap(s._display_funcs[(i, j)])
    for i in range(n_rows):
        for lvl in range(s.data.index.nlevels):
            s._display_funcs_index[(i, lvl)] = _wrap(s._display_funcs_index[(i, lvl)])
    for lvl in range(s.data.columns.nlevels):
        for j in range(n_cols):
            s._display_funcs_columns[(lvl, j)] = _wrap(s._display_funcs_columns[(lvl, j)])

    tex = s.to_latex(hrules=True, multirow_align="naive").rstrip()
    if cont and WRAP_MARK:
        tex = _add_wrap_mark(tex)
    return tex


def styler_to_latex(styler):
    line_width = LINE_WIDTH or pd.get_option("display.width") or 80
    base = copy.deepcopy(styler)
    base._compute()
    idx_w, widths = _col_widths(base)
    groups = _chunks(idx_w, widths, line_width)

    if len(groups) <= 1:
        tex = _render(styler)
    else:
        last = len(groups) - 1
        tex = "\n\\par\\medskip\n".join(
            _render(styler, keep=g, cont=(k < last)) for k, g in enumerate(groups)
        )

    if TABLE_FONT:
        tex = "{" + TABLE_FONT + "\n" + tex + "\n}\n"
    return tex


def styler_to_plain(styler, p, cycle):
    p.text(styler.to_string())


def df_to_latex(df):
    max_rows = pd.get_option("display.max_rows") or len(df)
    if len(df) > max_rows:
        half = max_rows // 2
        df = pd.concat([df.head(half), df.tail(half)])
    return styler_to_latex(df.style)   # stessa pipeline dei DataFrame con .style


def setup():
    ip = get_ipython()
    if ip is None:
        return
    latex = ip.display_formatter.formatters["text/latex"]
    plain = ip.display_formatter.formatters["text/plain"]
    latex.for_type(Styler, styler_to_latex)
    latex.for_type(pd.DataFrame, df_to_latex)
    plain.for_type(Styler, styler_to_plain)


setup()