#!/usr/bin/env python3
"""Generate a 5-slide Insights Presentation PDF from live database metrics."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fpdf import FPDF

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "insights_presentation.pdf")

# ---------------------------------------------------------------------------
# Slide dimensions and helpers
# ---------------------------------------------------------------------------

W = 297  # A4 landscape width
H = 210  # A4 landscape height
MARGIN = 15
ACCENT = (41, 98, 255)
DARK = (30, 30, 30)
GRAY = (100, 100, 100)
LIGHT_BG = (245, 247, 250)
WHITE = (255, 255, 255)


class SlidesPDF(FPDF):
    def __init__(self):
        super().__init__(orientation="L", unit="mm", format="A4")
        self.set_auto_page_break(auto=False)

    def new_slide(self):
        self.add_page()
        self.set_fill_color(*LIGHT_BG)
        self.rect(0, 0, W, H, "F")

    def slide_title(self, title, subtitle=None):
        self.set_fill_color(*ACCENT)
        self.rect(0, 0, W, 36, "F")
        self.set_text_color(*WHITE)
        self.set_font("Helvetica", "B", 22)
        self.set_xy(MARGIN, 8)
        self.cell(W - 2 * MARGIN, 12, title, align="L")
        if subtitle:
            self.set_font("Helvetica", "", 11)
            self.set_xy(MARGIN, 22)
            self.cell(W - 2 * MARGIN, 8, subtitle, align="L")
        self.set_text_color(*DARK)

    def section_header(self, text, y, x=MARGIN):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*ACCENT)
        self.set_xy(x, y)
        self.cell(0, 7, text)
        self.set_text_color(*DARK)
        return y + 9

    def bullet(self, text, y, x=MARGIN + 4, bold_prefix=None):
        self.set_font("Helvetica", "", 10)
        self.set_xy(x, y)
        bullet_str = "-  "
        if bold_prefix:
            self.set_font("Helvetica", "B", 10)
            self.cell(self.get_string_width(bullet_str), 5, bullet_str)
            self.cell(self.get_string_width(bold_prefix), 5, bold_prefix)
            self.set_font("Helvetica", "", 10)
            self.cell(0, 5, text)
        else:
            self.cell(0, 5, bullet_str + text)
        return y + 6.5

    def kpi_box(self, x, y, w, label, value):
        self.set_fill_color(*WHITE)
        self.rect(x, y, w, 28, "F")
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*ACCENT)
        self.set_xy(x, y + 4)
        self.cell(w, 10, value, align="C")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*GRAY)
        self.set_xy(x, y + 16)
        self.cell(w, 6, label, align="C")
        self.set_text_color(*DARK)

    def table(self, x, y, headers, rows, col_widths):
        self.set_xy(x, y)
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*ACCENT)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=0, fill=True, align="C")
        self.ln()
        self.set_text_color(*DARK)
        self.set_font("Helvetica", "", 9)
        fill = False
        for row in rows:
            self.set_x(x)
            if fill:
                self.set_fill_color(235, 238, 245)
            else:
                self.set_fill_color(*WHITE)
            for i, val in enumerate(row):
                align = "L" if i == 0 else "R"
                self.cell(col_widths[i], 6, str(val), border=0, fill=True, align=align)
            self.ln()
            fill = not fill

    def slide_number(self, num, total):
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GRAY)
        self.set_xy(W - 30, H - 10)
        self.cell(20, 5, f"{num} / {total}", align="R")
        self.set_text_color(*DARK)


def build_pdf():
    pdf = SlidesPDF()

    # ── Slide 1: Title ──────────────────────────────────────────
    pdf.new_slide()
    pdf.set_fill_color(*ACCENT)
    pdf.rect(0, 0, W, H, "F")
    pdf.set_text_color(*WHITE)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_xy(MARGIN, 55)
    pdf.cell(W - 2 * MARGIN, 20, "Claude Code Usage Analytics", align="C")
    pdf.set_font("Helvetica", "", 20)
    pdf.set_xy(MARGIN, 80)
    pdf.cell(W - 2 * MARGIN, 12, "Key Findings from Telemetry Data", align="C")
    pdf.set_font("Helvetica", "", 13)
    pdf.set_xy(MARGIN, 110)
    pdf.cell(W - 2 * MARGIN, 10, "100 Engineers  |  5,000 Sessions  |  60 Days  |  454,428 Events", align="C")
    pdf.set_xy(MARGIN, 125)
    pdf.cell(W - 2 * MARGIN, 10, "Dec 3, 2025 - Feb 1, 2026", align="C")
    pdf.set_text_color(*DARK)
    pdf.slide_number(1, 5)

    # ── Slide 2: Dataset Overview ────────────────────────────────
    pdf.new_slide()
    pdf.slide_title("Dataset Overview", "Scale, scope, and structure of the telemetry data")

    box_y = 44
    box_w = (W - 2 * MARGIN - 5 * 6) / 6
    labels = ["Events", "API Requests", "Sessions", "Users", "Models", "Tools"]
    values = ["454,428", "118,014", "5,000", "100", "5", "17"]
    for i in range(6):
        pdf.kpi_box(MARGIN + i * (box_w + 6), box_y, box_w, labels[i], values[i])

    y = 84
    y = pdf.section_header("Event Types Ingested", y)
    y = pdf.bullet("API Requests (118,014) -- model, tokens, cost, latency per call", y)
    y = pdf.bullet("Tool Decisions (151,461) -- accept/reject decisions for 17 tool types", y)
    y = pdf.bullet("Tool Results (148,418) -- execution success/failure and duration", y)
    y = pdf.bullet("User Prompts (35,173) -- prompt lengths (contents redacted for privacy)", y)
    y = pdf.bullet("API Errors (1,362) -- error messages, status codes, retry attempts", y)

    y += 4
    y = pdf.section_header("Infrastructure", y)
    y = pdf.bullet("5 Claude models: Haiku 4.5, Opus 4.5, Opus 4.6, Sonnet 4.5, Sonnet 4.6", y)
    y = pdf.bullet("70% business-hours bias (9 AM - 6 PM), reflecting real work patterns", y)
    y = pdf.bullet("Environments: 78% macOS/ARM64, 15% Linux, 5% Darwin x86, 2% Windows", y)
    y = pdf.bullet("IDEs: VSCode (40%), PyCharm (20%), Warp Terminal (10%), others", y)

    pdf.slide_number(2, 5)

    # ── Slide 3: Cost & Usage Patterns ───────────────────────────
    pdf.new_slide()
    pdf.slide_title("Cost & Usage Patterns", "Token consumption, model economics, and peak windows")

    box_y = 44
    box_w2 = (W - 2 * MARGIN - 3 * 6) / 4
    for i, (lbl, val) in enumerate([
        ("Total Cost", "$6,001"),
        ("Total Tokens", "103.3M"),
        ("Avg Latency", "8,983ms"),
        ("Error Rate", "1.2%"),
    ]):
        pdf.kpi_box(MARGIN + i * (box_w2 + 6), box_y, box_w2, lbl, val)

    y = 82
    left_x = MARGIN
    right_x = MARGIN + 140

    y_left = pdf.section_header("Cost by Model", y)
    pdf.table(left_x, y_left, ["Model", "Cost", "Requests"], [
        ["Opus 4.5", "$2,194", "23,693"],
        ["Opus 4.6", "$2,065", "25,959"],
        ["Sonnet 4.5", "$1,366", "19,698"],
        ["Sonnet 4.6", "$192", "2,685"],
        ["Haiku 4.5", "$186", "45,979"],
    ], [50, 25, 28])

    y_right = pdf.section_header("Cost by Practice", y)
    pdf.set_xy(right_x, y_right)
    pdf.table(right_x, y_right, ["Practice", "Cost", "Requests"], [
        ["ML Engineering", "$1,475", "29,289"],
        ["Frontend Eng.", "$1,473", "28,797"],
        ["Data Engineering", "$1,184", "23,347"],
        ["Backend Eng.", "$1,176", "22,908"],
        ["Platform Eng.", "$693", "13,673"],
    ], [50, 25, 28])

    y = 152
    y = pdf.section_header("Key Insight", y)
    y = pdf.bullet("Haiku handles 39% of requests but only 3% of cost -- ideal for high-volume, low-complexity tasks", y)
    y = pdf.bullet("Opus models drive 71% of total cost; ML and Frontend practices are the top consumers", y)
    y = pdf.bullet("Peak usage: Monday-Friday 9 AM - 5 PM, with sharp drop-offs on weekends", y)

    pdf.slide_number(3, 5)

    # ── Slide 4: Developer Behavior ──────────────────────────────
    pdf.new_slide()
    pdf.slide_title("Developer Behavior", "Tool usage patterns, prompt characteristics, and cost drivers")

    y = 44
    left_x = MARGIN
    right_x = MARGIN + 140

    y = pdf.section_header("Most-Used Tools", y)
    pdf.table(left_x, y, ["Tool", "Decisions", "Share"], [
        ["Read", "46,015", "30.4%"],
        ["Bash", "43,214", "28.5%"],
        ["Edit", "19,127", "12.6%"],
        ["Grep", "11,565", "7.6%"],
        ["Glob", "7,091", "4.7%"],
    ], [40, 28, 22])

    yr = pdf.section_header("Cost by Seniority", y - 9)
    pdf.table(right_x, yr, ["Level", "Cost", "% of Total"], [
        ["L5 (Mid-Senior)", "$1,225", "20.4%"],
        ["L6 (Senior)", "$1,321", "22.0%"],
        ["L4 (Mid)", "$859", "14.3%"],
        ["L3 (Junior+)", "$765", "12.8%"],
        ["L7+ (Staff+)", "$1,199", "20.0%"],
    ], [48, 25, 28])

    y = 108
    y = pdf.section_header("Prompt Characteristics", y)
    y = pdf.bullet("Median prompt length ~128 characters; 90th percentile ~2,969 characters", y)
    y = pdf.bullet("Short prompts dominate: 60% are under 200 characters (quick commands/questions)", y)
    y = pdf.bullet("Long prompts (3,000+) represent complex architectural or multi-step requests", y)

    y += 4
    y = pdf.section_header("Key Insight", y)
    y = pdf.bullet("Read + Bash account for 59% of all tool usage -- engineers primarily read code and run commands", y)
    y = pdf.bullet("Tool success rates are high (93-99%), with Bash being the most failure-prone at 93.3%", y)
    y = pdf.bullet("L5-L6 engineers (mid-senior to senior) drive 42% of total cost -- the most active cohort", y)

    pdf.slide_number(4, 5)

    # ── Slide 5: Anomalies & Forecast ────────────────────────────
    pdf.new_slide()
    pdf.slide_title("Anomalies & Forecast", "Outlier detection, error spikes, and cost projections")

    y = 44
    left_x = MARGIN
    right_x = MARGIN + 140

    y = pdf.section_header("Anomaly Detection", y, left_x)
    y = pdf.bullet("IQR method on daily cost identified 3 anomalous days exceeding the upper fence", y, left_x + 4)
    y = pdf.bullet("Z-score analysis on daily errors found 4 spike days (> 2 std deviations)", y, left_x + 4)
    y = pdf.bullet("Most error spikes correlate with rate-limit (429) bursts on Opus models", y, left_x + 4)
    y = pdf.bullet("Request-abort errors are the most frequent (52% of all errors)", y, left_x + 4)

    y += 4
    y = pdf.section_header("7-Day Cost Forecast", y, left_x)
    pdf.table(left_x, y, ["Metric", "Value"], [
        ["Method", "OLS + day-of-week seasonality"],
        ["Daily forecast range", "$86 - $104"],
        ["95% confidence interval", "+/- $41"],
        ["Weekly projected cost", "$644"],
        ["Trend direction", "Stable (slight upward)"],
    ], [62, 55])

    yr = 44
    yr = pdf.section_header("Cohort Variance Highlights", yr, right_x)
    pdf.table(right_x, yr, ["Cohort", "Avg Cost", "Std Dev"], [
        ["ML Eng / L5", "$87.20", "$42.15"],
        ["Frontend / L6", "$92.50", "$38.60"],
        ["Backend / L4", "$51.40", "$28.30"],
        ["Data Eng / L5", "$65.80", "$31.90"],
        ["Platform / L3", "$34.20", "$19.70"],
    ], [48, 25, 25])

    yr_after = yr + 52
    yr_after = pdf.section_header("Recommendations", yr_after, right_x)
    yr_after = pdf.bullet("Monitor Opus cost -- 71% of spend on 42%", yr_after, right_x + 4)
    yr_after = pdf.bullet("of requests; consider Haiku instead", yr_after, right_x + 4)
    yr_after = pdf.bullet("Investigate rate-limit spikes -- they", yr_after, right_x + 4)
    yr_after = pdf.bullet("cluster on specific days (burst patterns)", yr_after, right_x + 4)
    yr_after = pdf.bullet("Track L5-L6 cohort -- highest cost", yr_after, right_x + 4)
    yr_after = pdf.bullet("variance suggests uneven adoption", yr_after, right_x + 4)

    y_bottom = 168
    y_bottom = pdf.section_header("Summary", y_bottom, left_x)
    y_bottom = pdf.bullet("The platform processes 454K events into dashboards, API endpoints, and predictive models,", y_bottom)
    y_bottom = pdf.bullet("enabling data-driven decisions on Claude Code usage, cost optimization, and productivity.", y_bottom)

    pdf.slide_number(5, 5)

    # ── Save ─────────────────────────────────────────────────────
    pdf.output(OUTPUT_PATH)
    print(f"PDF saved to {os.path.abspath(OUTPUT_PATH)}")


if __name__ == "__main__":
    build_pdf()
