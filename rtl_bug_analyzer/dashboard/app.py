"""
Streamlit Dashboard - Bug Triage Visualization
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from pathlib import Path


st.set_page_config(page_title="RTL Bug Triage Dashboard", layout="wide")


@st.cache_data
def load_data():
    """Load triage results"""
    try:
        bugs_df = pd.read_csv('../data/bug_triage_list.csv')
        with open('../data/triage_plan.json', 'r') as f:
            triage_plan = json.load(f)
        return bugs_df, triage_plan
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None


def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🐛 RTL Bug Triage Dashboard")
        st.markdown("**AI-Powered Bug Analysis & Prioritization**")
    
    st.markdown("---")
    
    # Load data
    bugs_df, triage_plan = load_data()
    
    if bugs_df is None:
        st.error("Unable to load triage data. Please run the analysis first.")
        return
    
    # Navigation
    page = st.sidebar.radio(
        "📄 Navigation",
        ["📊 Overview", "📋 Triage List", "📈 Analysis", "🎯 Fix Plan"]
    )
    
    if page == "📊 Overview":
        show_overview(bugs_df, triage_plan)
    elif page == "📋 Triage List":
        show_triage_list(bugs_df)
    elif page == "📈 Analysis":
        show_analysis(bugs_df)
    elif page == "🎯 Fix Plan":
        show_fix_plan(triage_plan)


def show_overview(bugs_df: pd.DataFrame, triage_plan: dict):
    """Overview dashboard"""
    st.header("📊 Triage Overview")
    
    # KPI cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Bugs", triage_plan['total_bugs'])
    
    with col2:
        st.metric("Critical Priority", triage_plan['critical_count'],
                 delta=f"EST: {triage_plan['estimated_fix_time']['total_hours']}h")
    
    with col3:
        st.metric("High Priority", triage_plan['high_count'])
    
    with col4:
        st.metric("Avg Priority Score", 
                 f"{bugs_df['priority_score'].mean():.2f}")
    
    st.markdown("---")
    
    # Priority distribution pie chart
    col1, col2 = st.columns(2)
    
    with col1:
        priority_counts = bugs_df['priority_level'].value_counts()
        fig = px.pie(
            values=priority_counts.values,
            names=priority_counts.index,
            title="Bug Distribution by Priority",
            color_discrete_map={
                'CRITICAL': '#FF4444',
                'HIGH': '#FF9500',
                'MEDIUM': '#FFD700',
                'LOW': '#00C851'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        module_counts = bugs_df['module'].value_counts().head(10)
        fig = px.bar(
            x=module_counts.values,
            y=module_counts.index,
            orientation='h',
            title="Most Affected Modules",
            labels={'x': 'Bug Count', 'y': 'Module'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Time estimate
    st.subheader("⏱️ Estimated Fix Timeline")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Hours", triage_plan['estimated_fix_time']['total_hours'])
    
    with col2:
        st.metric("Business Days", triage_plan['estimated_fix_time']['total_days'])
    
    with col3:
        st.metric("Calendar Weeks", triage_plan['estimated_fix_time']['total_weeks'])


def show_triage_list(bugs_df: pd.DataFrame):
    """Detailed triage list"""
    st.header("📋 Prioritized Bug Triage List")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        priority_filter = st.multiselect(
            "Priority Level",
            options=bugs_df['priority_level'].unique(),
            default=bugs_df['priority_level'].unique()
        )
    
    with col2:
        module_filter = st.multiselect(
            "Module",
            options=bugs_df['module'].unique(),
            default=bugs_df['module'].unique()
        )
    
    with col3:
        complexity_filter = st.multiselect(
            "Complexity",
            options=bugs_df['complexity'].unique(),
            default=bugs_df['complexity'].unique()
        )
    
    # Apply filters
    filtered_df = bugs_df[
        (bugs_df['priority_level'].isin(priority_filter)) &
        (bugs_df['module'].isin(module_filter)) &
        (bugs_df['complexity'].isin(complexity_filter))
    ]
    
    st.markdown(f"**Showing {len(filtered_df)} bugs**")
    
    # Create display dataframe
    display_df = filtered_df.copy()
    display_df['Priority'] = display_df['priority_level'].apply(
        lambda x: {'CRITICAL': '🔴 CRITICAL', 'HIGH': '🟠 HIGH',
                  'MEDIUM': '🟡 MEDIUM', 'LOW': '🟢 LOW'}.get(x, x)
    )
    
    st.dataframe(
        display_df[[
            'signature_id', 'Priority', 'failure_type', 'module',
            'occurrence_count', 'priority_score', 'complexity', 'severity'
        ]].rename(columns={
            'signature_id': 'ID',
            'failure_type': 'Failure Type',
            'module': 'Module',
            'occurrence_count': 'Count',
            'priority_score': 'Score',
            'complexity': 'Complexity',
            'severity': 'Severity'
        }),
        use_container_width=True,
        hide_index=True
    )


def show_analysis(bugs_df: pd.DataFrame):
    """Detailed analysis"""
    st.header("📈 Bug Analysis")
    
    col1, col2 = st.columns(2)
    
    # Failure type distribution
    with col1:
        failure_counts = bugs_df['failure_type'].value_counts().head(10)
        fig = px.barh(
            x=failure_counts.values,
            y=failure_counts.index,
            title="Bug Types Distribution",
            labels={'x': 'Count', 'y': 'Failure Type'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Priority score distribution
    with col2:
        fig = px.histogram(
            bugs_df,
            x='priority_score',
            nbins=20,
            title='Priority Score Distribution',
            labels={'priority_score': 'Priority Score', 'count': 'Bug Count'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Complexity vs Priority scatter
    st.subheader("Complexity vs Priority Score")
    fig = px.scatter(
        bugs_df,
        x='priority_score',
        y='complexity',
        color='failure_type',
        size='occurrence_count',
        title='Bug Complexity vs Priority',
        hover_data=['module', 'severity']
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Module impact analysis
    st.subheader("Module Impact Analysis")
    module_analysis = bugs_df.groupby('module').agg({
        'signature_id': 'count',
        'priority_score': 'mean',
        'occurrence_count': 'sum'
    }).rename(columns={
        'signature_id': 'bug_count',
        'priority_score': 'avg_priority',
        'occurrence_count': 'total_occurrences'
    }).sort_values('avg_priority', ascending=False).head(15)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=module_analysis.index, y=module_analysis['bug_count'],
               name='Bug Count', marker_color='lightblue'),
        secondary_y=False
    )
    fig.add_trace(
        go.Scatter(x=module_analysis.index, y=module_analysis['avg_priority'],
                  name='Avg Priority Score', mode='lines+markers',
                  line=dict(color='red', width=3)),
        secondary_y=True
    )
    
    fig.update_layout(title_text="Module Bug Count vs Average Priority", height=400)
    fig.update_yaxes(title_text="Bug Count", secondary_y=False)
    fig.update_yaxes(title_text="Average Priority Score", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


def show_fix_plan(triage_plan: dict):
    """Fix plan and recommendations"""
    st.header("🎯 Prioritized Fix Plan")
    
    # Timeline breakdown
    st.subheader("Fix Timeline by Priority")
    
    for priority in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if priority in triage_plan['triage_by_priority']:
            bugs = triage_plan['triage_by_priority'][priority]
            total_hours = sum(b['estimated_hours'] for b in bugs)
            
            # Color coding
            priority_colors = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }
            
            with st.expander(f"{priority_colors[priority]} {priority} Priority ({len(bugs)} bugs) - {total_hours}h"):
                bug_table = []
                for bug in bugs:
                    bug_table.append({
                        'ID': int(bug['signature_id']),
                        'Type': bug['failure_type'],
                        'Module': bug['module'],
                        'Occurrences': int(bug['occurrence_count']),
                        'Complexity': bug['complexity'],
                        'Est. Hours': bug['estimated_hours']
                    })
                
                st.dataframe(pd.DataFrame(bug_table), use_container_width=True, hide_index=True)
    
    # Gantt-style timeline
    st.subheader("🗓️ Recommended Development Timeline")
    
    timeline_text = f"""
    **Sprint 1 (Week 1)**: Fix all CRITICAL and top HIGH priority bugs
    - Estimated time: {triage_plan['estimated_fix_time']['total_hours'] // 3}h
    - Resources: 2-3 engineers
    
    **Sprint 2 (Week 2)**: Continue HIGH, start MEDIUM priority
    - Estimated time: {triage_plan['estimated_fix_time']['total_hours'] // 3}h
    - Resources: 1-2 engineers
    
    **Sprint 3 (Week 3)**: Complete MEDIUM and LOW priority
    - Estimated time: {triage_plan['estimated_fix_time']['total_hours'] // 3}h
    - Resources: 1 engineer
    
    **Total Duration**: {triage_plan['estimated_fix_time']['total_weeks']} weeks
    **Total Effort**: {triage_plan['estimated_fix_time']['total_hours']} engineer-hours
    """
    
    st.markdown(timeline_text)


if __name__ == "__main__":
    main()
