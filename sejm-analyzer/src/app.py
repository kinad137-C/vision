"""Sejm Analyzer Dashboard."""
import streamlit as st
import plotly.graph_objects as go
from loguru import logger

from src.analytics import Analytics
from src.db import Repository

st.set_page_config(page_title="Sejm Analyzer", page_icon="🏛️", layout="wide")

COLORS = {
    "PiS": "#1E3A8A", "KO": "#F97316", "TD": "#84CC16", "Lewica": "#DC2626",
    "PSL": "#22C55E", "Konfederacja": "#1F2937", "niez.": "#9CA3AF",
    "PSL-TD": "#22C55E", "Polska2050": "#6366F1", "Polska2050-TD": "#6366F1",
}

TERMS_WITH_VOTING_DATA = {7, 8, 9, 10}


def color(name: str) -> str:
    return COLORS.get(name, "#6B7280")


@st.cache_resource
def get_analytics():
    """Single Analytics instance for the app lifetime."""
    logger.info("Initializing Analytics (one-time)")
    return Analytics()


@st.cache_resource
def get_repository():
    """Single Repository instance for the app lifetime."""
    logger.info("Initializing Repository (one-time)")
    return Repository()


@st.cache_data(ttl=3600, show_spinner=False)
def precompute_term(term_id: int):
    """Precompute all analytics for a term (cached 1 hour)."""
    logger.info(f"Precomputing analytics for term {term_id}...")
    analytics = get_analytics()
    
    result = {
        "power": analytics.power_indices(term_id),
        "coalitions": analytics.coalitions(term_id),
        "cohesion": analytics.cohesion(term_id),
        "agreement": analytics.agreement_matrix(term_id),
        "has_voting_data": term_id in TERMS_WITH_VOTING_DATA,
    }
    
    logger.info(f"Term {term_id} precomputed: {len(result['power'])} parties")
    return result


@st.cache_data(ttl=3600, show_spinner=False)
def get_available_terms():
    """Get list of available terms from DB."""
    repo = get_repository()
    terms = repo.get_terms()
    return terms if terms else [10, 9, 8, 7]


def warmup_cache():
    """Precompute data for main terms on startup."""
    terms = get_available_terms()
    for term in terms[:4]:
        if term in TERMS_WITH_VOTING_DATA:
            precompute_term(term)


if "warmed_up" not in st.session_state:
    with st.spinner("🔄 Loading analytics data..."):
        warmup_cache()
    st.session_state.warmed_up = True


def pie_chart(power: list) -> go.Figure:
    return go.Figure(go.Pie(
        labels=[p.party for p in power],
        values=[p.seats for p in power],
        marker=dict(colors=[color(p.party) for p in power]),
        hole=0.3,
    )).update_layout(title="Parliament Composition", height=400, margin=dict(t=50, b=20))


def power_bars(power: list) -> go.Figure:
    parties = [p.party for p in power]
    fig = go.Figure([
        go.Bar(name="Seats %", x=parties, y=[p.seats_pct for p in power], marker_color="#94A3B8"),
        go.Bar(name="Shapley", x=parties, y=[p.shapley for p in power], marker_color="#3B82F6"),
        go.Bar(name="Banzhaf", x=parties, y=[p.banzhaf for p in power], marker_color="#10B981"),
    ])
    return fig.update_layout(barmode="group", title="Voting Power vs Seats", height=400)


def cohesion_bars(data: list) -> go.Figure:
    data = sorted(data, key=lambda x: x.rice_index)
    colors = ["#22C55E" if d.rice_index >= 0.9 else "#F59E0B" if d.rice_index >= 0.7 else "#EF4444" for d in data]
    
    return go.Figure(go.Bar(
        y=[d.party for d in data], x=[d.rice_index for d in data],
        orientation="h", marker_color=colors,
        text=[f"{d.rice_index:.2f}" for d in data], textposition="outside",
    )).update_layout(title="Party Cohesion (Rice Index)", height=max(300, len(data) * 25), xaxis=dict(range=[0, 1.1]))


def agreement_heatmap(matrix: dict) -> go.Figure:
    parties = list(matrix.keys())
    z = [[matrix[p1].get(p2, 0) for p2 in parties] for p1 in parties]
    
    return go.Figure(go.Heatmap(
        z=z, x=parties, y=parties, colorscale="RdYlGn", zmin=0, zmax=100,
        text=[[f"{v:.0f}%" for v in row] for row in z], texttemplate="%{text}",
    )).update_layout(title="Party Agreement Matrix", height=max(400, len(parties) * 40))


st.title("🏛️ Sejm Analyzer")
st.caption("Static analytical dashboard • Data precomputed for fast loading")

available_terms = get_available_terms()
term_id = st.sidebar.selectbox("📅 Select Term", available_terms, index=0)

if term_id not in TERMS_WITH_VOTING_DATA:
    st.sidebar.warning(f"⚠️ Term {term_id} has limited data (MPs only, no voting records in API)")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.session_state.warmed_up = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("**Data Coverage**")
for t in available_terms[:6]:
    icon = "✅" if t in TERMS_WITH_VOTING_DATA else "⚠️"
    st.sidebar.caption(f"{icon} Term {t}")

data = precompute_term(term_id)
power = data["power"]
has_voting = data["has_voting_data"]

if not power:
    st.error(f"❌ No data for term {term_id}. Run: `python sync_data.py {term_id}`")
    st.stop()

tab1, tab2, tab3, tab4 = st.tabs(["🏛️ Parliament", "⚡ Power", "🤝 Cohesion", "📊 Agreement"])

with tab1:
    st.header("Parliament Composition")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.plotly_chart(pie_chart(power), width="stretch")
    
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

with tab2:
    st.header("Voting Power Analysis")
    st.markdown("""
    **Shapley-Shubik Index**: Probability of being the pivotal voter in a random coalition.  
    **Banzhaf Index**: Proportion of winning coalitions where the party is critical.
    
    *Small parties can have disproportionate power if they're often needed for majority.*
    """)
    
    st.plotly_chart(power_bars(power), width="stretch")
    
    st.subheader("Possible Coalitions")
    coalitions = data["coalitions"]
    
    largest = max(power, key=lambda x: x.seats)
    total = sum(p.seats for p in power)
    quota = total // 2 + 1
    
    if largest.seats >= quota:
        st.info(f"**{largest.party}** has absolute majority — no coalition needed")
    elif coalitions:
        for i, c in enumerate(coalitions[:8], 1):
            parties_str = ' + '.join(sorted(c['parties']))
            st.write(f"**{i}.** {parties_str} — {c['seats']} seats (+{c['surplus']} surplus)")
    else:
        st.caption("No minimal winning coalitions found")

with tab3:
    st.header("Party Cohesion")
    
    if not has_voting:
        st.warning(f"⚠️ Term {term_id} has no voting data in the API. Cohesion analysis unavailable.")
    else:
        st.markdown("""
        **Rice Index** measures how unified a party votes:
        - **1.0** = All members vote the same way (unanimous)
        - **0.5** = Split 50/50
        - **0.0** = Maximum disagreement
        """)
        
        coh = data["cohesion"]
        if coh:
            st.plotly_chart(cohesion_bars(coh), width="stretch")
        else:
            st.caption("No cohesion data available")

with tab4:
    st.header("Party Agreement Matrix")
    
    if not has_voting:
        st.warning(f"⚠️ Term {term_id} has no voting data in the API. Agreement analysis unavailable.")
    else:
        st.markdown("*How often do parties vote the same way? 100% = always agree, 0% = always oppose*")
        
        matrix = data["agreement"]
        if matrix and len(matrix) > 1:
            st.plotly_chart(agreement_heatmap(matrix), width="stretch")
        else:
            st.caption("Not enough data to compute agreement matrix")
