import streamlit as st

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
    """Calculate the tax rebate for RA contributions."""
    max_deductible = min(income * 0.275, 350000)
    deductible = min(contribution, max_deductible)
    tax_rate = get_tax_rate(income)
    rebate = deductible * tax_rate
    return deductible, tax_rate, rebate

# Streamlit interface
st.title("South Africa RA Tax Rebate Calculator")
st.write("Enter client details to calculate their tax rebate for retirement annuity contributions.")

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
            deductible, tax_rate, rebate = calculate_ra_rebate(income, contribution)
            st.success("--- Tax Rebate Summary ---")
            st.write(f"**Client**: {name}")
            st.write(f"**Annual Pensionable Income**: R {income:,.2f}")
            st.write(f"**RA Contribution**: R {contribution:,.2f}")
            st.write(f"**Deductible Contribution**: R {deductible:,.2f}")
            st.write(f"**Marginal Tax Rate**: {tax_rate * 100:.1f}%")
            st.write(f"**Tax Rebate**: R {rebate:,.2f}")
            st.info("Note: Tax rates are based on 2024/2025 SARS tables. Verify with 2025/2026 rates when available.")
        except Exception as e:
            st.error(f"Error: {e}")