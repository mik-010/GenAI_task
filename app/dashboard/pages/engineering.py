"""Engineering Lead dashboard — tool behaviors, error rates, team comparisons."""

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

dash.register_page(__name__, path="/engineering", name="Engineering", order=1)

layout = html.Div([
    html.H3("Engineering Insights", className="mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Practice"),
            dcc.Dropdown(id="eng-practice-filter", placeholder="All practices"),
        ], md=3),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="tool-freq-chart"), md=6),
        dbc.Col(dcc.Graph(id="tool-success-chart"), md=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="tool-latency-chart"), md=6),
        dbc.Col(dcc.Graph(id="error-timeline-chart"), md=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="error-breakdown-chart"), md=6),
        dbc.Col(dcc.Graph(id="prompt-dist-chart"), md=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H5("Top Users by Cost"),
            html.Div(id="leaderboard-table"),
        ], md=12),
    ]),
])


@callback(Output("eng-practice-filter", "options"), Input("eng-practice-filter", "id"))
def load_eng_practices(_):
    from app.transform.queries import distinct_practices
    try:
        return [{"label": p, "value": p} for p in distinct_practices()]
    except Exception:
        return []


@callback(
    Output("tool-freq-chart", "figure"),
    Output("tool-success-chart", "figure"),
    Output("tool-latency-chart", "figure"),
    Input("eng-practice-filter", "value"),
)
def update_tool_charts(practice):
    from app.transform.queries import tool_behavior
    try:
        df = tool_behavior(practice=practice)
    except Exception:
        df = pd.DataFrame()

    empty = go.Figure().update_layout(title="No data")
    if df.empty:
        return empty, empty, empty

    # Frequency
    decisions = df[df["event_name"] == "tool_decision"].copy()
    freq_fig = px.bar(decisions.sort_values("event_count", ascending=True),
                      x="event_count", y="tool_name", orientation="h",
                      title="Tool Decision Frequency",
                      labels={"event_count": "Decisions", "tool_name": "Tool"})

    # Success rate
    results = df[df["event_name"] == "tool_result"].copy()
    if not results.empty:
        results["success_rate"] = results["success_count"] / (
            results["success_count"] + results["failure_count"]
        ).replace(0, 1) * 100
        success_fig = px.bar(results.sort_values("success_rate"),
                             x="success_rate", y="tool_name", orientation="h",
                             title="Tool Success Rate (%)",
                             labels={"success_rate": "Success %", "tool_name": "Tool"})
        success_fig.update_xaxes(range=[80, 100])
    else:
        success_fig = empty

    # Latency
    if not results.empty and "avg_duration_ms" in results.columns:
        latency_fig = px.bar(results.dropna(subset=["avg_duration_ms"]).sort_values("avg_duration_ms", ascending=True),
                             x="avg_duration_ms", y="tool_name", orientation="h",
                             title="Avg Tool Latency (ms)",
                             labels={"avg_duration_ms": "ms", "tool_name": "Tool"},
                             log_x=True)
    else:
        latency_fig = empty

    return freq_fig, success_fig, latency_fig


@callback(
    Output("error-timeline-chart", "figure"),
    Output("error-breakdown-chart", "figure"),
    Input("eng-practice-filter", "value"),
)
def update_error_charts(_):
    from app.transform.queries import error_rates_daily, error_summary
    try:
        daily = error_rates_daily()
        summary = error_summary()
    except Exception:
        daily, summary = pd.DataFrame(), pd.DataFrame()

    empty = go.Figure().update_layout(title="No data")

    if daily.empty:
        timeline = empty
    else:
        timeline = px.line(daily.groupby("day")["error_count"].sum().reset_index(),
                           x="day", y="error_count", title="API Errors Over Time",
                           labels={"error_count": "Errors", "day": ""})

    if summary.empty:
        breakdown = empty
    else:
        breakdown = px.bar(summary, x="model", y="total_errors", color="status_code",
                           title="Errors by Model & Status", barmode="stack",
                           labels={"total_errors": "Errors"})
        breakdown.update_xaxes(tickangle=30)

    return timeline, breakdown


@callback(Output("prompt-dist-chart", "figure"), Input("eng-practice-filter", "value"))
def update_prompt_dist(_):
    from app.transform.queries import prompt_length_distribution
    try:
        df = prompt_length_distribution()
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")
    return px.bar(df, x="bucket", y="count", title="Prompt Length Distribution",
                  labels={"bucket": "Characters", "count": "Prompts"})


@callback(Output("leaderboard-table", "children"), Input("eng-practice-filter", "value"))
def update_leaderboard(_):
    from app.transform.queries import user_leaderboard
    try:
        df = user_leaderboard(limit=15)
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return html.P("No data")
    df_display = df[["full_name", "practice", "level", "requests", "total_cost", "sessions"]].copy()
    df_display["total_cost"] = df_display["total_cost"].map(lambda x: f"${x:,.2f}")
    return dbc.Table.from_dataframe(df_display, striped=True, bordered=True, hover=True, size="sm")
