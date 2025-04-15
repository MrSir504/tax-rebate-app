import streamlit as st

# Add custom CSS for grey background and white text to match Navigate Wealth logo
st.markdown(
    """
    <style>
    .stApp {
        background-color: #4A4A4A;  /* Grey background similar to logo */
        color: white;  /* White text */
    }
    h1 {
        color: white;  /* Ensure title is white */
    }
    .stTextInput > div > div > input {
        background-color: #333333;  /* Darker grey for input fields */
        color: white;  /* White text in inputs */
    }
    .stButton > button {
        background-color: #666666;  /* Medium grey for button */
        color: white;  /* White text on button */
    }
    .stAlert {
        background-color: #333333;  /* Darker grey for success/info boxes */
        color: white;  /* White text in alerts */
    }
    .stSelectbox > div > div > select {
        background-color: #333333;  /* Darker grey for dropdown */
        color: white;  /* White text in dropdown */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# RA Tax Rebate Calculator Functions
def get_tax_rate(income):
    """Return the marginal tax rate based on annual taxable income (2024/2025 rates)."""
    tax_brackets = [
        (0, 237100, 0.18, 0),
        (237101, 370500, 0.26, 42678),
        (370501, 512800, 0.31, 77362),
        (512801, 673000, 0.36, 121475),
        (673001, 857900, 0.39, 179147),
        (857901, 1817000, 0.41, 251258),
        (1817001, float('inf'), 0.45, 644489)
    ]
    for lower, upper, rate, base_tax in tax_brackets:
        if lower <= income <= upper:
            return rate
    return 0.45

def calculate_ra_rebate(income, contribution):
    """Calculate the tax rebate for RA contributions and excess carryover."""
    max_deductible = min(income * 0.275, 350000)  # 27.5% of income, capped at R350,000
    deductible = min(contribution, max_deductible)  # Deductible amount
    excess = max(0, contribution - max_deductible)  # Excess contribution to carry over
    tax_rate = get_tax_rate(income)
    rebate = deductible * tax_rate
    return deductible, tax_rate, rebate, excess

# Streamlit interface
# Center the logo using columns
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("logo.png", width=300)
st.markdown("<br>", unsafe_allow_html=True)
st.title("Navigate Wealth Financial Tools")
# Add tagline
st.markdown("<p style='text-align: center; color: #CCCCCC;'>Powered by Navigate Wealth</p>", unsafe_allow_html=True)

# Tool selection dropdown
tool_options = ["Select a Tool", "RA Tax Rebate Calculator"]  # Add more tools here in the future
selected_tool = st.selectbox("Choose a Financial Tool:", tool_options)

# Display the selected tool's interface
if selected_tool == "Select a Tool":
    st.write("Please select a tool from the dropdown above to get started.")
elif selected_tool == "RA Tax Rebate Calculator":
    st.write("Enter client details to calculate their tax rebate for retirement annuity contributions.")
    # RA contribution limits note with smaller font
    st.markdown(
        "<p style='font-size: 14px; font-style: italic; color: #CCCCCC;'>RA Contribution Limits: You can deduct RA contributions up to 27.5% of your taxable income, capped at R350,000 per year. Excess contributions roll over to future years. Verify limits for the 2025/2026 tax year.</p>",
        unsafe_allow_html=True
    )

    # Input fields
    name = st.text_input("Client's Name")
    income = st.number_input("Annual Pensionable Income (R)", min_value=0.0, step=1000.0)
    contribution = st.number_input("Annual RA Contribution (R)", min_value=0.0, step=1000.0)

    # Calculate button
    if st.button("Calculate Rebate"):
        if not name.strip():
            st.error("Please enter a name.")
        elif income < 0 or contribution < 0:
            st.error("Income and contribution must be non-negative.")
        else:
            try:
                deductible, tax_rate, rebate, excess = calculate_ra_rebate(income, contribution)
                st.success("--- Tax Rebate Summary ---")
                st.write(f"**Client**: {name}")
                st.write(f"**Annual Pensionable Income**: R {income:,.2f}")
                st.write(f"**RA Contribution**: R {contribution:,.2f}")
                st.write(f"**Deductible Contribution**: R {deductible:,.2f}")
                if excess > 0:
                    st.write(f"**Excess Contribution (Carried Over)**: R {excess:,.2f}")
                st.write(f"**Marginal Tax Rate**: {tax_rate * 100:.1f}%")
                st.write(f"**Tax Rebate**: R {rebate:,.2f}")
                # Tax rates note with smaller font
                st.markdown(
                    "<p style='font-size: 14px; color: #888888;'>Note: Tax rates are based on 2024/2025 SARS tables. Verify with 2025/2026 rates when available.</p>",
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.write("This tool is coming soon! Contact the Navigate Wealth team to suggest new tools.")