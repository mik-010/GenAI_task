"""Main Dash application — multi-page layout with global filters."""

import dash
from dash import html, dcc, Input, Output, callback
import dash_bootstrap_components as dbc

from app.config import DASH_PORT

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder="pages",
    external_stylesheets=[dbc.themes.FLATLY, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Claude Code Analytics",
)

SIDEBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "bottom": 0,
    "width": "16rem",
    "padding": "2rem 1rem",
    "backgroundColor": "#f8f9fa",
    "overflowY": "auto",
}

CONTENT_STYLE = {
    "marginLeft": "17rem",
    "padding": "2rem 2rem",
}

sidebar = html.Div(
    [
        html.H4("Claude Code", className="text-primary"),
        html.H6("Analytics Platform", className="text-muted mb-4"),
        html.Hr(),
        dbc.Nav(
            [
                dbc.NavLink(
                    [html.I(className="fas fa-tachometer-alt me-2"), "Executive"],
                    href="/",
                    active="exact",
                ),
                dbc.NavLink(
                    [html.I(className="fas fa-tools me-2"), "Engineering"],
                    href="/engineering",
                    active="exact",
                ),
                dbc.NavLink(
                    [html.I(className="fas fa-chart-bar me-2"), "Analyst"],
                    href="/analyst",
                    active="exact",
                ),
                dbc.NavLink(
                    [html.I(className="fas fa-brain me-2"), "Predictions"],
                    href="/predictions",
                    active="exact",
                ),
            ],
            vertical=True,
            pills=True,
        ),
        html.Hr(),
        html.Div(id="data-freshness", className="small text-muted mt-3"),
    ],
    style=SIDEBAR_STYLE,
)

content = html.Div(dash.page_container, style=CONTENT_STYLE)

app.layout = html.Div([
    dcc.Interval(id="refresh-interval", interval=60_000, n_intervals=0),
    sidebar,
    content,
])


@callback(Output("data-freshness", "children"), Input("refresh-interval", "n_intervals"))
def update_freshness(_n):
    try:
        from app.transform.queries import last_ingested_at
        ts = last_ingested_at()
        return f"Last data: {ts[:19]}" if ts else "No data loaded"
    except Exception:
        return "DB unavailable"


def main():
    app.run(debug=True, host="0.0.0.0", port=DASH_PORT)


if __name__ == "__main__":
    main()
