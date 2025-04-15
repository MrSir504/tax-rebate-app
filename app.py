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

# Tax Rates and Rebates (2024/2025) - Easily updatable
TAX_BRACKETS = [
    (0, 237100, 0.18, 0),
    (237101, 370500, 0.26, 42678),
    (370501, 512800, 0.31, 77362),
    (512801, 673000, 0.36, 121475),
    (673001, 857900, 0.39, 179147),
    (857901, 1817000, 0.41, 251258),
    (1817001, float('inf'), 0.45, 644489)
]
REBATES = {
    "primary": 17235,
    "secondary": 9444,  # Age 65+
    "tertiary": 3145    # Age 75+
}
UIF_RATE = 0.01  # 1% employee contribution
UIF_MONTHLY_CAP = 14872  # Max monthly salary for UIF calculation
UIF_ANNUAL_CAP = UIF_MONTHLY_CAP * 12  # R178,464

# RA Tax Rebate Calculator Functions
def get_tax_rate(income):
    """Return the marginal tax rate based on annual taxable income (2024/2025 rates)."""
    for lower, upper, rate, base_tax in TAX_BRACKETS:
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

# Salary Tax Calculator Function (Corrected)
def calculate_salary_tax(gross_salary, pension_contribution, age):
    """Calculate PAYE, UIF, taxable income, and tax rates."""
    # Step 1: Calculate Taxable Income
    max_deductible = min(gross_salary * 0.275, 350000)  # Pension/RA deduction limit
    deductible_contribution = min(pension_contribution, max_deductible)
    taxable_income = max(0, gross_salary - deductible_contribution)

    # Step 2: Calculate PAYE (Corrected)
    tax_before_rebates = 0
    marginal_rate = 0
    for lower, upper, rate, base_tax in TAX_BRACKETS:
        if taxable_income > lower:
            if taxable_income <= upper:
                tax_before_rebates = base_tax + (taxable_income - lower) * rate
                marginal_rate = rate
                break
            marginal_rate = rate
        else:
            break

    # Apply rebates based on age
    total_rebate = REBATES["primary"]
    if age >= 75:
        total_rebate += REBATES["secondary"] + REBATES["tertiary"]
    elif age >= 65:
        total_rebate += REBATES["secondary"]
    paye = max(0, tax_before_rebates - total_rebate)

    # Step 3: Calculate UIF (employee contribution)
    annual_salary_for_uif = min(gross_salary, UIF_ANNUAL_CAP)
    uif = annual_salary_for_uif * UIF_RATE

    # Step 4: Calculate Net Income
    net_income = gross_salary - paye - uif

    return taxable_income, paye, uif, net_income, marginal_rate

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
tool_options = ["Select a Tool", "RA Tax Rebate Calculator", "Salary Tax Calculator"]
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
elif selected_tool == "Salary Tax Calculator":
    st.write("Enter client details to calculate their salary tax, UIF, and net income.")
    # Input fields
    name = st.text_input("Client's Name", key="tax_calc_name")
    gross_salary = st.number_input("Gross Annual Salary (R)", min_value=0.0, step=1000.0)
    pension_contribution = st.number_input("Annual Pension/RA Contribution (R)", min_value=0.0, step=1000.0)
    age = st.number_input("Client's Age", min_value=0, max_value=120, step=1)

    # Calculate button
    if st.button("Calculate Tax"):
        if not name.strip():
            st.error("Please enter a name.")
        elif gross_salary < 0 or pension_contribution < 0 or age < 0:
            st.error("All inputs must be non-negative.")
        else:
            try:
                taxable_income, paye, uif, net_income, marginal_rate = calculate_salary_tax(gross_salary, pension_contribution, age)
                st.success("--- Salary Tax Summary ---")
                st.write(f"**Client**: {name}")
                st.write(f"**Gross Annual Salary**: R {gross_salary:,.2f}")
                st.write(f"**Taxable Income**: R {taxable_income:,.2f}")
                st.write(f"**PAYE (Income Tax)**: R {paye:,.2f}")
                st.write(f"**UIF Contribution (Employee)**: R {uif:,.2f}")
                st.write(f"**Net Annual Income**: R {net_income:,.2f}")
                st.write(f"**Marginal Tax Rate**: {marginal_rate * 100:.1f}%")
                # Tax rates note with smaller font
                st.markdown(
                    "<p style='font-size: 14px; color: #888888;'>Note: Tax rates and UIF limits are based on 2024/2025 SARS tables. Verify with 2025/2026 rates when available.</p>",
                    unsafe_allow_html=True
                )
            except Exception as e:
                st.error(f"Error: {e}")
else:
    st.write("This tool is coming soon! Contact the Navigate Wealth team to suggest new tools.")