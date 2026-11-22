"""Single source of truth for report-wide LaTeX layout and visual styling."""

from __future__ import annotations

import re


PAGE = {
    "paper": "a4paper",
    "top": "0.88in",
    "bottom": "1.12in",
    "left": "1in",
    "right": "1in",
    "headheight": "34pt",
    "headsep": "18pt",
    "footskip": "34pt",
}
TABLE = {
    "column_padding_pt": 6,
    "row_stretch": 1.12,
    "extra_row_height_pt": 1.5,
    "rule_width_pt": 0.5,
    "longtable_pre_pt": 0,
    "longtable_post_pt": 6,
    "minimum_space_lines": 7,
    "compact_padding_pt": 3.5,
    "tight_padding_pt": 3,
    "compact_row_stretch": 1.25,
}
COLORS = {
    "brand_green": "91B014",
    "header_fill": "EAF0D7",
    "grid": "AAB18E",
    "pass": "3B6E35",
    "fail": "B3261E",
    "chart_blue": "477A9E",
    "chart_green": "91B014",
    "chart_orange": "D28A36",
}


def latex_layout_settings() -> str:
    """Return the centrally configured geometry, table spacing, and colors."""
    return rf"""
\usepackage[{PAGE['paper']},top={PAGE['top']},bottom={PAGE['bottom']},left={PAGE['left']},right={PAGE['right']},includeheadfoot,headheight={PAGE['headheight']},headsep={PAGE['headsep']},footskip={PAGE['footskip']} ]{{geometry}}
\definecolor{{osdagGreen}}{{HTML}}{{{COLORS['brand_green']}}}
\definecolor{{reportHeaderFill}}{{HTML}}{{{COLORS['header_fill']}}}
\definecolor{{reportGrid}}{{HTML}}{{{COLORS['grid']}}}
\definecolor{{reportFail}}{{HTML}}{{{COLORS['fail']}}}
\definecolor{{reportPass}}{{HTML}}{{{COLORS['pass']}}}
\setlength{{\tabcolsep}}{{{TABLE['column_padding_pt']}pt}}
\renewcommand{{\arraystretch}}{{{TABLE['row_stretch']}}}
\setlength{{\LTleft}}{{\fill}}
\setlength{{\LTright}}{{\fill}}
\setlength{{\LTpre}}{{{TABLE['longtable_pre_pt']}pt}}
\setlength{{\LTpost}}{{{TABLE['longtable_post_pt']}pt}}
\setlength{{\arrayrulewidth}}{{{TABLE['rule_width_pt']}pt}}
\setlength{{\extrarowheight}}{{{TABLE['extra_row_height_pt']}pt}}
\newcommand{{\ReportCompactTable}}{{\setlength{{\tabcolsep}}{{{TABLE['compact_padding_pt']}pt}}}}
\newcommand{{\ReportTightTable}}{{\setlength{{\tabcolsep}}{{{TABLE['tight_padding_pt']}pt}}\renewcommand{{\arraystretch}}{{{TABLE['compact_row_stretch']}}}}}
\newcommand{{\ReportLeftAlignedLongTable}}{{\setlength{{\LTleft}}{{0pt}}\setlength{{\LTright}}{{\fill}}}}
\BeforeBeginEnvironment{{table}}{{\needspace{{{TABLE['minimum_space_lines']}\baselineskip}}}}
\BeforeBeginEnvironment{{longtable}}{{\needspace{{{TABLE['minimum_space_lines']}\baselineskip}}}}
\clubpenalty=10000
\widowpenalty=10000
\displaywidowpenalty=10000
\raggedbottom
"""


def repeat_longtable_headers(document_tex: str) -> str:
    """Add first-page and continuation headings to longtables with a header row.

    Existing explicit longtable heads are preserved. The table's first row after
    its caption/rule is treated as the column heading and repeated verbatim.
    """
    pattern = re.compile(r"\\begin\{longtable\}.*?\\end\{longtable\}", re.DOTALL)

    def update(match: re.Match[str]) -> str:
        block = match.group(0)
        if r"\endfirsthead" in block or r"\endhead" in block:
            return block
        lines = block.splitlines()
        # Find the first rule following the caption (or the opening line).
        rule = next((i for i, line in enumerate(lines[1:], 1) if r"\hline" in line), None)
        if rule is None:
            return block
        header_start = rule + 1
        while header_start < len(lines) and not lines[header_start].strip():
            header_start += 1
        header_end = next((i for i in range(header_start, len(lines)) if r"\hline" in lines[i]), None)
        if header_end is None:
            return block
        header = lines[header_start:header_end]
        if not header or not any(r"\textbf" in line for line in header):
            return block
        repeated = [r"\endfirsthead", *header, r"\hline", r"\endhead"]
        lines[header_end + 1:header_end + 1] = repeated
        return "\n".join(lines)

    return pattern.sub(update, document_tex)
