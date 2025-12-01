"""Sejm Analyzer Dashboard."""

import plotly.graph_objects as go
import streamlit as st
from loguru import logger

from src.analytics import Analytics
from src.ml_analytics import PassPrediction, TopicModeling
from src.repository import Repository

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

TERMS_WITH_VOTING_DATA = {7, 8, 9, 10}
TERMS_WITH_PROCESSES = {10}  # Only term 10 has processes synced


def color(name: str) -> str:
    return COLORS.get(name, "#6B7280")


@st.cache_resource
def get_analytics():
    """Single Analytics instance for the app lifetime."""
    logger.info("Initializing Analytics")
    return Analytics(Repository())


@st.cache_resource
def get_repository():
    """Single Repository instance for the app lifetime."""
    logger.info("Initializing Repository")
    return Repository()


@st.cache_data(ttl=3600, show_spinner=False)
def get_term_data(term_id: int):
    """Get analytics for a term (from DB cache or compute)."""
    analytics = get_analytics()

    return {
        "power": analytics.power_indices(term_id),
        "coalitions": analytics.coalitions(term_id),
        "cohesion": analytics.cohesion(term_id),
        "agreement": analytics.agreement_matrix(term_id),
        "has_voting_data": term_id in TERMS_WITH_VOTING_DATA,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_processes_data(term_id: int):
    """Get processes data for a term."""
    repo = get_repository()
    processes = repo.get_processes(term_id)
    process_stats = repo.get_process_stats(term_id)
    voting_links = repo.get_process_voting_links(term_id)
    return {
        "processes": processes,
        "stats": process_stats,
        "voting_links": voting_links,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_terms():
    """Get list of available terms from DB."""
    repo = get_repository()
    terms = repo.get_terms()
    return terms if terms else [10, 9, 8, 7]


@st.cache_data(ttl=3600, show_spinner="Analyzing topics...")
def get_topic_data(term_id: int):
    """Get topic modeling results."""
    repo = get_repository()
    tm = TopicModeling(repo)
    return tm.get_topic_stats(term_id)


@st.cache_data(ttl=3600, show_spinner="Training model...")
def get_prediction_model(term_id: int):
    """Train and get prediction model stats."""
    repo = get_repository()
    pred = PassPrediction(repo)
    pred.train(term_id)
    eval_result = pred.evaluate(term_id)
    model_stats = pred.get_model_stats()
    return {
        "evaluation": eval_result,
        "model_stats": model_stats,
    }


def pie_chart(power: list) -> go.Figure:
    return go.Figure(
        go.Pie(
            labels=[p.party for p in power],
            values=[p.seats for p in power],
            marker=dict(colors=[color(p.party) for p in power]),
            hole=0.3,
        )
    ).update_layout(title="Parliament Composition", height=400, margin=dict(t=50, b=20))


def power_bars(power: list) -> go.Figure:
    parties = [p.party for p in power]
    fig = go.Figure(
        [
            go.Bar(name="Seats %", x=parties, y=[p.seats_pct for p in power], marker_color="#94A3B8"),
            go.Bar(name="Shapley", x=parties, y=[p.shapley for p in power], marker_color="#3B82F6"),
            go.Bar(name="Banzhaf", x=parties, y=[p.banzhaf for p in power], marker_color="#10B981"),
        ]
    )
    return fig.update_layout(barmode="group", title="Voting Power vs Seats", height=400)


def cohesion_bars(data: list) -> go.Figure:
    data = sorted(data, key=lambda x: x.rice_index)
    colors = ["#22C55E" if d.rice_index >= 0.9 else "#F59E0B" if d.rice_index >= 0.7 else "#EF4444" for d in data]

    return go.Figure(
        go.Bar(
            y=[d.party for d in data],
            x=[d.rice_index for d in data],
            orientation="h",
            marker_color=colors,
            text=[f"{d.rice_index:.2f}" for d in data],
            textposition="outside",
        )
    ).update_layout(title="Party Cohesion (Rice Index)", height=max(300, len(data) * 25), xaxis=dict(range=[0, 1.1]))


def agreement_heatmap(matrix: dict) -> go.Figure:
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
        )
    ).update_layout(title="Party Agreement Matrix", height=max(400, len(parties) * 40))


def legislation_pie(stats: dict) -> go.Figure:
    """Pie chart for legislation outcomes."""
    labels = ["Passed", "Rejected"]
    values = [stats.get("passed", 0), stats.get("rejected", 0)]
    colors = ["#22C55E", "#EF4444"]

    return go.Figure(go.Pie(labels=labels, values=values, marker=dict(colors=colors), hole=0.4)).update_layout(
        title="Legislative Outcomes", height=350
    )


def legislation_by_type(stats: dict) -> go.Figure:
    """Bar chart for legislation by type."""
    by_type = stats.get("by_type", [])
    if not by_type:
        return None

    types = [t["type"][:30] for t in by_type]
    total = [t["total"] for t in by_type]
    passed = [t["passed"] for t in by_type]

    fig = go.Figure(
        [
            go.Bar(name="Total", x=types, y=total, marker_color="#94A3B8"),
            go.Bar(name="Passed", x=types, y=passed, marker_color="#22C55E"),
        ]
    )
    return fig.update_layout(barmode="group", title="Legislation by Type", height=400)


# ========== MAIN APP ==========

st.title("🏛️ Sejm Analyzer")
st.caption("Parliamentary voting analysis • Data cached in database")

available_terms = get_available_terms()
term_id = st.sidebar.selectbox("📅 Select Term", available_terms, index=0)

if term_id not in TERMS_WITH_VOTING_DATA:
    st.sidebar.warning(f"⚠️ Term {term_id} has limited data (MPs only, no voting records in API)")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Coverage**")
for t in available_terms[:6]:
    v_icon = "✅" if t in TERMS_WITH_VOTING_DATA else "⚠️"
    p_icon = "📜" if t in TERMS_WITH_PROCESSES else ""
    st.sidebar.caption(f"{v_icon} Term {t} {p_icon}")

data = get_term_data(term_id)
power = data["power"]
has_voting = data["has_voting_data"]
has_processes = term_id in TERMS_WITH_PROCESSES

if not power:
    st.error(f"❌ No data for term {term_id}. Run: `python sync_data.py {term_id}`")
    st.stop()

# Create tabs - add Legislation, Topics, and Prediction tabs
tabs = ["🏛️ Parliament", "⚡ Power", "🤝 Cohesion", "📊 Agreement"]
if has_processes:
    tabs.extend(["📜 Legislation", "🏷️ Topics", "🔮 Prediction"])

tab_objects = st.tabs(tabs)

with tab_objects[0]:
    st.header("Parliament Composition")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(pie_chart(power), use_container_width=True)

    with col2:
        st.subheader("Seat Distribution")
        largest = max(power, key=lambda x: x.seats)
        total = sum(p.seats for p in power)
        quota = total // 2 + 1

        st.metric("Total Seats", total)
        st.metric("Majority Threshold", quota)
        st.metric("Largest Party", f"{largest.party} ({largest.seats})")

        if largest.seats >= quota:
            st.success(f"🏆 **{largest.party}** has absolute majority")
            opposition = total - largest.seats
            st.caption(f"Opposition: {opposition} seats (need {quota})")

with tab_objects[1]:
    st.header("Voting Power Analysis")
    st.markdown(
        """
    **Shapley-Shubik Index**: Probability of being the pivotal voter in a random coalition.
    **Banzhaf Index**: Proportion of winning coalitions where the party is critical.

    *Small parties can have disproportionate power if they're often needed for majority.*
    """
    )

    st.plotly_chart(power_bars(power), use_container_width=True)

    st.subheader("Possible Coalitions")
    coalitions = data["coalitions"]

    largest = max(power, key=lambda x: x.seats)
    total = sum(p.seats for p in power)
    quota = total // 2 + 1

    if largest.seats >= quota:
        st.info(f"**{largest.party}** has absolute majority — no coalition needed")
    elif coalitions:
        for i, c in enumerate(coalitions[:8], 1):
            parties_str = " + ".join(sorted(c["parties"]))
            st.write(f"**{i}.** {parties_str} — {c['seats']} seats (+{c['surplus']} surplus)")
    else:
        st.caption("No minimal winning coalitions found")

with tab_objects[2]:
    st.header("Party Cohesion")

    if not has_voting:
        st.warning(f"⚠️ Term {term_id} has no voting data in the API. Cohesion analysis unavailable.")
    else:
        st.markdown(
            """
        **Rice Index** measures how unified a party votes:
        - **1.0** = All members vote the same way (unanimous)
        - **0.5** = Split 50/50
        - **0.0** = Maximum disagreement
        """
        )

        coh = data["cohesion"]
        if coh:
            st.plotly_chart(cohesion_bars(coh), use_container_width=True)
        else:
            st.caption("No cohesion data available")

with tab_objects[3]:
    st.header("Party Agreement Matrix")

    if not has_voting:
        st.warning(f"⚠️ Term {term_id} has no voting data in the API. Agreement analysis unavailable.")
    else:
        st.markdown("*How often do parties vote the same way? 100% = always agree, 0% = always oppose*")

        matrix = data["agreement"]
        if matrix and len(matrix) > 1:
            st.plotly_chart(agreement_heatmap(matrix), use_container_width=True)
        else:
            st.caption("Not enough data to compute agreement matrix")

# Legislation tab (only for terms with processes)
if has_processes and len(tab_objects) > 4:
    with tab_objects[4]:
        st.header("📜 Legislative Processes")

        proc_data = get_processes_data(term_id)
        stats = proc_data["stats"]
        processes = proc_data["processes"]
        voting_links = proc_data["voting_links"]

        # Stats row
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Processes", stats.get("total", 0))
        col2.metric("✅ Passed", stats.get("passed", 0))
        col3.metric("❌ Rejected", stats.get("rejected", 0))
        col4.metric("🔗 Voting Links", len(voting_links))

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(legislation_pie(stats), use_container_width=True)

        with col2:
            type_chart = legislation_by_type(stats)
            if type_chart:
                st.plotly_chart(type_chart, use_container_width=True)

        # Recent legislation
        st.subheader("Recent Legislation")

        filter_type = st.selectbox(
            "Filter by type",
            ["All", "projekt ustawy", "projekt uchwały", "wniosek", "informacja rządowa"],
        )

        filter_status = st.radio("Status", ["All", "Passed", "Rejected"], horizontal=True)

        filtered = processes
        if filter_type != "All":
            filtered = [p for p in filtered if p.get("document_type") == filter_type]
        if filter_status == "Passed":
            filtered = [p for p in filtered if p.get("passed") is True]
        elif filter_status == "Rejected":
            filtered = [p for p in filtered if p.get("passed") is False]

        st.caption(f"Showing {len(filtered)} of {len(processes)} processes")

        for p in filtered[:20]:
            status = "✅" if p.get("passed") else "❌"
            title = p.get("title", "")[:80]
            doc_type = p.get("document_type", "")
            st.write(f"{status} **#{p.get('number')}** {title}... *({doc_type})*")

# Topics tab
if has_processes and len(tab_objects) > 5:
    with tab_objects[5]:
        st.header("🏷️ Topic Analysis")
        st.markdown(
            """
        Automatic topic detection from legislative titles using keyword patterns.
        Topics are extracted using regex matching on Polish legal terminology.
        """
        )

        topic_data = get_topic_data(term_id)
        clusters = topic_data["clusters"]

        st.metric("Topics Detected", topic_data["total_topics"])

        st.markdown("---")

        # Topic pass rates chart
        if clusters:
            sorted_clusters = sorted(clusters, key=lambda x: -x["pass_rate"])

            fig = go.Figure(
                go.Bar(
                    y=[c["name"] for c in sorted_clusters],
                    x=[c["pass_rate"] for c in sorted_clusters],
                    orientation="h",
                    marker_color=[
                        "#22C55E" if c["pass_rate"] >= 70 else "#F59E0B" if c["pass_rate"] >= 50 else "#EF4444"
                        for c in sorted_clusters
                    ],
                    text=[f"{c['pass_rate']:.0f}% ({c['count']})" for c in sorted_clusters],
                    textposition="outside",
                )
            )
            fig.update_layout(
                title="Pass Rate by Topic",
                height=max(400, len(clusters) * 30),
                xaxis={"range": [0, 105], "title": "Pass Rate %"},
                yaxis={"title": ""},
            )
            st.plotly_chart(fig, use_container_width=True)

        # Topic details
        st.subheader("Topic Details")
        for c in sorted(clusters, key=lambda x: -x["count"]):
            with st.expander(f"**{c['name']}** — {c['count']} processes ({c['pass_rate']:.0f}% pass)"):
                st.write(f"**Keywords:** {', '.join(c['keywords'])}")

# Prediction tab
if has_processes and len(tab_objects) > 6:
    with tab_objects[6]:
        st.header("🔮 Prediction Model")
        st.markdown(
            """
        **Logistic Regression** model trained on historical legislative outcomes.

        Features used:
        - Document type (one-hot encoded)
        - Topic category
        - Historical pass rates for similar processes
        """
        )

        pred_data = get_prediction_model(term_id)
        evaluation = pred_data["evaluation"]
        model_stats = pred_data["model_stats"]

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Accuracy", f"{evaluation['accuracy']:.1%}")
        col2.metric("Precision", f"{evaluation['precision']:.1%}")
        col3.metric("Recall", f"{evaluation['recall']:.1%}")
        col4.metric("F1 Score", f"{evaluation['f1_score']:.1%}")

        st.markdown("---")

        # Confusion matrix
        st.subheader("Confusion Matrix")
        cm = evaluation["confusion_matrix"]
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"✅ True Positive: {cm['true_positive']}")
            st.error(f"❌ False Negative: {cm['false_negative']}")
        with col2:
            st.warning(f"⚠️ False Positive: {cm['false_positive']}")
            st.info(f"✅ True Negative: {cm['true_negative']}")

        st.caption(f"Total samples: {evaluation['total_samples']}")

        st.markdown("---")

        # Feature importance
        st.subheader("Feature Importance")
        importance = model_stats.get("feature_importance", [])[:12]

        if importance:
            fig = go.Figure(
                go.Bar(
                    y=[f[0] for f in reversed(importance)],
                    x=[f[1] for f in reversed(importance)],
                    orientation="h",
                    marker_color="#3B82F6",
                )
            )
            fig.update_layout(
                title="Top Features (by absolute weight)",
                height=max(300, len(importance) * 30),
                xaxis={"title": "Importance"},
            )
            st.plotly_chart(fig, use_container_width=True)

        # Base rates
        st.subheader("Historical Pass Rates")
        base_rates = model_stats.get("base_rates", {})
        doc_rates = {k: v for k, v in base_rates.items() if not k.startswith("topic_")}
        topic_rates = {k.replace("topic_", ""): v for k, v in base_rates.items() if k.startswith("topic_")}

        col1, col2 = st.columns(2)
        with col1:
            st.write("**By Document Type:**")
            for dt, rate in sorted(doc_rates.items(), key=lambda x: -x[1]):
                bar_width = int(rate * 100)
                st.write(f"{dt}: {rate:.0%}")
        with col2:
            st.write("**By Topic:**")
            for topic, rate in sorted(topic_rates.items(), key=lambda x: -x[1])[:10]:
                st.write(f"{topic}: {rate:.0%}")
