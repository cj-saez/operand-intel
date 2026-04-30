import fitz, os

OUT_DIR = os.path.join(os.path.dirname(__file__), 'sample_ppms')
os.makedirs(OUT_DIR, exist_ok=True)

DARK_TITLE = (0.08, 0.08, 0.15)  # near-black
BLUE = (0.23, 0.51, 0.96)
GRAY = (0.4, 0.4, 0.45)
TEXT = (0.15, 0.15, 0.2)


def wrap_text(text, max_chars=90):
    """Simple word wrap."""
    words = text.split()
    lines, line = [], []
    for w in words:
        if sum(len(x)+1 for x in line) + len(w) > max_chars:
            lines.append(' '.join(line))
            line = [w]
        else:
            line.append(w)
    if line:
        lines.append(' '.join(line))
    return lines


def create_ppm(filename, fund_name, searcher_name, capital_target, sections):
    doc = fitz.open()

    # Cover page
    page = doc.new_page(width=612, height=792)
    # Header bar
    page.draw_rect(fitz.Rect(0, 0, 612, 120), color=DARK_TITLE, fill=DARK_TITLE)
    page.insert_text((54, 55), "PRIVATE PLACEMENT MEMORANDUM", fontname="helv", fontsize=11, color=(0.6, 0.6, 0.7))
    page.insert_text((54, 80), fund_name, fontname="helv", fontsize=22, color=(1, 1, 1))
    page.insert_text((54, 105), searcher_name, fontname="helv", fontsize=13, color=(0.7, 0.7, 0.8))

    y = 160
    page.insert_text((54, y), "Capital Target", fontname="helv", fontsize=10, color=GRAY)
    page.insert_text((54, y+18), capital_target, fontname="helv", fontsize=16, color=TEXT)

    page.insert_text((54, y+60), "Date of Issue", fontname="helv", fontsize=10, color=GRAY)
    page.insert_text((54, y+78), "April 2026", fontname="helv", fontsize=12, color=TEXT)

    page.insert_text((54, y+120), "CONFIDENTIAL — For Authorized Investors Only", fontname="helv", fontsize=10, color=GRAY)

    # Disclaimer
    disc = ("This Private Placement Memorandum is confidential and has been prepared solely for "
            "informational purposes in connection with the proposed offering described herein. "
            "This memorandum does not constitute an offer to sell or a solicitation of an offer "
            "to buy any security.")
    y = 350
    for line in wrap_text(disc, 85):
        page.insert_text((54, y), line, fontname="helv", fontsize=9, color=GRAY)
        y += 14

    # Content pages
    for section_title, paragraphs in sections:
        page = doc.new_page(width=612, height=792)
        # Section header
        page.draw_rect(fitz.Rect(0, 0, 612, 60), color=DARK_TITLE, fill=DARK_TITLE)
        page.insert_text((54, 38), section_title.upper(), fontname="helv", fontsize=14, color=(1, 1, 1))

        y = 90
        for para_title, para_text in paragraphs:
            if para_title:
                page.insert_text((54, y), para_title, fontname="helv", fontsize=12, color=BLUE)
                y += 20
            for line in wrap_text(para_text, 88):
                page.insert_text((54, y), line, fontname="helv", fontsize=10, color=TEXT)
                y += 15
            y += 10
            if y > 720:
                page = doc.new_page(width=612, height=792)
                y = 60

    out = os.path.join(OUT_DIR, filename)
    doc.save(out)
    print(f"Created: {out}")
    doc.close()


# ── PPM 1: FND Partners LLC (Claudia Leon) ────────────────────────────────────
create_ppm("FND_Partners_PPM.pdf", "FND Partners LLC", "Claudia (Clau) Leon",
    "$627,000 (100 Units @ $6,270)",
    [
        ("Executive Summary", [
            ("Fund Overview", "FND Partners LLC is a self-funded search fund formed by Claudia Leon to acquire and operate a single privately held business. The fund is targeting a capital raise of $627,000 across 100 units at $6,270 per unit. Claudia brings a unique combination of engineering operations, private equity deal experience, and an MBA from Harvard Business School."),
            ("Investment Thesis", "The fund targets niche industrial services, environmental testing, and municipal compliance services companies with $2M-$10M EBITDA in the United States. These businesses exhibit recurring revenue, high barriers to entry due to regulatory requirements, and strong free cash flow characteristics that reward operational improvement."),
            ("Target Return", "Searcher targets a minimum 3.0x gross MOIC and 25% gross IRR over a 5-7 year hold period, consistent with upper-quartile search fund returns."),
        ]),
        ("Searcher Background", [
            ("Education", "Claudia Leon holds an MBA from Harvard Business School (Class of 2025), an MS in Engineering from Georgia Tech, and a BS in Engineering from Rice University. She completed the HBS ETA course and a search fund internship during her MBA."),
            ("Professional Experience", "Prior to HBS, Claudia worked at Baker Hughes in operational engineering roles for 4 years, managing field service teams across the Gulf Coast. She subsequently joined a lower-middle-market private equity firm as a deal professional, where she led two platform acquisitions in industrial services totaling $85M in enterprise value."),
            ("Personal Background", "Claudia is a first-generation college graduate of Cuban descent, raised in Miami, FL. She is fluent in Spanish and English. Her operational and deal background is uniquely suited to the industrial services sector she is targeting."),
        ]),
        ("Investment Criteria", [
            ("Target Sectors", "Primary: Industrial services with regulatory compliance components (environmental testing, municipal water/air quality, NDT inspection, calibration services). Secondary: Facilities services with long-term government or institutional contracts."),
            ("Geography", "Continental United States, with a preference for the Southeast and Gulf Coast where Claudia has existing relationships and operational familiarity."),
            ("Business Characteristics", "Revenue of $5M-$25M, EBITDA margins of 15%-30%, recurring contract revenue of at least 60%, limited customer concentration (no single customer >25%), established team of 20+ employees, owner ready to transition."),
            ("Acquisition Price", "Target TEV of $10M-$40M at 4x-7x EBITDA. Expects to use SBA 7(a) or conventional senior debt plus search fund equity to fund the acquisition."),
        ]),
        ("Fund Terms", [
            ("Structure", "FND Partners LLC is organized as a Delaware limited liability company. Claudia Leon serves as the sole managing member and will act as CEO post-acquisition."),
            ("Search Capital", "Total search capital: $627,000 across 100 units at $6,270 per unit. Search capital will be used for 24 months of operating expenses including salary, travel, deal costs, and professional services."),
            ("Acquisition Rights", "Search fund investors receive the right to participate in the acquisition financing on a pro-rata basis. Step-up: 1.5x on search capital converted to equity at acquisition."),
            ("Carry & Preferred Return", "20% carried interest above an 8% preferred return. Carry vests over 4 years post-acquisition with a 1-year cliff."),
        ]),
        ("Risk Factors", [
            ("Key Person Risk", "As a solo searcher, the fund is dependent on Claudia Leon. Illness, incapacity, or departure would materially impact the fund's ability to execute."),
            ("Search Risk", "There is no guarantee that a suitable acquisition target will be identified within the 24-month search period. If no acquisition is made, search capital may be partially or fully lost."),
            ("Acquisition Financing Risk", "Availability and terms of senior debt are subject to market conditions at the time of acquisition. Deterioration in credit markets could reduce leverage or increase cost of capital."),
            ("Operational Risk", "Post-acquisition, the fund is reliant on Claudia's ability to manage a business in a sector where she has operational but not CEO-level experience. Operand Group will provide board support and advisory services."),
        ]),
    ]
)

# ── PPM 2: 51st Capital Group LLC (Marcus Webb) ────────────────────────────────
create_ppm("51st_Capital_Group_PPM.pdf", "51st Capital Group, LLC", "Marcus Webb",
    "$540,000 (100 Units @ $5,400)",
    [
        ("Executive Summary", [
            ("Fund Overview", "51st Capital Group, LLC is a partnered search fund formed by Marcus Webb and co-searcher Derek Johnson to identify, acquire, and operate a single lower-middle-market business. The fund is raising $540,000 across 100 units at $5,400 per unit to fund a 24-month search for a suitable acquisition target."),
            ("Partnership", "Marcus Webb and Derek Johnson bring complementary skill sets: Marcus has deep investment banking and private equity experience at Goldman Sachs and a mid-market PE fund, while Derek brings 8 years of operational management experience in business services and healthcare services companies."),
            ("Investment Thesis", "51st Capital Group targets business services and healthcare services companies with strong recurring revenue, defensible market positions, and clear operational improvement opportunities in the $15M-$60M TEV range."),
        ]),
        ("Searcher Background", [
            ("Marcus Webb — Education & Experience", "Marcus holds an MBA from The Wharton School at the University of Pennsylvania (Class of 2024) and a BS in Finance from Howard University. He spent 3 years as an investment banking analyst at Goldman Sachs in the Business Services and Healthcare coverage group, followed by 2 years as a private equity associate at a $400M mid-market fund focused on business services acquisitions."),
            ("Derek Johnson — Education & Experience", "Derek holds a BS in Business Administration from University of Georgia. He spent 10 years at a national janitorial and facilities management company, rising to Regional Operations Director overseeing 250 employees across 8 states. He subsequently served as VP of Operations at a healthcare staffing firm."),
            ("Geographic Focus", "The partnership is based in Atlanta, GA and focuses on the Southeast United States, with familiarity in Georgia, Florida, Tennessee, North Carolina, and South Carolina."),
        ]),
        ("Investment Criteria", [
            ("Target Sectors", "Business Services (staffing & recruiting, commercial cleaning, security services, payroll, compliance) and Healthcare Services (home health, behavioral health, medical staffing, physical therapy)."),
            ("Financial Profile", "Revenue of $8M-$40M, EBITDA of $1.5M-$6M, EBITDA margins of 12%-25%. Prefer companies with >50% recurring revenue and contract-based revenue."),
            ("Management Transition", "Target businesses where the founder/owner is seeking full transition over 12-24 months. No requirement for seller to remain post-close, but preference for 6-12 month transition support."),
            ("Acquisition Financing", "Target TEV of $15M-$60M at 5x-8x EBITDA using SBA 7(a) or conventional senior debt, seller notes where available, and search fund equity."),
        ]),
        ("Fund Terms", [
            ("Capital Structure", "51st Capital Group, LLC is organized as a Delaware LLC. Marcus Webb and Derek Johnson are co-managing members. $540,000 search capital across 100 units at $5,400 per unit."),
            ("Investor Rights", "Pro-rata acquisition participation rights. 1.5x step-up on search capital converted to acquisition equity."),
            ("Economics", "20% carried interest above 8% preferred return. Carry split equally between the two searchers. 4-year vesting with 1-year cliff post-acquisition."),
            ("Use of Proceeds", "Search capital will fund two full-time salaries, office expenses, deal legal/accounting fees, travel, and broker/advisor fees for 24 months."),
        ]),
        ("Risk Factors", [
            ("Partnership Dynamics", "As a partnered fund, 51st Capital Group is exposed to partnership execution risk. Disagreements between co-searchers could delay or derail the search. The partners have established a formal operating agreement with dispute resolution mechanisms."),
            ("Competition for Deals", "The lower-middle-market M&A market is competitive. The fund may compete with other search funds, private equity firms, and strategic buyers for attractive acquisition targets."),
            ("Integration Risk", "Post-acquisition, the integration of the existing management team, workforce, and processes presents operational risk. The fund plans to retain key employees and leverage Derek's operational experience to mitigate this risk."),
            ("Regulatory Risk", "Healthcare services companies are subject to Medicare/Medicaid regulations, state licensing requirements, and HIPAA compliance. Changes in reimbursement rates or regulatory environment could impact portfolio company performance."),
        ]),
    ]
)

# ── PPM 3: Accelerate Point Search Fund (Sarah Kim) ────────────────────────────
create_ppm("Accelerate_Point_PPM.pdf", "Accelerate Point Search Fund", "Sarah Kim",
    "$480,000 (100 Units @ $4,800)",
    [
        ("Executive Summary", [
            ("Fund Overview", "Accelerate Point Search Fund is a self-funded search fund formed by Sarah Kim to acquire and operate a vertical SaaS or technology-enabled services business. The fund is raising $480,000 across 100 units at $4,800 per unit to support a 24-month active search."),
            ("Searcher Profile", "Sarah brings an exceptionally rare combination of elite technical training (BS Computer Science, MIT), management consulting experience (McKinsey & Company), and product management at scale (Google, $1B+ revenue products). Her background uniquely positions her to identify and create value in software-enabled businesses."),
            ("Investment Thesis", "Technology-enabled services and vertical SaaS businesses serving SMBs are underserved by traditional private equity but represent an attractive search fund opportunity: lower multiples than pure-play SaaS, recurring revenue, high retention, and significant operational improvement potential."),
        ]),
        ("Searcher Background", [
            ("Education", "Sarah holds an MBA from Stanford Graduate School of Business (Class of 2025) with concentrations in Finance and Technology Management, and a BS in Computer Science from MIT. She completed the GSB ETA course and was a teaching assistant for the course in her second year."),
            ("McKinsey Experience", "Sarah spent 2 years at McKinsey & Company in the San Francisco office, working in the Technology, Media & Telecom practice. She led engagements for Fortune 500 technology companies on digital transformation, pricing strategy, and M&A integration."),
            ("Google Experience", "Prior to her MBA, Sarah spent 4 years at Google as a Product Manager, most recently managing a suite of SMB advertising products with $1.2B in annual revenue and a team of 12 engineers and designers. She developed deep expertise in SMB software buying behavior and product monetization."),
        ]),
        ("Investment Criteria", [
            ("Target Sectors", "Primary: Vertical SaaS serving SMBs (field service management, dental/medical practice management, property management, professional services workflow). Secondary: Tech-enabled services with proprietary software components (managed IT, digital marketing services, specialized staffing with tech platforms)."),
            ("Technical Requirements", "Preference for businesses with proprietary software or technology that creates switching costs and is difficult to replicate. Not interested in businesses where technology is purely a productivity tool without customer-facing value."),
            ("Financial Profile", "Revenue of $3M-$15M, EBITDA of $0.8M-$4M, EBITDA margins of 20%-45%. Prefer NRR (net revenue retention) of >90% and logo retention of >85%. ARR growth of 10%+ preferred."),
            ("Geography", "Headquarters-agnostic. Sarah is open to relocating. Preference for companies that can operate with distributed/remote teams, consistent with modern software business models."),
        ]),
        ("Fund Terms", [
            ("Structure", "Accelerate Point Search Fund is organized as a Delaware LLC. Sarah Kim is the sole managing member. $480,000 search capital across 100 units at $4,800 per unit."),
            ("Search Period", "24 months from first capital close. Extension of up to 6 months available with majority investor approval."),
            ("Acquisition Rights", "Standard search fund pro-rata acquisition participation rights. 1.5x step-up on search capital at acquisition."),
            ("Carried Interest", "20% carried interest above 8% preferred return. 4-year vesting with 1-year cliff from acquisition close date."),
        ]),
        ("Risk Factors", [
            ("Solo Search Risk", "As a solo searcher, the fund carries key-person risk. Sarah will mitigate this by building a strong board and advisory team pre-acquisition, including operators with CEO experience in SaaS businesses."),
            ("Valuation Risk", "Technology and SaaS businesses typically trade at premium multiples (6x-12x EBITDA or revenue-based multiples) compared to traditional search fund targets. Sarah is focused on businesses that have been passed over by SaaS-focused PE due to size or complexity, creating a valuation arbitrage opportunity."),
            ("Technical Complexity", "Acquiring a software business introduces technical due diligence requirements beyond standard financial and operational diligence. Sarah's technical background mitigates but does not eliminate the risk of undiscovered technical debt or architecture issues."),
            ("Market Risk", "SMB-focused SaaS businesses are exposed to SMB economic cycles. A downturn that causes SMB customer churn could reduce revenues and EBITDA more rapidly than traditional services businesses."),
        ]),
    ]
)

print("All 3 PPMs created in:", OUT_DIR)
