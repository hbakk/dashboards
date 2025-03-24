import streamlit as st
import plotly.express as px
import pandas as pd
import plotly.graph_objects as go
from rapidfuzz import fuzz
import csv
import warnings
warnings.filterwarnings('ignore')

# --- Fuzzy Matching Helper Function ---
def find_best_column(possible_names, column_list):
    matches = {}
    for col in column_list:
        score = max([fuzz.ratio(col.lower(), key.lower()) for key in possible_names])
        matches[col] = score
    best_match = max(matches, key=matches.get)
    return best_match if matches[best_match] > 60 else None  # threshold adjustable

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="Universal Sales Dashboard", page_icon="📊", layout="wide")
st.title("📊 Universal Interactive Sales Dashboard")
st.markdown('<style>div.block-container{padding-top:1rem;}</style>', unsafe_allow_html=True)

# --- File uploader ---
fl = st.file_uploader(":file_folder: Upload Sales File", type=["csv", "xlsx"])

if fl is not None:
    filename = fl.name
    st.write(f"**Uploaded File:** {filename}")

    try:
        if filename.endswith(('csv', 'txt')):
            # Try multiple delimiters
            detected = False
            for delimiter in [',', ';', '\t']:
                try:
                    fl.seek(0)
                    df = pd.read_csv(fl, encoding='ISO-8859-1', delimiter=delimiter)
                    if df.shape[1] > 1:
                        detected = True
                        break
                except:
                    continue
            if not detected:
                st.error("Could not read CSV file. Please check delimiter or file structure.")
                st.stop()
        else:
            df = pd.read_excel(fl)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    # --- Detecting Key Columns ---
    columns = df.columns.tolist()

    date_col = find_best_column(["InvoiceDate", "Order Date", "Date"], columns)
    sales_col = find_best_column(["TotalSales", "Sales"], columns)
    profit_col = find_best_column(["OperatingProfit", "Profit"], columns)
    product_col = find_best_column(["Product", "Category", "Product Name"], columns)
    region_col = find_best_column(["Region"], columns)
    state_col = find_best_column(["State"], columns)
    city_col = find_best_column(["City"], columns)
    retailer_col = find_best_column(["Retailer"], columns)
    quantity_col = find_best_column(["UnitsSold", "Quantity"], columns)

    st.success(f"Detected Columns:\n- Date: {date_col}\n- Sales: {sales_col}\n- Profit: {profit_col}\n- Product: {product_col}\n- Region: {region_col}\n- State: {state_col}\n- City: {city_col}\n- Retailer: {retailer_col}\n- Quantity: {quantity_col}")

    # --- Data Cleaning ---
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')

    numeric_cols = [sales_col, profit_col, quantity_col]
    for col in numeric_cols:
        if col:
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('$', '').str.strip()
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # --- Sidebar Filters ---
    st.sidebar.header("Filter Data: ")

    if region_col:
        region = st.sidebar.multiselect("Pick Region", df[region_col].unique())
    else:
        region = []

    if state_col:
        state = st.sidebar.multiselect("Pick State", df[state_col].unique())
    else:
        state = []

    if city_col:
        city = st.sidebar.multiselect("Pick City", df[city_col].unique())
    else:
        city = []

    filtered_df = df.copy()

    if region and region_col:
        filtered_df = filtered_df[filtered_df[region_col].isin(region)]
    if state and state_col:
        filtered_df = filtered_df[filtered_df[state_col].isin(state)]
    if city and city_col:
        filtered_df = filtered_df[filtered_df[city_col].isin(city)]

    # --- Date Filter ---
    col1, col2 = st.columns((2))
    startDate = filtered_df[date_col].min() if date_col else None
    endDate = filtered_df[date_col].max() if date_col else None

    if date_col:
        with col1:
            date1 = pd.to_datetime(st.date_input("Start Date", startDate))

        with col2:
            date2 = pd.to_datetime(st.date_input("End Date", endDate))

        filtered_df = filtered_df[(filtered_df[date_col] >= date1) & (filtered_df[date_col] <= date2)].copy()

    # --- KPIs ---
    total_sales = filtered_df[sales_col].sum() if sales_col else 0
    total_profit = filtered_df[profit_col].sum() if profit_col else 0
    total_units = filtered_df[quantity_col].sum() if quantity_col else 0
    total_orders = filtered_df.shape[0]

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="Total Sales", value=f"${total_sales:,.0f}")
    kpi2.metric(label="Total Profit", value=f"${total_profit:,.0f}")
    kpi3.metric(label="Units Sold", value=f"{total_units:,}")
    kpi4.metric(label="Total Orders", value=f"{total_orders}")

    # --- Visualizations ---

    # Retailer wise sales
    if retailer_col and sales_col:
        st.subheader("Total Sales by Retailer")
        retailer_df = filtered_df.groupby(retailer_col, as_index=False)[sales_col].sum()
        fig1 = px.bar(retailer_df, x=retailer_col, y=sales_col, text_auto=True)
        st.plotly_chart(fig1, use_container_width=True)

    # Sales Over Time
    if date_col and sales_col:
        st.subheader("Total Sales Over Time")
        filtered_df["Month_Year"] = filtered_df[date_col].dt.to_period("M").astype(str)
        time_df = filtered_df.groupby("Month_Year", as_index=False)[sales_col].sum()
        fig2 = px.line(time_df, x="Month_Year", y=sales_col)
        st.plotly_chart(fig2, use_container_width=True)

    # Treemap Region & City
    if region_col and city_col and sales_col:
        st.subheader("Total Sales by Region and City in Treemap")
        fig3 = px.treemap(filtered_df, path=[region_col, city_col], values=sales_col)
        st.plotly_chart(fig3, use_container_width=True)

    # Sales & Units by State
    if state_col and sales_col and quantity_col:
        st.subheader("Total Sales and Units Sold by State")
        state_df = filtered_df.groupby(state_col, as_index=False).agg({sales_col: "sum", quantity_col: "sum"})
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(x=state_df[state_col], y=state_df[sales_col], name='Total Sales'))
        fig4.add_trace(go.Scatter(x=state_df[state_col], y=state_df[quantity_col], name='Units Sold', yaxis="y2"))
        fig4.update_layout(yaxis2=dict(overlaying='y', side='right', title='Units Sold'))
        st.plotly_chart(fig4, use_container_width=True)

    # Pie Charts
    chart1, chart2 = st.columns((2))
    if retailer_col and sales_col:
        with chart1:
            st.subheader("Retailer wise Sales")
            fig5 = px.pie(filtered_df, values=sales_col, names=retailer_col, hole=0.4)
            st.plotly_chart(fig5, use_container_width=True)

    if product_col and sales_col:
        with chart2:
            st.subheader("Product wise Sales")
            product_df = filtered_df.groupby(product_col, as_index=False)[sales_col].sum()
            fig6 = px.pie(product_df, values=sales_col, names=product_col, hole=0.4)
            st.plotly_chart(fig6, use_container_width=True)

    # Download Data
    with st.expander("Download Filtered Data"):
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Filtered Data", data=csv, file_name="Filtered_Data.csv", mime="text/csv")

    # View Data
    with st.expander("View Filtered Data"):
        st.dataframe(filtered_df)

else:
    st.warning("Please upload a valid Sales file to proceed.")
    