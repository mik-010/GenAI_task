"""Predictions dashboard — forecasting, anomaly detection, advanced statistics."""

import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

dash.register_page(__name__, path="/predictions", name="Predictions", order=3)

layout = html.Div([
    html.H3("Predictive Analytics & Advanced Stats", className="mb-3"),

    dbc.Row([
        dbc.Col([
            dbc.Label("Forecast Horizon (days)"),
            dcc.Slider(id="forecast-days", min=3, max=30, step=1, value=7,
                       marks={3: "3", 7: "7", 14: "14", 30: "30"}),
        ], md=4),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="forecast-chart"), md=12),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col(dcc.Graph(id="cost-anomaly-chart"), md=6),
        dbc.Col(dcc.Graph(id="error-spike-chart"), md=6),
    ], className="mb-4"),

    dbc.Row([
        dbc.Col([
            html.H5("Token Percentiles by Practice"),
            html.Div(id="percentile-table"),
        ], md=6),
        dbc.Col([
            html.H5("Cohort Cost Variance (Practice x Level)"),
            html.Div(id="cohort-table"),
        ], md=6),
    ]),
])


@callback(Output("forecast-chart", "figure"), Input("forecast-days", "value"))
def update_forecast(periods):
    from app.ml.analytics import forecast_daily_cost
    from app.transform.queries import daily_usage_trends
    try:
        hist = daily_usage_trends()
        forecast = forecast_daily_cost(periods=periods)
    except Exception:
        return go.Figure().update_layout(title="Forecast unavailable")

    fig = go.Figure()

    if not hist.empty:
        daily = hist.groupby("day")["total_cost"].sum().reset_index()
        fig.add_trace(go.Scatter(x=daily["day"], y=daily["total_cost"],
                                 mode="lines", name="Historical"))

    if not forecast.empty:
        fig.add_trace(go.Scatter(x=forecast["day"], y=forecast["forecast_cost"],
                                 mode="lines+markers", name="Forecast",
                                 line=dict(dash="dash")))
        fig.add_trace(go.Scatter(
            x=list(forecast["day"]) + list(forecast["day"][::-1]),
            y=list(forecast["upper"]) + list(forecast["lower"][::-1]),
            fill="toself", fillcolor="rgba(68,68,68,0.15)",
            line=dict(color="rgba(255,255,255,0)"),
            name="95% CI",
        ))

    fig.update_layout(title=f"Cost Forecast ({periods}-day horizon)",
                      xaxis_title="", yaxis_title="Cost (USD)", hovermode="x unified")
    return fig


@callback(Output("cost-anomaly-chart", "figure"), Input("forecast-days", "value"))
def update_cost_anomalies(_):
    from app.ml.analytics import detect_cost_anomalies
    try:
        df = detect_cost_anomalies()
    except Exception:
        return go.Figure().update_layout(title="Anomaly detection unavailable")

    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = go.Figure()
    normal = df[~df["is_anomaly"]]
    anomaly = df[df["is_anomaly"]]
    fig.add_trace(go.Scatter(x=normal["day"], y=normal["total_cost"],
                             mode="markers", name="Normal", marker=dict(color="steelblue")))
    fig.add_trace(go.Scatter(x=anomaly["day"], y=anomaly["total_cost"],
                             mode="markers", name="Anomaly",
                             marker=dict(color="red", size=12, symbol="x")))
    if len(df) > 0:
        fig.add_hline(y=df["upper_fence"].iloc[0], line_dash="dot",
                      annotation_text="Upper Fence", line_color="orange")
        fig.add_hline(y=df["lower_fence"].iloc[0], line_dash="dot",
                      annotation_text="Lower Fence", line_color="orange")
    fig.update_layout(title="Daily Cost Anomalies (IQR)", xaxis_title="", yaxis_title="Cost (USD)")
    return fig


@callback(Output("error-spike-chart", "figure"), Input("forecast-days", "value"))
def update_error_spikes(_):
    from app.ml.analytics import detect_error_spikes
    try:
        df = detect_error_spikes()
    except Exception:
        return go.Figure().update_layout(title="Error spike detection unavailable")

    if df.empty:
        return go.Figure().update_layout(title="No data")

    fig = go.Figure()
    normal = df[~df["is_spike"]]
    spikes = df[df["is_spike"]]
    fig.add_trace(go.Bar(x=normal["day"], y=normal["error_count"], name="Normal"))
    fig.add_trace(go.Bar(x=spikes["day"], y=spikes["error_count"], name="Spike",
                         marker_color="red"))
    fig.update_layout(title="Error Spikes (Z-Score > 2)", xaxis_title="", yaxis_title="Errors",
                      barmode="overlay")
    return fig


@callback(Output("percentile-table", "children"), Input("forecast-days", "value"))
def update_percentiles(_):
    from app.ml.analytics import token_percentiles_by_practice
    try:
        df = token_percentiles_by_practice()
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return html.P("No data")
    display_cols = [c for c in df.columns if c != "count"]
    for col in display_cols:
        if col != "practice" and df[col].dtype in ("float64", "float32"):
            df[col] = df[col].map(lambda x: f"{x:,.0f}" if pd.notna(x) else "")
    return dbc.Table.from_dataframe(df[display_cols], striped=True, bordered=True, hover=True, size="sm")


@callback(Output("cohort-table", "children"), Input("forecast-days", "value"))
def update_cohorts(_):
    from app.ml.analytics import cohort_cost_variance
    try:
        df = cohort_cost_variance()
    except Exception:
        df = pd.DataFrame()
    if df.empty:
        return html.P("No data")
    for col in ["avg_cost", "std_cost", "min_cost", "max_cost"]:
        if col in df.columns:
            df[col] = df[col].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "")
    return dbc.Table.from_dataframe(df, striped=True, bordered=True, hover=True, size="sm")
