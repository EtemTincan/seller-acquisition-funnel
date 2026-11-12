"""Seller acquisition funnel: which lead sources bring sellers who actually sell?

Run with:  streamlit run app.py
"""
from math import sqrt

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from funnel.db import CUTOFF, connect, read_sql, run

AUTHOR = "Etem Tincan"
REPO_URL = "https://github.com/EtemTincan/seller-acquisition-funnel"
GITHUB_URL = "https://github.com/EtemTincan"
LINKEDIN_URL = ""  # paste your LinkedIn profile link here to show it on the page

# Design tokens. One blue for every data mark, a lighter tint for small samples,
# ochre reserved for the few things the reader must not miss.
INK = "#1B2A32"
MUTED = "#5F6E76"
RULE = "#DDE3E6"
PANEL = "#F2F5F6"
BLUE = "#1F6F8B"
BLUE_TINT = "#A9C9D4"
OCHRE = "#B8730F"
FONT = "Instrument Sans, Helvetica Neue, Arial, sans-serif"
SMALL_SAMPLE = 30  # below this many observed sellers a rate is too noisy to rank on

st.set_page_config(page_title="Seller acquisition funnel", layout="centered")


# ---------------------------------------------------------------- helpers ---

def wilson(successes: float, n: float, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson interval for a proportion. Behaves well for small n."""
    if not n:
        return (0.0, 0.0)
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, centre - half), min(1.0, centre + half))


def two_proportion_z(s1: float, n1: float, s2: float, n2: float) -> float:
    """z statistic for the difference between two proportions."""
    pooled = (s1 + s2) / (n1 + n2)
    se = sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    return (s1 / n1 - s2 / n2) / se if se else 0.0


def pct(x: float, digits: int = 0) -> str:
    return f"{100 * x:.{digits}f}%"


def brl(x: float) -> str:
    return f"R${x:,.0f}"


@st.cache_data(show_spinner=False)
def load(window: int, skip_top: bool) -> dict[str, pd.DataFrame]:
    con = connect(window, skip_top)
    names = ["01_funnel", "02_channels", "03_speed", "04_speed_buckets",
             "05_cohorts", "06_profiles", "07_concentration", "08_late_starters"]
    return {n: run(con, n) for n in names}


def style(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=8, t=34, b=0),
        font=dict(family=FONT, size=14, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        hoverlabel=dict(bgcolor="white", bordercolor=RULE,
                        font=dict(family=FONT, size=13, color=INK)),
        bargap=0.38,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=MUTED, size=13), fixedrange=True)
    fig.update_yaxes(showgrid=False, zeroline=False, showline=False, ticks="",
                     tickfont=dict(color=INK, size=14), fixedrange=True)
    return fig


def show(fig: go.Figure, wide_key: str | None = None) -> None:
    """Draw a chart. Charts given a wide_key scroll sideways on small screens."""
    holder = st.container(key=f"wide-{wide_key}") if wide_key else st.container()
    holder.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def numbers_and_sql(df: pd.DataFrame, sql_name: str) -> None:
    """Every chart ships with its table and the query that produced it."""
    with st.expander("See the numbers and the SQL"):
        st.dataframe(df, hide_index=True, width="stretch")
        st.code(read_sql(sql_name), language="sql")


# ------------------------------------------------------------------ style ---

st.html(f"""
<style>
  header[data-testid="stHeader"], [data-testid="stToolbar"], footer {{ display: none; }}
  .stApp {{ background: #FFFFFF; }}
  .block-container {{ max-width: 1020px; padding: 4.5rem 2rem 6rem; }}
  html, body, .stApp, .stMarkdown, p, li, label, button, input {{
    font-family: {FONT}; color: {INK}; font-feature-settings: "tnum" 1;
  }}
  h1 {{ font-size: 3.05rem; line-height: 1.06; font-weight: 600; letter-spacing: -0.028em;
        margin: 0 0 1.1rem; max-width: 17ch; padding: 0; }}
  h2 {{ font-size: 1.72rem; line-height: 1.18; font-weight: 600; letter-spacing: -0.018em;
        margin: 4.2rem 0 .7rem; max-width: 30ch; padding: 0; }}
  .lede {{ font-size: 1.22rem; line-height: 1.5; color: {MUTED}; max-width: 62ch; margin: 0; }}
  .prose {{ font-size: 1.04rem; line-height: 1.62; max-width: 68ch; margin: 0 0 1.4rem; }}
  .prose b {{ font-weight: 600; }}
  .byline {{ font-size: .95rem; color: {MUTED}; margin: 1.5rem 0 0; }}
  .byline a {{ color: {BLUE}; text-decoration: underline; text-underline-offset: 3px; }}

  .funnel {{ margin: 3.2rem 0 0; }}
  .stage {{ display: grid; grid-template-columns: 11.5rem 1fr; align-items: center;
            gap: 1.25rem; padding: .95rem 0; border-top: 1px solid {RULE}; }}
  .stage:last-child {{ border-bottom: 1px solid {RULE}; }}
  .stage .count {{ font-size: 2.1rem; font-weight: 600; letter-spacing: -0.02em; line-height: 1; }}
  .stage .what {{ font-size: .95rem; color: {MUTED}; margin-top: .35rem; line-height: 1.35; }}
  .track {{ height: 34px; }}
  .fill {{ height: 100%; background: {BLUE}; border-radius: 0 4px 4px 0; min-width: 3px;
           transform-origin: left; animation: grow .9s cubic-bezier(.2,.7,.2,1) both; }}
  .lost {{ font-size: .92rem; color: {MUTED}; margin-top: .4rem; }}
  @keyframes grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
  @media (prefers-reduced-motion: reduce) {{ .fill {{ animation: none; }} }}

  .actions {{ counter-reset: act; margin: 1.6rem 0 0; padding: 0; list-style: none;
              border-top: 2px solid {INK}; }}
  .actions li {{ counter-increment: act; display: grid; grid-template-columns: 2.6rem 1fr;
                 padding: 1.25rem 0; border-bottom: 1px solid {RULE}; }}
  .actions li::before {{ content: counter(act); font-size: 1.5rem; font-weight: 600; color: {OCHRE};
                         line-height: 1.2; }}
  .actions .do {{ font-size: 1.14rem; font-weight: 600; line-height: 1.35; margin: 0 0 .3rem; }}
  .actions .why {{ font-size: 1rem; line-height: 1.58; color: {MUTED}; margin: 0; max-width: 66ch; }}

  .author {{ margin-top: 4.5rem; padding-top: 1.6rem; border-top: 2px solid {INK}; }}
  .author .name {{ font-size: 1.3rem; font-weight: 600; letter-spacing: -0.012em; margin: 0 0 .5rem; }}
  .note {{ font-size: .92rem; line-height: 1.55; color: {MUTED}; max-width: 70ch; }}
  .settings {{ margin-top: 4rem; padding: 1.1rem 1.3rem .4rem; background: {PANEL}; border-radius: 6px; }}
  [data-testid="stExpander"] details {{ border: 0; border-top: 1px solid {RULE}; border-radius: 0; }}
  [data-testid="stExpander"] summary {{ padding-left: 0; color: {MUTED}; }}
  [data-testid="stExpander"] summary:hover {{ color: {BLUE}; }}
  :focus-visible {{ outline: 2px solid {BLUE}; outline-offset: 2px; }}
  @media (max-width: 640px) {{
    h1 {{ font-size: 2.2rem; }} h2 {{ font-size: 1.4rem; }}
    .stage {{ grid-template-columns: 1fr; gap: .5rem; }}
    .block-container {{ padding: 2.5rem 1.1rem 4rem; }}
    /* Wide charts keep their shape and scroll sideways instead of squeezing. */
    .st-key-wide-scorecard, .st-key-wide-cohorts {{ overflow-x: auto; }}
    .st-key-wide-scorecard .stElementContainer, .st-key-wide-cohorts .stElementContainer {{ min-width: 780px; }}
  }}
</style>
""")

# ------------------------------------------------------------ headline view ---

base = load(90, False)          # the fixed 90-day view behind the hero and the actions
f = base["01_funnel"].iloc[0]
win_rate = f.signed / f.leads
act_rate = f.activated / f.observed

st.html(f"""
<h1>Which lead sources bring sellers who actually sell?</h1>
<p class="lede">Olist, a Brazilian marketplace, published a year of its seller-acquisition funnel:
{f.leads:,.0f} businesses that asked to sell on the platform, the {f.signed:,.0f} that signed, and every
order those sellers went on to receive. This analysis follows each lead from first contact to first sale.</p>
<p class="byline">By <b style="color:{INK}; font-weight:600">{AUTHOR}</b>, growth and business development.
SQL on DuckDB, charts in Python.
<a href="{REPO_URL}" target="_blank" rel="noopener">Code and queries on GitHub</a></p>

<div class="funnel" role="img"
     aria-label="Funnel: {f.leads:,.0f} leads, {f.signed:,.0f} signed, {pct(act_rate)} of signed sellers sold within 90 days">
  <div class="stage">
    <div><div class="count">{f.leads:,.0f}</div><div class="what">leads asked to sell on Olist</div></div>
    <div><div class="track"><div class="fill" style="width:100%"></div></div></div>
  </div>
  <div class="stage">
    <div><div class="count">{f.signed:,.0f}</div><div class="what">signed a contract</div></div>
    <div><div class="track"><div class="fill" style="width:{100 * win_rate:.2f}%; animation-delay:.25s"></div></div>
         <div class="lost">{pct(1 - win_rate)} of leads never signed</div></div>
  </div>
  <div class="stage">
    <div><div class="count">{pct(act_rate)}</div><div class="what">of signed sellers made a sale within 90 days</div></div>
    <div><div class="track"><div class="fill" style="width:{100 * win_rate * act_rate:.2f}%; animation-delay:.5s"></div></div>
         <div class="lost">{f.activated:,.0f} of the {f.observed:,.0f} sellers signed early enough to be watched for a full 90 days</div></div>
  </div>
</div>
""")

st.html(f"""
<h2>More than half of signed sellers never make a sale</h2>
<p class="prose">The sales team closes about one lead in ten, which is where most funnel reviews stop.
The larger loss comes afterwards: <b>{pct(1 - act_rate)} of sellers who signed had not sold a single item
90 days later</b>. Those who did sell needed a median of {f.median_days_to_first_sale:.0f} days to get their
first order. A signed contract is a cost until the seller's first sale, so the rest of this page
measures channels on what happens after signing as well as before it.</p>
""")

# --------------------------------------------------------------- settings ---

st.html('<h2 style="margin-bottom:.2rem">Channel scorecard</h2>'
        '<p class="prose" style="margin-bottom:.6rem">Each row is a lead source. Read across: how many leads it '
        'brings, how many sign, and whether those sellers go on to sell.</p>')

c1, c2 = st.columns([1, 1.25], vertical_alignment="bottom")
with c1:
    window = st.segmented_control("Count a seller's sales for", [30, 60, 90], default=90,
                                  format_func=lambda d: f"{d} days", key="window") or 90
with c2:
    skip_top = st.toggle("Leave out the single largest seller", value=True, key="skip",
                         help="One seller produced 22% of all 90-day revenue. Left in, it decides "
                              "which channel looks best on revenue per seller.")

data = load(window, skip_top)
ch = data["02_channels"].copy()
ch[["win_lo", "win_hi"]] = [wilson(s, n) for s, n in zip(ch.signed, ch.leads)]
ch[["act_lo", "act_hi"]] = [wilson(s, n) for s, n in zip(ch.activated, ch.observed)]
ch["thin"] = ch.observed < SMALL_SAMPLE
rows = ch.iloc[::-1]  # Plotly draws horizontal bars bottom-up

titles = ["Share of all leads", "Leads that sign", f"Signed sellers selling<br>within {window} days",
          f"Revenue per signed<br>seller, {window} days"]
fig = make_subplots(rows=1, cols=4, shared_yaxes=True, horizontal_spacing=0.045, subplot_titles=titles)
solid = [BLUE] * len(rows)
by_sample = [BLUE_TINT if t else BLUE for t in rows.thin]


def bar(col, x, text, colors, hover, err=None, label_at=None):
    fig.add_trace(go.Bar(
        y=rows.channel, x=x, orientation="h", marker=dict(color=colors, cornerradius=3),
        customdata=hover, hovertemplate="<b>%{y}</b><br>%{customdata}<extra></extra>",
        error_x=err), row=1, col=col)
    # Value labels are their own trace so they sit past the interval line, not on it.
    fig.add_trace(go.Scatter(
        y=rows.channel, x=x if label_at is None else label_at, mode="text", text=[f" {t}" for t in text],
        textposition="middle right", textfont=dict(color=INK, size=13), cliponaxis=False,
        hoverinfo="skip"), row=1, col=col)


def whiskers(lo, hi, x):
    return dict(type="data", symmetric=False, array=hi - x, arrayminus=x - lo,
                color=INK, thickness=1, width=0)


bar(1, rows.lead_share, [pct(v) for v in rows.lead_share], solid,
    [f"{n:,.0f} of {f.leads:,.0f} leads" for n in rows.leads])
bar(2, rows.win_rate, [pct(v, 1) for v in rows.win_rate], solid,
    [f"{s:,.0f} of {n:,.0f} leads signed<br>95% interval {pct(lo, 1)} to {pct(hi, 1)}"
     for s, n, lo, hi in zip(rows.signed, rows.leads, rows.win_lo, rows.win_hi)],
    whiskers(rows.win_lo, rows.win_hi, rows.win_rate), rows.win_hi)
bar(3, rows.activation_rate, [pct(v) for v in rows.activation_rate], by_sample,
    [f"{a:,.0f} of {n:,.0f} observed sellers sold<br>95% interval {pct(lo)} to {pct(hi)}"
     for a, n, lo, hi in zip(rows.activated, rows.observed, rows.act_lo, rows.act_hi)],
    whiskers(rows.act_lo, rows.act_hi, rows.activation_rate), rows.act_hi)
bar(4, rows.gmv_per_signed, [brl(v) for v in rows.gmv_per_signed], by_sample,
    [f"{brl(v)} per signed seller, from {n:,.0f} sellers" for v, n in zip(rows.gmv_per_signed, rows.observed)])

style(fig, 440)
fig.update_layout(margin=dict(t=64, r=40))
fig.update_xaxes(showticklabels=False)
fig.update_xaxes(range=[0, ch.lead_share.max() * 1.45], row=1, col=1)
fig.update_xaxes(range=[0, ch.win_hi.max() * 1.45], row=1, col=2)
fig.update_xaxes(range=[0, ch.act_hi.max() * 1.3], row=1, col=3)
fig.update_xaxes(range=[0, ch.gmv_per_signed.max() * 1.5], row=1, col=4)
for a in fig.layout.annotations:  # left-align the column titles over their bars
    a.update(font=dict(size=13.5, color=MUTED), xanchor="left", align="left",
             x=a.x - (1 - 3 * 0.045) / 8, yanchor="bottom", y=1.035)
show(fig, "scorecard")

thin = ", ".join(ch.channel[ch.thin])
st.html(f"""<p class="note">Thin lines show the 95% confidence interval. A long line means
few sellers behind the number. Paler bars
({thin}) rest on fewer than {SMALL_SAMPLE} observed sellers and should not be ranked against the others.
Revenue is item price in Brazilian reais, excluding freight and cancelled orders.</p>""")
numbers_and_sql(ch.drop(columns=["thin"]), "02_channels")

# --------------------------------------------------------- channel reading ---

b = base["02_channels"].set_index("channel")
paid, organic, social, unattr = (b.loc[k] for k in ["Paid search", "Organic search", "Social", "Unattributed"])
z_act = two_proportion_z(paid.activated, paid.observed, organic.activated, organic.observed)
search_win = (paid.signed + organic.signed) / (paid.leads + organic.leads)

st.html(f"""
<h2>Paid and organic search sign at the same rate, but paid search sellers sell</h2>
<p class="prose">Judged on win rate alone the two search channels are interchangeable:
{pct(paid.win_rate, 1)} against {pct(organic.win_rate, 1)}. After signing they separate.
<b>{pct(paid.activation_rate)} of paid search sellers made a sale within 90 days, against
{pct(organic.activation_rate)} from organic search</b>, a gap of
{100 * (paid.activation_rate - organic.activation_rate):.0f} points that is unlikely to be chance
(z = {z_act:.1f}). Social is the opposite case: it supplies {pct(social.lead_share)} of all leads and
signs {pct(social.win_rate, 1)} of them, less than half the search rate of {pct(search_win, 1)}.</p>
<p class="prose">The best-converting source is the one nobody can name. Leads with no recorded origin
are {pct(unattr.lead_share)} of the funnel and sign at {pct(unattr.win_rate, 1)}, the highest rate
of any group. Whatever is producing them cannot be scaled until it is tracked.</p>
""")

# ------------------------------------------------------------------- speed ---

sp, bk = data["03_speed"], data["04_speed_buckets"]
within_30 = bk.share[bk.bucket_order <= 2].sum()
slow = bk.share[bk.bucket_order >= 4].sum()
social_days = sp.set_index("channel").median_days["Social"]

st.html(f"""
<h2>Two thirds of deals close within a month, and social is the slowest source</h2>
<p class="prose">{pct(within_30)} of signed sellers closed within 30 days of first contact. A further
{pct(slow)} took more than three months, which says old leads are worth a second look before they are
written off. By channel, the median social lead needs {social_days:.0f} days to sign, twice as long as a
search lead and the slowest of any source.</p>
""")

left, right = st.columns([1, 1], gap="large")
with left:
    fig = go.Figure(go.Bar(
        x=bk.bucket, y=bk.share, marker=dict(color=BLUE, cornerradius=3),
        text=[pct(v) for v in bk.share], textposition="outside", textfont=dict(color=INK, size=13),
        customdata=bk.signed, hovertemplate="<b>%{x}</b><br>%{customdata} sellers signed<extra></extra>"))
    style(fig, 330)
    fig.update_layout(title=dict(text="Time from first contact to signing", font=dict(size=13.5, color=MUTED, weight=400), x=0),
                      bargap=0.3)
    fig.update_yaxes(showticklabels=False, range=[0, bk.share.max() * 1.2])
    fig.update_xaxes(tickfont=dict(size=12.5, color=INK))
    show(fig)
with right:
    s = sp.iloc[::-1]
    fig = go.Figure(go.Bar(
        y=s.channel, x=s.median_days, orientation="h", marker=dict(color=BLUE, cornerradius=3),
        text=[f"{d:.0f}" for d in s.median_days], textposition="outside",
        textfont=dict(color=INK, size=13), cliponaxis=False, customdata=s.signed,
        hovertemplate="<b>%{y}</b><br>median %{x:.0f} days, from %{customdata} signed sellers<extra></extra>"))
    style(fig, 330)
    fig.update_layout(title=dict(text="Median days to sign, by channel", font=dict(size=13.5, color=MUTED, weight=400), x=0))
    fig.update_xaxes(showticklabels=False, range=[0, s.median_days.max() * 1.18])
    show(fig)
numbers_and_sql(sp, "03_speed")

# ----------------------------------------------------------------- cohorts ---

co = data["05_cohorts"].copy()
co["label"] = pd.to_datetime(co.cohort_month).dt.strftime("%b %Y")
order = co.sort_values("cohort_month").label.unique().tolist()
grid = co.pivot(index="label", columns="period", values="share_selling").reindex(order)
sizes = co.groupby("label").sellers.first().reindex(order)
plateau = co[co.period >= 2].share_selling
late = base["08_late_starters"].iloc[0]
late_rate = late.late_starters / late.silent_at_90
kept_rate = late.still_selling / late.selling_at_90

st.html(f"""
<h2>Only one in five sellers who are silent after 90 days starts later</h2>
<p class="prose">Each row is the group of sellers signed in one month. Each column is a 30-day period
after signing, and the cell is the share of that group with at least one sale in the period. Every
cohort climbs for about three periods and then flattens between {pct(plateau.min())} and
{pct(plateau.max())}.</p>
<p class="prose">Following the {late.sellers:.0f} sellers who can be watched for a full six months makes
the point directly. Of the {late.silent_at_90:.0f} with no sale in their first 90 days, <b>{late.late_starters:.0f}
({pct(late_rate)}) made one in the next 90</b>. Of the {late.selling_at_90:.0f} who had sold, {pct(kept_rate)}
were still selling. The first three months largely decide which group a seller ends up in.</p>
""")
text = [[("" if pd.isna(v) else pct(v)) for v in row] for row in grid.values]
fig = go.Figure(go.Heatmap(
    z=grid.values, x=[f"Days {30 * p + 1} to {30 * (p + 1)}" for p in grid.columns],
    y=[f"{m}  ({n} sellers)" for m, n in zip(order, sizes)],
    text=text, texttemplate="%{text}", textfont=dict(size=13, color=INK),
    colorscale=[[0, "#E9F1F4"], [1, "#6BA6BA"]], zmin=0.1, zmax=0.45, showscale=False,
    xgap=3, ygap=3, hoverongaps=False,
    hovertemplate="<b>Signed %{y}</b><br>%{x} after signing<br>%{text} had a sale<extra></extra>"))
style(fig, 60 + 44 * len(order))
fig.update_yaxes(autorange="reversed")
fig.update_xaxes(side="top", tickfont=dict(size=12.5, color=MUTED))
fig.update_layout(margin=dict(t=30))
show(fig, "cohorts")
st.html("""<p class="note">Empty cells are periods the order data does not fully cover for that cohort.
Cohorts with fewer than 20 sellers are left out.</p>""")
numbers_and_sql(co.drop(columns=["label"]), "05_cohorts")
with st.expander("See the six-month follow-up and its SQL"):
    st.dataframe(base["08_late_starters"], hide_index=True, width="stretch")
    st.code(read_sql("08_late_starters"), language="sql")

# ---------------------------------------------------------------- profiles ---

pr = data["06_profiles"]
bp = base["06_profiles"].set_index("profile")
big, offline = bp.loc["online big"], bp.loc["offline"]
reseller, maker = bp.loc["reseller"], bp.loc["manufacturer"]

st.html(f"""
<h2>The seller's profile predicts sales better than the channel does</h2>
<p class="prose">At signing, the sales team records what kind of business each seller is. That label
separates outcomes more sharply than lead source: <b>{pct(big.activation_rate)} of large online
sellers were selling within 90 days, against {pct(offline.activation_rate)} of offline businesses</b>.
Resellers activate at {pct(reseller.activation_rate)}, manufacturers at {pct(maker.activation_rate)}.
The spread between the best and worst profile is {100 * (big.activation_rate - offline.activation_rate):.0f}
points. Between the best and worst large channel it is
{100 * (b.activation_rate[b.observed >= SMALL_SAMPLE].max() - b.activation_rate[b.observed >= SMALL_SAMPLE].min()):.0f}.</p>
""")
left, right = st.columns([1, 1], gap="large")
for col, metric, title, fmt in [
    (left, "activation_rate", f"Selling within {window} days", pct),
    (right, "gmv_per_signed", f"Revenue per signed seller, {window} days", brl),
]:
    with col:
        p = pr.sort_values(["dimension", metric], ascending=[True, True])
        labels = [f"{x.capitalize()}" for x in p.profile]
        fig = go.Figure(go.Bar(
            y=labels, x=p[metric], orientation="h", marker=dict(color=BLUE, cornerradius=3),
            text=[fmt(v) for v in p[metric]], textposition="outside",
            textfont=dict(color=INK, size=13), cliponaxis=False, customdata=p.observed,
            hovertemplate="<b>%{y}</b><br>%{text}, from %{customdata} sellers<extra></extra>"))
        style(fig, 390)
        fig.update_layout(title=dict(text=title, font=dict(size=13.5, color=MUTED, weight=400), x=0))
        fig.update_xaxes(showticklabels=False, range=[0, p[metric].max() * 1.3])
        n_business = int((p.dimension == "Business type").sum())
        fig.add_hline(y=n_business - 0.5, line=dict(color=RULE, width=1))
        show(fig)
st.html("""<p class="note">Above the line: lead type. Below it: business type. Both are recorded by the
sales team at signing, so they are known before any onboarding effort is spent.</p>""")
numbers_and_sql(pr, "06_profiles")

# ----------------------------------------------------------- concentration ---

cc = base["07_concentration"]
top1 = cc.cumulative_gmv_share.iloc[0]
decile = cc[cc.cumulative_seller_share <= 0.10]
top10_share, top10_n = decile.cumulative_gmv_share.iloc[-1], len(decile)

st.html(f"""
<h2>A tenth of sellers produce {pct(top10_share)} of the revenue</h2>
<p class="prose">Revenue per seller is a fragile yardstick here. Across the {f.observed:,.0f} observable
sellers, the top {top10_n} account for {pct(top10_share)} of 90-day revenue, and a single seller for
{pct(top1)}. That is why the scorecard leaves the largest seller out by default, and why the conclusions
on this page lean on rates, which one account cannot move.</p>
""")
fig = go.Figure()
fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color=RULE, width=1.5, dash="dot"),
                         hoverinfo="skip"))
fig.add_trace(go.Scatter(
    x=[0, *cc.cumulative_seller_share], y=[0, *cc.cumulative_gmv_share], mode="lines",
    line=dict(color=BLUE, width=2.5), fill="tozeroy", fillcolor="rgba(31,111,139,0.08)",
    hovertemplate="Top %{x:.0%} of sellers<br>%{y:.0%} of revenue<extra></extra>"))
fig.add_trace(go.Scatter(x=[0.10], y=[top10_share], mode="markers",
                         marker=dict(color=OCHRE, size=11, line=dict(color="white", width=2)), hoverinfo="skip"))
fig.add_annotation(x=0.10, y=top10_share, text=f"Top 10% of sellers<br>{pct(top10_share)} of revenue",
                   showarrow=False, xanchor="left", yanchor="top", xshift=14, yshift=-2, align="left",
                   font=dict(size=13.5, color=INK))
fig.add_annotation(x=0.72, y=0.72, text="If every seller sold the same", showarrow=False, textangle=-27,
                   yshift=-14, font=dict(size=12.5, color=MUTED))
style(fig, 380)
fig.update_xaxes(tickformat=".0%", dtick=0.2, range=[0, 1.005], title=dict(
    text="Sellers, ranked from largest to smallest", font=dict(size=13, color=MUTED)))
fig.update_yaxes(tickformat=".0%", dtick=0.25, range=[0, 1.03], showgrid=True, gridcolor="#EDF0F2",
                 tickfont=dict(color=MUTED, size=13))
fig.update_layout(title=dict(text="Cumulative share of 90-day revenue", font=dict(size=13.5, color=MUTED, weight=400), x=0),
                  hovermode="x")
show(fig)
numbers_and_sql(cc.head(50), "07_concentration")

# ----------------------------------------------------------------- actions ---

extra_active = 0.10 * f.signed
small = b.loc[["Email", "Other sources"]]
st.html(f"""
<h2>What I would change, in order</h2>
<ol class="actions">
  <li><div><p class="do">Move effort from signing sellers to getting them to a first sale.</p>
      <p class="why">{pct(1 - act_rate)} of signed sellers sell nothing in 90 days, and only {pct(late_rate)} of
      those start in the following 90. Lifting activation by 10 points across the {f.signed:,.0f} signed
      sellers adds about {extra_active:.0f} active sellers. For scale, email and the three
      smallest sources together signed {small.signed.sum():.0f} sellers in the whole year.</p></div></li>
  <li><div><p class="do">Qualify on seller profile before spending sales time.</p>
      <p class="why">Large online sellers activate at {pct(big.activation_rate)}, offline businesses
      at {pct(offline.activation_rate)}. The profile is known at the first call, so it can decide who gets a
      fast track and who gets a lighter, self-serve onboarding.</p></div></li>
  <li><div><p class="do">Shift budget from social toward paid search.</p>
      <p class="why">Social brings {pct(social.lead_share)} of leads, signs {pct(social.win_rate, 1)} and takes
      twice as long as search to close. Paid search signs {pct(paid.win_rate, 1)} and its sellers activate at
      {pct(paid.activation_rate)}, the best of any large channel. This dataset has no spend figures, so the
      size of the shift needs cost per lead before it is decided.</p></div></li>
  <li><div><p class="do">Fix attribution for the {pct(unattr.lead_share)} of leads with no source.</p>
      <p class="why">They sign at {pct(unattr.win_rate, 1)}, better than every named channel. Until their
      origin is captured, the best-performing part of the funnel cannot be repeated on purpose.</p></div></li>
</ol>
""")

# ------------------------------------------------------------------ method ---

st.html(f"""
<h2>How this was measured</h2>
<p class="note"><b style="color:{INK}">Data.</b> Olist's public Marketing Funnel and Brazilian E-Commerce
datasets (CC BY-NC-SA 4.0): 8,000 marketing qualified leads with first contact between June 2017 and May 2018,
842 closed deals, and the orders of those sellers up to {pd.Timestamp(CUTOFF):%d %B %Y}. It is a real but
sampled and anonymised extract, so absolute volumes understate the business.</p>
<p class="note"><b style="color:{INK}">Fair observation windows.</b> A seller counts toward a sales metric only
if they signed at least that many days before the order data ends. Without this rule, recently signed sellers
would look like failures simply because their sales had not happened yet.</p>
<p class="note"><b style="color:{INK}">What it cannot answer.</b> There is no marketing spend in the data, so
cost per lead, CAC and return on ad spend are out of reach. The findings rank channels on the quality of what
they bring, which is half of a budget decision. Differences between channels are associations, and the mix of
seller profiles each channel attracts may explain part of them.</p>
<p class="note"><b style="color:{INK}">Reproduce it.</b> Every figure on this page comes from the SQL files in
the <a href="{REPO_URL}" target="_blank" rel="noopener" style="color:{BLUE}">repository</a>, shown under each chart.</p>
""")

# ------------------------------------------------------------------ author ---

links = [f'<a href="{GITHUB_URL}" target="_blank" rel="noopener">GitHub</a>']
if LINKEDIN_URL:
    links.insert(0, f'<a href="{LINKEDIN_URL}" target="_blank" rel="noopener">LinkedIn</a>')
st.html(f"""
<div class="author">
  <p class="name">{AUTHOR}</p>
  <p class="prose" style="margin-bottom:.5rem">I work in growth and business development, across partnerships,
  affiliate and performance marketing. This project puts the questions I ask of a partner funnel to a public
  dataset: where leads come from, which ones sign, and which of those go on to produce revenue.</p>
  <p class="byline" style="margin:0">{" and ".join(links)}</p>
</div>
""")
