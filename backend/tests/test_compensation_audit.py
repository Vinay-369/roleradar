"""
Comprehensive Regression Tests for Compensation & Stipend Audit & Normalization.

Validates:
1. Numeric LPA ranges (e.g. ₹8–12 LPA, 6 to 9 LPA)
2. Numeric INR full ranges (e.g. INR 600,000 to 1,000,000)
3. Numeric single LPA (e.g. 10 LPA)
4. Numeric monthly stipends (e.g. ₹25,000/month)
5. Qualitative compensation phrases (e.g. "Best in industry salary", "competitive compensation")
6. Internship distinction (numeric stipend, qualitative paid/unpaid, undisclosed)
7. Strict false-positive safeguards:
   - Project budgets
   - Customer/client salaries
   - Contract values / deal sizes
   - Equipment budgets
   - Company sales / revenues
   - Loan offerings (Cred pattern)
   - Experience bounds (years of experience)
8. Provider structured payload extraction (Lever salaryRange, Greenhouse pay)
9. JobOut serialization & route strip metadata attachment
"""
import pytest
from app.modules.jobs.compensation_extractor import (
    extract_compensation_from_payload_and_text,
    CompensationDetails,
)
from app.modules.jobs.schemas import JobOut
from app.modules.jobs.routes import _strip_for_detail, _strip_for_list


class TestNumericCompensationExtraction:
    def test_usd_annual_range_preserves_currency_amount_and_period(self):
        comp = extract_compensation_from_payload_and_text(
            "Compensation range: $231,000 - $340,000 USD/year."
        )
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 231000
        assert comp.salary_max == 340000
        assert comp.salary_currency == "USD"
        assert comp.salary_period == "YEAR"
        assert comp.compensation_text == "$231,000–$340,000 /year"

    def test_lpa_range_hyphen(self):
        text = "Role: Backend Developer. Compensation: ₹8–12 LPA based on skills."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_disclosed is True
        assert comp.salary_min == 8.0
        assert comp.salary_max == 12.0
        assert comp.compensation_text == "₹8–12 LPA"

    def test_lpa_range_ascii_dash(self):
        text = "Expected salary: INR 6 - 9.5 LPA."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 6.0
        assert comp.salary_max == 9.5

    def test_lpa_range_to_word(self):
        text = "We offer 10 to 15 lakhs per annum for senior engineers."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 10.0
        assert comp.salary_max == 15.0

    def test_inr_full_number_range(self):
        text = "Remuneration: ₹600,000 - ₹1,200,000 annually."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 600000
        assert comp.salary_max == 1200000
        assert comp.salary_currency == "INR"
        assert comp.salary_period == "YEAR"
        assert comp.compensation_text == "₹600,000–₹1,200,000 /year"

    def test_single_lpa(self):
        text = "Annual CTC: ₹14 LPA fixed."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 14.0
        assert comp.salary_max is None
        assert comp.compensation_text == "₹14 LPA"

    def test_single_lakhs_with_salary_keyword(self):
        text = "Fixed salary of 12 Lakhs with performance bonus."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 12.0
        assert comp.compensation_text == "₹12 lakh"


class TestNumericStipendExtraction:
    def test_monthly_stipend_range_preserves_currency_and_period(self):
        comp = extract_compensation_from_payload_and_text(
            "Internship stipend: ₹20,000 - ₹25,000 per month.", is_internship=True
        )
        assert comp.compensation_type == "STIPEND"
        assert comp.salary_min is None
        assert comp.stipend_min == 20000
        assert comp.stipend_max == 25000
        assert comp.stipend_currency == "INR"
        assert comp.stipend_period == "MONTH"

    def test_monthly_salary_is_not_reclassified_as_stipend(self):
        comp = extract_compensation_from_payload_and_text(
            "Salary: $3,000 per month.", is_internship=True
        )
        assert comp.compensation_type == "SALARY"
        assert comp.salary_min == 3000
        assert comp.salary_currency == "USD"
        assert comp.salary_period == "MONTH"
        assert comp.stipend_min is None

    def test_monthly_stipend_rupees(self):
        text = "Full Stack Internship. Stipend: ₹25,000/month. Duration: 6 months."
        comp = extract_compensation_from_payload_and_text(text, is_internship=True)
        assert comp.compensation_type == "STIPEND"
        assert comp.salary_disclosed is True
        assert comp.stipend_min == 25000.0
        assert comp.compensation_text == "₹25,000 /month"

    def test_monthly_stipend_pm(self):
        text = "Software Engineer Intern. Monthly stipend of ₹15,000 pm."
        comp = extract_compensation_from_payload_and_text(text, is_internship=True)
        assert comp.compensation_type == "STIPEND"
        assert comp.stipend_min == 15000.0


class TestQualitativeCompensationRecognition:
    def test_best_in_industry_salary(self):
        text = "Blueberry Labs is hiring! Qualifications: Python, Django. Best in industry salary."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.salary_disclosed is True
        assert comp.compensation_text == "Best in industry salary"

    def test_competitive_compensation(self):
        text = "We offer competitive compensation, health insurance, and flexible hours."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.salary_disclosed is True
        assert comp.compensation_text == "Competitive compensation disclosed by employer"

    def test_attractive_package(self):
        text = "Attractive remuneration package for the right candidate."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.salary_disclosed is True

    def test_commensurate_with_experience(self):
        text = "Salary commensurate with experience and market standards."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.compensation_text == "Compensation commensurate with experience"


class TestInternshipDistinction:
    def test_paid_internship_statement(self):
        text = "This is a paid internship opportunity for engineering students."
        comp = extract_compensation_from_payload_and_text(text, is_internship=True)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.compensation_text == "Paid internship"

    def test_unpaid_internship_statement(self):
        text = "This is an unpaid internship intended for academic credits."
        comp = extract_compensation_from_payload_and_text(text, is_internship=True)
        assert comp.compensation_type == "QUALITATIVE"
        assert comp.compensation_text == "Unpaid internship"

    def test_undisclosed_internship(self):
        text = "Software intern required to build features. Requires React and Python."
        comp = extract_compensation_from_payload_and_text(text, is_internship=True)
        assert comp.compensation_type == "UNDISCLOSED"
        assert comp.compensation_text is None
        assert comp.salary_disclosed is False


class TestFalsePositiveSafeguards:
    def test_cred_loan_offerings(self):
        text = (
            "We are a digital lending platform that makes credit accessible to millions across India. "
            "With loan offerings ranging from ₹50,000 to ₹5 Lakh, we're enabling instant personal loans "
            "and flexible pay-later credit lines."
        )
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"
        assert comp.salary_disclosed is False
        assert comp.salary_min is None

    def test_bosch_sales_revenue(self):
        text = (
            "Bosch in India recorded sales of ₹12,000 crores in the last financial year. "
            "We are seeking an experienced Embedded Software Engineer."
        )
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"
        assert comp.salary_disclosed is False

    def test_project_budget(self):
        text = "Responsible for managing project budget of 50 Lakhs and client deliveries."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"
        assert comp.salary_min is None

    def test_equipment_budget(self):
        text = "Oversee lab operations with an equipment budget of ₹20 Lakhs."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"

    def test_contract_value(self):
        text = "Experience negotiating deal sizes and contract value of ₹30 Lakhs."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"

    def test_customer_salaries(self):
        text = "Our software handles processing payroll for client salaries across 500 enterprises."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"

    def test_experience_years_not_salary(self):
        text = "Required Qualifications: 3-5 years of experience in distributed systems."
        comp = extract_compensation_from_payload_and_text(text)
        assert comp.compensation_type == "UNDISCLOSED"


class TestStructuredProviderPayloads:
    def test_lever_structured_salary_range(self):
        raw_payload = {
            "salaryRange": {
                "min": 1200000,
                "max": 1800000,
                "currency": "INR",
                "interval": "per-year-salary"
            }
        }
        comp = extract_compensation_from_payload_and_text("", raw_payload=raw_payload)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_disclosed is True
        assert comp.salary_min == 1200000
        assert comp.salary_max == 1800000
        assert comp.salary_currency == "INR"
        assert comp.salary_period == "YEAR"
        assert comp.compensation_text == "₹1,200,000–₹1,800,000 /year"

    def test_greenhouse_structured_pay(self):
        raw_payload = {
            "pay": {
                "min_value": 800000,
                "max_value": 1400000,
                "unit": "per_year"
            }
        }
        comp = extract_compensation_from_payload_and_text("", raw_payload=raw_payload)
        assert comp.compensation_type == "SALARY"
        assert comp.salary_disclosed is True
        assert comp.salary_min == 800000
        assert comp.salary_max == 1400000
        assert comp.salary_currency is None
        assert comp.salary_period == "YEAR"

    def test_ashby_stipend_component_is_not_salary(self):
        comp = extract_compensation_from_payload_and_text(
            raw_payload={"compensation": {"summaryComponents": [{
                "compensationType": "Stipend",
                "interval": "1 MONTH",
                "currencyCode": "INR",
                "minValue": 20000,
                "maxValue": 25000,
            }]}}
        )
        assert comp.compensation_type == "STIPEND"
        assert comp.salary_min is None
        assert comp.stipend_min == 20000
        assert comp.stipend_max == 25000
        assert comp.stipend_currency == "INR"
        assert comp.stipend_period == "MONTH"

    def test_dummy_zero_range_treated_as_undisclosed(self):
        raw_payload = {
            "salaryRange": {"min": 0, "max": 0, "currency": "INR"}
        }
        comp = extract_compensation_from_payload_and_text("Software Engineer role.", raw_payload=raw_payload)
        assert comp.compensation_type == "UNDISCLOSED"
        assert comp.salary_disclosed is False


class TestRouteSerializationAndStrip:
    def test_route_strip_recovers_explicit_salary_from_undisclosed_legacy_record(self):
        job = {
            "id": "gh_example_123",
            "source": "greenhouse",
            "title": "Backend Engineer",
            "company": "Example Co",
            "description": "Compensation: ₹12–18 LPA based on experience.",
            "location": "Bengaluru, India",
            "job_type": "full_time",
            "compensation_type": "UNDISCLOSED",
            "compensation_text": None,
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
        }

        job_out = JobOut(**_strip_for_detail(job))

        assert job_out.compensation_type == "SALARY"
        assert job_out.compensation_text == "₹12–18 LPA"
        assert job_out.salary_min == 12
        assert job_out.salary_max == 18
        assert job_out.salary_disclosed is True

    def test_route_strip_attaches_qualitative_compensation(self):
        job = {
            "id": "sr_blueberry_123",
            "source": "smartrecruiters",
            "title": "Full Stack Developer",
            "company": "Blueberry Labs",
            "industry": "Technology",
            "description": "Python, React developer needed. Best in industry salary.",
            "location": "Hyderabad, India",
            "is_remote": False,
            "job_type": "full_time",
            "skills_required": ["Python", "React"],
            "skills_nice_to_have": [],
            "apply_url": "https://careers.smartrecruiters.com/BlueberryLabs/123",
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
            "stipend_min": None,
            "internship_duration_months": None,
            "fresher_friendly": False,
        }
        detail_data = _strip_for_detail(job)
        job_out = JobOut(**detail_data)
        assert job_out.compensation_type == "QUALITATIVE"
        assert job_out.compensation_text == "Best in industry salary"
        assert job_out.salary_disclosed is True

    def test_route_strip_preserves_undisclosed_truthfully(self):
        job = {
            "id": "sr_bosch_456",
            "source": "smartrecruiters",
            "title": "Embedded Engineer",
            "company": "Bosch",
            "industry": "Automotive",
            "description": "Develop microcontrollers in C/C++. Good teamwork skills.",
            "location": "Bengaluru, India",
            "is_remote": False,
            "job_type": "full_time",
            "skills_required": ["C", "C++"],
            "skills_nice_to_have": [],
            "apply_url": "https://careers.smartrecruiters.com/Bosch/456",
            "salary_min": None,
            "salary_max": None,
            "salary_disclosed": False,
            "stipend_min": None,
            "internship_duration_months": None,
            "fresher_friendly": False,
        }
        detail_data = _strip_for_detail(job)
        job_out = JobOut(**detail_data)
        assert job_out.compensation_type == "UNDISCLOSED"
        assert job_out.compensation_text is None
        assert job_out.salary_disclosed is False
