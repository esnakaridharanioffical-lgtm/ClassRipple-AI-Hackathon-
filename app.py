import streamlit as st
import pandas as pd
import plotly.express as px

from src.data_loader import load_dataset, find_column
from src.impact_engine import build_service_graph, trace_service_impacts, incident_service_ids
from src.validation import data_quality_report, validate_initial_services
from src.activity_impact import activity_impacts


def make_ripple_figure(selected_roots, impacts):
    """Create an explainable left-to-right graph from traced dataset edges."""
    import plotly.graph_objects as go

    roots = list(dict.fromkeys(str(x) for x in selected_roots))
    levels = {root: 0 for root in roots}
    parents = {}
    if impacts is not None and not impacts.empty:
        for _, row in impacts.iterrows():
            node = str(row["service_id"])
            parent = str(row["parent_service"])
            levels[node] = int(row["impact_level"])
            parents[node] = parent

    # Stable, readable layout: columns represent ripple depth.
    by_level = {}
    for node, level in levels.items():
        by_level.setdefault(level, []).append(node)
    positions = {}
    for level, nodes in sorted(by_level.items()):
        nodes = sorted(nodes)
        for index, node in enumerate(nodes):
            positions[node] = (level, -index)

    edge_x, edge_y = [], []
    for child, parent in parents.items():
        if parent in positions and child in positions:
            x0, y0 = positions[parent]
            x1, y1 = positions[child]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    node_x, node_y, node_text, node_colors = [], [], [], []
    for node, (x, y) in positions.items():
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)
        node_colors.append("#dc2626" if levels[node] == 0 else ("#f59e0b" if levels[node] == 1 else "#0ea5e9"))

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y, mode="lines",
        line=dict(width=1.8, color="#94a3b8"),
        hoverinfo="skip", name="Dependency links"
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=node_text, textposition="middle right",
        marker=dict(size=25, color=node_colors, line=dict(width=1, color="white")),
        customdata=[[levels[n], "Initial failure" if levels[n] == 0 else f"Downstream level {levels[n]}"] for n in positions],
        hovertemplate="Service: %{text}<br>Level: %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
        name="Services"
    ))
    fig.update_layout(
        title="Service ripple map — each arrow follows service_links.csv",
        xaxis=dict(title="Ripple depth (edges from selected failure)", tickmode="linear", dtick=1, range=[-0.4, max(levels.values(), default=0) + 0.8], zeroline=False),
        yaxis=dict(visible=False),
        height=max(360, min(760, 90 + 55 * max((len(v) for v in by_level.values()), default=1))),
        margin=dict(l=20, r=100, t=65, b=45),
        showlegend=False,
    )
    return fig


st.set_page_config(page_title="ClassRipple AI", page_icon="🌊", layout="wide")
st.title("🌊 ClassRipple AI")
st.caption("THE RIPPLE: Campus in Crisis — explainable incident impact analysis")

@st.cache_data
def get_data():
    # Return data loaded from the project-local supplied dataset.
    return load_dataset()

loaded = get_data()
tables, incident = loaded["tables"], loaded["incident"]

with st.sidebar:
    st.header("Incident Control")
    st.write("**Scenario:** Dataset default incident")
    st.write("**Simulation window:** 09:00–16:30 (from supplied scenario)")
    st.info("This MVP analyzes relationships in the supplied data. It does not yet certify a recovery schedule.")

if loaded["errors"]:
    st.error("Dataset setup needs attention")
    for e in loaded["errors"]:
        st.write(f"• {e}")
else:
    st.success(f"Loaded {len(tables)} CSV tables and incident.json")

for warning in loaded["warnings"]:
    st.warning(warning)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Overview", "Ripple Explorer", "Activity Impacts", "Data Audit", "How It Works"
])

with tab1:
    st.subheader("Campus situation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Data tables loaded", len(tables))
    c2.metric("Activities", len(tables.get("activities", [])))
    c3.metric("Rooms", len(tables.get("rooms", [])))
    c4.metric("Services", len(tables.get("services", [])))
    st.markdown("### Incident definition")
    st.json(incident, expanded=False)
    st.markdown("### Dataset tables")
    table_summary = data_quality_report(tables)
    st.dataframe(table_summary, use_container_width=True, hide_index=True)

with tab2:
    st.subheader("Ripple Explorer")
    graph, mapping = build_service_graph(tables)
    st.caption(f"Dependency edge mapping: {mapping}. Confirm the direction against the dataset glossary before interpreting results.")
    incident_ids = incident_service_ids(incident)
    known_services = sorted(graph.keys())
    service_df = tables.get("services", pd.DataFrame())
    service_col = find_column(service_df, ["service_id", "id", "service"]) if not service_df.empty else None
    if service_col:
        known_services = sorted(set(known_services) | set(service_df[service_col].dropna().astype(str)))
    defaults = [s for s in incident_ids if s in known_services]
    chosen = st.multiselect(
        "Select initial failed services",
        options=known_services,
        default=defaults[:8],
        help="Choose the initial service failure(s). The graph traces downstream links present in service_links.csv."
    )
    depth = st.slider("Maximum dependency depth", min_value=1, max_value=8, value=3)
    if st.button("Trace ripple effects", type="primary"):
        impacts = trace_service_impacts(chosen, graph, max_depth=depth)
        st.session_state["impacts"] = impacts
        st.session_state["selected_roots"] = chosen
    impacts = st.session_state.get("impacts")
    if impacts is not None:
        if impacts.empty:
            st.info("No downstream links were found for the selected services. Check the service-link column mapping and direction.")
        else:
            st.metric("Downstream service impacts", len(impacts))
            st.markdown("#### Visual ripple chain")
            st.plotly_chart(
                make_ripple_figure(st.session_state.get("selected_roots", chosen), impacts),
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.caption("Red = selected initial failure; orange = first downstream level; blue = later levels. Arrows show recorded service dependencies, not proof that every downstream service is currently unavailable.")
            st.dataframe(impacts, use_container_width=True, hide_index=True)
            fig = px.bar(
                impacts.groupby("impact_level", as_index=False).size(),
                x="impact_level", y="size",
                labels={"impact_level": "Dependency level", "size": "Services"},
                title="Potential impacts by dependency level"
            )
            st.plotly_chart(fig, use_container_width=True)
            st.warning("These are dependency-derived candidates. Confirm link direction, outage timing, and service requirements before calling an activity impacted.")
    if chosen:
        st.markdown("### Initial service validation")
        st.dataframe(pd.DataFrame(validate_initial_services(chosen, tables)), use_container_width=True, hide_index=True)


with tab3:
    st.subheader("Activity Impact Analysis")
    st.write("Connect the selected failed services to activities scheduled in rooms that require those services.")
    graph, _mapping = build_service_graph(tables)
    service_df = tables.get("services", pd.DataFrame())
    service_col = find_column(service_df, ["service_id", "id", "service"]) if not service_df.empty else None
    all_services = sorted(set(service_df[service_col].dropna().astype(str))) if service_col else sorted(graph.keys())
    default_services = [x for x in ["PWR-CAB", "NET-CAB", "PWR-ABA", "NET-ABA", "PWR-ABB", "PWR-ABC"] if x in all_services]
    failed = st.multiselect(
        "Affected/failed services",
        options=all_services,
        default=default_services,
        help="Select services to evaluate against the actual service states in services.csv."
    )
    incident_time = st.text_input("Incident start time (HH:MM)", value="10:00")
    if st.button("Analyze affected activities", type="primary"):
        impacts_df, notes = activity_impacts(tables, failed, incident_time=incident_time)
        st.session_state["activity_impacts_df"] = impacts_df
        st.session_state["activity_impact_notes"] = notes
    impacts_df = st.session_state.get("activity_impacts_df")
    if impacts_df is not None:
        if impacts_df.empty:
            st.info("No matching activity impacts were found for the selected services and incident time. This may mean the selected services are not required by the original room/activity, or the service states need inspection.")
        else:
            st.metric("Potentially affected activities", len(impacts_df))
            st.dataframe(impacts_df, use_container_width=True, hide_index=True)
            if "priority" in impacts_df.columns:
                priority_counts = impacts_df.groupby("priority", as_index=False).size()
                st.plotly_chart(px.bar(priority_counts, x="priority", y="size", title="Potentially affected activities by priority"), use_container_width=True)
        for note in st.session_state.get("activity_impact_notes", []):
            st.caption("• " + note)

with tab4:
    st.subheader("Data Audit")
    audit = data_quality_report(tables)
    st.dataframe(audit, use_container_width=True, hide_index=True)
    st.markdown("### Files detected")
    st.write(", ".join(sorted(tables.keys())))
    st.markdown("### Validation notes")
    st.write("- Missing values and duplicate rows are reported, not silently repaired.")
    st.write("- Service-link direction is displayed in Ripple Explorer and should be confirmed against the data dictionary.")
    st.write("- The current MVP does not yet solve the complete timetable and repair-allocation optimization problem.")

with tab5:
    st.subheader("Execution pipeline")
    st.markdown("""
    1. **Load** the supplied CSV tables and incident JSON.
    2. **Audit** row counts, missing cells, duplicate rows, and required files.
    3. **Select** the initial service failure(s).
    4. **Traverse** the service dependency graph to identify downstream service candidates.
    5. **Explain** each link with its source relationship.
    6. **Validate next:** the full product should connect service states to activities, room availability, staff, repair prerequisites, and hard constraints before recommending a recovery plan.
    """)
    st.info("Next implementation milestone: connect the service ripple map to time-aware activity impacts, then add validated mitigation and recovery strategy comparison.")
