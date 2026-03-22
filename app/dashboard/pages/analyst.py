"""Analyst dashboard — deep filters, downloadable aggregates, session-level drill-down."""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

dash.register_page(__name__, path="/analyst", name="Analyst", order=2)

layout = html.Div([
    html.H3("Analyst Deep-Dive", className="mb-3"),

    # Filters
    dbc.Row([
        dbc.Col([
            dbc.Label("Practice"),
            dcc.Dropdown(id="an-practice", placeholder="All"),
        ], md=2),
        dbc.Col([
            dbc.Label("Level"),
            dcc.Dropdown(id="an-level", placeholder="All"),
        ], md=2),
        dbc.Col([
            dbc.Label("Model"),
            dcc.Dropdown(id="an-model", placeholder="All"),
        ], md=3),
        dbc.Col([
            dbc.Label("Tool"),
            dcc.Dropdown(id="an-tool", placeholder="All"),
        ], md=3),
        dbc.Col([
            dbc.Label("\u00A0"),
            dbc.Button("Export CSV", id="an-export-btn", color="secondary", className="d-block"),
        ], md=2),
    ], className="mb-4"),

    dcc.Download(id="an-download"),

    # Aggregated data table
    html.H5("Aggregated Daily Usage"),
    html.Div(id="an-agg-table", className="mb-4", style={"overflowX": "auto"}),

    # Tool usage over time
    dbc.Row([
        dbc.Col(dcc.Graph(id="an-tool-timeline"), md=6),
        dbc.Col(dcc.Graph(id="an-session-scatter"), md=6),
    ]),
])


@callback(
    Output("an-practice", "options"),
    Output("an-level", "options"),
    Output("an-model", "options"),
    Output("an-tool", "options"),
    Input("an-practice", "id"),
)
def load_analyst_filters(_):
    from app.transform.queries import distinct_practices, distinct_levels, distinct_models, distinct_tools
    try:
        return (
            [{"label": p, "value": p} for p in distinct_practices()],
            [{"label": l, "value": l} for l in distinct_levels()],
            [{"label": m, "value": m} for m in distinct_models()],
            [{"label": t, "value": t} for t in distinct_tools()],
        )
    except Exception:
        return [], [], [], []


@callback(
    Output("an-agg-table", "children"),
    Input("an-practice", "value"),
    Input("an-level", "value"),
)
def update_agg_table(practice, level):
    from app.transform.queries import daily_usage_trends
    try:
        df = daily_usage_trends(practice=practice, level=level)
    except Exception:
        df = pd.DataFrame()

    if df.empty:
        return html.P("No data matching filters")

    summary = df.groupby("day").agg(
        requests=("request_count", "sum"),
        cost=("total_cost", "sum"),
        input_tokens=("total_input_tokens", "sum"),
        output_tokens=("total_output_tokens", "sum"),
        sessions=("session_count", "sum"),
        users=("user_count", "sum"),
    ).reset_index()
    summary["cost"] = summary["cost"].map(lambda x: f"${x:,.2f}")
    return dbc.Table.from_dataframe(
        summary.tail(30), striped=True, bordered=True, hover=True, size="sm",
    )


@callback(
    Output("an-download", "data"),
    Input("an-export-btn", "n_clicks"),
    State("an-practice", "value"),
    State("an-level", "value"),
    prevent_initial_call=True,
)
def export_csv(n_clicks, practice, level):
    from app.transform.queries import daily_usage_trends
    try:
        df = daily_usage_trends(practice=practice, level=level)
    except Exception:
        df = pd.DataFrame()
    return dcc.send_data_frame(df.to_csv, "claude_analytics_export.csv", index=False)


@callback(Output("an-tool-timeline", "figure"), Input("an-tool", "value"))
def update_tool_timeline(tool):
    from app.transform.queries import tool_usage_over_time
    try:
        df = tool_usage_over_time()
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    if tool:
        df = df[df["tool_name"] == tool]

    fig = px.line(df, x="day", y="usage_count", color="tool_name",
                  title="Tool Usage Over Time",
                  labels={"usage_count": "Uses", "day": "", "tool_name": "Tool"})
    return fig


@callback(Output("an-session-scatter", "figure"), Input("an-practice", "value"))
def update_session_scatter(_):
    from app.transform.queries import session_stats
    try:
        df = session_stats()
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = px.scatter(df, x="sessions", y="total_events", color="practice",
                     size="users", hover_data=["level"],
                     title="Sessions vs Events by Practice",
                     labels={"sessions": "Sessions", "total_events": "Total Events"})
    return fig
