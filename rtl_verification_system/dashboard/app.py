"""
Interactive Streamlit Dashboard for RTL Verification System
Visualizes ML predictions, module risk heatmaps, and test prioritization
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from datetime import datetime, timedelta
import joblib
from sklearn.preprocessing import StandardScaler

# Page config
st.set_page_config(
    page_title="RTL Verification Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .risk-high { color: #ff4444; font-weight: bold; }
    .risk-medium { color: #ff9500; font-weight: bold; }
    .risk-low { color: #00c851; font-weight: bold; }
    h1 { color: #1f77b4; }
    h2 { color: #2c3e50; margin-top: 30px; }
</style>
""", unsafe_allow_html=True)

# === UTILITY FUNCTIONS ===

@st.cache_resource
def load_model_artifacts():
    """Load pre-trained ML model and artifacts"""
    try:
        model = joblib.load('models/rtl_predictor_model.pkl')
        scaler = joblib.load('models/scaler.pkl')
        feature_cols = joblib.load('models/feature_cols.pkl')
        with open('models/model_metadata.json', 'r') as f:
            metadata = json.load(f)
        return model, scaler, feature_cols, metadata
    except Exception as e:
        st.error(f"Error loading model: {e}")
        return None, None, None, None


@st.cache_data
def load_data():
    """Load datasets"""
    try:
        df_history = pd.read_csv('data/rtl_verification_history.csv')
        df_recent = pd.read_csv('data/recent_commits.csv')
        df_optimized = pd.read_csv('data/optimized_test_queue.csv')
        
        with open('data/optimization_impact.json', 'r') as f:
            impact_metrics = json.load(f)
        
        return df_history, df_recent, df_optimized, impact_metrics
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None, None, None


def preprocess_commit(commit_df):
    """Preprocess commit data for prediction"""
    commit_df = commit_df.copy()
    
    # Handle has_critical_module - use is_hotspot_module if modules_affected not available
    if 'modules_affected' in commit_df.columns:
        critical_modules = ['AHB_Controller', 'Memory_Controller', 'Cache_L1', 'Interconnect']
        commit_df['has_critical_module'] = commit_df['modules_affected'].apply(
            lambda x: 1 if any(mod in x for mod in critical_modules) else 0
        )
    else:
        # For interactive predictor, use is_hotspot_module as proxy
        commit_df['has_critical_module'] = commit_df.get('is_hotspot_module', 0)
    
    commit_df['code_churn_normalized'] = commit_df['code_churn_ratio'] * commit_df['files_modified']
    commit_df['bug_density'] = commit_df['historical_bug_frequency'] / (commit_df['modules_affected_count'] + 1)
    commit_df['risk_score'] = (
        (1 - commit_df['author_experience_years'] / 20) * 0.2 +
        commit_df['code_churn_ratio'] * 0.3 +
        commit_df['is_hotspot_module'] * 0.2 +
        (commit_df['bug_density'] / (commit_df['bug_density'].max() + 1)) * 0.3
    )
    
    return commit_df


# === MAIN APP ===

def main():
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("⚡ RTL Verification Dashboard")
        st.markdown("**AI-Driven Test Prioritization System**")
    with col2:
        st.metric("Last Updated", datetime.now().strftime("%H:%M:%S"))
    
    st.markdown("---")
    
    # Load data
    df_history, df_recent, df_optimized, impact = load_data()
    
    if df_history is None:
        st.error("Unable to load data. Please ensure CSV files exist in 'data/' folder.")
        return
    
    model, scaler, feature_cols, metadata = load_model_artifacts()
    
    # === SIDEBAR NAVIGATION ===
    st.sidebar.markdown("## Navigation")
    page = st.sidebar.radio("Select View", [
        "🏠 Dashboard Overview",
        "📊 Test Queue Analysis",
        "🔥 Risk Heatmap",
        "💡 Model Insights",
        "💰 ROI Analysis",
        "🎮 Interactive Predictor"
    ])
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### System Info")
    st.sidebar.metric("Historical Commits", len(df_history))
    st.sidebar.metric("Recent Commits", len(df_recent))
    st.sidebar.metric("Model ROC-AUC", f"{metadata['roc_auc_score']:.4f}")
    
    # === PAGE CONTENT ===
    
    if page == "🏠 Dashboard Overview":
        show_overview(df_history, df_recent, df_optimized, impact, metadata)
    
    elif page == "📊 Test Queue Analysis":
        show_test_queue_analysis(df_optimized)
    
    elif page == "🔥 Risk Heatmap":
        show_risk_heatmap(df_optimized)
    
    elif page == "💡 Model Insights":
        show_model_insights(df_history, metadata)
    
    elif page == "💰 ROI Analysis":
        show_roi_analysis(impact)
    
    elif page == "🎮 Interactive Predictor":
        show_interactive_predictor(model, scaler, feature_cols)


def show_overview(df_history, df_recent, df_optimized, impact, metadata):
    """Dashboard overview page"""
    st.header("Executive Summary")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Regression Time Saved",
            f"{impact['time_saved_hours']:.1f}h",
            f"{impact['time_saved_percent']:.1f}%"
        )
    
    with col2:
        st.metric(
            "Cost Savings",
            f"${impact['cost_saved_usd']:.0f}",
            f"{impact['cost_saved_percent']:.1f}%"
        )
    
    with col3:
        st.metric(
            "Model Accuracy (ROC-AUC)",
            f"{metadata['roc_auc_score']:.4f}",
            "Trained ✓"
        )
    
    with col4:
        st.metric(
            "Failures Detected Early",
            f"{impact['failure_catch_rate_percent']:.0f}%",
            "First 30% of tests"
        )
    
    st.markdown("---")
    
    # Two-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Historical Failure Rate")
        failure_rate = df_history['test_failed'].mean() * 100
        fig = go.Figure(data=[
            go.Indicator(
                mode="gauge+number+delta",
                value=failure_rate,
                title={'text': "Test Failure Rate (%)"},
                delta={'reference': 20},
                gauge={
                    'axis': {'range': [0, 50]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 15], 'color': "#d4e6d4"},
                        {'range': [15, 30], 'color': "#fff4e6"},
                        {'range': [30, 50], 'color': "#f4d4d4"}
                    ]
                }
            )
        ])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🎯 Test Priority Distribution")
        priority_bins = pd.cut(df_optimized['risk_score'], 
                               bins=[0, 33, 66, 100], 
                               labels=['Low', 'Medium', 'High'])
        risk_dist = priority_bins.value_counts()
        
        fig = go.Figure(data=[go.Pie(
            labels=risk_dist.index,
            values=risk_dist.values,
            marker=dict(colors=['#00c851', '#ff9500', '#ff4444']),
            textposition='inside',
            textinfo='label+percent'
        )])
        fig.update_layout(height=350)
        st.plotly_chart(fig, use_container_width=True)
    
    # Recent commits status
    st.subheader("📋 Latest Optimized Test Queue")
    top_tests = df_optimized.head(15)[['test_priority', 'commit_id', 'risk_score', 
                                        'predicted_failure_probability', 'modules_affected']]
    top_tests['Risk Level'] = pd.cut(top_tests['risk_score'], 
                                     bins=[0, 33, 66, 100], 
                                     labels=['🟢 Low', '🟡 Medium', '🔴 High'])
    top_tests['Failure Risk'] = (top_tests['predicted_failure_probability'] * 100).round(1).astype(str) + '%'
    
    st.dataframe(
        top_tests[['test_priority', 'commit_id', 'Risk Level', 'Failure Risk', 'modules_affected']],
        use_container_width=True,
        hide_index=True
    )


def show_test_queue_analysis(df_optimized):
    """Test queue analysis page"""
    st.header("Test Queue Analysis & Prioritization")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📊 Risk Score Distribution")
        fig = px.histogram(df_optimized, x='risk_score', nbins=30,
                          title='Distribution of Risk Scores',
                          labels={'risk_score': 'Risk Score', 'count': 'Number of Tests'},
                          color_discrete_sequence=['#1f77b4'])
        fig.add_vline(x=df_optimized['risk_score'].mean(), 
                     line_dash="dash", line_color="red",
                     annotation_text="Mean")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.metric("Mean Risk Score", f"{df_optimized['risk_score'].mean():.1f}")
        st.metric("Median Risk Score", f"{df_optimized['risk_score'].median():.1f}")
        st.metric("Max Risk Score", f"{df_optimized['risk_score'].max():.1f}")
        st.metric("Min Risk Score", f"{df_optimized['risk_score'].min():.1f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎲 Predicted Failure Rate by Risk Quartile")
        df_optim_copy = df_optimized.copy()
        # qcut can fail if there are duplicate bin edges; allow pandas to drop duplicates
        df_optim_copy['risk_quartile'] = pd.qcut(
            df_optim_copy['risk_score'],
            q=4,
            labels=['Q1 (Lowest)', 'Q2', 'Q3', 'Q4 (Highest)'],
            duplicates='drop'
        )
        failure_by_quartile = df_optim_copy.groupby('risk_quartile')['predicted_failure_probability'].agg(['mean', 'std', 'count'])
        
        fig = px.bar(failure_by_quartile.reset_index().rename(
            columns={'mean': 'Avg Failure Probability'}),
            x='risk_quartile', y='Avg Failure Probability',
            color='Avg Failure Probability',
            color_continuous_scale='RdYlGn_r',
            title='Average Failure Probability by Risk Quartile',
            labels={'risk_quartile': 'Risk Quartile'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ Test Duration vs Risk")
        fig = px.scatter(df_optimized, x='risk_score', y='regression_time_hours',
                        size='predicted_failure_probability',
                        color='risk_score',
                        color_continuous_scale='RdYlGn_r',
                        title='Test Duration vs Risk Score',
                        labels={'risk_score': 'Risk Score', 
                               'regression_time_hours': 'Duration (hours)'})
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Full queue table
    st.subheader("📋 Full Optimized Test Queue")
    display_df = df_optimized.copy()
    
    # Create risk level column
    display_df['Risk Level'] = pd.cut(display_df['risk_score'], 
                                     bins=[0, 33, 66, 100], 
                                     labels=['🟢 Low', '🟡 Medium', '🔴 High'])
    display_df['Failure Risk %'] = (display_df['predicted_failure_probability'] * 100).round(1)
    
    st.dataframe(
        display_df[['test_priority', 'commit_id', 'Risk Level', 'Failure Risk %', 
                   'code_churn_ratio', 'historical_bug_frequency', 'regression_time_hours']],
        use_container_width=True,
        hide_index=True
    )


def show_risk_heatmap(df_optimized):
    """Risk heatmap visualization page - SoC floorplan style with interactive selection"""
    st.header("🔥 Module Risk Heatmap")
    
    st.markdown("**Click on a module to see details. Visualization shows which RTL modules are at highest risk.**")
    
    # Extract module risks
    module_risks = {}
    
    for _, row in df_optimized.iterrows():
        modules = row['modules_affected'].split(',')
        for module in modules:
            module = module.strip()
            if module not in module_risks:
                module_risks[module] = {
                    'count': 0,
                    'total_risk': 0,
                    'total_failure_prob': 0
                }
            module_risks[module]['count'] += 1
            module_risks[module]['total_risk'] += row['risk_score']
            module_risks[module]['total_failure_prob'] += row['predicted_failure_probability']
    
    # Calculate average risk per module
    module_stats = []
    for module, stats in module_risks.items():
        module_stats.append({
            'Module': module,
            'Avg Risk Score': stats['total_risk'] / stats['count'],
            'Avg Failure Prob': stats['total_failure_prob'] / stats['count'],
            'Commit Count': stats['count'],
        })
    
    module_df = pd.DataFrame(module_stats).sort_values('Avg Risk Score', ascending=False)
    
    # Initialize session state for selected module
    if 'selected_module' not in st.session_state:
        st.session_state.selected_module = module_df.iloc[0]['Module']
    
    # Create SoC floorplan layout
    module_layout = {
        'Memory_Controller': (0, 0, 2, 2),
        'Cache_L1': (2, 0, 1.5, 2),
        'Cache_L2': (3.5, 0, 1.5, 2),
        'AHB_Controller': (0, 2, 2, 1.5),
        'Interconnect': (2, 2, 3, 1.5),
        'ALU': (0, 3.5, 1.5, 1.5),
        'Control_Unit': (1.5, 3.5, 1.5, 1.5),
        'Data_Path': (3, 3.5, 2.5, 1.5),
        'Register_File': (5.5, 3.5, 1, 1.5),
        'SPI_Interface': (0, 5, 1.3, 1),
        'I2C_Interface': (1.3, 5, 1.3, 1),
        'UART_Controller': (2.6, 5, 1.4, 1),
        'GPIO_Controller': (4, 5, 1.5, 1),
        'Clock_Domain': (5.5, 5, 1, 1),
        'Reset_Logic': (6.5, 5, 1, 1),
    }
    
    # Module selector sidebar
    with st.sidebar:
        st.markdown("### 🎯 Select Module")
        selected = st.selectbox(
            "Click to explore module details:",
            module_df.sort_values('Avg Risk Score', ascending=False)['Module'].values,
            index=list(module_df['Module'].values).index(st.session_state.selected_module),
            key="module_select"
        )
        st.session_state.selected_module = selected
    
    # Create floorplan figure with highlight
    fig = go.Figure()
    
    # Normalize risk scores for color mapping
    max_risk = module_df['Avg Risk Score'].max()
    min_risk = module_df['Avg Risk Score'].min()
    
    # Add module rectangles
    for module in module_layout.keys():
        if module in module_df['Module'].values:
            module_data = module_df[module_df['Module'] == module].iloc[0]
            risk_score = module_data['Avg Risk Score']
            failure_prob = module_data['Avg Failure Prob']
            commits = module_data['Commit Count']
        else:
            risk_score = min_risk
            failure_prob = 0
            commits = 0
        
        x, y, w, h = module_layout[module]
        
        # Color mapping: green (low) to red (high)
        normalized = (risk_score - min_risk) / (max_risk - min_risk + 0.01)
        color = f'rgba({int(255 * normalized)}, {int(255 * (1 - normalized))}, 0, 0.8)'
        
        # Check if this is the selected module
        is_selected = module == st.session_state.selected_module
        border_width = 4 if is_selected else 2
        border_color = "gold" if is_selected else "white"
        
        fig.add_shape(
            type="rect",
            x0=x, y0=y, x1=x+w, y1=y+h,
            fillcolor=color,
            line=dict(color=border_color, width=border_width),
        )
        
        # Add module label with risk info
        label_color = "white" if is_selected else "black"
        label_size = 11 if is_selected else 10
        fig.add_annotation(
            x=x + w/2, y=y + h/2,
            text=f"<b>{module}</b><br>{risk_score:.1f}",
            showarrow=False,
            font=dict(size=label_size, color=label_color),
            align="center"
        )
    
    fig.update_layout(
        title="SoC Module Risk Floorplan (Click modules in sidebar to highlight)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        plot_bgcolor='#222',
        paper_bgcolor='rgba(0,0,0,0)',
        height=600,
        hovermode='closest',
        margin=dict(l=20, r=20, t=50, b=20)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display detailed info for selected module
    st.markdown("---")
    
    if st.session_state.selected_module in module_df['Module'].values:
        selected_data = module_df[module_df['Module'] == st.session_state.selected_module].iloc[0]
        
        # Show module details
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            risk_level = "🔴 HIGH" if selected_data['Avg Risk Score'] > 66 else ("🟡 MEDIUM" if selected_data['Avg Risk Score'] > 33 else "🟢 LOW")
            st.metric(
                f"📍 {st.session_state.selected_module}",
                risk_level,
                f"Risk: {selected_data['Avg Risk Score']:.1f}/100"
            )
        
        with col2:
            st.metric(
                "Failure Probability",
                f"{selected_data['Avg Failure Prob']*100:.1f}%",
                f"Avg: {selected_data['Avg Failure Prob']:.3f}"
            )
        
        with col3:
            st.metric(
                "Affected Commits",
                int(selected_data['Commit Count']),
                "test changes"
            )
        
        with col4:
            priority = 1 if selected_data['Avg Risk Score'] > 66 else (2 if selected_data['Avg Risk Score'] > 33 else 3)
            st.metric(
                "Priority",
                f"P{priority}",
                "Fix urgency"
            )
        
        # Show commits affecting this module
        st.subheader("📋 Recent Commits Affecting This Module")
        affected_commits = []
        for _, row in df_optimized.iterrows():
            if st.session_state.selected_module in row['modules_affected']:
                affected_commits.append({
                    'Commit': row['commit_id'],
                    'Risk': row['risk_score'],
                    'Failure %': f"{row['predicted_failure_probability']*100:.1f}%",
                    'Tests': int(row['test_priority'])
                })
        
        if affected_commits:
            st.dataframe(
                pd.DataFrame(affected_commits).sort_values('Risk', ascending=False).head(10),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No recent commits affecting this module.")
    
    # Risk legend and statistics
    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("### 🎨 Risk Legend")
        st.markdown("""
        🟢 **Green** — Low Risk (0-33)  
        🟡 **Yellow** — Medium Risk (33-66)  
        🔴 **Red** — High Risk (66-100)
        """)
    
    with col2:
        st.subheader("📊 All Modules - Ranked by Risk")
        st.dataframe(
            module_df.sort_values('Avg Risk Score', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Avg Risk Score": st.column_config.NumberColumn(format="%.1f"),
                "Avg Failure Prob": st.column_config.NumberColumn(format="%.3f"),
            }
        )
    
    # Risk distribution visualization
    st.subheader("🎯 Risk Distribution Across Modules")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Add bar chart
    fig.add_trace(
        go.Bar(x=module_df['Module'], y=module_df['Commit Count'],
               name='Commits Affecting Module',
               marker_color='lightblue'),
        secondary_y=False
    )
    
    # Add line chart
    fig.add_trace(
        go.Scatter(x=module_df['Module'], y=module_df['Avg Failure Prob']*100,
                  name='Avg Failure Probability (%)',
                  mode='lines+markers',
                  line=dict(color='red', width=3),
                  marker=dict(size=10)),
        secondary_y=True
    )
    
    fig.update_layout(title_text="Module Impact Analysis",
                     height=400,
                     hovermode='x unified')
    fig.update_yaxes(title_text="Number of Commits", secondary_y=False)
    fig.update_yaxes(title_text="Failure Probability (%)", secondary_y=True)
    
    st.plotly_chart(fig, use_container_width=True)


def show_model_insights(df_history, metadata):
    """Model performance and insights page"""
    st.header("💡 ML Model Insights")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Model Type", "XGBoost Classifier")
    with col2:
        st.metric("ROC-AUC Score", f"{metadata['roc_auc_score']:.4f}")
    with col3:
        st.metric("F1 Score", f"{metadata['f1_score']:.4f}")
    
    st.markdown("---")
    
    # Feature importance
    st.subheader("🎯 Feature Importance Ranking")
    
    feature_imp = pd.DataFrame(metadata['feature_importance'])
    feature_imp = feature_imp.sort_values('importance', ascending=True).tail(15)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Plotly express does not have barh; use bar with orientation='h'
        fig = px.bar(
            feature_imp,
            x='importance',
            y='feature',
            orientation='h',
            title='Top 15 Most Important Features',
            labels={'importance': 'Importance Score', 'feature': 'Feature'},
            color='importance',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("### Feature Descriptions")
        st.markdown("""
        - **code_churn_ratio**: Amount of code changed
        - **author_experience**: Years of developer experience
        - **risk_score**: Engineered composite risk metric
        - **lines_added/deleted**: Lines of code modifications
        - **modules_affected**: Count of affected modules
        - **historical_bug_freq**: Past bugs in modules
        - **is_hotspot_module**: Critical module flag
        """)
    
    # Model performance metrics
    st.markdown("---")
    st.subheader("📊 Training Performance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Training Configuration:**
        - Training samples: {metadata['training_samples']}
        - Test samples: {metadata['test_samples']}
        - Algorithm: {metadata['model_type']}
        - Estimators: {metadata['n_estimators']}
        - Max depth: {metadata['max_depth']}
        """)
    
    with col2:
        st.success(f"""
        **Model Quality:**
        - ROC-AUC: {metadata['roc_auc_score']:.4f}
        - F1-Score: {metadata['f1_score']:.4f}
        - Status: ✓ Production Ready
        - Trained: {metadata['timestamp']}
        """)


def show_roi_analysis(impact):
    """ROI and business impact analysis page"""
    st.header("💰 Return on Investment (ROI) Analysis")
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Cost Saved Per Run",
            f"${impact['cost_saved_usd']:.0f}",
            f"{impact['cost_saved_percent']:.1f}%"
        )
    
    with col2:
        st.metric(
            "Time Saved Per Run",
            f"{impact['time_saved_hours']:.1f}h",
            f"{impact['time_saved_percent']:.1f}%"
        )
    
    with col3:
        annual_cost_saved = impact['cost_saved_usd'] * 250 * 20
        st.metric(
            "Annual Cost Savings",
            f"${annual_cost_saved:,.0f}",
            "250 commits × 20 devs"
        )
    
    with col4:
        annual_time_saved = impact['time_saved_hours'] * 250 * 20
        st.metric(
            "Annual Time Saved",
            f"{annual_time_saved:,.0f}h",
            "~{:.0f} dev-years".format(annual_time_saved / 2000)
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Annual Savings Projection")
        
        years = np.arange(1, 6)
        annual_savings = years * annual_cost_saved
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=annual_savings,
            fill='tozeroy',
            name='Cumulative Savings',
            line=dict(color='green', width=3),
            fillcolor='rgba(0, 200, 81, 0.3)'
        ))
        
        fig.update_layout(
            title="5-Year ROI Projection (20 Developers)",
            xaxis_title="Year",
            yaxis_title="Cumulative Savings ($)",
            hovermode='x unified',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💵 ROI Breakdown")
        
        breakdown_data = {
            'Category': ['Compute Costs', 'Developer Time', 'Total'],
            'Savings': [
                impact['cost_saved_usd'] * 0.6,
                impact['cost_saved_usd'] * 0.4,
                impact['cost_saved_usd']
            ]
        }
        
        fig = px.pie(
            values=breakdown_data['Savings'],
            names=breakdown_data['Category'],
            title="Annual Savings by Category",
            color_discrete_sequence=['#1f77b4', '#ff7f0e', '#2ca02c']
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed metrics
    st.markdown("---")
    st.subheader("📊 Detailed Impact Metrics")
    
    metrics_data = {
        'Metric': [
            'Tests in Optimized Mode',
            'Total Tests Analyzed',
            'Optimized Regression Time',
            'Original Regression Time',
            'Failures Caught in First Pass',
            'Cost per Test Hour (AWS)',
            'Annual Developer Commits',
            'Developers Affected'
        ],
        'Value': [
            f"{impact['tests_run_in_optimized_mode']}",
            f"{impact['total_tests']}",
            f"{impact['optimized_regression_hours']:.2f} hours",
            f"{impact['original_regression_hours']:.2f} hours",
            f"{impact['failure_catch_rate_percent']:.1f}%",
            "$0.50",
            "250 (per developer)",
            "20"
        ]
    }
    
    st.dataframe(
        pd.DataFrame(metrics_data),
        use_container_width=True,
        hide_index=True
    )


def show_interactive_predictor(model, scaler, feature_cols):
    """Interactive ML predictor page"""
    st.header("🎮 Interactive Failure Predictor")
    
    st.markdown("**Input commit parameters below to get real-time failure predictions**")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        author_exp = st.slider("Author Experience (years)", 0, 20, 8)
        files_mod = st.slider("Files Modified", 1, 50, 5)
        lines_add = st.slider("Lines Added", 10, 5000, 100)
    
    with col2:
        lines_del = st.slider("Lines Deleted", 0, 3000, 50)
        modules_count = st.slider("Modules Affected", 1, 15, 3)
        hotspot = st.checkbox("Touches Hotspot Module (AHB/Memory/Interconnect)", value=False)
    
    with col3:
        bug_freq = st.slider("Historical Bug Frequency", 0, 20, 5)
        reg_time = st.slider("Expected Regression Time (hours)", 2, 50, 6)
    
    # Calculate code churn
    code_churn_ratio = (lines_add + lines_del) / (lines_add + lines_del + 5000)
    
    # Create input dataframe
    input_data = pd.DataFrame({
        'author_experience_years': [author_exp],
        'files_modified': [files_mod],
        'lines_added': [lines_add],
        'lines_deleted': [lines_del],
        'modules_affected_count': [modules_count],
        'code_churn_ratio': [code_churn_ratio],
        'is_hotspot_module': [1 if hotspot else 0],
        'historical_bug_frequency': [bug_freq],
        'regression_time_hours': [reg_time],
    })
    
    # Preprocess
    processed = preprocess_commit(input_data)
    
    # Add requires features if missing
    for col in feature_cols:
        if col not in processed.columns:
            processed[col] = 0
    
    X = processed[feature_cols]
    X_scaled = scaler.transform(X)
    
    # Predict
    failure_prob = model.predict_proba(X_scaled)[0, 1]
    risk_score = (
        failure_prob * 60 +
        code_churn_ratio * 15 +
        (1 if hotspot else 0) * 15 +
        (bug_freq / (modules_count + 1)) * 10
    )
    risk_score = min(100, risk_score)
    
    # Display results
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Failure Probability", f"{failure_prob*100:.1f}%")
    
    with col2:
        st.metric("Risk Score", f"{risk_score:.1f}/100")
    
    with col3:
        if risk_score > 66:
            st.metric("Risk Level", "🔴 HIGH", "Run First!")
        elif risk_score > 33:
            st.metric("Risk Level", "🟡 MEDIUM", "Prioritize")
        else:
            st.metric("Risk Level", "🟢 LOW", "Can Wait")
    
    # Risk gauge
    fig = go.Figure(data=[
        go.Indicator(
            mode="gauge+number",
            value=risk_score,
            title={'text': "Overall Risk Score"},
            gauge={
                'axis': {'range': [0, 100]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 33], 'color': "#d4e6d4"},
                    {'range': [33, 66], 'color': "#fff4e6"},
                    {'range': [66, 100], 'color': "#f4d4d4"}
                ]
            }
        )
    ])
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    # Recommendation
    st.markdown("---")
    
    if risk_score > 66:
        st.error(f"""
        ⚠️ **HIGH RISK** - This commit should be tested immediately!
        
        - Failure probability: {failure_prob*100:.1f}%
        - Recommend: Run full regression suite FIRST
        - Expected regression time: {reg_time} hours
        """)
    elif risk_score > 33:
        st.warning(f"""
        ⚠️ **MEDIUM RISK** - Prioritize this commit
        
        - Failure probability: {failure_prob*100:.1f}%
        - Recommend: Schedule for next test batch
        """)
    else:
        st.success(f"""
        ✅ **LOW RISK** - Can follow standard queue
        
        - Failure probability: {failure_prob*100:.1f}%
        - Recommend: Can defer to later regression
        """)


# === MAIN ENTRY POINT ===

if __name__ == '__main__':
    main()
