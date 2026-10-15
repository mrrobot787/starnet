"""
Agent University Dashboard
-------------------------

This Streamlit application provides an interactive dashboard for visualizing
key performance indicators (KPIs) for a university.  The design is inspired
by a typical executive dashboard: summary statistics are presented in
columns at the top of the page, followed by a series of interactive
charts and a detailed data table.  Users can upload their own data file
(JSON or CSV) or explore a synthetic data set generated at runtime.  The
data model includes academic tracks, lessons taught, student counts,
teacher counts, graduation rates, teacher retention, satisfaction rates,
scholarship and tuition costs, staff costs, and location breakdowns.

The dashboard takes advantage of Streamlit’s built‑in widgets for
filtering the data by track and date range, and uses Altair to build
interactive bar charts, line charts, and pie charts.  Metrics shown at
the top of the page include Total Lessons, Total Students, Number of
Tracks, Student/Teacher Ratio, Average Graduation Rate, Average
Satisfaction Score, and Average Teacher Retention.  Each metric also
displays the change from the previous month when possible.

To run this application locally, install the required dependencies
(`streamlit`, `pandas`, `numpy`, `altair`) and execute:

```
streamlit run agent_university_dashboard.py
```

Users can upload their own data file via the sidebar.  The file should
contain at least the following columns:

* `date`:  a date or datetime column
* `track`: the name of the academic track or college
* `lessons`: number of lessons taught in the given period
* `students`: number of enrolled students
* `teachers`: number of instructors
* `graduation_rate`: graduation rate as a fraction (0–1)
* `satisfaction_rate`: satisfaction score as a fraction (0–1)
* `retention_years`: average tenure of teachers (in years)
* `foreign_students`, `in_state_students`, `out_of_state_students`: counts
  for location breakdowns

Additional columns (e.g., `tuition_costs`, `scholarship_costs`,
`staff_cost_ratio`, `admin_cost_per_student`) will automatically be
integrated into the detailed table.

"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta


def generate_sample_data() -> pd.DataFrame:
    """Generate a synthetic data set for demonstration purposes.

    The data spans the last 24 months and includes five academic tracks.  For
    each track and month the following fields are created:

    - lessons:    number of lessons taught
    - students:   number of enrolled students
    - teachers:   number of teachers
    - graduation_rate: fraction of students who graduate
    - satisfaction_rate: average satisfaction (0–1)
    - retention_years: average teacher tenure in years
    - foreign_students, in_state_students, out_of_state_students: location counts
    - tuition_costs: average tuition per student
    - scholarship_costs: total scholarship expenses
    - staff_cost_ratio: staff cost as fraction of total budget
    - admin_cost_per_student: administrative cost per student

    Returns:
        pd.DataFrame: long‑form table with one row per (date, track)
    """
    np.random.seed(42)  # reproducible results
    tracks = [
        "College of Science",
        "College of Arts",
        "College of Engineering",
        "School of Business",
        "School of Medicine",
    ]
    # Create a monthly date range for the past two years
    today = datetime.now().date()
    start_date = (today.replace(day=1) - pd.DateOffset(months=23)).date()
    dates = pd.date_range(start=start_date, end=today, freq="MS")  # month start frequency
    records = []
    for date in dates:
        for track in tracks:
            lessons = np.random.randint(50, 400)
            students = np.random.randint(200, 4000)
            teachers = np.random.randint(20, 400)
            graduation_rate = np.random.uniform(0.6, 0.95)
            satisfaction_rate = np.random.uniform(0.6, 0.95)
            retention_years = np.random.uniform(3.0, 20.0)
            # Location distribution (should sum to students)
            foreign_pct = np.random.uniform(0.05, 0.3)
            out_state_pct = np.random.uniform(0.1, 0.4)
            in_state_pct = max(0.0, 1.0 - foreign_pct - out_state_pct)
            foreign_students = int(students * foreign_pct)
            out_of_state_students = int(students * out_state_pct)
            in_state_students = students - foreign_students - out_of_state_students
            tuition_costs = np.random.uniform(5000, 20000) * students
            scholarship_costs = np.random.uniform(1000, 15000) * students * np.random.uniform(0.05, 0.3)
            staff_cost_ratio = np.random.uniform(0.4, 0.7)
            admin_cost_per_student = np.random.uniform(1000, 10000)
            records.append(
                {
                    "date": date.date(),
                    "track": track,
                    "lessons": lessons,
                    "students": students,
                    "teachers": teachers,
                    "graduation_rate": graduation_rate,
                    "satisfaction_rate": satisfaction_rate,
                    "retention_years": retention_years,
                    "foreign_students": foreign_students,
                    "in_state_students": in_state_students,
                    "out_of_state_students": out_of_state_students,
                    "tuition_costs": tuition_costs,
                    "scholarship_costs": scholarship_costs,
                    "staff_cost_ratio": staff_cost_ratio,
                    "admin_cost_per_student": admin_cost_per_student,
                }
            )
    df = pd.DataFrame(records)
    return df


@st.cache_data(show_spinner=False)
def load_data(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile | None) -> pd.DataFrame:
    """Load metrics data from an uploaded JSON/CSV file or return sample data.

    Args:
        uploaded_file (UploadedFile | None): file uploaded by the user

    Returns:
        pd.DataFrame: DataFrame containing the metrics
    """
    if uploaded_file is not None:
        try:
            # Attempt to parse JSON first
            data = pd.read_json(uploaded_file)
        except Exception:
            try:
                data = pd.read_csv(uploaded_file)
            except Exception:
                st.error("File format not recognized. Please upload a JSON or CSV file.")
                return pd.DataFrame()
        # Ensure date column is parsed
        if "date" in data.columns:
            data["date"] = pd.to_datetime(data["date"]).dt.date
        else:
            st.warning("Uploaded file is missing a 'date' column. A synthetic date range will be generated.")
            if len(data) > 0:
                # assign a sequence of dates to each row
                start_date = datetime.now().date() - timedelta(days=len(data))
                data["date"] = pd.date_range(start=start_date, periods=len(data)).date
        return data
    # If no file uploaded, generate synthetic sample data
    return generate_sample_data()


def compute_summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Compute summary metrics from the filtered data.

    Args:
        df (pd.DataFrame): filtered subset of the data

    Returns:
        dict[str, float]: dictionary of metric values
    """
    metrics = {}
    # Aggregate values
    total_lessons = int(df["lessons"].sum())
    total_students = int(df["students"].sum())
    total_teachers = int(df["teachers"].sum())
    # Compute derived metrics
    student_teacher_ratio = total_students / total_teachers if total_teachers > 0 else 0
    avg_graduation_rate = df["graduation_rate"].mean() if not df.empty else 0.0
    avg_satisfaction = df["satisfaction_rate"].mean() if not df.empty else 0.0
    avg_retention = df["retention_years"].mean() if not df.empty else 0.0
    # Populate dictionary
    metrics.update(
        {
            "total_lessons": total_lessons,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "student_teacher_ratio": student_teacher_ratio,
            "avg_graduation_rate": avg_graduation_rate,
            "avg_satisfaction_rate": avg_satisfaction,
            "avg_retention_years": avg_retention,
        }
    )
    return metrics


def compute_deltas(df: pd.DataFrame, metric_key: str) -> float:
    """Compute the month‑over‑month delta for a given metric.

    This function looks at the most recent month in the data and compares
    it to the previous month to compute a change.  If fewer than two
    monthly periods are available, a delta of 0 is returned.

    Args:
        df (pd.DataFrame): filtered data
        metric_key (str): column name of the metric to compute delta for

    Returns:
        float: difference between the most recent month and the prior month
    """
    if df.empty or metric_key not in df.columns:
        return 0.0
    # Group by month start date to aggregate the metric
    df_monthly = (
        df.assign(month=pd.to_datetime(df["date"]).dt.to_period("M").dt.to_timestamp())
        .groupby("month")[metric_key]
        .sum()
        .sort_index()
    )
    if len(df_monthly) < 2:
        return 0.0
    latest = df_monthly.iloc[-1]
    previous = df_monthly.iloc[-2]
    delta = latest - previous
    return float(delta)


def main() -> None:
    """Run the Streamlit dashboard application."""
    st.set_page_config(page_title="Agent University Dashboard", layout="wide")
    st.title("Agent University — Live Portfolio Dashboard")

    st.markdown(
        "This dashboard provides an interactive overview of key performance metrics for Agent University. "
        "Use the filters in the sidebar to select specific tracks and time ranges. Upload your own data file "
        "to explore real metrics or explore the sample data provided."
    )

    # Sidebar controls
    with st.sidebar:
        st.header("Filters")
        uploaded_file = st.file_uploader(
            "Upload metrics JSON or CSV", type=["json", "csv"], help="Optional: upload your data file."
        )
        data = load_data(uploaded_file)
        if data.empty:
            st.stop()
        # Ensure date column is a date (not datetime) for the date picker
        data["date"] = pd.to_datetime(data["date"]).dt.date
        tracks = sorted(data["track"].unique())
        selected_tracks = st.multiselect(
            "Select track(s)", options=tracks, default=tracks, help="Filter by academic track"
        )
        # Determine date bounds for the date range picker
        min_date = data["date"].min()
        max_date = data["date"].max()
        date_range = st.date_input(
            "Select date range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filter data by start and end date",
        )
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date, end_date = min_date, max_date

    # Filter data based on sidebar selections
    filtered_df = data[
        (data["track"].isin(selected_tracks))
        & (data["date"] >= start_date)
        & (data["date"] <= end_date)
    ].copy()

    # Compute summary metrics and deltas
    summary = compute_summary_metrics(filtered_df)
    delta_lessons = compute_deltas(filtered_df, "lessons")
    delta_students = compute_deltas(filtered_df, "students")
    delta_teacher_ratio = compute_deltas(filtered_df, "students") - compute_deltas(filtered_df, "teachers")
    delta_graduation = compute_deltas(filtered_df, "graduation_rate")
    delta_satisfaction = compute_deltas(filtered_df, "satisfaction_rate")
    delta_retention = compute_deltas(filtered_df, "retention_years")

    # KPI cards
    metrics_cols = st.columns(7)
    metrics_cols[0].metric(
        label="Total Lessons",
        value=f"{summary['total_lessons']:,}",
        delta=f"{delta_lessons:+,.0f}",
    )
    metrics_cols[1].metric(
        label="Total Students",
        value=f"{summary['total_students']:,}",
        delta=f"{delta_students:+,.0f}",
    )
    metrics_cols[2].metric(
        label="Tracks",
        value=f"{len(selected_tracks)}",
        delta="",  # no delta for count of tracks
    )
    metrics_cols[3].metric(
        label="Student/Teacher Ratio",
        value=f"{summary['student_teacher_ratio']:.1f}",
        delta=f"{delta_teacher_ratio:+.1f}",
    )
    metrics_cols[4].metric(
        label="Avg Graduation Rate",
        value=f"{summary['avg_graduation_rate']*100:.1f}%",
        delta=f"{delta_graduation*100:+.1f}%",
    )
    metrics_cols[5].metric(
        label="Avg Satisfaction Score",
        value=f"{summary['avg_satisfaction_rate']*100:.1f}%",
        delta=f"{delta_satisfaction*100:+.1f}%",
    )
    metrics_cols[6].metric(
        label="Avg Teacher Retention (yrs)",
        value=f"{summary['avg_retention_years']:.1f}",
        delta=f"{delta_retention:.1f}",
    )

    st.markdown("---")

    # Lessons by track bar chart
    st.subheader("Lessons by Track")
    bar_data = (
        filtered_df.groupby("track")["lessons"]
        .sum()
        .reset_index()
        .sort_values("lessons", ascending=False)
    )
    bar_chart = (
        alt.Chart(bar_data)
        .mark_bar(color="#1f77b4")
        .encode(
            x=alt.X("lessons:Q", title="Number of Lessons"),
            y=alt.Y("track:N", title="Track", sort="-x"),
            tooltip=["track", "lessons"],
        )
        .properties(height=350, width=600)
    )
    st.altair_chart(bar_chart, use_container_width=True)

    st.markdown("---")

    # Time series chart for selectable metric
    st.subheader("Trend Over Time")
    metric_options = {
        "Lessons": "lessons",
        "Students": "students",
        "Teachers": "teachers",
        "Graduation Rate": "graduation_rate",
        "Satisfaction Score": "satisfaction_rate",
        "Teacher Retention (yrs)": "retention_years",
    }
    selected_display_name = st.selectbox(
        "Select a metric to plot over time", list(metric_options.keys()), index=0
    )
    metric_column = metric_options[selected_display_name]
    # Aggregate by month for the selected metric
    trend_data = (
        filtered_df.assign(month=pd.to_datetime(filtered_df["date"]).dt.to_period("M").dt.to_timestamp())
        .groupby("month")[metric_column]
        .sum()
        .reset_index()
    )
    y_axis_title = selected_display_name
    # Use appropriate formatting for percentages
    if metric_column in {"graduation_rate", "satisfaction_rate"}:
        trend_data[metric_column] = trend_data[metric_column] * 100
        y_axis_title += " (%)"
    line_chart = (
        alt.Chart(trend_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("month:T", title="Month"),
            y=alt.Y(f"{metric_column}:Q", title=y_axis_title),
            tooltip=["month", metric_column],
        )
        .properties(height=350, width=600)
    )
    st.altair_chart(line_chart, use_container_width=True)

    st.markdown("---")

    # Location distribution chart
    st.subheader("Student Location Distribution")
    # Aggregate location counts over the filtered data
    loc_totals = {
        "In‑State": int(filtered_df["in_state_students"].sum()),
        "Out‑of‑State": int(filtered_df["out_of_state_students"].sum()),
        "International": int(filtered_df["foreign_students"].sum()),
    }
    loc_df = pd.DataFrame(
        {
            "category": list(loc_totals.keys()),
            "count": list(loc_totals.values()),
        }
    )
    # Pie chart using altair's mark_arc
    pie_chart = (
        alt.Chart(loc_df)
        .mark_arc()
        .encode(
            theta=alt.Theta("count:Q", stack=True),
            color=alt.Color("category:N", legend=alt.Legend(title="Location")),
            tooltip=["category", "count"],
        )
        .properties(height=350, width=350)
    )
    st.altair_chart(pie_chart, use_container_width=False)

    st.markdown("---")

    # Detailed data table
    st.subheader("Detailed Data")
    st.caption("Below is the data underlying the selected filters. You can scroll horizontally to see all columns.")
    # Sort columns for readability
    display_df = filtered_df.sort_values("date").reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True)

    # Footer
    st.markdown(
        "<small>Last update: <strong>{}</strong></small>".format(
            filtered_df["date"].max().strftime("%B %d, %Y") if not filtered_df.empty else datetime.now().strftime("%B %d, %Y")
        ),
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()