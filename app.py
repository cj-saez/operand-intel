import os, json, sqlite3, re
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.')
client = Anthropic(api_key=os.environ.get('ANTHROPIC_API_KEY', '').strip())
DB_PATH = os.path.join(os.path.dirname(__file__), 'operand.db')


# ── Database ──────────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    with open(os.path.join(os.path.dirname(__file__), 'schema.sql')) as f:
        conn.executescript(f.read())
    seed_data(conn)
    conn.commit()
    conn.close()

def seed_data(conn):
    # Only seed if empty
    if conn.execute('SELECT COUNT(*) FROM funds').fetchone()[0] > 0:
        return

    funds = [
        ('fund2', 'Fund II', 2016, 'HARVESTING', 21200000, 20200000, 57300000, 2.72, 2.72, 0.33, 2.38),
        ('fund3', 'Fund III', 2020, 'HARVESTING', 21700000, 21700000, 56000000, 2.68, 2.68, 0.26, 2.42),
        ('fund4', 'Fund IV', 2023, 'DEPLOYING', 42500000, 21300000, 20000000, 1.06, 1.06, 0.01, 1.05),
    ]
    conn.executemany('INSERT INTO funds (id,name,vintage,status,committed,called,total_value,moic,tvpi,dvpi,rvpi) VALUES (?,?,?,?,?,?,?,?,?,?,?)', funds)

    companies = [
        ('fund3', 'Circa Health LLC', 'Ennoble Care', 'Healthcare Services', 'ACTIVE', 3550000, 363555, 34973773, 35337328, 9.95, 74.9, 2.9),
        ('fund4', 'Nuance Medical', None, 'Healthcare Products', 'ACTIVE', 1500000, 0, 1500000, 1500000, None, None, None),
        ('fund4', 'Tacna', None, 'Business Services', 'ACTIVE', 1200000, 0, 1380000, 1380000, None, None, None),
        ('fund4', 'Blue Peak Tents', None, 'Consumer Products', 'ACTIVE', 2100000, 0, 2100000, 2100000, None, None, None),
        ('fund4', 'North American Trade Schools', None, 'Education', 'ACTIVE', 3365000, 0, 3365000, 3365000, None, None, None),
        ('fund4', 'Freelaunce', None, 'Technology', 'ACTIVE', 1200000, 0, 1200000, 1200000, None, None, None),
        ('fund4', 'Landlines', None, 'Telecommunications', 'ACTIVE', 1800000, 700000, 2500000, 3200000, None, None, None),
        ('fund4', 'PDBA', None, 'Business Services', 'ACTIVE', 1200000, 0, 1200000, 1200000, None, None, None),
        ('fund4', 'Itrazen', None, 'Cloud Services', 'ACTIVE', 1700000, 0, 1700000, 1700000, None, None, None),
        ('fund4', '1AR', None, 'Industrial Services', 'ACTIVE', 1200000, 0, 1200000, 1200000, None, None, None),
        ('fund4', 'BSG Inc.', None, 'Specialty Manufacturing', 'ACTIVE', 1200000, 0, 1200000, 1200000, None, None, None),
    ]
    conn.executemany('''INSERT INTO companies (fund_id,name,short_name,sector,status,invested,realized,unrealized,total_return,moic,irr,ownership_pct)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', companies)

    # Seed sample searchers
    searchers = [
        {
            'searcher_identifier': 'FND Partners',
            'searcher_name': 'Claudia (Clau) Leon',
            'llc_name': 'FND Partners LLC',
            'search_type': 'Solo',
            'ethnicity': 'Hispanic (Cuban)',
            'gender': 'Female',
            'estimated_age': '30–35',
            'marital_status': 'Not Stated',
            'education': 'MBA (Harvard Business School); MS Engineering (Georgia Tech); BS Engineering (Rice)',
            'took_eta_class': 1,
            'completed_eta_internship': 1,
            'professional_background': 'Engineering, Operations, Private Equity (deal lead exposure), Entrepreneurship',
            'post_mba_years': '<1',
            'search_capital_target': 627000,
            'capital_value_per_unit': 6270,
            'total_units': 100,
            'capital_raised': 627000,
            'capital_called': 0,
            'location_general': 'U.S.',
            'location_specific': 'TBD (ties to Miami, FL)',
            'target_industries': 'Niche industrial services, environmental testing, municipal compliance services, industrial outsourced services',
            'headline_score': 6,
            'score_color': 'GREEN',
            'risk_positive': json.dumps(['Female searcher (diversity signal)', 'URM (Hispanic background)', 'Top-tier MBA (Harvard)', 'Age ~30–35 (ideal range)', '<1 year post-MBA', 'Strong engineering + operations + deal exposure', 'Institutional pedigree (GE, Baker Hughes)', 'Structured sourcing strategy']),
            'risk_mixed': json.dumps(['Solo searcher (vs. partnered benchmark)', 'Search capital $627K (above ideal range >$600K)', 'Non-traditional finance/PE background (though includes deal exposure)', 'Marital status unclear']),
            'risk_negative': json.dumps(['Solo execution risk (key-person dependency)', 'Higher capital raise than benchmark sweet spot ($400–499K)', 'Limited direct CEO/operator experience', 'Slight delay in search start']),
            'score_signals': json.dumps([
                {'signal': '≥ 1 MBA', 'weight': '+3', 'applied': True},
                {'signal': 'Partnered team', 'weight': '+2', 'applied': False},
                {'signal': 'URM present', 'weight': '+1', 'applied': True},
                {'signal': 'PE background', 'weight': '+1', 'applied': True},
                {'signal': '$500–600K target', 'weight': '−2', 'applied': False},
                {'signal': 'Consulting-solo penalty', 'weight': '−3', 'applied': False},
                {'signal': '< $400K / ≥ $600K target', 'weight': '+1', 'applied': True},
            ]),
            'overall_take': 'High-caliber but non-traditional searcher—exceptional operational and technical profile with elite education, offset by solo structure and higher capital target. Signals are strong but not perfectly aligned with classic search fund success patterns.',
            'fund_id': 'fund4',
            'sector': 'Industrial Services',
            'status': 'SEARCHING',
            'company_acquired': None,
            'operand_participation': 1,
            'notes': 'Sourced via Harvard ETA program. Strong candidate.',
        },
        {
            'searcher_identifier': '51st Capital Group',
            'searcher_name': 'Marcus Webb',
            'llc_name': '51st Capital Group, LLC',
            'search_type': 'Partnered',
            'ethnicity': 'African American',
            'gender': 'Male',
            'estimated_age': '32–37',
            'marital_status': 'Married',
            'education': 'MBA (Wharton); BS Finance (Howard University)',
            'took_eta_class': 1,
            'completed_eta_internship': 0,
            'professional_background': 'Investment Banking (Goldman Sachs), Private Equity (mid-market)',
            'post_mba_years': '2',
            'search_capital_target': 540000,
            'capital_value_per_unit': 5400,
            'total_units': 100,
            'capital_raised': 540000,
            'capital_called': 180000,
            'location_general': 'U.S.',
            'location_specific': 'Atlanta, GA',
            'target_industries': 'Business services, healthcare services, light manufacturing',
            'headline_score': 8,
            'score_color': 'GREEN',
            'risk_positive': json.dumps(['URM (African American)', 'Top-tier MBA (Wharton)', 'Partnered team (+2)', 'Strong PE background', 'Ideal capital range $540K', 'Married (positive signal)', 'IB + PE pedigree']),
            'risk_mixed': json.dumps(['2 years post-MBA (slightly above ideal)', 'Howard undergrad (good but less target school)']),
            'risk_negative': json.dumps(['Less operational experience', 'Partner dynamic untested']),
            'score_signals': json.dumps([
                {'signal': '≥ 1 MBA', 'weight': '+3', 'applied': True},
                {'signal': 'Partnered team', 'weight': '+2', 'applied': True},
                {'signal': 'URM present', 'weight': '+1', 'applied': True},
                {'signal': 'PE background', 'weight': '+1', 'applied': True},
                {'signal': '$500–600K target', 'weight': '−2', 'applied': False},
                {'signal': 'Consulting-solo penalty', 'weight': '−3', 'applied': False},
                {'signal': '< $400K / ≥ $600K target', 'weight': '+1', 'applied': False},
            ]),
            'overall_take': 'Strong partnered team with blue-chip finance credentials and URM representation. Capital structure is well within benchmark range. Primary risk is limited operational depth pre-acquisition.',
            'fund_id': 'fund4',
            'sector': 'Business Services',
            'status': 'SEARCHING',
            'company_acquired': None,
            'operand_participation': 1,
            'notes': '',
        },
        {
            'searcher_identifier': 'Accelerate Point',
            'searcher_name': 'Sarah Kim',
            'llc_name': 'Accelerate Point Search Fund',
            'search_type': 'Solo',
            'ethnicity': 'Asian',
            'gender': 'Female',
            'estimated_age': '28–33',
            'marital_status': 'Single',
            'education': 'MBA (Stanford GSB); BS Computer Science (MIT)',
            'took_eta_class': 1,
            'completed_eta_internship': 1,
            'professional_background': 'Product Management (Google), Consulting (McKinsey)',
            'post_mba_years': '<1',
            'search_capital_target': 480000,
            'capital_value_per_unit': 4800,
            'total_units': 100,
            'capital_raised': 480000,
            'capital_called': 96000,
            'location_general': 'U.S.',
            'location_specific': 'San Francisco, CA',
            'target_industries': 'SaaS, tech-enabled services, vertical software',
            'headline_score': 5,
            'score_color': 'GREEN',
            'risk_positive': json.dumps(['Top-tier MBA (Stanford)', 'Female searcher', 'Asian (URM adjacent)', '<1 year post-MBA', 'Strong tech/consulting background', 'Ideal capital range']),
            'risk_mixed': json.dumps(['Solo searcher', 'Tech focus (higher multiples)', 'Limited M&A exposure']),
            'risk_negative': json.dumps(['No PE/deal background', 'Solo execution risk', 'SF location (higher cost base)']),
            'score_signals': json.dumps([
                {'signal': '≥ 1 MBA', 'weight': '+3', 'applied': True},
                {'signal': 'Partnered team', 'weight': '+2', 'applied': False},
                {'signal': 'URM present', 'weight': '+1', 'applied': False},
                {'signal': 'PE background', 'weight': '+1', 'applied': False},
                {'signal': '$500–600K target', 'weight': '−2', 'applied': False},
                {'signal': 'Consulting-solo penalty', 'weight': '−3', 'applied': False},
                {'signal': '< $400K / ≥ $600K target', 'weight': '+1', 'applied': False},
            ]),
            'overall_take': 'Elite academic credentials with strong tech background. The solo structure and lack of deal/PE experience are the primary concerns. Tech sector focus may limit deal universe in Operand\'s typical target range.',
            'fund_id': 'fund3',
            'sector': 'Technology',
            'status': 'ACQUIRED',
            'company_acquired': 'Landlines',
            'operand_participation': 1,
            'notes': 'Acquired Landlines in 2024.',
        },
    ]
    for s in searchers:
        conn.execute('''INSERT INTO searchers
            (searcher_identifier,searcher_name,llc_name,search_type,ethnicity,gender,estimated_age,
             marital_status,education,took_eta_class,completed_eta_internship,professional_background,
             post_mba_years,search_capital_target,capital_value_per_unit,total_units,capital_raised,
             capital_called,location_general,location_specific,target_industries,headline_score,
             score_color,risk_positive,risk_mixed,risk_negative,score_signals,overall_take,
             fund_id,sector,status,company_acquired,operand_participation,notes)
            VALUES (:searcher_identifier,:searcher_name,:llc_name,:search_type,:ethnicity,:gender,
             :estimated_age,:marital_status,:education,:took_eta_class,:completed_eta_internship,
             :professional_background,:post_mba_years,:search_capital_target,:capital_value_per_unit,
             :total_units,:capital_raised,:capital_called,:location_general,:location_specific,
             :target_industries,:headline_score,:score_color,:risk_positive,:risk_mixed,:risk_negative,
             :score_signals,:overall_take,:fund_id,:sector,:status,
             :company_acquired,:operand_participation,:notes)''', s)


# ── API Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'operand-intel.html')

@app.route('/health')
def health():
    key = os.environ.get('ANTHROPIC_API_KEY', '')
    return jsonify({'ok': True, 'key_present': bool(key)})

@app.route('/api/funds')
def get_funds():
    conn = get_db()
    funds = [dict(r) for r in conn.execute('SELECT * FROM funds ORDER BY vintage').fetchall()]
    conn.close()
    return jsonify(funds)

@app.route('/api/funds/<fund_id>')
def get_fund(fund_id):
    conn = get_db()
    fund = conn.execute('SELECT * FROM funds WHERE id=?', (fund_id,)).fetchone()
    if not fund:
        return jsonify({'error': 'Not found'}), 404
    companies = [dict(r) for r in conn.execute(
        'SELECT * FROM companies WHERE fund_id=? ORDER BY name', (fund_id,)).fetchall()]
    result = dict(fund)
    result['companies'] = companies
    conn.close()
    return jsonify(result)

@app.route('/api/companies')
def get_companies():
    conn = get_db()
    companies = [dict(r) for r in conn.execute('''
        SELECT c.*, f.name as fund_name FROM companies c
        LEFT JOIN funds f ON c.fund_id=f.id ORDER BY c.name''').fetchall()]
    conn.close()
    return jsonify(companies)

@app.route('/api/companies/<int:company_id>')
def get_company(company_id):
    conn = get_db()
    company = conn.execute('''
        SELECT c.*, f.name as fund_name FROM companies c
        LEFT JOIN funds f ON c.fund_id=f.id WHERE c.id=?''', (company_id,)).fetchone()
    if not company:
        return jsonify({'error': 'Not found'}), 404
    cash_flows = [dict(r) for r in conn.execute(
        'SELECT * FROM cash_flows WHERE company_id=? ORDER BY date DESC', (company_id,)).fetchall()]
    result = dict(company)
    result['cash_flows'] = cash_flows
    conn.close()
    return jsonify(result)

@app.route('/api/searchers')
def get_searchers():
    conn = get_db()
    rows = [dict(r) for r in conn.execute('''
        SELECT s.*, f.name as fund_name FROM searchers s
        LEFT JOIN funds f ON s.fund_id=f.id ORDER BY s.created_at DESC''').fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/searchers/<int:searcher_id>')
def get_searcher(searcher_id):
    conn = get_db()
    row = conn.execute('''
        SELECT s.*, f.name as fund_name FROM searchers s
        LEFT JOIN funds f ON s.fund_id=f.id WHERE s.id=?''', (searcher_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    conn.close()
    return jsonify(dict(row))

@app.route('/api/searchers', methods=['POST'])
def create_searcher():
    data = request.get_json(silent=True) or {}
    conn = get_db()
    cur = conn.execute('''INSERT INTO searchers
        (searcher_identifier,searcher_name,llc_name,search_type,ethnicity,gender,estimated_age,
         marital_status,education,took_eta_class,completed_eta_internship,professional_background,
         post_mba_years,search_capital_target,capital_value_per_unit,total_units,capital_raised,
         capital_called,location_general,location_specific,target_industries,headline_score,
         score_color,risk_positive,risk_mixed,risk_negative,score_signals,overall_take,
         fund_id,sector,status,company_acquired,operand_participation,notes,ppm_raw)
        VALUES (:searcher_identifier,:searcher_name,:llc_name,:search_type,:ethnicity,:gender,
         :estimated_age,:marital_status,:education,:took_eta_class,:completed_eta_internship,
         :professional_background,:post_mba_years,:search_capital_target,:capital_value_per_unit,
         :total_units,:capital_raised,:capital_called,:location_general,:location_specific,
         :target_industries,:headline_score,:score_color,:risk_positive,:risk_mixed,:risk_negative,
         :score_signals,:overall_take,:fund_id,:sector,:status,:company_acquired,
         :operand_participation,:notes,:ppm_raw)''',
        {k: data.get(k) for k in ['searcher_identifier','searcher_name','llc_name','search_type',
         'ethnicity','gender','estimated_age','marital_status','education','took_eta_class',
         'completed_eta_internship','professional_background','post_mba_years','search_capital_target',
         'capital_value_per_unit','total_units','capital_raised','capital_called','location_general',
         'location_specific','target_industries','headline_score','score_color','risk_positive',
         'risk_mixed','risk_negative','score_signals','overall_take','fund_id','sector','status',
         'company_acquired','operand_participation','notes','ppm_raw']})
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({'id': new_id}), 201

@app.route('/api/searchers/<int:searcher_id>', methods=['PUT'])
def update_searcher(searcher_id):
    data = request.get_json(silent=True) or {}
    conn = get_db()
    fields = [k for k in data if k != 'id']
    if not fields:
        return jsonify({'error': 'No fields'}), 400
    set_clause = ', '.join(f'{f}=:{f}' for f in fields)
    data['id'] = searcher_id
    data['updated_at'] = 'CURRENT_TIMESTAMP'
    conn.execute(f'UPDATE searchers SET {set_clause}, updated_at=CURRENT_TIMESTAMP WHERE id=:id', data)
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/ppm/extract', methods=['POST'])
def extract_ppm():
    """Extract structured data from a PPM PDF using Claude."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(stream=f.read(), filetype='pdf')
        text = '\n'.join(page.get_text() for page in doc)
        doc.close()
    except Exception as e:
        return jsonify({'error': f'PDF read error: {e}'}), 400

    prompt = f"""You are analyzing a Private Placement Memorandum (PPM) for a search fund.
Extract ALL of the following fields as a JSON object. Use null for any field not found.

PPM TEXT:
{text[:40000]}

Return ONLY valid JSON with these exact keys:
{{
  "searcher_identifier": "fund/entity name",
  "searcher_name": "full name(s)",
  "llc_name": "LLC entity name",
  "search_type": "Solo or Partnered",
  "ethnicity": "ethnicity if stated",
  "gender": "Male/Female/Non-binary/Not Stated",
  "estimated_age": "age or range",
  "marital_status": "Married/Single/Not Stated",
  "education": "degrees, schools",
  "took_eta_class": true/false,
  "completed_eta_internship": true/false,
  "professional_background": "summary of work history",
  "post_mba_years": "years since MBA",
  "search_capital_target": number,
  "capital_value_per_unit": number,
  "total_units": number,
  "location_general": "US/International",
  "location_specific": "city/state",
  "target_industries": "comma-separated industries",
  "headline_score": number,
  "score_color": "GREEN or YELLOW or RED",
  "risk_positive": ["list", "of", "positive", "signals"],
  "risk_mixed": ["list", "of", "mixed", "signals"],
  "risk_negative": ["list", "of", "risk", "flags"],
  "score_signals": [
    {{"signal": "≥ 1 MBA", "weight": "+3", "applied": true/false}},
    {{"signal": "Partnered team", "weight": "+2", "applied": true/false}},
    {{"signal": "URM present", "weight": "+1", "applied": true/false}},
    {{"signal": "PE background", "weight": "+1", "applied": true/false}},
    {{"signal": "$500–600K target", "weight": "−2", "applied": true/false}},
    {{"signal": "Consulting-solo penalty", "weight": "−3", "applied": true/false}},
    {{"signal": "< $400K / ≥ $600K target", "weight": "+1", "applied": true/false}}
  ],
  "overall_take": "2-3 sentence assessment",
  "sector": "primary target sector",
  "notes": "any other important observations"
}}

Score calculation: sum the weights of all applied signals for headline_score.
GREEN = score >= 4, YELLOW = score 1-3, RED = score <= 0."""

    try:
        response = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=4000,
            messages=[{'role': 'user', 'content': prompt}]
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
        extracted = json.loads(raw)
        # Serialize list fields to JSON strings for storage
        for field in ['risk_positive', 'risk_mixed', 'risk_negative', 'score_signals']:
            if isinstance(extracted.get(field), list):
                extracted[field] = json.dumps(extracted[field])
        extracted['ppm_raw'] = text[:10000]
        return jsonify({'ok': True, 'data': extracted})
    except json.JSONDecodeError as e:
        return jsonify({'error': f'JSON parse error: {e}', 'raw': raw}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask():
    """Streaming AI chat with full context about the fund portfolio."""
    data = request.get_json(silent=True) or {}
    message = data.get('message', '').strip()
    history = data.get('history', [])
    if not message:
        return jsonify({'error': 'No message'}), 400

    # Build context from DB
    conn = get_db()
    funds = [dict(r) for r in conn.execute('SELECT * FROM funds').fetchall()]
    searchers = [dict(r) for r in conn.execute(
        'SELECT id,searcher_name,llc_name,search_type,score_color,headline_score,status,sector,company_acquired FROM searchers').fetchall()]
    conn.close()

    context = f"""You are an AI analyst for Operand Group, a search fund investment firm.

FUND PORTFOLIO:
{json.dumps(funds, indent=2)}

SEARCHER PIPELINE ({len(searchers)} total):
{json.dumps(searchers, indent=2)}

You have deep knowledge of search fund investing, preferred return calculations, MOIC/IRR/TVPI metrics, and searcher evaluation benchmarks. Answer questions about the portfolio, searchers, and fund performance with specific data and actionable insights."""

    def generate():
        try:
            with client.messages.stream(
                model='claude-sonnet-4-6',
                max_tokens=1500,
                system=context,
                messages=history + [{'role': 'user', 'content': message}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            yield "data: [DONE]\n\n"

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    key_ok = bool(os.environ.get('ANTHROPIC_API_KEY', '').startswith('sk-'))
    print(f"\n{'✓' if key_ok else '✗'} ANTHROPIC_API_KEY {'found' if key_ok else 'missing'}")
    print(f"→ Operand Intel running at http://localhost:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
