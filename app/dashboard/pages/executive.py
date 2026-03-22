"""Executive dashboard — high-level KPIs, cost/usage trends, peak windows."""

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

dash.register_page(__name__, path="/", name="Executive", order=0)

# ── layout ──────────────────────────────────────────────────────

layout = html.Div([
    html.H3("Executive Overview", className="mb-3"),

    # KPI cards row
    dbc.Row(id="kpi-cards", className="mb-4 g-3"),

    # Filters row
    dbc.Row([
        dbc.Col([
            dbc.Label("Practice"),
            dcc.Dropdown(id="exec-practice-filter", placeholder="All practices"),
        ], md=3),
        dbc.Col([
            dbc.Label("Level"),
            dcc.Dropdown(id="exec-level-filter", placeholder="All levels"),
        ], md=3),
    ], className="mb-4"),

    # Charts
    dbc.Row([
        dbc.Col(dcc.Graph(id="cost-trend-chart"), md=8),
        dbc.Col(dcc.Graph(id="cost-by-practice-chart"), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="token-trend-chart"), md=8),
        dbc.Col(dcc.Graph(id="cost-by-level-chart"), md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="peak-heatmap"), md=6),
        dbc.Col(dcc.Graph(id="model-efficiency-chart"), md=6),
    ]),
])


def _kpi_card(title, value, icon, color="primary"):
    return dbc.Col(
        dbc.Card(dbc.CardBody([
            html.Div([
                html.I(className=f"fas {icon} fa-2x text-{color}"),
            ], className="mb-2"),
            html.P(title, className="text-muted mb-1 small"),
            html.H5(
                value,
                className="mb-0 fw-bold text-nowrap",
                style={"fontSize": "clamp(0.85rem, 1.4vw, 1.25rem)"},
            ),
        ], className="text-center py-2"), className="shadow-sm h-100"),
        xs=6, sm=4, md=3, lg=2, className="mb-3",
    )


# ── callbacks ───────────────────────────────────────────────────

@callback(
    Output("exec-practice-filter", "options"),
    Output("exec-level-filter", "options"),
    Input("exec-practice-filter", "id"),
)
def load_filter_options(_):
    from app.transform.queries import distinct_practices, distinct_levels
    try:
        practices = [{"label": p, "value": p} for p in distinct_practices()]
        levels = [{"label": l, "value": l} for l in distinct_levels()]
    except Exception:
        practices, levels = [], []
    return practices, levels


@callback(
    Output("kpi-cards", "children"),
    Input("exec-practice-filter", "value"),
    Input("exec-level-filter", "value"),
)
def update_kpis(practice, level):
    from app.transform.queries import kpi_summary
    try:
        kpi = kpi_summary(practice=practice, level=level)
    except Exception:
        kpi = {}
    cards = [
        _kpi_card("Total Requests", f"{kpi.get('total_requests', 0):,.0f}", "fa-server", "primary"),
        _kpi_card("Total Cost", f"${kpi.get('total_cost', 0):,.2f}", "fa-dollar-sign", "success"),
        _kpi_card("Total Tokens", f"{kpi.get('total_tokens', 0):,.0f}", "fa-microchip", "info"),
        _kpi_card("Sessions", f"{kpi.get('total_sessions', 0):,.0f}", "fa-clock", "warning"),
        _kpi_card("Users", f"{kpi.get('total_users', 0):,.0f}", "fa-users", "danger"),
        _kpi_card("Avg Latency", f"{kpi.get('avg_latency_ms', 0):,.0f}ms", "fa-bolt", "secondary"),
    ]
    return cards


@callback(
    Output("cost-trend-chart", "figure"),
    Output("token-trend-chart", "figure"),
    Input("exec-practice-filter", "value"),
    Input("exec-level-filter", "value"),
)
def update_trends(practice, level):
    from app.transform.queries import daily_usage_trends
    try:
        df = daily_usage_trends(practice=practice, level=level)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        empty = go.Figure().update_layout(title="No data")
        return empty, empty

    daily = df.groupby("day").agg(
        total_cost=("total_cost", "sum"),
        total_input=("total_input_tokens", "sum"),
        total_output=("total_output_tokens", "sum"),
        requests=("request_count", "sum"),
    ).reset_index()

    cost_fig = px.area(daily, x="day", y="total_cost",
                       title="Daily Cost Trend", labels={"total_cost": "Cost (USD)", "day": ""})
    cost_fig.update_layout(hovermode="x unified")

    token_fig = go.Figure()
    token_fig.add_trace(go.Scatter(x=daily["day"], y=daily["total_input"],
                                   mode="lines", name="Input Tokens", stackgroup="one"))
    token_fig.add_trace(go.Scatter(x=daily["day"], y=daily["total_output"],
                                   mode="lines", name="Output Tokens", stackgroup="one"))
    token_fig.update_layout(title="Daily Token Consumption", hovermode="x unified",
                            xaxis_title="", yaxis_title="Tokens")

    return cost_fig, token_fig


@callback(
    Output("cost-by-practice-chart", "figure"),
    Input("exec-level-filter", "value"),
)
def update_cost_practice(level):
    from app.transform.queries import cost_by_practice
    try:
        df = cost_by_practice(level=level)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")
    return px.pie(df, values="total_cost", names="practice", title="Cost by Practice", hole=0.4)


@callback(
    Output("cost-by-level-chart", "figure"),
    Input("exec-practice-filter", "value"),
)
def update_cost_level(practice):
    from app.transform.queries import cost_by_level
    try:
        df = cost_by_level(practice=practice)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")
    return px.bar(df, x="level", y="total_cost", title="Cost by Seniority Level",
                  labels={"total_cost": "Cost (USD)"})


@callback(Output("peak-heatmap", "figure"), Input("exec-practice-filter", "value"))
def update_peak(_practice):
    from app.transform.queries import hourly_peak
    try:
        df = hourly_peak(practice=_practice)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    pivot = df.pivot_table(index="dow", columns="hour", values="request_count",
                           aggfunc="sum", fill_value=0)
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{h}:00" for h in pivot.columns],
        y=[dow_labels[int(d)] for d in pivot.index],
        colorscale="YlOrRd",
    ))
    fig.update_layout(title="Peak Usage Heatmap (Day x Hour)", xaxis_title="Hour", yaxis_title="")
    return fig


@callback(Output("model-efficiency-chart", "figure"), Input("exec-practice-filter", "value"))
def update_model_eff(practice):
    from app.transform.queries import model_efficiency
    try:
        df = model_efficiency(practice=practice)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    df["model_short"] = df["model"].str.replace("claude-", "").str[:20]
    fig = px.scatter(
        df, x="avg_cost", y="tokens_per_sec",
        size="request_count", color="model_short",
        title="Model Efficiency: Cost vs Speed",
        labels={"avg_cost": "Avg Cost (USD)", "tokens_per_sec": "Tokens/sec"},
        hover_data=["model", "total_cost"],
    )
    return fig
