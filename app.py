import streamlit as st
import pandas as pd
import io
import math

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
        background-color: #555555;  /* Lighter grey for input fields */
        color: white;  /* White text in inputs */
    }
    .stTextInput > div > div > input::placeholder {
        color: #CCCCCC;  /* Light grey placeholder text */
        opacity: 1;  /* Ensure placeholder is fully visible */
    }
    .stNumberInput > div > div > input {
        background-color: #555555;  /* Lighter grey for number input fields */
        color: white;  /* White text in inputs */
    }
    .stNumberInput > div > div > input::placeholder {
        color: #CCCCCC;  /* Light grey placeholder text */
        opacity: 1;  /* Ensure placeholder is fully visible */
    }
    .stButton > button {
        background-color: #666666;  /* Medium grey for button */
        color: white;  /* White text on button */
        border: 1px solid #777777;  /* Slight border for visibility */
    }
    .stButton > button:hover {
        background-color: #777777;  /* Slightly lighter grey on hover */
        color: red;  /* Red text on hover */
    }
    .stFormSubmitButton > button {
        background-color: #666666;  /* Medium grey for form submit button */
        color: white;  /* White text on button */
        border: 1px solid #777777;  /* Slight border for visibility */
    }
    .stFormSubmitButton > button:hover {
        background-color: #777777;  /* Slightly lighter grey on hover */
        color: red;  /* Red text on hover */
    }
    .stDownloadButton > button {
        background-color: #666666;  /* Medium grey for download button */
        color: white;  /* White text */
        border: 1px solid #777777;
    }
    .stDownloadButton > button:hover {
        background-color: #777777;  /* Slightly lighter grey on hover */
        color: red;  /* Red text on hover */
    }
    .stAlert {
        background-color: #333333;  /* Darker grey for success/info boxes */
        color: white;  /* White text in alerts */
    }
    .stSelectbox > div > div > select {
        background-color: #333333;  /* Darker grey for dropdown */
        color: white;  /* White text in dropdown */
    }
    /* Style for labels */
    .stTextInput > label, .stNumberInput > label, .stSelectbox > label {
        color: white;  /* White labels */
    }
    /* Style for descriptions (st.write text) */
    .stMarkdown, .stMarkdown p {
        color: white;  /* White description text */
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
UIF_MONTHLY_CAP = 17712  # Updated to R17,712/month as of 1 June 2021
UIF_ANNUAL_CAP = UIF_MONTHLY_CAP * 12  # R212,544
# Medical Tax Credits (2025/2026)
MTC_PER_PERSON = 364  # R364 per month for taxpayer and first dependant
MTC_ADDITIONAL_DEPENDANT = 246  # R246 per month for each additional dependant
# Estate Duty Rates (2025)
ESTATE_DUTY_ABATEMENT = 3500000  # R3.5 million
ESTATE_DUTY_RATE_1 = 0.20  # 20% up to R30 million
ESTATE_DUTY_RATE_2 = 0.25  # 25% above R30 million
ESTATE_DUTY_THRESHOLD = 30000000  # R30 million
EXECUTOR_FEE_RATE = 0.035  # 3.5%
VAT_RATE = 0.15  # 15%
CGT_INCLUSION_RATE = 0.40  # 40% inclusion rate for individuals
CGT_EXCLUSION_DEATH = 300000  # R300,000 exclusion in year of death

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

# Calculate Medical Tax Credits
def calculate_medical_tax_credits(num_dependants):
    """Calculate the Medical Scheme Fees Tax Credit (MTC) based on the number of dependants."""
    if num_dependants <= 0:
        return 0, 0
    # First two members (taxpayer + first dependant) get R364 each per month
    if num_dependants <= 2:
        annual_mtc = num_dependants * MTC_PER_PERSON * 12
    else:
        # First two get R364 each, additional dependants get R246 each
        annual_mtc = (2 * MTC_PER_PERSON * 12) + ((num_dependants - 2) * MTC_ADDITIONAL_DEPENDANT * 12)
    monthly_mtc = annual_mtc / 12
    return annual_mtc, monthly_mtc

# Salary Tax Calculator Function
def calculate_salary_tax(gross_salary, pension_contribution, age, medical_contributions, num_dependants):
    """Calculate PAYE, UIF, MTC, taxable income, and tax rates."""
    # Step 1: Calculate Taxable Income
    max_deductible = min(gross_salary * 0.275, 350000)  # Pension/RA deduction limit
    deductible_contribution = min(pension_contribution, max_deductible)
    taxable_income = max(0, gross_salary - deductible_contribution)

    # Step 2: Calculate PAYE before MTC
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
    paye_before_mtc = max(0, tax_before_rebates - total_rebate)
    paye_before_mtc_monthly = paye_before_mtc / 12

    # Step 3: Calculate Medical Tax Credits
    mtc_annual, mtc_monthly = calculate_medical_tax_credits(num_dependants)
    # Apply MTC to reduce PAYE
    paye = max(0, paye_before_mtc - mtc_annual)
    paye_monthly = paye / 12

    # Step 4: Calculate UIF (employee contribution)
    annual_salary_for_uif = min(gross_salary, UIF_ANNUAL_CAP)
    uif = annual_salary_for_uif * UIF_RATE
    uif_monthly = uif / 12

    # Step 5: Calculate Net Income
    net_income = gross_salary - paye - uif
    net_income_monthly = net_income / 12

    return taxable_income, paye_before_mtc, paye_before_mtc_monthly, mtc_annual, mtc_monthly, paye, paye_monthly, uif, uif_monthly, net_income, net_income_monthly, marginal_rate

# Budget Tool Function
def calculate_budget(monthly_income, expenses):
    """Calculate total expenses, remaining budget, and savings potential."""
    total_expenses = sum(expense for category, expense in expenses)
    remaining_budget = monthly_income - total_expenses
    savings_potential = max(0, remaining_budget)  # Savings if positive, 0 if negative
    return total_expenses, remaining_budget, savings_potential

# Retirement Calculator Functions
def calculate_future_value(current_value, annual_rate, years, monthly_contribution=0, annual_contribution_increase=0):
    """Calculate the future value of an investment with monthly contributions and annual increases."""
    future_value = current_value
    monthly_rate = (1 + annual_rate) ** (1/12) - 1  # Convert annual rate to monthly
    annual_contributions = monthly_contribution * 12  # Initial annual contribution

    for year in range(years):
        # Apply growth to the current value at the start of the year
        future_value = future_value * (1 + annual_rate)
        # Add contributions for the year, compounded monthly
        for month in range(12):
            monthly_contrib = (annual_contributions / 12) * (1 + monthly_rate) ** (11 - month)
            future_value += monthly_contrib
        # Increase contributions for the next year
        annual_contributions *= (1 + annual_contribution_increase)

    return future_value

def calculate_years_until_depletion(capital, annual_income, inflation_rate, years_to_retirement, assumed_return):
    """Calculate how many years the capital will last with annual withdrawals, considering SA laws."""
    current_capital = capital
    max_drawdown_rate = 0.175  # Living annuity max drawdown of 17.5%
    years = 0
    first_withdrawal = None
    capital_over_time = [current_capital]  # Track capital for graphing
    withdrawals_over_time = []  # Track withdrawals (income) for graphing
    monthly_income_over_time = []  # Track monthly income for graphing
    monthly_income_today_value = []  # Track monthly income in today's value

    while current_capital > 0:
        # Check if capital is below R125,000 threshold for full withdrawal
        if current_capital <= 125000:
            withdrawals_over_time.append(current_capital)  # Full withdrawal
            monthly_income = current_capital / 12
            monthly_income_over_time.append(monthly_income)
            # Adjust for inflation to today's value
            total_years = years_to_retirement + years + 1
            inflation_factor = (1 + inflation_rate) ** total_years
            monthly_income_today = monthly_income / inflation_factor
            monthly_income_today_value.append(monthly_income_today)
            years += 1
            capital_over_time.append(0)  # Capital drops to 0 after withdrawal
            # Pad the income arrays with 0 to match capital_over_time length
            withdrawals_over_time.append(0)
            monthly_income_over_time.append(0)
            monthly_income_today_value.append(0)
            break

        # Calculate the withdrawal at the start of the year (capped at 17.5%)
        max_withdrawal = current_capital * max_drawdown_rate
        withdrawal = min(annual_income, max_withdrawal)
        if years == 0:  # Store the first withdrawal
            first_withdrawal = withdrawal
        
        # Deduct the full annual withdrawal upfront
        current_capital -= withdrawal
        # Apply assumed return to the remaining capital at the end of the year
        current_capital = current_capital * (1 + assumed_return)
        years += 1
        capital_over_time.append(max(0, current_capital))
        withdrawals_over_time.append(withdrawal)
        # Calculate monthly income
        monthly_income = withdrawal / 12
        monthly_income_over_time.append(monthly_income)
        # Adjust monthly income to today's value
        total_years = years_to_retirement + years
        inflation_factor = (1 + inflation_rate) ** total_years
        monthly_income_today = monthly_income / inflation_factor
        monthly_income_today_value.append(monthly_income_today)

    return years, first_withdrawal, capital_over_time, withdrawals_over_time, monthly_income_over_time, monthly_income_today_value

def calculate_additional_savings_needed(shortfall, years_to_retirement, average_return):
    """Calculate additional monthly savings needed to bridge the shortfall using annual compounding."""
    if shortfall <= 0:
        return 0
    annual_rate = average_return
    # Use annual compounding for simplicity
    fv_factor = ((1 + annual_rate) ** years_to_retirement - 1) / annual_rate
    annual_savings = shortfall / fv_factor
    monthly_savings = annual_savings / 12
    return monthly_savings

def calculate_retirement_plan(monthly_income, inflation_rate, annual_increase, years_to_retirement, preserve_capital, preservation_years, assumed_return):
    """Calculate the retirement plan details."""
    annual_income = monthly_income * 12
    # Future value of the annual income needed at retirement, adjusted for inflation and annual increase
    future_annual_income = annual_income * (1 + inflation_rate) ** years_to_retirement * (1 + annual_increase) ** years_to_retirement
    future_monthly_income = future_annual_income / 12

    if preserve_capital:
        # Step 1: For the preservation period, income is drawn from returns only
        if assumed_return <= 0:
            capital_at_retirement = float('inf')
        else:
            # Capital needed to generate the income during preservation
            capital_at_retirement = future_annual_income / assumed_return
            # Check if the withdrawal rate exceeds 17.5%
            withdrawal_rate = future_annual_income / capital_at_retirement
            max_drawdown_rate = 0.175
            if withdrawal_rate > max_drawdown_rate:
                capital_at_retirement = future_annual_income / max_drawdown_rate
                withdrawal_rate = max_drawdown_rate
        
        # Step 2: After preservation, deplete the capital over remaining life expectancy (assume 20 years)
        remaining_years = 20  # From age 75 to 95
        income_after_preservation = future_annual_income * (1 + inflation_rate) ** preservation_years * (1 + annual_increase) ** preservation_years
        # Present value of an annuity to deplete the capital over 20 years
        if assumed_return > 0:
            annuity_factor = (1 - (1 + assumed_return) ** (-remaining_years)) / assumed_return
            capital_required = income_after_preservation * annuity_factor
            # Discount back to retirement age
            capital_required = capital_required / (1 + assumed_return) ** preservation_years
            # Use the higher of the two capital amounts (preservation period or depletion period)
            capital_required = max(capital_at_retirement, capital_required)
        else:
            capital_required = capital_at_retirement

        years_until_depletion = None
        withdrawal_at_retirement = min(future_annual_income, capital_required * max_drawdown_rate)
    else:
        capital_required = None
        years_until_depletion, withdrawal_at_retirement = None, future_annual_income

    return future_annual_income, future_monthly_income, capital_required, years_until_depletion, withdrawal_at_retirement

# Estate Liquidity Tool Functions
def calculate_estate_duty(net_value, has_surviving_spouse, spouse_bequest_value, pbo_bequest_value):
    """Calculate estate duty based on net estate value and deductions."""
    # Apply Section 4q deduction (spouse bequest) and Section 18A (PBO bequest)
    dutiable_value = max(0, net_value - spouse_bequest_value - pbo_bequest_value)
    # Apply R3.5 million abatement
    dutiable_value = max(0, dutiable_value - ESTATE_DUTY_ABATEMENT)
    
    if dutiable_value <= 0:
        return 0
    if dutiable_value <= ESTATE_DUTY_THRESHOLD:
        estate_duty = dutiable_value * ESTATE_DUTY_RATE_1
    else:
        estate_duty = (ESTATE_DUTY_THRESHOLD * ESTATE_DUTY_RATE_1) + ((dutiable_value - ESTATE_DUTY_THRESHOLD) * ESTATE_DUTY_RATE_2)
    
    if has_surviving_spouse:
        # Note that estate duty is deferred until second spouse's death
        return 0
    return estate_duty

def calculate_cgt(assets, marginal_tax_rate):
    """Calculate Capital Gains Tax on assets at death."""
    total_gain = 0
    for asset in assets:
        gain = max(0, asset["market_value"] - asset["base_cost"])
        total_gain += gain
    
    # Apply R300,000 exclusion in year of death
    taxable_gain = max(0, total_gain - CGT_EXCLUSION_DEATH)
    # Apply inclusion rate
    taxable_amount = taxable_gain * CGT_INCLUSION_RATE
    # Apply marginal tax rate
    cgt = taxable_amount * marginal_tax_rate
    return cgt

def calculate_executor_fees(gross_value):
    """Calculate executor's fees based on gross estate value."""
    base_fee = gross_value * EXECUTOR_FEE_RATE
    total_fee = base_fee * (1 + VAT_RATE)  # Add 15% VAT
    return total_fee

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
tool_options = ["Select a Tool", "Budget Tool", "RA Tax Rebate Calculator", "Retirement Calculator", "Salary Tax Calculator", "Estate Liquidity Tool"]
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
                # Export to Excel
                summary_data = {
                    "Client": [name],
                    "Annual Pensionable Income (R)": [income],
                    "RA Contribution (R)": [contribution],
                    "Deductible Contribution (R)": [deductible],
                    "Excess Contribution (Carried Over) (R)": [excess if excess > 0 else 0],
                    "Marginal Tax Rate (%)": [tax_rate * 100],
                    "Tax Rebate (R)": [rebate]
                }
                df = pd.DataFrame(summary_data)
                # Create a buffer to store the Excel file
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="RA Tax Rebate Summary")
                    # Add a note sheet for chart instructions
                    instructions = pd.DataFrame({
                        "Instructions": [
                            "This Excel file contains your RA Tax Rebate Summary.",
                            "There are no charts in this tool, but you can create your own in Excel.",
                            "For example, select your data and use Insert > Chart to visualize your results."
                        ]
                    })
                    instructions.to_excel(writer, index=False, sheet_name="Instructions")
                buffer.seek(0)
                st.download_button(
                    label="Download Summary as Excel",
                    data=buffer,
                    file_name="ra_tax_rebate_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
elif selected_tool == "Salary Tax Calculator":
    st.write("Enter client details to calculate their salary tax, UIF, medical tax credits, and net income.")
    # Input fields
    name = st.text_input("Client's Name", key="tax_calc_name")
    gross_salary = st.number_input("Gross Annual Salary (R)", min_value=0.0, step=1000.0)
    pension_contribution = st.number_input("Annual Pension/RA Contribution (R)", min_value=0.0, step=1000.0)
    medical_contributions = st.number_input("Annual Medical Scheme Contributions (R)", min_value=0.0, step=1000.0)
    num_dependants = st.number_input("Number of Dependants on Medical Scheme (including you)", min_value=0, max_value=10, step=1)
    age = st.number_input("Client's Age", min_value=0, max_value=120, step=1)

    # Calculate button
    if st.button("Calculate Tax"):
        if not name.strip():
            st.error("Please enter a name.")
        elif gross_salary < 0 or pension_contribution < 0 or medical_contributions < 0 or num_dependants < 0 or age < 0:
            st.error("All inputs must be non-negative.")
        else:
            try:
                taxable_income, paye_before_mtc, paye_before_mtc_monthly, mtc_annual, mtc_monthly, paye, paye_monthly, uif, uif_monthly, net_income, net_income_monthly, marginal_rate = calculate_salary_tax(gross_salary, pension_contribution, age, medical_contributions, num_dependants)
                st.success("--- Salary Tax Summary ---")
                st.write(f"**Client**: {name}")
                st.write(f"**Gross Annual Salary**: R {gross_salary:,.2f}")
                st.write(f"**Taxable Income**: R {taxable_income:,.2f}")
                st.write(f"**PAYE (Before Medical Tax Credits, Annual)**: R {paye_before_mtc:,.2f}")
                st.write(f"**PAYE (Before Medical Tax Credits, Monthly)**: R {paye_before_mtc_monthly:,.2f}")
                summary_data = {
                    "Client": [name],
                    "Gross Annual Salary (R)": [gross_salary],
                    "Taxable Income (R)": [taxable_income],
                    "PAYE Before Medical Tax Credits (Annual) (R)": [paye_before_mtc],
                    "PAYE Before Medical Tax Credits (Monthly) (R)": [paye_before_mtc_monthly]
                }
                if num_dependants > 0:
                    st.write(f"**Medical Tax Credits (Annual)**: R {mtc_annual:,.2f}")
                    st.write(f"**Medical Tax Credits (Monthly)**: R {mtc_monthly:,.2f}")
                    # Visual: Progress bar for tax savings
                    tax_savings_percentage = min((mtc_annual / paye_before_mtc) * 100 if paye_before_mtc > 0 else 0, 100)
                    st.write(f"**Tax Savings from Medical Credits**: {tax_savings_percentage:.1f}% of your PAYE")
                    st.progress(tax_savings_percentage / 100)
                    # Note about dependent credits
                    st.markdown(
                        "<p style='font-size: 14px; font-style: italic; color: #CCCCCC;'>Dependent Credits: R364/month for you and your first dependant, R246/month for each additional dependant (e.g., spouse, children, or other family members on your medical scheme).</p>",
                        unsafe_allow_html=True
                    )
                    summary_data["Medical Tax Credits (Annual) (R)"] = [mtc_annual]
                    summary_data["Medical Tax Credits (Monthly) (R)"] = [mtc_monthly]
                    summary_data["Tax Savings from Medical Credits (%)"] = [tax_savings_percentage]
                st.write(f"**PAYE (After Medical Tax Credits, Annual)**: R {paye:,.2f}")
                st.write(f"**PAYE (After Medical Tax Credits, Monthly)**: R {paye_monthly:,.2f}")
                st.write(f"**UIF Contribution (Employee, Annual)**: R {uif:,.2f}")
                st.write(f"**UIF Contribution (Employee, Monthly)**: R {uif_monthly:,.2f}")
                st.write(f"**Net Annual Income**: R {net_income:,.2f}")
                st.write(f"**Net Monthly Income**: R {net_income_monthly:,.2f}")
                st.write(f"**Marginal Tax Rate**: {marginal_rate * 100:.1f}%")
                # Add to summary data
                summary_data["PAYE After Medical Tax Credits (Annual) (R)"] = [paye]
                summary_data["PAYE After Medical Tax Credits (Monthly) (R)"] = [paye_monthly]
                summary_data["UIF Contribution (Employee, Annual) (R)"] = [uif]
                summary_data["UIF Contribution (Employee, Monthly) (R)"] = [uif_monthly]
                summary_data["Net Annual Income (R)"] = [net_income]
                summary_data["Net Monthly Income (R)"] = [net_income_monthly]
                summary_data["Marginal Tax Rate (%)"] = [marginal_rate * 100]
                # Visual: Bar chart for tax breakdown
                st.write("**Tax Breakdown Visualization**")
                chart_data = pd.DataFrame({
                    "Category": ["Gross Income", "PAYE", "UIF", "Medical Tax Credits", "Net Income"],
                    "Amount (R)": [gross_salary, -paye, -uif, -mtc_annual if num_dependants > 0 else 0, net_income]
                })
                st.bar_chart(chart_data.set_index("Category"))
                # Tax rates note with smaller font
                st.markdown(
                    "<p style='font-size: 14px; color: #888888;'>Note: Tax rates, UIF limits, and medical tax credits are based on 2024/2025 SARS tables. Verify with 2025/2026 rates when available.</p>",
                    unsafe_allow_html=True
                )
                # Export to Excel
                summary_df = pd.DataFrame(summary_data)
                chart_df = pd.DataFrame(chart_data).reset_index()
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    summary_df.to_excel(writer, index=False, sheet_name="Salary Tax Summary")
                    chart_df.to_excel(writer, index=False, sheet_name="Chart Data", startrow=0)
                    # Add a note sheet for chart instructions
                    instructions = pd.DataFrame({
                        "Instructions": [
                            "This Excel file contains your Salary Tax Summary and Chart Data.",
                            "To recreate the bar chart in Excel:",
                            "1. Go to the 'Chart Data' sheet.",
                            "2. Select the 'Category' and 'Amount (R)' columns.",
                            "3. Click Insert > Bar Chart in Excel to visualize the tax breakdown.",
                            "Note: The progress bar (Tax Savings %) cannot be exported as it is a dynamic widget."
                        ]
                    })
                    instructions.to_excel(writer, index=False, sheet_name="Instructions")
                buffer.seek(0)
                st.download_button(
                    label="Download Summary as Excel",
                    data=buffer,
                    file_name="salary_tax_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
elif selected_tool == "Budget Tool":
    st.write("Enter your monthly income and expenses to create a budget and see your savings potential.")
    # Input fields
    monthly_income = st.number_input("Monthly Income (R)", min_value=0.0, step=1000.0, value=39500.0)  # Default to ~R39,494 from previous example

    # Dynamic expense inputs using a form
    st.write("**Add Your Monthly Expenses**")
    with st.form(key="expense_form"):
        num_expenses = st.number_input("Number of Expense Categories", min_value=1, max_value=10, step=1, value=3)
        expenses = []
        for i in range(num_expenses):
            col1, col2 = st.columns(2)
            with col1:
                category = st.text_input(f"Expense Category {i+1}", value=f"Category {i+1}", key=f"category_{i}")
            with col2:
                amount = st.number_input(f"Amount (R)", min_value=0.0, step=100.0, key=f"amount_{i}")
            expenses.append((category, amount))
        submit_button = st.form_submit_button("Calculate Budget")

    if submit_button:
        if monthly_income < 0:
            st.error("Monthly income must be non-negative.")
        else:
            try:
                total_expenses, remaining_budget, savings_potential = calculate_budget(monthly_income, expenses)
                st.success("--- Budget Summary ---")
                st.write(f"**Monthly Income**: R {monthly_income:,.2f}")
                st.write("**Expenses Breakdown**:")
                expenses_data = []
                for category, amount in expenses:
                    st.write(f"- {category}: R {amount:,.2f}")
                    expenses_data.append({"Category": category, "Amount (R)": amount})
                st.write(f"**Total Monthly Expenses**: R {total_expenses:,.2f}")
                st.write(f"**Remaining Budget**: R {remaining_budget:,.2f}")
                summary_data = {
                    "Monthly Income (R)": [monthly_income],
                    "Total Monthly Expenses (R)": [total_expenses],
                    "Remaining Budget (R)": [remaining_budget]
                }
                if remaining_budget < 0:
                    st.warning("You're overspending! Consider reducing expenses to avoid debt.")
                else:
                    st.write(f"**Savings Potential**: R {savings_potential:,.2f}")
                    summary_data["Savings Potential (R)"] = [savings_potential]
                # Visual: Bar chart for budget breakdown
                st.write("**Budget Breakdown Visualization**")
                chart_data = pd.DataFrame({
                    "Category": [category for category, amount in expenses] + ["Remaining Budget"],
                    "Amount (R)": [amount for category, amount in expenses] + [max(0, remaining_budget)]
                })
                st.bar_chart(chart_data.set_index("Category"))
                # Export to Excel
                summary_df = pd.DataFrame(summary_data)
                expenses_df = pd.DataFrame(expenses_data)
                chart_df = pd.DataFrame(chart_data).reset_index()
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    summary_df.to_excel(writer, index=False, sheet_name="Budget Summary")
                    expenses_df.to_excel(writer, startrow=len(summary_df) + 2, index=False, sheet_name="Budget Summary")
                    chart_df.to_excel(writer, index=False, sheet_name="Chart Data", startrow=0)
                    # Add a note sheet for chart instructions
                    instructions = pd.DataFrame({
                        "Instructions": [
                            "This Excel file contains your Budget Summary and Chart Data.",
                            "To recreate the bar chart in Excel:",
                            "1. Go to the 'Chart Data' sheet.",
                            "2. Select the 'Category' and 'Amount (R)' columns.",
                            "3. Click Insert > Bar Chart in Excel to visualize the budget breakdown."
                        ]
                    })
                    instructions.to_excel(writer, index=False, sheet_name="Instructions")
                buffer.seek(0)
                st.download_button(
                    label="Download Summary as Excel",
                    data=buffer,
                    file_name="budget_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
elif selected_tool == "Retirement Calculator":
    st.write("Enter client details to calculate the capital needed for retirement.")
    # Input fields
    name = st.text_input("Client's Name", key="retirement_calc_name")
    desired_monthly_income = st.number_input("Desired Monthly Income at Retirement (R)", min_value=0.0, step=1000.0)
    desired_annual_increase = st.number_input("Desired Annual Income Increase (%)", min_value=0.0, max_value=20.0, value=3.0, step=0.5) / 100
    current_age = st.number_input("Current Age", min_value=18, max_value=100, step=1)
    retirement_age = st.selectbox("Retirement Age", [55, 60, 65])
    inflation_rate = st.number_input("Inflation Rate (%)", min_value=0.0, max_value=20.0, value=6.0, step=0.5) / 100
    assumed_return = st.number_input("Assumed Annual Return After Retirement (%)", min_value=0.0, max_value=20.0, value=7.0, step=0.5) / 100
    preserve_capital = st.checkbox("Preserve Capital at Retirement")
    preservation_years = 0
    if preserve_capital:
        preservation_years = st.selectbox("Preservation Period (Years)", [10, 15, 20, 25])

    # Dynamic provision inputs
    st.write("**Add Your Current Provisions**")
    provision_types = [
        "Retirement Annuity", "Pension Fund", "Provident Fund", "Preservation Fund",
        "Business", "Endowment", "Savings Fund", "Shares", "Linked Investment",
        "Property", "Fixed Deposit", "Other"
    ]
    with st.form(key="provision_form"):
        num_provisions = st.number_input("Number of Provisions", min_value=1, max_value=10, step=1, value=1)
        provisions = []
        for i in range(num_provisions):
            st.write(f"**Provision {i+1}**")
            col1, col2 = st.columns(2)
            with col1:
                provision_type = st.selectbox(f"Provision Type {i+1}", provision_types, key=f"prov_type_{i}")
                current_value = st.number_input(f"Current Value (R)", min_value=0.0, step=1000.0, key=f"prov_value_{i}")
            with col2:
                annual_return = st.number_input(f"Assumed Annual Return (%)", min_value=0.0, max_value=20.0, value=7.0, step=0.5, key=f"prov_return_{i}") / 100
                monthly_contribution = st.number_input(f"Monthly Contribution (R)", min_value=0.0, step=100.0, key=f"prov_contrib_{i}")
            col3, col4 = st.columns(2)
            with col3:
                contribution_increase = st.number_input(f"Annual Contribution Increase (%)", min_value=0.0, max_value=20.0, value=5.0, step=0.5, key=f"prov_increase_{i}") / 100
            provisions.append({
                "type": provision_type,
                "current_value": current_value,
                "annual_return": annual_return,
                "monthly_contribution": monthly_contribution,
                "contribution_increase": contribution_increase
            })
        submit_button = st.form_submit_button("Calculate Retirement Plan")

    if submit_button:
        if not name.strip():
            st.error("Please enter a name.")
        elif desired_monthly_income <= 0 or current_age < 18 or current_age >= retirement_age:
            st.error("Please ensure desired income is positive and current age is valid (18 or older, less than retirement age).")
        else:
            try:
                years_to_retirement = retirement_age - current_age
                # Step 1: Calculate future income needed
                future_annual_income, future_monthly_income, capital_required, years_until_depletion, withdrawal_at_retirement = calculate_retirement_plan(
                    desired_monthly_income, inflation_rate, desired_annual_increase, years_to_retirement, preserve_capital, preservation_years, assumed_return
                )
                # Step 2: Calculate future value of current provisions
                total_provision_value = 0
                provisions_data = []
                average_return = 0
                total_weight = 0
                for provision in provisions:
                    fv = calculate_future_value(
                        provision["current_value"],
                        provision["annual_return"],
                        years_to_retirement,
                        provision["monthly_contribution"],
                        provision["contribution_increase"]
                    )
                    total_provision_value += fv
                    provisions_data.append({
                        "Type": provision["type"],
                        "Current Value (R)": provision["current_value"],
                        "Annual Return (%)": provision["annual_return"] * 100,
                        "Monthly Contribution (R)": provision["monthly_contribution"],
                        "Annual Contribution Increase (%)": provision["contribution_increase"] * 100,
                        "Future Value at Retirement (R)": fv
                    })
                    # Weighted average return for additional savings calculation
                    weight = provision["current_value"] + (provision["monthly_contribution"] * 12 * years_to_retirement)
                    average_return += provision["annual_return"] * weight
                    total_weight += weight
                if total_weight > 0:
                    average_return /= total_weight

                # Step 3: Calculate shortfall or excess
                summary_data = {
                    "Client": [name],
                    "Current Age": [current_age],
                    "Retirement Age": [retirement_age],
                    "Years to Retirement": [years_to_retirement],
                    "Desired Monthly Income at Retirement (R)": [desired_monthly_income],
                    "Future Annual Income Needed (R)": [future_annual_income],
                    "Future Monthly Income Needed (R)": [future_monthly_income]
                }
                st.success("--- Retirement Plan Summary ---")
                st.write(f"**Client**: {name}")
                st.write(f"**Current Age**: {current_age}")
                st.write(f"**Retirement Age**: {retirement_age}")
                st.write(f"**Years to Retirement**: {years_to_retirement}")
                st.write(f"**Desired Monthly Income at Retirement (Today's Value)**: R {desired_monthly_income:,.2f}")
                st.write(f"**Future Annual Income Needed (Inflation Adjusted)**: R {future_annual_income:,.2f}")
                st.write(f"**Future Monthly Income Needed (Inflation Adjusted)**: R {future_monthly_income:,.2f}")

                # Display provisions
                st.write("**Provisions at Retirement**:")
                provisions_df = pd.DataFrame(provisions_data)
                st.write(provisions_df)
                st.write(f"**Total Future Value of Provisions**: R {total_provision_value:,.2f}")
                summary_data["Total Future Value of Provisions (R)"] = [total_provision_value]

                if preserve_capital:
                    shortfall = capital_required - total_provision_value
                    st.write(f"**Capital Required at Retirement (Preserve Capital)**: R {capital_required:,.2f}")
                    summary_data["Capital Required at Retirement (R)"] = [capital_required]
                    summary_data["Preserve Capital"] = ["Yes"]
                    summary_data["Preservation Period (Years)"] = [preservation_years]
                    st.write(f"**Initial Withdrawal at Retirement (Annual)**: R {withdrawal_at_retirement:,.2f}")
                    st.write(f"**Initial Withdrawal at Retirement (Monthly)**: R {(withdrawal_at_retirement / 12):,.2f}")
                    summary_data["Initial Withdrawal at Retirement (Annual) (R)"] = [withdrawal_at_retirement]
                    summary_data["Initial Withdrawal at Retirement (Monthly) (R)"] = [withdrawal_at_retirement / 12]
                else:
                    # Calculate how long the capital will last
                    years_until_depletion, first_withdrawal, capital_over_time, withdrawals_over_time, monthly_income_over_time, monthly_income_today_value = calculate_years_until_depletion(
                        total_provision_value, future_annual_income, inflation_rate, years_to_retirement, assumed_return
                    )
                    st.write(f"**Capital at Retirement (Based on Provisions)**: R {total_provision_value:,.2f}")
                    st.write(f"**Years Until Capital Depletion**: {years_until_depletion}")
                    st.write(f"**Initial Withdrawal at Retirement (Annual)**: R {first_withdrawal:,.2f}")
                    st.write(f"**Initial Withdrawal at Retirement (Monthly)**: R {(first_withdrawal / 12):,.2f}")
                    summary_data["Capital at Retirement (R)"] = [total_provision_value]
                    summary_data["Years Until Capital Depletion"] = [years_until_depletion]
                    summary_data["Initial Withdrawal at Retirement (Annual) (R)"] = [first_withdrawal]
                    summary_data["Initial Withdrawal at Retirement (Monthly) (R)"] = [first_withdrawal / 12]
                    summary_data["Preserve Capital"] = ["No"]
                    summary_data["Preservation Period (Years)"] = [0]
                    # Visual: Line chart for capital depletion
                    st.write("**Capital Depletion Over Time**")
                    chart_data = pd.DataFrame({
                        "Year": list(range(years_to_retirement, years_to_retirement + len(capital_over_time))),
                        "Capital (R)": capital_over_time,
                        "Annual Withdrawal (R)": withdrawals_over_time,
                        "Monthly Income (R)": monthly_income_over_time,
                        "Monthly Income in Today's Value (R)": monthly_income_today_value
                    })
                    st.line_chart(chart_data.set_index("Year")[["Capital (R)", "Annual Withdrawal (R)", "Monthly Income (R)", "Monthly Income in Today's Value (R)"]])

                # Step 4: Calculate additional savings needed
                if preserve_capital and shortfall > 0:
                    additional_savings = calculate_additional_savings_needed(shortfall, years_to_retirement, average_return)
                    st.warning(f"**Capital Shortfall**: R {shortfall:,.2f}")
                    st.write(f"**Additional Monthly Savings Needed**: R {additional_savings:,.2f}")
                    summary_data["Capital Shortfall (R)"] = [shortfall]
                    summary_data["Additional Monthly Savings Needed (R)"] = [additional_savings]
                elif preserve_capital and shortfall <= 0:
                    st.write(f"**Capital Excess**: R {-shortfall:,.2f}")
                    summary_data["Capital Excess (R)"] = [-shortfall]
                    summary_data["Capital Shortfall (R)"] = [0]
                    summary_data["Additional Monthly Savings Needed (R)"] = [0]

                # Export to Excel
                summary_df = pd.DataFrame(summary_data)
                chart_df = pd.DataFrame(chart_data).reset_index() if not preserve_capital else pd.DataFrame()
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    summary_df.to_excel(writer, index=False, sheet_name="Retirement Plan Summary")
                    provisions_df.to_excel(writer, startrow=len(summary_df) + 2, index=False, sheet_name="Retirement Plan Summary")
                    if not preserve_capital:
                        chart_df.to_excel(writer, index=False, sheet_name="Chart Data", startrow=0)
                    # Add a note sheet for chart instructions
                    instructions = pd.DataFrame({
                        "Instructions": [
                            "This Excel file contains your Retirement Plan Summary and Provisions Data.",
                            "If you did not opt to preserve capital, the 'Chart Data' sheet includes data for visualizing capital depletion over time.",
                            "To recreate the line chart in Excel (if applicable):",
                            "1. Go to the 'Chart Data' sheet.",
                            "2. Select the 'Year' and 'Capital (R)' columns (or other metrics).",
                            "3. Click Insert > Line Chart in Excel to visualize the depletion."
                        ]
                    })
                    instructions.to_excel(writer, index=False, sheet_name="Instructions")
                buffer.seek(0)
                st.download_button(
                    label="Download Summary as Excel",
                    data=buffer,
                    file_name="retirement_plan_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
elif selected_tool == "Estate Liquidity Tool":
    st.write("Enter details to assess your estate's liquidity and ensure your beneficiaries are protected.")
    # Note about estate duty rates
    st.markdown(
        "<p style='font-size: 14px; font-style: italic; color: #CCCCCC;'>Note: Estate duty rates are based on 2025 South African laws: R3.5M abatement, 20% up to R30M, 25% above R30M. Verify with a tax professional for your specific case.</p>",
        unsafe_allow_html=True
    )

    # Input fields
    name = st.text_input("Client's Name", key="estate_name")
    
    # Personal Details
    marital_status = st.selectbox("Marital Status", ["Single", "Married in Community of Property", "Married Out of Community (No Accrual)", "Married Out of Community (With Accrual)"])
    has_surviving_spouse = st.checkbox("Is there a surviving spouse?", value=False)

    # Assets
    st.write("**Liquid Assets**")
    cash = st.number_input("Cash in Bank/Savings (R)", min_value=0.0, step=1000.0)
    life_insurance_to_estate = st.number_input("Life Insurance Payable to Estate (R)", min_value=0.0, step=1000.0)

    st.write("**Non-Liquid Assets**")
    num_properties = st.number_input("Number of Properties", min_value=0, max_value=10, step=1, value=0)
    properties = []
    for i in range(num_properties):
        st.write(f"**Property {i+1}**")
        market_value = st.number_input(f"Market Value of Property {i+1} (R)", min_value=0.0, step=1000.0, key=f"prop_value_{i}")
        properties.append(market_value)

    num_investments = st.number_input("Number of Investments (e.g., Shares, Bonds)", min_value=0, max_value=10, step=1, value=0)
    investments = []
    for i in range(num_investments):
        st.write(f"**Investment {i+1}**")
        market_value = st.number_input(f"Market Value of Investment {i+1} (R)", min_value=0.0, step=1000.0, key=f"inv_value_{i}")
        base_cost = st.number_input(f"Base Cost of Investment {i+1} (R)", min_value=0.0, step=1000.0, key=f"inv_base_{i}")
        investments.append({"market_value": market_value, "base_cost": base_cost})

    other_assets = st.number_input("Other Non-Liquid Assets (e.g., Vehicles, Jewelry) (R)", min_value=0.0, step=1000.0)

    # Liabilities
    st.write("**Liabilities**")
    debts = st.number_input("Outstanding Debts (e.g., Loans, Bonds) (R)", min_value=0.0, step=1000.0)
    medical_bills = st.number_input("Medical Bills or Pre-Death Expenses (R)", min_value=0.0, step=1000.0)

    # Will Details
    st.write("**Will Details**")
    cash_bequests = st.number_input("Cash Bequests to Beneficiaries (R)", min_value=0.0, step=1000.0)
    spouse_bequest_value = st.number_input("Bequests to Surviving Spouse (R)", min_value=0.0, step=1000.0, disabled=not has_surviving_spouse)
    pbo_bequest_value = st.number_input("Bequests to Public Benefit Organizations (R)", min_value=0.0, step=1000.0)

    # Assumptions
    st.write("**Assumptions**")
    marginal_tax_rate = st.number_input("Marginal Tax Rate for CGT (e.g., 0.45 for 45%)", min_value=0.0, max_value=0.45, value=0.45, step=0.01)

    # Calculate button
    if st.button("Calculate Estate Liquidity"):
        if not name.strip():
            st.error("Please enter a name.")
        elif cash < 0 or life_insurance_to_estate < 0 or any(p < 0 for p in properties) or any(i["market_value"] < 0 or i["base_cost"] < 0 for i in investments) or other_assets < 0 or debts < 0 or medical_bills < 0 or cash_bequests < 0 or spouse_bequest_value < 0 or pbo_bequest_value < 0 or marginal_tax_rate < 0 or marginal_tax_rate > 0.45:
            st.error("All financial inputs must be non-negative, and marginal tax rate must be between 0 and 45%.")
        else:
            try:
                # Calculate Gross Estate Value
                gross_estate = cash + life_insurance_to_estate + sum(properties) + sum(i["market_value"] for i in investments) + other_assets

                # Calculate Net Estate Value
                net_estate = gross_estate - debts - medical_bills - cash_bequests

                # Calculate Capital Gains Tax
                cgt = calculate_cgt(investments, marginal_tax_rate)

                # Calculate Estate Duty
                estate_duty = calculate_estate_duty(net_estate, has_surviving_spouse, spouse_bequest_value, pbo_bequest_value)

                # Calculate Executor Fees
                executor_fees = calculate_executor_fees(gross_estate)

                # Calculate Total Costs
                total_costs = cgt + estate_duty + executor_fees

                # Calculate Liquid Assets Available
                liquid_assets = cash + life_insurance_to_estate

                # Assess Liquidity
                liquidity_shortfall = max(0, total_costs - liquid_assets)

                st.success("--- Estate Liquidity Summary ---")
                st.write(f"**Client**: {name}")
                st.write(f"**Gross Estate Value**: R {gross_estate:,.2f}")
                st.write(f"**Net Estate Value (after debts, medical bills, and cash bequests)**: R {net_estate:,.2f}")
                st.write(f"**Capital Gains Tax**: R {cgt:,.2f}")
                st.write(f"**Estate Duty**: R {estate_duty:,.2f}")
                st.write(f"**Executor Fees (incl. VAT)**: R {executor_fees:,.2f}")
                st.write(f"**Total Costs**: R {total_costs:,.2f}")
                st.write(f"**Liquid Assets Available**: R {liquid_assets:,.2f}")
                if liquidity_shortfall > 0:
                    st.warning(f"**Liquidity Shortfall**: R {liquidity_shortfall:,.2f}")
                    st.write("**Recommendation**: Consider increasing life insurance payable to the estate or liquidating non-liquid assets to cover the shortfall.")
                else:
                    st.write("**Liquidity Status**: Sufficient liquid assets to cover costs.")

                # Export to Excel
                summary_data = {
                    "Client": [name],
                    "Gross Estate Value (R)": [gross_estate],
                    "Net Estate Value (R)": [net_estate],
                    "Capital Gains Tax (R)": [cgt],
                    "Estate Duty (R)": [estate_duty],
                    "Executor Fees (R)": [executor_fees],
                    "Total Costs (R)": [total_costs],
                    "Liquid Assets Available (R)": [liquid_assets],
                    "Liquidity Shortfall (R)": [liquidity_shortfall if liquidity_shortfall > 0 else 0]
                }
                summary_df = pd.DataFrame(summary_data)
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    summary_df.to_excel(writer, index=False, sheet_name="Estate Liquidity Summary")
                    # Add a note sheet for instructions
                    instructions = pd.DataFrame({
                        "Instructions": [
                            "This Excel file contains your Estate Liquidity Summary.",
                            "There are no charts in this tool, but you can create your own in Excel.",
                            "For example, select your data and use Insert > Chart to visualize your results."
                        ]
                    })
                    instructions.to_excel(writer, index=False, sheet_name="Instructions")
                buffer.seek(0)
                st.download_button(
                    label="Download Summary as Excel",
                    data=buffer,
                    file_name="estate_liquidity_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            except Exception as e:
                st.error(f"Error: {e}")
