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
    """Avvolge la funzione di formato f applicando sfondo, colore del testo e grassetto."""
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


def styler_to_latex(styler):
    s = copy.deepcopy(styler)
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

    tex = s.to_latex(hrules=True, multirow_align="naive")
    if TABLE_FONT:
        tex = "{" + TABLE_FONT + "\n" + tex.rstrip() + "\n}\n"
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