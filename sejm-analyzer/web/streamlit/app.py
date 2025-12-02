"""Sejm Analyzer Dashboard."""

import sys
from pathlib import Path

# Add project root to path (for streamlit which runs this file directly)
_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_root))

import plotly.graph_objects as go  # noqa: E402
import streamlit as st  # noqa: E402
from loguru import logger  # noqa: E402

from app.container import container  # noqa: E402
from web.api import dashboard, legislation, voting  # noqa: E402

# Ensure container is initialized
container.init()

st.set_page_config(page_title="Sejm Analyzer", page_icon="🏛️", layout="wide")

COLORS = {
    "PiS": "#1E3A8A",
    "KO": "#F97316",
    "TD": "#84CC16",
    "Lewica": "#DC2626",
    "PSL": "#22C55E",
    "Konfederacja": "#1F2937",
    "niez.": "#9CA3AF",
    "PSL-TD": "#22C55E",
    "Polska2050": "#6366F1",
    "Polska2050-TD": "#6366F1",
}


def color(name: str) -> str:
    return COLORS.get(name, "#6B7280")


@st.cache_data(ttl=3600, show_spinner=False)
def get_terms_info():
    """Get terms metadata from DB."""
    terms_resp = dashboard.get_terms()
    return {t.id: {"voting": t.has_voting_data, "processes": t.has_processes} for t in terms_resp.items}


@st.cache_data(ttl=3600, show_spinner=False)
def get_term_data(term_id: int):
    """Get analytics for a term via views."""
    logger.info("Loading term data for {}", term_id)

    terms_info = get_terms_info()
    has_voting = terms_info.get(term_id, {}).get("voting", False)

    power_resp = voting.get_power_indices(term_id)
    coalitions_resp = voting.get_coalitions(term_id)
    cohesion_resp = voting.get_cohesion(term_id)
    agreement_resp = voting.get_agreement_matrix(term_id)

    return {
        "power": [p.model_dump() for p in power_resp.items],
        "coalitions": [c.model_dump() for c in coalitions_resp.items],
        "cohesion": [c.model_dump() for c in cohesion_resp.items],
        "agreement": agreement_resp.matrix,
        "has_voting_data": has_voting,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_processes_data(term_id: int):
    """Get processes data for a term via service."""
    return container.legislation_analytics.get_processes_data(term_id)


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_terms():
    """Get list of available terms from DB."""
    terms_resp = dashboard.get_terms()
    return [t.id for t in terms_resp.items] if terms_resp.items else [10, 9, 8, 7]


@st.cache_data(ttl=3600, show_spinner="Analyzing topics...")
def get_topic_data(term_id: int):
    """Get topic modeling results via views."""
    resp = legislation.get_topic_stats(term_id)
    return {
        "total_topics": resp.total_topics,
        "clusters": [c.model_dump() for c in resp.clusters],
    }


@st.cache_data(ttl=3600, show_spinner="Training model...")
def get_prediction_model(term_id: int):
    """Train and get prediction model stats."""
    container.legislation_analytics.train(term_id)
    eval_result = container.legislation_analytics.evaluate(term_id)
    model_stats = container.legislation_analytics.get_model_stats()
    return {
        "evaluation": eval_result,
        "model_stats": model_stats,
    }


def pie_chart(power: list) -> go.Figure:
    return go.Figure(
        go.Pie(
            labels=[p["party"] for p in power],
            values=[p["seats"] for p in power],
            marker=dict(colors=[color(p["party"]) for p in power]),
            hole=0.4,
            textposition="inside",
            textinfo="label+percent",
        )
    ).update_layout(showlegend=False, margin=dict(t=20, b=20, l=20, r=20), height=350)


def bar_chart(data: list, x_key: str, y_key: str, title: str = "") -> go.Figure:
    return go.Figure(
        go.Bar(
            x=[d[x_key] for d in data],
            y=[d[y_key] for d in data],
            marker_color=[color(d[x_key]) for d in data],
            text=[f"{d[y_key]:.1f}" if isinstance(d[y_key], float) else d[y_key] for d in data],
            textposition="outside",
        )
    ).update_layout(
        title=title,
        xaxis_title="",
        yaxis_title="",
        margin=dict(t=40, b=40, l=40, r=20),
        height=350,
    )


def heatmap_chart(matrix: dict, title: str = "") -> go.Figure:
    parties = list(matrix.keys())
    z = [[matrix[p1].get(p2, 0) for p2 in parties] for p1 in parties]

    return go.Figure(
        go.Heatmap(
            z=z,
            x=parties,
            y=parties,
            colorscale="RdYlGn",
            zmin=0,
            zmax=100,
            text=[[f"{v:.0f}%" for v in row] for row in z],
            texttemplate="%{text}",
            textfont={"size": 10},
        )
    ).update_layout(
        title=title,
        margin=dict(t=40, b=40, l=80, r=20),
        height=450,
    )


def voting_tab(term_id: int, data: dict):
    """Voting analytics tab."""
    if not data["has_voting_data"]:
        st.warning(f"Term {term_id} doesn't have voting data synced yet.")
        return

    power = data["power"]
    cohesion = data["cohesion"]
    coalitions = data["coalitions"]
    agreement = data["agreement"]

    if not power:
        st.info("No voting data available for this term.")
        return

    # Power indices
    st.subheader("🏛️ Power Distribution")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(pie_chart(power), width="stretch")

    with col2:
        st.plotly_chart(
            bar_chart(power, "party", "shapley", "Shapley-Shubik Power Index (%)"),
            width="stretch",
        )

    # Metrics
    st.subheader("📊 Key Metrics")
    cols = st.columns(4)
    total_seats = sum(p["seats"] for p in power)
    largest = max(power, key=lambda p: p["seats"])

    cols[0].metric("Total Seats", total_seats)
    cols[1].metric("Largest Party", f"{largest['party']} ({largest['seats']})")
    cols[2].metric("Quota", total_seats // 2 + 1)
    cols[3].metric("Parties", len(power))

    # Cohesion
    if cohesion:
        st.subheader("🤝 Party Cohesion (Rice Index)")
        st.plotly_chart(
            bar_chart(cohesion, "party", "rice_index", "Party Discipline (1.0 = unanimous)"),
            width="stretch",
        )

    # Coalitions
    if coalitions:
        st.subheader("🤝 Minimum Winning Coalitions")
        for i, c in enumerate(coalitions[:5]):
            parties_str = " + ".join(c["parties"])
            st.write(f"{i + 1}. **{parties_str}** — {c['seats']} seats (surplus: {c['surplus']})")

    # Agreement matrix
    if agreement:
        st.subheader("🔄 Party Agreement Matrix")
        st.plotly_chart(heatmap_chart(agreement, "How often parties vote together (%)"), width="stretch")


def legislation_tab(term_id: int):
    """Legislation analytics tab."""
    terms_info = get_terms_info()
    if not terms_info.get(term_id, {}).get("processes", False):
        st.warning(f"Term {term_id} doesn't have legislation data synced yet.")
        return

    data = get_processes_data(term_id)
    stats = data["stats"]
    processes = data["processes"]

    if not processes:
        st.info("No legislation data available.")
        return

    # Overview metrics
    st.subheader("📜 Legislative Overview")
    cols = st.columns(4)

    total = stats["total"]
    passed = stats["passed"]
    rejected = stats["rejected"]
    pass_rate = passed / total * 100 if total > 0 else 0

    cols[0].metric("Total Processes", total)
    cols[1].metric("Passed", passed, f"{pass_rate:.1f}%")
    cols[2].metric("Rejected", rejected)
    cols[3].metric("Pending", total - passed - rejected)

    # By type breakdown
    if stats["by_type"]:
        st.subheader("📊 By Document Type")
        type_data = [
            {"type": t["type"] or "Unknown", "count": t["total"], "passed": t["passed"]} for t in stats["by_type"][:10]
        ]

        fig = go.Figure(
            data=[
                go.Bar(name="Total", x=[t["type"] for t in type_data], y=[t["count"] for t in type_data]),
                go.Bar(name="Passed", x=[t["type"] for t in type_data], y=[t["passed"] for t in type_data]),
            ]
        )
        fig.update_layout(barmode="group", height=350)
        st.plotly_chart(fig, width="stretch")


def topics_tab(term_id: int):
    """Topic modeling tab."""
    terms_info = get_terms_info()
    if not terms_info.get(term_id, {}).get("processes", False):
        st.warning(f"Term {term_id} doesn't have legislation data.")
        return

    topics = get_topic_data(term_id)

    if not topics["clusters"]:
        st.info("No topic data available.")
        return

    st.subheader(f"🏷️ {topics['total_topics']} Topics Identified")

    for cluster in topics["clusters"]:
        with st.expander(
            f"**{cluster['name']}** — {cluster['count']} processes ({cluster['pass_rate']:.0f}% pass rate)"
        ):
            st.write("**Keywords:** " + ", ".join(cluster["keywords"]))


def prediction_tab(term_id: int):
    """ML prediction tab."""
    terms_info = get_terms_info()
    if not terms_info.get(term_id, {}).get("processes", False):
        st.warning(f"Term {term_id} doesn't have legislation data.")
        return

    model_data = get_prediction_model(term_id)
    evaluation = model_data["evaluation"]
    model_stats = model_data["model_stats"]

    if "error" in evaluation:
        st.error(evaluation["error"])
        return

    st.subheader("🤖 Pass Prediction Model")

    cols = st.columns(4)
    cols[0].metric("Accuracy", f"{evaluation['accuracy']:.1%}")
    cols[1].metric("Precision", f"{evaluation['precision']:.1%}")
    cols[2].metric("Recall", f"{evaluation['recall']:.1%}")
    cols[3].metric("F1 Score", f"{evaluation['f1_score']:.1%}")

    if model_stats.get("feature_importance"):
        st.subheader("📊 Feature Importance")
        importance = model_stats["feature_importance"][:10]
        fig = go.Figure(
            go.Bar(
                x=[f[1] for f in importance],
                y=[f[0] for f in importance],
                orientation="h",
            )
        )
        fig.update_layout(height=350, margin=dict(l=150))
        st.plotly_chart(fig, width="stretch")


def main():
    st.title("🏛️ Sejm Analyzer")
    st.markdown("*Analysis of Polish Parliament voting patterns and legislative processes*")

    # Term selector
    terms = get_available_terms()
    term_id = st.sidebar.selectbox("Select Term (Kadencja)", terms, index=0)

    # Load data
    with st.spinner("Loading data..."):
        data = get_term_data(term_id)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🗳️ Voting", "📜 Legislation", "🏷️ Topics", "🤖 Prediction"])

    with tab1:
        voting_tab(term_id, data)

    with tab2:
        legislation_tab(term_id)

    with tab3:
        topics_tab(term_id)

    with tab4:
        prediction_tab(term_id)

    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Data Source:** [api.sejm.gov.pl](https://api.sejm.gov.pl)")


if __name__ == "__main__":
    main()
