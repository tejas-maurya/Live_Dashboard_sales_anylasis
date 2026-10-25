
import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# 1. PAGE CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Sales Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

# =====================================================
# 2. HELPER FUNCTIONS
# =====================================================

def load_data(uploaded_file):
    """Read CSV, Excel or JSON into a DataFrame."""
    extension = uploaded_file.name.rsplit(".", 1)[-1].lower()

    if extension == "csv":
        return pd.read_csv(uploaded_file)
    elif extension == "xlsx":
        return pd.read_excel(uploaded_file, engine="openpyxl")
    elif extension == "json":
        return pd.read_json(uploaded_file)
    else:
        raise ValueError("Unsupported file format.")


def find_column(columns, keywords):
    """Find a likely column based on its name."""
    for column in columns:
        name = str(column).strip().lower().replace("_", " ")
        if name in keywords:
            return column
    return None


def clean_data(data, missing_method, remove_duplicates,
               standardize_text, date_columns):
    """Clean data without changing the original DataFrame."""
    df = data.copy()

    # Clean column names
    df.columns = [
        str(column).strip() for column in df.columns
    ]

    # Standardize text values
    if standardize_text:
        for column in df.select_dtypes(include=["object", "string"]).columns:
            df[column] = df[column].apply(
                lambda value: value.strip() if isinstance(value, str) else value
            )

    # Convert selected columns to datetime
    for column in date_columns:
        if column in df.columns:
            df[column] = pd.to_datetime(
                df[column], errors="coerce"
            )

    # Handle missing values
    if missing_method == "Drop rows":
        df = df.dropna()

    elif missing_method == "Fill with median/mode":
        for column in df.columns:
            if pd.api.types.is_numeric_dtype(df[column]):
                median = df[column].median()
                if pd.notna(median):
                    df[column] = df[column].fillna(median)
            else:
                mode = df[column].mode(dropna=True)
                if not mode.empty:
                    df[column] = df[column].fillna(mode.iloc[0])

    # Remove complete duplicate rows
    if remove_duplicates:
        df = df.drop_duplicates()

    return df


def numeric_column(data, column):
    """Convert a selected column into numeric values safely."""
    if column is None or column not in data.columns:
        return None

    return pd.to_numeric(data[column], errors="coerce")


def money(value):
    """Format a numeric value as currency."""
    if pd.isna(value):
        return "N/A"
    return f"₹{value:,.2f}"


def show_kpi(label, value, help_text=None):
    """Display a KPI card."""
    st.metric(label, value, help=help_text)


def statistical_summary(data):
    """Reusable descriptive statistics function."""
    return data.describe(include="all").T


# =====================================================
# 3. APPLICATION HEADER
# =====================================================

st.title("📊 Sales Analytics Dashboard")
st.write(
    "Upload your data, validate it, clean it, "
    "and explore your sales performance."
)

# =====================================================
# 4. FILE UPLOAD
# =====================================================

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV, Excel or JSON",
    type=["csv", "xlsx", "json"]
)

if uploaded_file is None:
    st.info("Upload a dataset from the sidebar to begin.")

    st.subheader("What this application provides")
    col1, col2, col3 = st.columns(3)
    col1.info("📁 Data upload and validation")
    col2.info("🧹 Data preprocessing")
    col3.info("📈 Interactive analysis")

    st.stop()

try:
    original_df = load_data(uploaded_file)

    if original_df.empty or len(original_df.columns) == 0:
        st.warning("The uploaded file has no usable data.")
        st.stop()

except Exception as error:
    st.error("Unable to read the uploaded file.")
    st.caption(f"Details: {error}")
    st.stop()


# =====================================================
# 5. VALIDATION REPORT
# =====================================================

st.success(f"Loaded: {uploaded_file.name}")

st.subheader("1. Data Validation")

rows, columns = original_df.shape

c1, c2, c3, c4 = st.columns(4)
c1.metric("Rows", rows)
c2.metric("Columns", columns)
c3.metric("Missing Cells", int(original_df.isna().sum().sum()))
c4.metric("Duplicate Rows", int(original_df.duplicated().sum()))

with st.expander("Preview original data", expanded=True):
    st.dataframe(original_df.head(20), use_container_width=True)

column_info = pd.DataFrame({
    "Column Name": original_df.columns.astype(str),
    "Data Type": original_df.dtypes.astype(str).values,
    "Missing Values": original_df.isna().sum().values,
    "Missing (%)": (
        original_df.isna().mean().mul(100).round(2).values
    ),
    "Unique Values": original_df.nunique(dropna=True).values
})

st.subheader("Column Information")
st.dataframe(column_info, use_container_width=True, hide_index=True)

with st.expander("Missing values by column"):
    missing_report = (
        original_df.isna().sum()
        .rename("Missing Count")
        .to_frame()
    )
    st.dataframe(missing_report, use_container_width=True)

with st.expander("Duplicate records"):
    duplicates = original_df[
        original_df.duplicated(keep=False)
    ]
    if duplicates.empty:
        st.info("No complete duplicate rows found.")
    else:
        st.dataframe(duplicates, use_container_width=True)


# =====================================================
# 6. DATA PREPROCESSING
# =====================================================

st.subheader("2. Data Preprocessing")

date_candidates = [
    column for column in original_df.columns
    if any(word in str(column).lower()
           for word in ["date", "time"])
]

with st.sidebar:
    st.header("Data Cleaning")

    missing_method = st.selectbox(
        "Handle missing values",
        [
            "Keep unchanged",
            "Drop rows",
            "Fill with median/mode"
        ]
    )

    remove_duplicates = st.checkbox(
        "Remove duplicate rows",
        value=True
    )

    standardize_text = st.checkbox(
        "Remove extra spaces from text",
        value=True
    )

    date_columns = st.multiselect(
        "Convert these columns to dates",
        options=list(original_df.columns),
        default=date_candidates
    )

try:
    df = clean_data(
        original_df,
        missing_method,
        remove_duplicates,
        standardize_text,
        date_columns
    )

except Exception as error:
    st.error(f"Data cleaning failed: {error}")
    st.stop()

st.write(
    f"Original rows: {len(original_df)} | "
    f"Rows after cleaning: {len(df)}"
)

with st.expander("Preview cleaned data"):
    st.dataframe(df.head(20), use_container_width=True)

with st.expander("Statistical Summary"):
    st.dataframe(
        statistical_summary(df),
        use_container_width=True
    )

st.download_button(
    "Download cleaned data as CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="cleaned_sales_data.csv",
    mime="text/csv"
)

if df.empty:
    st.warning("No rows remain after preprocessing.")
    st.stop()


# =====================================================
# 7. COLUMN MAPPING
# =====================================================

st.subheader("3. Configure Sales Columns")

columns_list = list(df.columns)
column_options = ["None"] + columns_list

def default_index(keywords):
    match = find_column(columns_list, keywords)
    return column_options.index(match) if match in column_options else 0


with st.sidebar:
    st.header("Column Mapping")

    sales_col = st.selectbox(
        "Sales column",
        column_options,
        index=default_index(
            ["sales", "total sales", "revenue", "amount"]
        )
    )

    profit_col = st.selectbox(
        "Profit column",
        column_options,
        index=default_index(["profit", "total profit", "net profit"])
    )

    order_col = st.selectbox(
        "Order ID column",
        column_options,
        index=default_index(
            ["order id", "order_id", "order number", "order"]
        )
    )

    quantity_col = st.selectbox(
        "Quantity column",
        column_options,
        index=default_index(
            ["quantity", "qty", "quantity sold"]
        )
    )

    date_col = st.selectbox(
        "Date column",
        column_options,
        index=default_index(
            ["date", "order date", "order_date", "date of order"]
        )
    )

    region_col = st.selectbox(
        "Region column",
        column_options,
        index=default_index(["region", "area", "state", "city"])
    )

    category_col = st.selectbox(
        "Category column",
        column_options,
        index=default_index(
            ["category", "product category", "product type"]
        )
    )


def selected_column(value):
    return None if value == "None" else value


sales_col = selected_column(sales_col)
profit_col = selected_column(profit_col)
order_col = selected_column(order_col)
quantity_col = selected_column(quantity_col)
date_col = selected_column(date_col)
region_col = selected_column(region_col)
category_col = selected_column(category_col)

# Convert mapped measures to numbers
if sales_col:
    df[sales_col] = numeric_column(df, sales_col)

if profit_col:
    df[profit_col] = numeric_column(df, profit_col)

if quantity_col:
    df[quantity_col] = numeric_column(df, quantity_col)

# Ensure the selected date column is datetime
if date_col:
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")


# =====================================================
# 8. INTERACTIVE FILTERS
# =====================================================

st.subheader("4. Interactive Filters")

filtered_df = df.copy()

filter1, filter2, filter3 = st.columns(3)

# Filter 1: Region
with filter1:
    if region_col:
        region_values = sorted(
            filtered_df[region_col].dropna().unique().tolist(),
            key=str
        )

        selected_regions = st.multiselect(
            "Filter by region",
            options=region_values,
            default=region_values
        )

        filtered_df = filtered_df[
            filtered_df[region_col].isin(selected_regions)
        ]
    else:
        st.caption("Map a region column to enable this filter.")

# Filter 2: Category
with filter2:
    if category_col:
        category_values = sorted(
            filtered_df[category_col].dropna().unique().tolist(),
            key=str
        )

        selected_categories = st.multiselect(
            "Filter by category",
            options=category_values,
            default=category_values
        )

        filtered_df = filtered_df[
            filtered_df[category_col].isin(selected_categories)
        ]
    else:
        st.caption("Map a category column to enable this filter.")

# Filter 3: Date range
with filter3:
    if date_col:
        valid_dates = filtered_df[date_col].dropna()

        if not valid_dates.empty:
            minimum_date = valid_dates.min().date()
            maximum_date = valid_dates.max().date()

            selected_dates = st.date_input(
                "Filter by date",
                value=(minimum_date, maximum_date),
                min_value=minimum_date,
                max_value=maximum_date
            )

            if isinstance(selected_dates, (tuple, list)):
                if len(selected_dates) == 2:
                    start_date, end_date = selected_dates
                    filtered_df = filtered_df[
                        filtered_df[date_col].dt.date.between(
                            start_date, end_date
                        )
                    ]
                elif len(selected_dates) == 1:
                    filtered_df = filtered_df[
                        filtered_df[date_col].dt.date == selected_dates[0]
                    ]
        else:
            st.caption("No valid dates available for filtering.")
    else:
        st.caption("Map a date column to enable this filter.")

st.write(f"Records matching your filters: {len(filtered_df):,}")


# =====================================================
# 9. FIVE DYNAMIC KPIs
# =====================================================

st.subheader("5. Key Performance Indicators")

def total_numeric(data, column):
    if column is None:
        return None

    values = numeric_column(data, column)
    return values.sum()

total_sales = total_numeric(filtered_df, sales_col)
total_profit = total_numeric(filtered_df, profit_col)
total_quantity = total_numeric(filtered_df, quantity_col)

if order_col:
    total_orders = filtered_df[order_col].nunique()
else:
    total_orders = None

if total_sales is not None and pd.notna(total_sales) and total_sales != 0:
    profit_margin = (
        total_profit / total_sales * 100
        if total_profit is not None and pd.notna(total_profit)
        else None
    )
else:
    profit_margin = None

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    show_kpi(
        "Total Sales",
        money(total_sales) if total_sales is not None else "Map column"
    )

with k2:
    show_kpi(
        "Total Profit",
        money(total_profit) if total_profit is not None else "Map column"
    )

with k3:
    show_kpi(
        "Total Orders",
        f"{total_orders:,}" if total_orders is not None else "Map column"
    )

with k4:
    show_kpi(
        "Quantity Sold",
        f"{total_quantity:,.2f}"
        if total_quantity is not None and pd.notna(total_quantity)
        else "Map column"
    )

with k5:
    show_kpi(
        "Profit Margin",
        f"{profit_margin:.2f}%"
        if profit_margin is not None and pd.notna(profit_margin)
        else "N/A"
    )


# =====================================================
# 10. INTERACTIVE VISUALIZATIONS
# =====================================================

st.subheader("6. Interactive Visualizations")

if filtered_df.empty:
    st.warning("No data matches the selected filters.")

else:
    # Chart 1: Sales by category
    if category_col and sales_col:
        chart_data = filtered_df.dropna(
            subset=[category_col, sales_col]
        )

        if not chart_data.empty:
            sales_by_category = (
                chart_data.groupby(category_col, as_index=False)[sales_col]
                .sum()
                .sort_values(sales_col, ascending=False)
            )

            fig1 = px.bar(
                sales_by_category,
                x=category_col,
                y=sales_col,
                title="Sales by Category",
                labels={
                    category_col: "Category",
                    sales_col: "Sales"
                },
                color=category_col
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("No valid data for the category chart.")
    else:
        st.info("Map sales and category columns to show this chart.")

    # Chart 2: Sales over time
    if date_col and sales_col:
        chart_data = filtered_df.dropna(
            subset=[date_col, sales_col]
        )

        if not chart_data.empty:
            sales_over_time = (
                chart_data.assign(
                    Period=chart_data[date_col].dt.to_period("M").dt.to_timestamp()
                )
                .groupby("Period", as_index=False)[sales_col]
                .sum()
            )

            fig2 = px.line(
                sales_over_time,
                x="Period",
                y=sales_col,
                markers=True,
                title="Sales Over Time",
                labels={"Period": "Date", sales_col: "Sales"}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No valid data for the time-series chart.")
    else:
        st.info("Map sales and date columns to show the time-series chart.")

    # Chart 3: Profit by region
    if region_col and profit_col:
        chart_data = filtered_df.dropna(
            subset=[region_col, profit_col]
        )

        if not chart_data.empty:
            profit_by_region = (
                chart_data.groupby(region_col, as_index=False)[profit_col]
                .sum()
                .sort_values(profit_col, ascending=False)
            )

            fig3 = px.bar(
                profit_by_region,
                x=region_col,
                y=profit_col,
                title="Profit by Region",
                labels={
                    region_col: "Region",
                    profit_col: "Profit"
                },
                color=region_col
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No valid data for the regional profit chart.")
    else:
        st.info("Map profit and region columns to show this chart.")

    # Optional chart 4: Sales/profit relationship
    if sales_col and profit_col:
        chart_data = filtered_df.dropna(
            subset=[sales_col, profit_col]
        )

        if not chart_data.empty:
            fig4 = px.scatter(
                chart_data,
                x=sales_col,
                y=profit_col,
                title="Sales vs Profit",
                hover_data=(
                    [order_col] if order_col else None
                )
            )
            st.plotly_chart(fig4, use_container_width=True)



st.subheader("7. Export Filtered Data")

st.download_button(
    "Download filtered data as CSV",
    data=filtered_df.to_csv(index=False).encode("utf-8"),
    file_name="filtered_sales_data.csv",
    mime="text/csv"
)

st.caption(
    "Sales Analytics Dashboard | Built with Python, Pandas, "
    "Streamlit and Plotly"
)
