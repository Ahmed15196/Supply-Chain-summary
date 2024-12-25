import streamlit as st
import pandas as pd
import sys


# Set the page config for a modern UI
st.set_page_config(page_title="Supply Chain Procurement Dashboard", layout="wide")

# Title of the dashboard
st.title("🌍 Supply Chain Procurement Dashboard")

# Load the Excel file
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xlsm", "xls", "csv"])

# Initialize session state if not already done
if 'df' not in st.session_state:
    st.session_state['df'] = None

if uploaded_file:
    # Read the uploaded Excel file
    df = pd.read_excel(uploaded_file)

    # Clean up column names (strip spaces, etc.)
    df.columns = df.columns.str.strip()

    # Check if necessary columns exist
    required_columns = ['Sales Order No', 'Customer Name', 'PO Number', 'PO Total Amount (EGP)', 'Invoice Amount', 'Delivery Date', 'PO Date', 'Estimated Delivery Date','Quantity', 'Received Quantity']
    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error(f"Missing columns in the uploaded file: {', '.join(missing_columns)}")
    else:
        # Remove rows containing 'Summary' in 'Sales Order No'
        df = df[~df['Sales Order No'].str.contains('Summary', na=False)]

        # Filter out any rows without valid data
        df = df.dropna(subset=["Sales Order No"])

        # Convert date columns to datetime
        date_columns = ['Delivery Date', 'PO Date', 'Estimated Delivery Date']
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Store the DataFrame in session state
        st.session_state['df'] = df

        # FILTERS: Multi-select filters for Sales Order, Customer Name, and Supplier
        st.sidebar.header("Filters")
        sales_order_no = st.sidebar.multiselect("Select Sales Order No", df["Sales Order No"].unique())
        customer_name = st.sidebar.multiselect("Select Customer Name", df["Customer Name"].unique())
        supplier = st.sidebar.multiselect("Select Supplier", df["Supplier"].unique())

        # Apply filters
        filtered_df = df.copy()

        if sales_order_no:
            filtered_df = filtered_df[filtered_df["Sales Order No"].isin(sales_order_no)]
        if customer_name:
            filtered_df = filtered_df[filtered_df["Customer Name"].isin(customer_name)]
        if supplier:
            filtered_df = filtered_df[filtered_df["Supplier"].isin(supplier)]

        # Display the filtered data
        st.write("## Filtered Data")
        st.dataframe(filtered_df)

        # --- SHIPMENT DELAY ANALYSIS ---
        st.write("### Shipment Delay Analysis")

        # Identify delayed shipments using Estimated Delivery Date and Delivery Date
        delay_threshold = st.sidebar.slider("Set Delay Threshold (Days)", 0, 90, 30)
        delayed_shipments = filtered_df[
            (filtered_df['Estimated Delivery Date'] - filtered_df['Delivery Date']).dt.days > delay_threshold
        ]
        
        st.write(f"Total Delayed Shipments (More than {delay_threshold} days): {len(delayed_shipments)}")
        st.dataframe(delayed_shipments)

        # ALERT: Display alert if critical delay threshold is breached
        if len(delayed_shipments) > 5:
            st.warning("🚨 ALERT: More than 5 delayed shipments detected!")

        # --- SUPPLIER PERFORMANCE ---
        st.write("### Supplier Performance")

        # Calculate on-time delivery rate and other supplier KPIs
        supplier_performance = filtered_df.groupby("Supplier").agg(
            total_orders=("PO Number", "nunique"),
            total_procurement=("PO Total Amount (EGP)", "sum"),
            on_time_deliveries=("Delivery Date", lambda x: (x <= filtered_df.loc[x.index, 'Estimated Delivery Date']).sum()),
            delayed_deliveries=("Delivery Date", lambda x: (x > filtered_df.loc[x.index, 'Estimated Delivery Date']).sum())
        )

        supplier_performance["On-Time Delivery Rate (%)"] = (supplier_performance["on_time_deliveries"] / supplier_performance["total_orders"]) * 100

        st.dataframe(supplier_performance)

        # Bar chart: On-time delivery rate by supplier
        st.bar_chart(supplier_performance["On-Time Delivery Rate (%)"])

        # --- TOP SUPPLIERS & CUSTOMERS ---
        st.write("### Top 5 Suppliers by Procurement Amount")
        top_suppliers = supplier_performance["total_procurement"].nlargest(5)
        st.bar_chart(top_suppliers)

        st.write("### Top 5 Customers by Sales Order Amount")
        top_customers = filtered_df.groupby("Customer Name")["PO Total Amount (EGP)"].sum().nlargest(5)
        st.bar_chart(top_customers)

        # --- RECEIPTS vs. INVOICE COMPARISON ---
st.write("### Receipts vs. Invoice Comparison")

# Check required columns exist
if all(col in filtered_df.columns for col in ["PO Number", "Quantity", "Received Quantity"]):
    # Group data by PO Number
    receipts_vs_quantity = filtered_df.groupby("PO Number").agg(
        total_quantity=("Quantity", "sum"),
        total_received=("Received Quantity", "sum")
    )

    # Adding a new column for the difference
    receipts_vs_quantity["Difference"] = receipts_vs_quantity["total_quantity"] - receipts_vs_quantity["total_received"]

    # Display the resulting DataFrame
    st.dataframe(receipts_vs_quantity)

    # Highlight mismatches
    mismatches = receipts_vs_quantity[receipts_vs_quantity["Difference"] != 0]
    st.write(f"Total Mismatches (Quantity vs Received): {len(mismatches)}")
    st.dataframe(mismatches)
else:
    st.error("The required columns for Receipts vs. Invoice Comparison are missing.")


        # --- DYNAMIC SUMMARY TABLES ---
        st.write("### Summary Tables")

        # Show summarized data of key metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Sales Orders", len(filtered_df["Sales Order No"].unique()))
        with col2:
            st.metric("Total PO Amount (EGP)", f"{filtered_df['PO Total Amount (EGP)'].sum():,.2f} EGP")
        with col3:
            delayed_count = len(filtered_df[filtered_df['Delivery Date'] > filtered_df['Estimated Delivery Date']])
            st.metric("Delayed Shipments", delayed_count)

        # --- EXPORT FILTERED DATA ---
        st.write("### Export Data")
        st.download_button(
            "Download Filtered Data as CSV",
            filtered_df.to_csv(index=False),
            "filtered_data.csv",
            "text/csv"
        )

        st.download_button(
            "Download Summary Data as CSV",
            supplier_performance.to_csv(index=True),
            "supplier_performance.csv",
            "text/csv"
        )
