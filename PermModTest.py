import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.colors import LogNorm
import io
import base64
from scipy import stats
from scipy.optimize import curve_fit
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import gaussian_kde
from PIL import Image
import requests

# Set page configuration
st.set_page_config(
    page_title="Permeability Modeling App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #1f77b4;
        margin-top: 1.5rem;
        margin-bottom: 1rem;
    }
    .group-box {
        border: 1px solid #ccc;
        border-radius: 5px;
        padding: 10px;
        margin: 10px 0;
    }
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# App title and logo
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<h1 class="main-header">Permeability Modeling App</h1>', unsafe_allow_html=True)
    
    # Add a logo (using a placeholder URL - replace with your own logo URL)
    try:
        # You can replace this with your own logo URL or use a local file
        logo_url = "https://raw.githubusercontent.com/Chepe1980/Unify/main/PermeMod.png"
        response = requests.get(logo_url, stream=True)
        logo = Image.open(response.raw)
        st.image(logo, width=200)
    except:
        # Fallback to text if logo can't be loaded
        st.markdown("**Geoscience Analysis**")

# Initialize session state variables
if 'df' not in st.session_state:
    st.session_state.df = None
if 'fzi' not in st.session_state:
    st.session_state.fzi = None
if 'rqi' not in st.session_state:
    st.session_state.rqi = None
if 'groups' not in st.session_state:
    st.session_state.groups = {}
if 'group_colors' not in st.session_state:
    st.session_state.group_colors = {}
if 'color_scale' not in st.session_state:
    st.session_state.color_scale = 'viridis'

# Define consistent color scheme for groups
GROUP_COLORS = {
    1: '#1f77b4',  # Blue
    2: '#ff7f0e',  # Orange
    3: '#2ca02c',  # Green
    4: '#d62728',  # Red
    5: '#9467bd'   # Purple
}

# Available color scales
COLOR_SCALES = [
    'viridis', 'plasma', 'inferno', 'magma', 'cividis',
    'reds', 'blues', 'greens', 'oranges', 'purples',
    'rainbow', 'jet', 'hot', 'cool', 'portland',
    'blackbody', 'electric', 'plotly3', 'picnic', 'armyrose'
]

# Sidebar for file upload and parameters
with st.sidebar:
    st.header("Data Input")
    
    # File upload
    uploaded_file = st.file_uploader("Upload Excel file", type=['xlsx', 'xls'])
    
    if uploaded_file is not None:
        try:
            # Read the Excel file
            df = pd.read_excel(uploaded_file)
            st.session_state.df = df
            
            # Calculate FZI and RQI
            phie = df.iloc[:, 1]  # Assuming column 1 is porosity
            perm = df.iloc[:, 2]  # Assuming column 2 is permeability
            depth = df.iloc[:, 0]  # Assuming column 0 is depth
            
            # Calculate FZI and RQI
            KphiRatio = perm / phie
            SQTHphi = np.sqrt(KphiRatio)
            RQI = 0.0314 * SQTHphi
            PhIndex = phie / (1 - phie)
            FZI = RQI / PhIndex
            
            st.session_state.fzi = FZI
            st.session_state.rqi = RQI
            st.session_state.depth = depth
            
            st.success("Data loaded successfully!")
            
            # Show column names for selection
            st.subheader("Select Data Columns")
            x_col = st.selectbox("X-axis", df.columns, index=1)
            y_col = st.selectbox("Y-axis", df.columns, index=2)
            
        except Exception as e:
            st.error(f"Error loading file: {e}")
    
    # Color scale selection
    st.header("Visualization Settings")
    color_scale = st.selectbox("Color Scale", COLOR_SCALES, index=0)
    st.session_state.color_scale = color_scale
    
    # FZI group parameters
    st.header("FZI Group Parameters")
    
    group_params = {}
    for i in range(1, 6):
        col1, col2 = st.columns(2)
        with col1:
            min_val = st.number_input(f"Group {i} Min", value=0.1*(i-1), key=f"g{i}_min")
        with col2:
            max_val = st.number_input(f"Group {i} Max", value=0.1*i, key=f"g{i}_max")
        group_params[i] = (min_val, max_val)
    
    st.session_state.group_params = group_params

# Main content area
if st.session_state.df is not None:
    df = st.session_state.df
    FZI = st.session_state.fzi
    RQI = st.session_state.rqi
    depth = st.session_state.depth
    color_scale = st.session_state.color_scale
    
    # Create groups based on FZI values
    groups = {}
    group_assignments = np.zeros(len(df), dtype=int)
    for i, (min_val, max_val) in st.session_state.group_params.items():
        mask = (FZI > min_val) & (FZI <= max_val)
        groups[i] = {
            'phie': df.iloc[:, 1][mask],
            'perm': df.iloc[:, 2][mask],
            'depth': df.iloc[:, 0][mask],
            'fzi': FZI[mask]
        }
        group_assignments[mask] = i
    
    st.session_state.groups = groups
    st.session_state.group_assignments = group_assignments
    
    # Create tabs for different visualizations
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Scatter Plots", "FZI Analysis", "Group Analysis", "3D Visualization", "Export Data"])
    
    with tab1:
        st.subheader("Scatter Plot with FZI Coloring")
        
        # Get selected columns
        x_col = st.selectbox("X-axis", df.columns, index=1, key="scatter_x")
        y_col = st.selectbox("Y-axis", df.columns, index=2, key="scatter_y")
        
        # Create scatter plot with Plotly
        fig = px.scatter(df, x=x_col, y=y_col, color=FZI, 
                         color_continuous_scale=color_scale, 
                         log_x=True, log_y=True,
                         title=f"{y_col} vs {x_col} colored by FZI",
                         labels={'color': 'FZI'})
        
        # Regression options
        st.subheader("Regression Analysis")
        reg_type = st.selectbox("Regression Type", 
                               ["Power law relationship", "Exponential relationship", 
                                "Logarithmic relationship", "Linear relationship"])
        
        # Perform regression based on selection
        x_data = df[x_col].values
        y_data = df[y_col].values
        
        # Remove zeros and NaN values for log scaling
        mask = (x_data > 0) & (y_data > 0) & (~np.isnan(x_data)) & (~np.isnan(y_data))
        x_clean = x_data[mask]
        y_clean = y_data[mask]
        
        if len(x_clean) > 0 and len(y_clean) > 0:
            if reg_type == "Power law relationship":
                # Log-log regression
                log_x = np.log(x_clean)
                log_y = np.log(y_clean)
                slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
                y_pred = np.exp(intercept) * x_clean**slope
                equation = f"y = {np.exp(intercept):.4f} * x^{slope:.4f}"
                
            elif reg_type == "Exponential relationship":
                # Exponential regression (log y)
                log_y = np.log(y_clean)
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, log_y)
                y_pred = np.exp(intercept) * np.exp(slope * x_clean)
                equation = f"y = {np.exp(intercept):.4f} * e^{slope:.4f}x"
                
            elif reg_type == "Logarithmic relationship":
                # Logarithmic regression (log x)
                log_x = np.log(x_clean)
                slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, y_clean)
                y_pred = intercept + slope * np.log(x_clean)
                equation = f"y = {intercept:.4f} + {slope:.4f} * ln(x)"
                
            else:  # Linear relationship
                slope, intercept, r_value, p_value, std_err = stats.linregress(x_clean, y_clean)
                y_pred = intercept + slope * x_clean
                equation = f"y = {intercept:.4f} + {slope:.4f}x"
            
            # Add regression line to the plot
            sorted_indices = np.argsort(x_clean)
            x_sorted = x_clean[sorted_indices]
            y_pred_sorted = y_pred[sorted_indices]
            
            fig.add_trace(go.Scatter(x=x_sorted, y=y_pred_sorted, 
                                    mode='lines', 
                                    name=f'{reg_type}<br>{equation}<br>R² = {r_value**2:.4f}',
                                    line=dict(color='red', width=3)))
        
        st.plotly_chart(fig, use_container_width=True)
        
        if len(x_clean) == 0 or len(y_clean) == 0:
            st.warning("Not enough valid data points for regression analysis.")
    
    with tab2:
        st.subheader("FZI and RQI Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # FZI vs Depth plot with Plotly
            fig_fzi = px.scatter(x=FZI, y=depth, 
                                labels={'x': 'FZI', 'y': 'Depth'},
                                title='FZI vs Depth',
                                color_continuous_scale=color_scale,
                                color=FZI)
            fig_fzi.update_yaxes(autorange="reversed")  # Reverse y-axis for depth
            st.plotly_chart(fig_fzi, use_container_width=True)
        
        with col2:
            # RQI vs Depth plot with Plotly
            fig_rqi = px.scatter(x=RQI, y=depth, 
                                labels={'x': 'RQI', 'y': 'Depth'},
                                title='RQI vs Depth',
                                color_continuous_scale=color_scale,
                                color=RQI)
            fig_rqi.update_yaxes(autorange="reversed")  # Reverse y-axis for depth
            st.plotly_chart(fig_rqi, use_container_width=True)
            
        # Log plots
        st.subheader("Logarithmic Plots")
        col3, col4 = st.columns(2)
        
        with col3:
            # FZI vs Depth plot (log scale)
            valid_mask = (FZI > 0) & (~np.isnan(FZI))
            if np.any(valid_mask):
                fig_fzi_log = px.scatter(x=FZI[valid_mask], y=depth[valid_mask], 
                                        labels={'x': 'FZI', 'y': 'Depth'},
                                        title='FZI vs Depth (Log Scale)',
                                        log_x=True,
                                        color_continuous_scale=color_scale,
                                        color=FZI[valid_mask])
                fig_fzi_log.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_fzi_log, use_container_width=True)
        
        with col4:
            # RQI vs Depth plot (log scale)
            valid_mask = (RQI > 0) & (~np.isnan(RQI))
            if np.any(valid_mask):
                fig_rqi_log = px.scatter(x=RQI[valid_mask], y=depth[valid_mask], 
                                        labels={'x': 'RQI', 'y': 'Depth'},
                                        title='RQI vs Depth (Log Scale)',
                                        log_x=True,
                                        color_continuous_scale=color_scale,
                                        color=RQI[valid_mask])
                fig_rqi_log.update_yaxes(autorange="reversed")
                st.plotly_chart(fig_rqi_log, use_container_width=True)
    
    with tab3:
        st.subheader("FZI Group Analysis")
        
        # Plot all groups with Plotly
        fig = go.Figure()
        
        for i, group_data in groups.items():
            if len(group_data['phie']) > 0:
                # Power law fit
                x_data = group_data['phie']
                y_data = group_data['perm']
                
                # Remove zeros and NaN values
                mask = (x_data > 0) & (y_data > 0) & (~np.isnan(x_data)) & (~np.isnan(y_data))
                x_clean = x_data[mask]
                y_clean = y_data[mask]
                
                if len(x_clean) > 1 and len(y_clean) > 1:
                    # Log-log regression
                    log_x = np.log(x_clean)
                    log_y = np.log(y_clean)
                    slope, intercept, r_value, p_value, std_err = stats.linregress(log_x, log_y)
                    
                    # Generate points for the fitted line
                    x_fit = np.linspace(min(x_clean), max(x_clean), 100)
                    y_fit = np.exp(intercept) * x_fit**slope
                    
                    # Add scatter points
                    fig.add_trace(go.Scatter(
                        x=x_clean, y=y_clean,
                        mode='markers',
                        name=f'Group {i}',
                        marker=dict(color=GROUP_COLORS[i], size=8, opacity=0.7)
                    ))
                    
                    # Add fitted line
                    fig.add_trace(go.Scatter(
                        x=x_fit, y=y_fit,
                        mode='lines',
                        name=f'Group {i} Fit: y={np.exp(intercept):.2f}x^{slope:.2f}, R²={r_value**2:.3f}',
                        line=dict(color=GROUP_COLORS[i], width=3)
                    ))
        
        fig.update_xaxes(type='log', title='Porosity')
        fig.update_yaxes(type='log', title='Permeability')
        fig.update_layout(title='Power Law Relationships by FZI Group')
        st.plotly_chart(fig, use_container_width=True)
        
        # Show group statistics
        st.subheader("Group Statistics")
        stats_data = []
        for i, group_data in groups.items():
            if len(group_data['phie']) > 0:
                stats_data.append({
                    'Group': i,
                    'Count': len(group_data['phie']),
                    'Porosity Mean': np.mean(group_data['phie']),
                    'Porosity Std': np.std(group_data['phie']),
                    'Permeability Mean': np.mean(group_data['perm']),
                    'Permeability Std': np.std(group_data['perm']),
                    'FZI Mean': np.mean(group_data['fzi']),
                    'FZI Std': np.std(group_data['fzi'])
                })
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            st.dataframe(stats_df)
        
        # Show histograms for each group
        st.subheader("Group Distributions")
        for i, group_data in groups.items():
            if len(group_data['phie']) > 0:
                st.markdown(f"<h4>Group {i}</h4>", unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Porosity histogram
                    fig_por = px.histogram(x=group_data['phie'], 
                                          title=f'Group {i} Porosity Distribution',
                                          labels={'x': 'Porosity', 'y': 'Frequency'},
                                          color_discrete_sequence=[GROUP_COLORS[i]])
                    st.plotly_chart(fig_por, use_container_width=True)
                
                with col2:
                    # Permeability histogram
                    fig_perm = px.histogram(x=group_data['perm'], 
                                           title=f'Group {i} Permeability Distribution',
                                           labels={'x': 'Permeability', 'y': 'Frequency'},
                                           color_discrete_sequence=[GROUP_COLORS[i]])
                    st.plotly_chart(fig_perm, use_container_width=True)
        
        # PDF Contour Plots for each group - FIXED to match scatter plot groups
        st.subheader("Probability Density Function (PDF) Contours")
        
        # Create a grid for all groups
        fig_contour = go.Figure()
        
        for i, group_data in groups.items():
            if len(group_data['phie']) > 10:  # Need enough points for KDE
                x_data = group_data['phie']
                y_data = group_data['perm']
                
                # Remove zeros and NaN values
                mask = (x_data > 0) & (y_data > 0) & (~np.isnan(x_data)) & (~np.isnan(y_data))
                x_clean = x_data[mask]
                y_clean = y_data[mask]
                
                if len(x_clean) > 10:
                    # Calculate KDE
                    values = np.vstack([x_clean, y_clean])
                    kernel = gaussian_kde(values)
                    
                    # Create grid
                    x_min, x_max = x_clean.min(), x_clean.max()
                    y_min, y_max = y_clean.min(), y_clean.max()
                    xx, yy = np.mgrid[x_min:x_max:100j, y_min:y_max:100j]
                    positions = np.vstack([xx.ravel(), yy.ravel()])
                    
                    # Evaluate KDE on grid
                    zz = np.reshape(kernel(positions).T, xx.shape)
                    
                    # Add contour plot
                    fig_contour.add_trace(go.Contour(
                        z=zz, x=xx[:,0], y=yy[0,:],
                        name=f'Group {i}',
                        colorscale=[(0, 'white'), (1, GROUP_COLORS[i])],
                        showscale=False,
                        opacity=0.7,
                        contours=dict(
                            coloring='lines',
                            showlabels=True,
                        )
                    ))
        
        # Add scatter points for all groups
        for i, group_data in groups.items():
            if len(group_data['phie']) > 0:
                x_data = group_data['phie']
                y_data = group_data['perm']
                
                # Remove zeros and NaN values
                mask = (x_data > 0) & (y_data > 0) & (~np.isnan(x_data)) & (~np.isnan(y_data))
                x_clean = x_data[mask]
                y_clean = y_data[mask]
                
                if len(x_clean) > 0:
                    # Add scatter points
                    fig_contour.add_trace(go.Scatter(
                        x=x_clean, y=y_clean,
                        mode='markers',
                        name=f'Group {i} Data',
                        marker=dict(color=GROUP_COLORS[i], size=5, opacity=0.5)
                    ))
        
        fig_contour.update_xaxes(type='log', title='Porosity')
        fig_contour.update_yaxes(type='log', title='Permeability')
        fig_contour.update_layout(title='PDF Contours by FZI Group')
        st.plotly_chart(fig_contour, use_container_width=True)
    
    with tab4:
        st.subheader("3D Visualization")
        
        # Create a DataFrame with all variables including FZI and RQI
        df_with_fzi_rqi = df.copy()
        df_with_fzi_rqi['FZI'] = FZI
        df_with_fzi_rqi['RQI'] = RQI
        
        # Get all available columns including FZI and RQI
        all_columns = list(df.columns) + ['FZI', 'RQI']
        
        # Axis selection for 3D plots
        st.subheader("Axis Selection for 3D Plots")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            x_axis = st.selectbox("X-axis", all_columns, index=0, key="3d_x")
        with col2:
            y_axis = st.selectbox("Y-axis", all_columns, index=1, key="3d_y")
        with col3:
            z_axis = st.selectbox("Z-axis", all_columns, index=2, key="3d_z")
        
        # Color scale selection for 3D plots
        col4, col5 = st.columns(2)
        with col4:
            color_by = st.selectbox("Color by", ['FZI', 'RQI', 'FZI Group'], index=0)
        with col5:
            three_d_color_scale = st.selectbox("3D Color Scale", COLOR_SCALES, index=0, key="3d_color")
        
        # Create 3D scatter plot with Plotly
        if color_by == 'FZI Group':
            fig_3d = px.scatter_3d(df_with_fzi_rqi, x=x_axis, y=y_axis, z=z_axis,
                                  color=group_assignments, 
                                  color_continuous_scale=three_d_color_scale,
                                  title=f'3D Visualization: {x_axis} vs {y_axis} vs {z_axis} colored by FZI Groups',
                                  labels={'color': 'FZI Group'})
        else:
            color_data = FZI if color_by == 'FZI' else RQI
            fig_3d = px.scatter_3d(df_with_fzi_rqi, x=x_axis, y=y_axis, z=z_axis,
                                  color=color_data, 
                                  color_continuous_scale=three_d_color_scale,
                                  title=f'3D Visualization: {x_axis} vs {y_axis} vs {z_axis} colored by {color_by}',
                                  labels={'color': color_by})
        
        st.plotly_chart(fig_3d, use_container_width=True)
        
        # Additional 3D visualization options
        st.subheader("Additional 3D Visualization Options")
        
        col6, col7, col8 = st.columns(3)
        
        with col6:
            x_axis2 = st.selectbox("X-axis", all_columns, index=0, key="3d_x2")
        with col7:
            y_axis2 = st.selectbox("Y-axis", all_columns, index=1, key="3d_y2")
        with col8:
            z_axis2 = st.selectbox("Z-axis", all_columns, index=2, key="3d_z2")
        
        # Create 3D scatter plot with size based on FZI
        fig_3d_size = px.scatter_3d(df_with_fzi_rqi, x=x_axis2, y=y_axis2, z=z_axis2,
                                   size=FZI, color=FZI,
                                   color_continuous_scale=three_d_color_scale,
                                   title=f'3D Visualization: {x_axis2} vs {y_axis2} vs {z_axis2} with FZI sizing',
                                   labels={'size': 'FZI', 'color': 'FZI'})
        st.plotly_chart(fig_3d_size, use_container_width=True)
    
    with tab5:
        st.subheader("Export Results")
        
        # Create results DataFrame
        results_df = df.copy()
        results_df['FZI'] = FZI
        results_df['RQI'] = RQI
        results_df['FZI_Group'] = group_assignments
        
        # Show data preview
        st.dataframe(results_df.head())
        
        # Export options
        export_format = st.selectbox("Export Format", ["CSV", "Excel"])
        
        if export_format == "CSV":
            csv = results_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="fzi_analysis_results.csv",
                mime="text/csv"
            )
        else:
            # Excel export
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, sheet_name='FZI Analysis', index=False)
                
                # Add group statistics sheet
                if st.session_state.groups:
                    stats_data = []
                    for i, group_data in st.session_state.groups.items():
                        if len(group_data['phie']) > 0:
                            stats_data.append({
                                'Group': i,
                                'Count': len(group_data['phie']),
                                'Porosity Mean': np.mean(group_data['phie']),
                                'Porosity Std': np.std(group_data['phie']),
                                'Permeability Mean': np.mean(group_data['perm']),
                                'Permeability Std': np.std(group_data['perm']),
                                'FZI Mean': np.mean(group_data['fzi']),
                                'FZI Std': np.std(group_data['fzi'])
                            })
                    
                    if stats_data:
                        stats_df = pd.DataFrame(stats_data)
                        stats_df.to_excel(writer, sheet_name='Group Statistics', index=False)
            
            st.download_button(
                label="Download Excel",
                data=buffer.getvalue(),
                file_name="fzi_analysis_results.xlsx",
                mime="application/vnd.ms-excel"
            )

else:
    st.info("Please upload an Excel file to get started. The file should contain columns for depth, porosity, and permeability.")
    
    # Display some information about the app
    st.markdown("""
    ### About This App
    
    This app analyzes permeability and porosity data using Flow Zone Indicator (FZI) methodology.
    
    **Expected data format:**
    - Column 1: Depth
    - Column 2: Porosity
    - Column 3: Permeability
    
    **The app will calculate:**
    - FZI (Flow Zone Indicator)
    - RQI (Reservoir Quality Index)
    - Group data based on FZI ranges
    - Power law relationships for each group
    
    **Features:**
    - Interactive scatter plots with FZI coloring
    - Regression analysis with different model types
    - FZI group analysis and visualization
    - Interactive 3D visualization with customizable axes (including FZI and RQI)
    - Customizable color scales for all visualizations
    - Data export capabilities
    """)
