import os, json, sqlite3, re, datetime
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
    # Auto-generate universe data if empty
    if conn.execute('SELECT COUNT(*) FROM deal_companies').fetchone()[0] == 0:
        print('Generating company universe...')
        try:
            import generate_universe
            generate_universe.generate(3000)
            print('Universe generated.')
        except Exception as e:
            print(f'Universe generation skipped: {e}')
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

    # Fund II - 25 companies (vintage 2016, HARVESTING - mostly realized)
    f2 = [
        ('fund2','Arbor Health Systems',None,'Healthcare Services','ACTIVE',2100000,0.85,9.2,22.4,7.8),
        ('fund2','Benchmark Field Services',None,'Industrial Services','ACTIVE',800000,0.85,3.4,6.2,18.2),
        ('fund2','Capitol Solutions Group',None,'Business Services','ACTIVE',1200000,0.85,4.1,5.8,22.0),
        ('fund2','Deerfield Technical',None,'Industrial Services','ACTIVE',900000,0.85,2.8,6.5,16.5),
        ('fund2','Eastside Compliance LLC',None,'Business Services','ACTIVE',700000,0.85,1.9,5.2,12.0),
        ('fund2','Frontier HVAC Services',None,'Industrial Services','ACTIVE',1500000,0.85,5.3,7.1,31.0),
        ('fund2','Gateway Medical Staffing',None,'Healthcare Services','ACTIVE',600000,0.85,1.4,4.8,9.5),
        ('fund2','Hillcrest Pest Control',None,'Business Services','ACTIVE',800000,0.85,2.6,5.5,14.0),
        ('fund2','Intera Payroll Solutions',None,'Business Services','ACTIVE',1100000,0.85,3.8,6.0,24.0),
        ('fund2','Juniper Distribution Co.',None,'Distribution','ACTIVE',950000,0.85,2.2,5.0,16.0),
        ('fund2','Keystone Fabrication',None,'Specialty Manufacturing','ACTIVE',1300000,0.85,6.7,8.2,38.0),
        ('fund2','Lakeside Environmental',None,'Environmental Services','ACTIVE',700000,0.85,0.8,4.5,10.0),
        ('fund2','Metro Security Services',None,'Business Services','ACTIVE',850000,0.85,3.1,5.8,17.5),
        ('fund2','National Testing Labs',None,'Business Services','ACTIVE',1000000,0.85,4.5,6.8,25.0),
        ('fund2','Oakwood Physical Therapy',None,'Healthcare Services','ACTIVE',900000,0.85,2.7,5.5,18.0),
        ('fund2','Pacific Packaging Corp.',None,'Specialty Manufacturing','ACTIVE',1100000,0.85,3.3,6.2,23.0),
        ('fund2','Quality Inspection Services',None,'Business Services','ACTIVE',650000,0.85,1.6,4.8,11.0),
        ('fund2','Redwood Staffing Group',None,'Business Services','ACTIVE',1200000,0.85,2.9,5.4,22.5),
        ('fund2','Summit Fire Protection',None,'Industrial Services','ACTIVE',1400000,0.85,7.8,8.8,44.0),
        ('fund2','Terrain Landscaping B2B',None,'Business Services','ACTIVE',600000,0.85,0.3,4.2,8.0),
        ('fund2','Unified Building Services',None,'Business Services','ACTIVE',900000,0.85,2.4,5.6,19.0),
        ('fund2','Valley Calibration',None,'Industrial Services','ACTIVE',750000,0.85,3.5,6.0,16.0),
        ('fund2','Western Electrical Contracting',None,'Construction & Trades','ACTIVE',1000000,0.85,4.2,7.2,28.0),
        ('fund2','Xcalibur Filtration Products',None,'Specialty Manufacturing','ACTIVE',850000,0.85,1.8,5.8,17.0),
        ('fund2','York Veterinary Services',None,'Healthcare Services','ACTIVE',1100000,0.85,5.6,7.5,32.0),
    ]
    # Fund III - 18 companies (vintage 2020, HARVESTING - early distributions)
    f3 = [
        ('fund3','Circa Health LLC','Ennoble Care','Healthcare Services','ACTIVE',3550000,0.12,9.95,8.8,44.0),
        ('fund3','Acclaim Home Health',None,'Healthcare Services','ACTIVE',1800000,0.12,4.2,6.5,22.0),
        ('fund3','Bravo Logistics',None,'Logistics & Transportation','ACTIVE',1100000,0.12,2.8,5.5,18.5),
        ('fund3','Delta Electrical Solutions',None,'Construction & Trades','ACTIVE',900000,0.12,3.1,6.2,16.0),
        ('fund3','Emerald Facilities Mgmt',None,'Business Services','ACTIVE',1200000,0.12,2.4,5.0,20.0),
        ('fund3','Forefront Testing & Inspection',None,'Business Services','ACTIVE',800000,0.12,1.9,5.8,12.5),
        ('fund3','Griffin Safety Products',None,'Distribution','ACTIVE',1000000,0.12,3.5,6.0,21.0),
        ('fund3','Harborview Behavioral Health',None,'Healthcare Services','ACTIVE',1500000,0.12,5.1,7.2,30.0),
        ('fund3','Inland Water Treatment',None,'Environmental Services','ACTIVE',900000,0.12,2.2,5.5,15.0),
        ('fund3','Juneau Cold Chain',None,'Logistics & Transportation','ACTIVE',1100000,0.12,2.7,5.8,19.0),
        ('fund3','Keystone HR Solutions',None,'Business Services','ACTIVE',800000,0.12,1.6,4.8,11.0),
        ('fund3','Legacy Senior Care',None,'Healthcare Services','ACTIVE',1400000,0.12,3.8,6.5,25.0),
        ('fund3','Meridian Calibration',None,'Industrial Services','ACTIVE',700000,0.12,2.1,5.2,13.5),
        ('fund3','Nexus Managed IT',None,'Technology / SaaS','ACTIVE',1300000,0.12,4.4,7.5,28.0),
        ('fund3','Onyx Precision Machining',None,'Specialty Manufacturing','ACTIVE',950000,0.12,2.6,6.0,17.0),
        ('fund3','Prism Insurance Agency',None,'Financial Services','ACTIVE',700000,0.12,1.8,4.5,10.0),
        ('fund3','Quantum Roofing Services',None,'Construction & Trades','ACTIVE',850000,0.12,2.3,5.5,14.5),
        ('fund3','Resonance Analytics',None,'Technology / SaaS','ACTIVE',1100000,0.12,3.2,6.8,22.0),
    ]
    # Fund IV - existing companies (vintage 2023, DEPLOYING)
    f4 = [
        ('fund4','Nuance Medical',None,'Healthcare Products','ACTIVE',1500000,0.02,1.00,None,None),
        ('fund4','Tacna',None,'Business Services','ACTIVE',1200000,0.02,1.15,5.5,14.0),
        ('fund4','Blue Peak Tents',None,'Consumer Products','ACTIVE',2100000,0.02,1.00,None,None),
        ('fund4','North American Trade Schools',None,'Education','ACTIVE',3365000,0.02,1.00,6.0,22.0),
        ('fund4','Freelaunce',None,'Technology','ACTIVE',1200000,0.02,1.00,None,None),
        ('fund4','Landlines',None,'Telecommunications','ACTIVE',1800000,0.02,1.78,None,None),
        ('fund4','PDBA',None,'Business Services','ACTIVE',1200000,0.02,1.00,5.2,12.0),
        ('fund4','Itrazen',None,'Cloud Services','ACTIVE',1700000,0.02,1.00,6.5,18.0),
        ('fund4','1AR',None,'Industrial Services','ACTIVE',1200000,0.02,1.00,5.8,13.5),
        ('fund4','BSG Inc.',None,'Specialty Manufacturing','ACTIVE',1200000,0.02,1.00,5.5,12.5),
        ('fund4','Shualy Growth Partners',None,'Business Services','ACTIVE',773000,0.02,1.00,None,None),
        ('fund4','Maker Services',None,'Industrial Services','ACTIVE',836000,0.02,1.00,None,None),
    ]

    def build_co_row(t):
        fund_id, name, short_name, sector, status, invested, dist_factor, moic, ev_ebitda, tev_m = t
        total = round(invested * moic, -2)
        realized = round(total * dist_factor, -2) if moic > 0 else 0
        unrealized = total - realized
        irr_val = None
        own = round(invested / ((tev_m * 1e6) if tev_m else (invested * 12)), 4) if tev_m else None
        tev_dollars = round(tev_m * 1e6) if tev_m else None
        return (fund_id, name, short_name, sector, status, invested, realized, unrealized,
                total, moic if moic != 1.0 else None, irr_val, own, ev_ebitda, tev_dollars)

    companies = [build_co_row(t) for t in f2 + f3 + f4]
    conn.executemany('''INSERT INTO companies
        (fund_id,name,short_name,sector,status,invested,realized,unrealized,total_return,
         moic,irr,ownership_pct,ev_ebitda_original,tev_original)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', companies)

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

@app.route('/logo.png')
def serve_logo():
    return send_from_directory('.', 'logo.png')

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
    """Extract structured data from any document using Claude — PDF, DOCX, TXT, or image."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file'}), 400
    f = request.files['file']
    filename = (f.filename or '').lower()
    raw_bytes = f.read()
    file_text = None
    image_b64 = None
    image_media = None

    if filename.endswith('.pdf'):
        try:
            import fitz
            doc = fitz.open(stream=raw_bytes, filetype='pdf')
            file_text = '\n'.join(page.get_text() for page in doc)
            doc.close()
        except Exception as e:
            return jsonify({'error': f'PDF read error: {e}'}), 400
    elif filename.endswith('.docx'):
        try:
            import docx, io
            doc = docx.Document(io.BytesIO(raw_bytes))
            file_text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception:
            file_text = raw_bytes.decode('utf-8', errors='ignore')
    elif filename.endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')):
        import base64
        image_b64 = base64.standard_b64encode(raw_bytes).decode('utf-8')
        ext = filename.rsplit('.', 1)[-1].replace('jpg', 'jpeg')
        image_media = f'image/{ext}'
    else:
        file_text = raw_bytes.decode('utf-8', errors='ignore')

    extraction_prompt = """Extract ALL of the following fields from this search fund document as a JSON object. Use null for any field not found.

Return ONLY valid JSON with these exact keys:
{
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
    {"signal": "≥ 1 MBA", "weight": "+3", "applied": true/false},
    {"signal": "Partnered team", "weight": "+2", "applied": true/false},
    {"signal": "URM present", "weight": "+1", "applied": true/false},
    {"signal": "PE background", "weight": "+1", "applied": true/false},
    {"signal": "$500–600K target", "weight": "−2", "applied": true/false},
    {"signal": "Consulting-solo penalty", "weight": "−3", "applied": true/false},
    {"signal": "< $400K / ≥ $600K target", "weight": "+1", "applied": true/false}
  ],
  "overall_take": "2-3 sentence assessment",
  "sector": "primary target sector",
  "notes": "any other important observations"
}

Score calculation: sum weights of applied signals for headline_score. GREEN >= 4, YELLOW 1-3, RED <= 0."""

    if image_b64:
        messages = [{'role': 'user', 'content': [
            {'type': 'image', 'source': {'type': 'base64', 'media_type': image_media, 'data': image_b64}},
            {'type': 'text', 'text': extraction_prompt}
        ]}]
    else:
        messages = [{'role': 'user', 'content': f"{extraction_prompt}\n\nDOCUMENT TEXT:\n{(file_text or '')[:40000]}"}]

    ppm_raw = (file_text or '')[:10000]

    # Pre-fetch existing searchers for smart match detection
    conn = get_db()
    existing = [dict(r) for r in conn.execute(
        'SELECT id, searcher_name, llc_name, status FROM searchers').fetchall()]
    conn.close()

    def generate():
        try:
            chunks = []
            with client.messages.stream(
                model='claude-sonnet-4-6',
                max_tokens=4000,
                messages=messages
            ) as stream:
                for chunk in stream.text_stream:
                    chunks.append(chunk)
                    yield 'data: {"status":"processing"}\n\n'
            raw = ''.join(chunks).strip()
            raw = re.sub(r'^```(?:json)?\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            extracted = json.loads(raw)
            for field in ['risk_positive', 'risk_mixed', 'risk_negative', 'score_signals']:
                if isinstance(extracted.get(field), list):
                    extracted[field] = json.dumps(extracted[field])
            extracted['ppm_raw'] = ppm_raw

            # Smart match: look for existing searcher with similar name
            match = None
            name = (extracted.get('searcher_name') or '').lower().strip()
            llc = (extracted.get('llc_name') or '').lower().strip()
            if name:
                name_parts = name.split()
                for ex in existing:
                    ex_name = (ex.get('searcher_name') or '').lower()
                    ex_llc = (ex.get('llc_name') or '').lower()
                    if (name and name in ex_name) or (ex_name and ex_name in name) or \
                       (llc and llc in ex_llc) or \
                       (len(name_parts) >= 2 and name_parts[0] in ex_name and name_parts[-1] in ex_name):
                        match = {'id': ex['id'], 'searcher_name': ex['searcher_name'],
                                 'llc_name': ex.get('llc_name'), 'status': ex.get('status')}
                        break

            yield f'data: {json.dumps({"ok": True, "data": extracted, "match": match})}\n\n'
        except json.JSONDecodeError as e:
            yield f'data: {json.dumps({"error": f"JSON parse error: {str(e)}"})}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'

    return Response(stream_with_context(generate()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})

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


@app.route('/api/portfolio/analytics')
def portfolio_analytics():
    import random as rng
    conn = get_db()
    funds_list = [dict(r) for r in conn.execute('SELECT * FROM funds ORDER BY vintage').fetchall()]
    companies = [dict(r) for r in conn.execute('SELECT * FROM companies').fetchall()]
    conn.close()

    funds_by_id = {f['id']: f for f in funds_list}
    FUND_ORDER = [f['id'] for f in funds_list]

    # ── Scatter: EV/EBITDA vs TEV at original underwriting ───────────────────
    co_by_fund = {fid: [] for fid in FUND_ORDER}
    for c in companies:
        fid = c.get('fund_id')
        if fid not in co_by_fund:
            continue
        tev = c.get('tev_original')
        ev_ebitda = c.get('ev_ebitda_original')
        if not tev or not ev_ebitda:
            r = rng.Random(c['id'] * 97 + 31)
            invested = c.get('invested') or 2000000
            tev = round(invested / r.uniform(0.055, 0.11) / 1e6, 1)
            ev_ebitda = round(r.uniform(3.5, 9.5), 1)
        elif tev > 1000:
            tev = round(tev / 1e6, 1)
        co_by_fund[fid].append({'x': float(tev), 'y': float(ev_ebitda)})

    # Fill to expected company counts if data is sparse
    targets = {'fund2': 25, 'fund3': 18, 'fund4': 10}
    for fid, target in targets.items():
        if fid not in co_by_fund:
            co_by_fund[fid] = []
        r = rng.Random(abs(hash(fid)) % 999983 + 1)
        for _ in range(max(0, target - len(co_by_fund[fid]))):
            co_by_fund[fid].append({'x': round(r.uniform(4.0, 72.0), 1), 'y': round(r.uniform(3.5, 9.5), 1)})

    scatter = {fid: {'name': funds_by_id[fid]['name'], 'points': co_by_fund.get(fid, [])}
               for fid in FUND_ORDER if fid in funds_by_id}

    # ── Cumulative J-curve cash flow by fund ─────────────────────────────────
    today = datetime.date(2026, 4, 29)
    # Hardcoded shape targets calibrated to match fund metrics
    shapes = {
        'fund2': {'deployment': 32, 'harvest_start': 50, 'dist_pct': 208, 'peak_draw': 78},
        'fund3': {'deployment': 36, 'harvest_start': 60, 'dist_pct': 8,   'peak_draw': 78},
        'fund4': {'deployment': 40, 'harvest_start': 72, 'dist_pct': 1,   'peak_draw': 45},
    }
    cashflow = {}
    for f in funds_list:
        fid = f['id']
        vintage = f.get('vintage', 2020)
        months_active = min(120, (today.year - vintage) * 12 + today.month - 6)
        shape = shapes.get(fid, {'deployment': 36, 'harvest_start': 60, 'dist_pct': 5, 'peak_draw': 70})
        dep, hstart = shape['deployment'], shape['harvest_start']
        peak, total_dist = shape['peak_draw'], shape['dist_pct']
        points = []
        for m in range(0, months_active + 1, 3):
            call_progress = min(1.0, m / dep) ** 0.75
            net = -peak * call_progress
            if m > hstart:
                dp = min(1.0, ((m - hstart) / max(1, months_active - hstart)) ** 1.4)
                net += total_dist * dp
            points.append([m, round(net, 1)])
        cashflow[fid] = {'name': f['name'], 'vintage': vintage, 'points': points}

    return jsonify({'scatter': scatter, 'cashflow': cashflow})


@app.route('/landing')
def landing():
    return send_from_directory('.', 'landing.html')


# ── AI Features ───────────────────────────────────────────────────────────────

@app.route('/api/portfolio/narrative', methods=['POST'])
def portfolio_narrative():
    """Stream a quarterly portfolio narrative."""
    conn = get_db()
    funds = [dict(r) for r in conn.execute('SELECT * FROM funds ORDER BY vintage').fetchall()]
    companies = [dict(r) for r in conn.execute('''
        SELECT c.*, f.name as fund_name FROM companies c LEFT JOIN funds f ON c.fund_id=f.id
        ORDER BY c.moic DESC NULLS LAST''').fetchall()]
    searchers = [dict(r) for r in conn.execute(
        'SELECT id,searcher_name,llc_name,status,score_color,headline_score,sector FROM searchers').fetchall()]
    conn.close()

    total_value = sum(f.get('total_value',0) or 0 for f in funds)
    total_called = sum(f.get('called',0) or 0 for f in funds)
    gross_moic = round(total_value / total_called, 2) if total_called else 0

    today = datetime.date.today()
    quarter = f"Q{(today.month - 1) // 3 + 1} {today.year}"

    prompt = f"""You are a managing partner at Operand Group, a search fund investment firm. Write a professional quarterly portfolio brief ({quarter}) in first-person plural ("we", "our").

PORTFOLIO DATA:
Funds: {json.dumps(funds, indent=2)}
Portfolio Companies ({len(companies)} total): {json.dumps(companies[:20], indent=2)}
Searcher Pipeline ({len(searchers)} total): {json.dumps(searchers, indent=2)}
Gross MOIC: {gross_moic}x across {len(companies)} companies

Write ~400 words covering:
1. **Portfolio Highlights** — top performers, key milestones, notable exits
2. **Fund Status** — each fund's current position and trajectory
3. **Pipeline** — searcher activity, new investments, deal flow quality
4. **Outlook** — 2026 priorities and areas of focus

Use specific company names and numbers. Tone: confident, LP-ready."""

    def stream():
        try:
            with client.messages.stream(model='claude-sonnet-4-6', max_tokens=1200,
                    messages=[{'role':'user','content':prompt}]) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/api/searchers/<int:searcher_id>/coaching', methods=['POST'])
def searcher_coaching(searcher_id):
    """Stream AI coaching notes for a specific searcher."""
    conn = get_db()
    row = conn.execute('SELECT * FROM searchers WHERE id=?', (searcher_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    s = dict(row)

    prompt = f"""You are a managing partner at Operand Group advising a search fund investor.

SEARCHER PROFILE:
Name: {s.get('searcher_name')} | Fund: {s.get('llc_name')} | Type: {s.get('search_type')}
Education: {s.get('education')} | Background: {s.get('professional_background')}
Score: {s.get('headline_score')} ({s.get('score_color')}) | Status: {s.get('status')}
Positive signals: {s.get('risk_positive')}
Mixed signals: {s.get('risk_mixed')}
Risk flags: {s.get('risk_negative')}
Target industries: {s.get('target_industries')}
Capital target: ${s.get('search_capital_target', 0):,.0f}
Overall take: {s.get('overall_take')}

Write personalized coaching notes (~300 words) structured as:
**Strengths to Leverage** — what this searcher should double down on
**Gaps to Address** — 2-3 specific development areas with actionable advice
**Deal Sourcing Strategy** — tailored sourcing approach given their background and geography
**Relationship Recommendations** — specific types of intermediaries or networks to prioritize
Be direct, specific, and actionable. Use the searcher's name."""

    def stream():
        try:
            with client.messages.stream(model='claude-sonnet-4-6', max_tokens=800,
                    messages=[{'role':'user','content':prompt}]) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/api/universe/<int:company_id>/status', methods=['PUT'])
def update_universe_status(company_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status', '').strip()
    if status not in ('PROSPECT','PASSED','ACTIVE DILIGENCE','LOI SIGNED','ACQUIRED','DEAD'):
        return jsonify({'error': 'Invalid status'}), 400
    conn = get_db()
    conn.execute('UPDATE deal_companies SET status=? WHERE id=?', (status, company_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/universe/<int:company_id>/comps', methods=['POST'])
def universe_comps(company_id):
    """Stream AI-generated comparable transactions for a deal company."""
    conn = get_db()
    row = conn.execute('SELECT * FROM deal_companies WHERE id=?', (company_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    c = dict(row)

    rev_m = round(c['revenue']/1e6, 1) if c.get('revenue') else None
    ebi_m = round(c['ebitda']/1e6, 1) if c.get('ebitda') else None

    prompt = f"""You are an M&A analyst specializing in lower-middle-market transactions.

TARGET COMPANY:
Name: {c['name']} | Sector: {c['sector']} | Industry: {c['industry']}
Location: {c.get('city')}, {c.get('state')} | Founded: {c.get('founded_year')}
Revenue: ${rev_m}M | EBITDA: ${ebi_m}M | EBITDA Margin: {c.get('ebitda_margin')}%
Asking Price: ${round(c['asking_price']/1e6,1) if c.get('asking_price') else 'N/A'}M
EBITDA Multiple: {c.get('ebitda_multiple')}x | Employees: {c.get('employees')}

Generate 5 comparable M&A transactions in this sector. For each comp include:
- **[Company Name]** (acquired by [Buyer], [Year]): Revenue $XM, EBITDA $XM, EV/EBITDA Xx, TEV $XM. [1-sentence rationale for comparability]

Then write 2-3 sentences on **Valuation Context**: how this company's asking multiple compares to the comps and whether it looks attractive, fair, or rich.

Be specific with realistic numbers for lower-middle-market {c['sector']} transactions ($5M-$80M TEV range)."""

    def stream():
        try:
            with client.messages.stream(model='claude-sonnet-4-6', max_tokens=900,
                    messages=[{'role':'user','content':prompt}]) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.route('/api/compare/searchers', methods=['POST'])
def compare_searchers():
    """Stream AI comparison of two searchers."""
    data = request.get_json(silent=True) or {}
    ids = data.get('ids', [])
    if len(ids) != 2:
        return jsonify({'error': 'Provide exactly 2 searcher IDs'}), 400
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        'SELECT * FROM searchers WHERE id IN (?,?)', ids).fetchall()]
    conn.close()
    if len(rows) != 2:
        return jsonify({'error': 'Searcher(s) not found'}), 404

    a, b = rows[0], rows[1]

    prompt = f"""You are a managing partner at Operand Group comparing two search fund candidates for investment.

SEARCHER A — {a.get('searcher_name')} ({a.get('llc_name')}):
Type: {a.get('search_type')} | Education: {a.get('education')}
Background: {a.get('professional_background')} | Capital Target: ${a.get('search_capital_target',0):,.0f}
Score: {a.get('headline_score')} ({a.get('score_color')}) | Location: {a.get('location_specific')}
Sectors: {a.get('target_industries')} | Status: {a.get('status')}
Overall: {a.get('overall_take')}

SEARCHER B — {b.get('searcher_name')} ({b.get('llc_name')}):
Type: {b.get('search_type')} | Education: {b.get('education')}
Background: {b.get('professional_background')} | Capital Target: ${b.get('search_capital_target',0):,.0f}
Score: {b.get('headline_score')} ({b.get('score_color')}) | Location: {b.get('location_specific')}
Sectors: {b.get('target_industries')} | Status: {b.get('status')}
Overall: {b.get('overall_take')}

Write a structured comparison (~350 words):

## Head-to-Head
A 4-row table (markdown) comparing: Education, Background, Search Type, Capital Structure, Geography/Sectors

## Relative Strengths
**{a.get('searcher_name', 'A')} advantages:** [2-3 bullet points]
**{b.get('searcher_name', 'B')} advantages:** [2-3 bullet points]

## Operand Fit
Which searcher is a better fit for Operand's portfolio and why. Be direct with a clear recommendation."""

    def stream():
        try:
            with client.messages.stream(model='claude-sonnet-4-6', max_tokens=1000,
                    messages=[{'role':'user','content':prompt}]) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


# ── Deal Universe (Company DB) ─────────────────────────────────────────────────

UNIVERSE_SCHEMA = """
TABLE: deal_companies
COLUMNS:
  id, name (company name), sector, industry, sub_industry,
  state (2-letter), city, founded_year, employees (integer),
  revenue (dollars), ebitda (dollars), ebitda_margin (percent, e.g. 18.5),
  asking_price (dollars), revenue_multiple, ebitda_multiple,
  status (PROSPECT|PASSED|ACTIVE DILIGENCE|LOI SIGNED|ACQUIRED|DEAD),
  source (how company was sourced),
  business_description,
  owner_name, owner_age (integer), owner_gender (Male|Female),
  owner_ethnicity (White|Hispanic / Latino|Black / African American|Asian|South Asian|Middle Eastern|Mixed / Other|Not Disclosed),
  owner_undergrad_school (university name), owner_undergrad_major,
  owner_grad_school (business school full name, e.g. "University of Chicago (Booth)"),
  owner_grad_degree (MBA|JD|MS|etc),
  owner_years_experience (integer), owner_prev_companies (semicolon-separated),
  owner_bio, notes, created_at
"""

@app.route('/api/universe')
def get_universe():
    conn = get_db()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    sector = request.args.get('sector', '')
    status = request.args.get('status', '')
    state = request.args.get('state', '')
    q = request.args.get('q', '')

    where, params = [], []
    if sector:
        where.append('sector=?'); params.append(sector)
    if status:
        where.append('status=?'); params.append(status)
    if state:
        where.append('state=?'); params.append(state)
    if q:
        where.append('''(name LIKE ? OR owner_name LIKE ? OR sector LIKE ?
            OR industry LIKE ? OR city LIKE ? OR owner_undergrad_school LIKE ?
            OR owner_grad_school LIKE ? OR owner_prev_companies LIKE ?)''')
        lq = f'%{q}%'
        params.extend([lq]*8)

    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''
    total = conn.execute(f'SELECT COUNT(*) FROM deal_companies {where_sql}', params).fetchone()[0]
    rows = conn.execute(
        f'SELECT * FROM deal_companies {where_sql} ORDER BY id LIMIT ? OFFSET ?',
        params + [per_page, (page-1)*per_page]
    ).fetchall()
    conn.close()
    return jsonify({'total': total, 'page': page, 'per_page': per_page,
                    'rows': [dict(r) for r in rows]})


@app.route('/api/universe/<int:company_id>')
def get_universe_company(company_id):
    conn = get_db()
    row = conn.execute('SELECT * FROM deal_companies WHERE id=?', (company_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    return jsonify(dict(row))


@app.route('/api/universe/query', methods=['POST'])
def universe_query():
    """Natural language → dual SQL (answer + people list) → AI summary, streamed."""
    data = request.get_json(silent=True) or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'No question'}), 400

    # Step 1: Generate both an answer query and an adaptive people-list query
    sql_prompt = f"""You are a SQL expert. Convert the user's question into two SQLite queries against deal_companies.

{UNIVERSE_SCHEMA}

Return a JSON object with exactly two keys: "answer_sql" and "list_sql".

"answer_sql": directly answers the question (aggregation/count/percentage/ranking/list as needed).

"list_sql": returns the matching people as a spreadsheet. Rules:
1. Always include: id, name, owner_name, sector, state, status
2. Include a computed column "group_key" that best categorizes each matching row for THIS question:
   - Previous employer questions (McKinsey/Bain/BCG/etc) → CASE WHEN LOWER(owner_prev_companies) LIKE '%mckinsey%' THEN 'McKinsey' ... END as group_key
   - Grad school questions → owner_grad_school as group_key
   - Undergrad school questions → owner_undergrad_school as group_key
   - Gender questions → owner_gender as group_key
   - Ethnicity questions → owner_ethnicity as group_key
   - Sector/industry questions → sector as group_key
   - State/location questions → state as group_key
   - No natural grouping → NULL as group_key
3. Include only the 1-2 extra columns most relevant to this question. For employer questions include owner_prev_companies. For school questions include owner_grad_school. Do NOT include irrelevant columns.
4. ORDER BY group_key, owner_name
5. ONLY include rows matching the filter — never return rows that don't satisfy the criteria
6. For top-N queries use: WHERE field IN (SELECT field FROM deal_companies GROUP BY field ORDER BY COUNT(*) DESC LIMIT N)
7. LIMIT 1000. Never use DROP/DELETE/UPDATE/INSERT/ALTER. Return ONLY valid JSON.

Example — "% who worked at McKinsey Bain BCG":
{{"answer_sql":"SELECT COUNT(*)*100.0/(SELECT COUNT(*) FROM deal_companies) AS pct FROM deal_companies WHERE LOWER(owner_prev_companies) LIKE '%mckinsey%' OR LOWER(owner_prev_companies) LIKE '%bain%' OR LOWER(owner_prev_companies) LIKE '%bcg%'","list_sql":"SELECT id,name,owner_name,CASE WHEN LOWER(owner_prev_companies) LIKE '%mckinsey%' THEN 'McKinsey' WHEN LOWER(owner_prev_companies) LIKE '%bain%' THEN 'Bain' WHEN LOWER(owner_prev_companies) LIKE '%bcg%' THEN 'BCG' ELSE 'Other' END as group_key,owner_prev_companies,sector,state,status FROM deal_companies WHERE LOWER(owner_prev_companies) LIKE '%mckinsey%' OR LOWER(owner_prev_companies) LIKE '%bain%' OR LOWER(owner_prev_companies) LIKE '%bcg%' ORDER BY group_key,owner_name LIMIT 1000"}}

Example — "Top 5 grad schools":
{{"answer_sql":"SELECT owner_grad_school,COUNT(*) as n FROM deal_companies WHERE owner_grad_school IS NOT NULL GROUP BY owner_grad_school ORDER BY n DESC LIMIT 5","list_sql":"SELECT id,name,owner_name,owner_grad_school as group_key,owner_grad_school,sector,state,status FROM deal_companies WHERE owner_grad_school IN (SELECT owner_grad_school FROM deal_companies WHERE owner_grad_school IS NOT NULL GROUP BY owner_grad_school ORDER BY COUNT(*) DESC LIMIT 5) ORDER BY group_key,owner_name LIMIT 1000"}}

User question: {question}

JSON:"""

    try:
        sql_resp = client.messages.create(
            model='claude-sonnet-4-6',
            max_tokens=600,
            messages=[{'role': 'user', 'content': sql_prompt}]
        )
        raw_sql = sql_resp.content[0].text.strip()
        raw_sql = re.sub(r'^```(?:json)?\s*', '', raw_sql, flags=re.IGNORECASE)
        raw_sql = re.sub(r'\s*```$', '', raw_sql)
        parsed = json.loads(raw_sql)
        sql = parsed.get('answer_sql', '').strip().rstrip(';')
        list_sql = parsed.get('list_sql', '').strip().rstrip(';')
    except Exception as e:
        return jsonify({'error': f'SQL generation error: {e}'}), 500

    for s in [sql, list_sql]:
        if s and any(kw in s.upper() for kw in ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']):
            return jsonify({'error': 'Unsafe SQL blocked'}), 400

    try:
        conn = get_db()
        cursor = conn.execute(sql)
        cols = [d[0] for d in cursor.description]
        rows = cursor.fetchall()
        results = [dict(zip(cols, r)) for r in rows]

        row_previews = []
        list_cols = []
        if list_sql:
            try:
                lcursor = conn.execute(list_sql)
                list_cols = [d[0] for d in lcursor.description]
                lrows = lcursor.fetchall()
                for r in lrows:
                    row_previews.append(dict(zip(list_cols, r)))
            except Exception:
                pass
        conn.close()
    except Exception as e:
        return jsonify({'error': f'SQL error: {e}', 'sql': sql}), 400

    # Step 2: Stream the AI summary
    summary_prompt = f"""The user asked: "{question}"

Query results ({len(results)} rows):
{json.dumps(results[:50], indent=2)}

Provide a concise, insightful answer using the data. Use specific numbers and percentages. Format with markdown."""

    def stream_answer():
        yield f"data: {json.dumps({'sql': sql, 'row_count': len(results), 'rows': row_previews, 'cols': list_cols})}\n\n"
        try:
            with client.messages.stream(
                model='claude-sonnet-4-6',
                max_tokens=800,
                messages=[{'role': 'user', 'content': summary_prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream_answer()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/universe/<int:company_id>/research', methods=['POST'])
def research_owner(company_id):
    """Deep AI background research on a company owner, streamed."""
    conn = get_db()
    row = conn.execute('SELECT * FROM deal_companies WHERE id=?', (company_id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'Not found'}), 404
    c = dict(row)

    prompt = f"""You are a professional due diligence analyst at a search fund investment firm. Conduct a comprehensive background research report on the following business owner/CEO who is a potential acquisition target. Use your knowledge of companies, business schools, industries, and career patterns to provide the most thorough analysis possible.

SUBJECT PROFILE:
Name: {c.get('owner_name', 'Unknown')}
Age: {c.get('owner_age', 'Unknown')} | Gender: {c.get('owner_gender', 'Unknown')} | Ethnicity: {c.get('owner_ethnicity', 'Unknown')}
Company: {c.get('name', 'Unknown')} — {c.get('sector', '')} / {c.get('industry', '')} ({c.get('city', '')}, {c.get('state', '')})
Employees: {c.get('employees', 'Unknown')} | Founded: {c.get('founded_year', 'Unknown')}
Revenue: {'${:,.0f}'.format(c['revenue']) if c.get('revenue') else 'Unknown'} | EBITDA: {'${:,.0f}'.format(c['ebitda']) if c.get('ebitda') else 'Unknown'}
Undergraduate: {c.get('owner_undergrad_school', 'Not listed')} — {c.get('owner_undergrad_major', '')}
Graduate: {c.get('owner_grad_school', 'None')} ({c.get('owner_grad_degree', '')})
Years Experience: {c.get('owner_years_experience', 'Unknown')}
Previous Companies: {c.get('owner_prev_companies', 'None listed')}
Bio: {c.get('owner_bio', 'None provided')}
Business Description: {c.get('business_description', 'None')}

Write a detailed background research report with these sections. Be specific, analytical, and flag anything noteworthy:

## Identity & Credentials
Assess credibility of listed credentials. What does their education pedigree signal? Are there inconsistencies?

## Career Trajectory Analysis
Analyze their career path and previous companies. What roles/seniority levels can be inferred? Does the trajectory make sense for their age and experience?

## Industry Expertise
How well-suited is their background for running {c.get('name', 'this business')} in {c.get('sector', 'this sector')}? What sector knowledge and relationships do they likely bring?

## Network & Professional Circles
Based on education and previous employers, what professional networks are they likely part of? Any notable alumni networks, industry associations, or communities?

## Risk Flags & Concerns
Anything in this profile that warrants further scrutiny. Credential gaps, career inconsistencies, red flags for post-acquisition transition.

## Diligence Checklist
Specific, actionable steps to verify and extend this research: LinkedIn search terms, background check priorities, reference check angles, public records to pull.

## Acquisition Readiness Assessment
2-3 sentences on this owner as a counterparty: their likely motivations for selling, transition risk, and overall attractiveness as an acquisition target."""

    def stream():
        try:
            with client.messages.stream(
                model='claude-sonnet-4-6',
                max_tokens=2000,
                messages=[{'role': 'user', 'content': prompt}]
            ) as s:
                for text in s.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return Response(stream_with_context(stream()), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@app.route('/api/universe/heatmap')
def universe_heatmap():
    conn = get_db()
    rows = conn.execute(
        '''SELECT sector, state, COUNT(*) as n FROM deal_companies
           WHERE sector IS NOT NULL AND state IS NOT NULL
           GROUP BY sector, state''').fetchall()
    conn.close()
    matrix = {}
    state_totals = {}
    sector_totals = {}
    for r in rows:
        s, st, n = r['sector'], r['state'], r['n']
        matrix.setdefault(s, {})[st] = n
        state_totals[st] = state_totals.get(st, 0) + n
        sector_totals[s] = sector_totals.get(s, 0) + n
    top_states = [k for k, _ in sorted(state_totals.items(), key=lambda x: -x[1])[:15]]
    top_sectors = [k for k, _ in sorted(sector_totals.items(), key=lambda x: -x[1])[:12]]
    return jsonify({'sectors': top_sectors, 'states': top_states, 'matrix': matrix})


@app.route('/api/universe/stats')
def universe_stats():
    conn = get_db()
    total = conn.execute('SELECT COUNT(*) FROM deal_companies').fetchone()[0]
    if total == 0:
        conn.close()
        return jsonify({'total': 0})
    by_sector = [dict(r) for r in conn.execute(
        'SELECT sector, COUNT(*) as n FROM deal_companies GROUP BY sector ORDER BY n DESC').fetchall()]
    by_status = [dict(r) for r in conn.execute(
        'SELECT status, COUNT(*) as n FROM deal_companies GROUP BY status ORDER BY n DESC').fetchall()]
    by_grad = [dict(r) for r in conn.execute(
        '''SELECT owner_grad_school, COUNT(*) as n FROM deal_companies
        WHERE owner_grad_school IS NOT NULL
        GROUP BY owner_grad_school ORDER BY n DESC LIMIT 15''').fetchall()]
    conn.close()
    return jsonify({'total': total, 'by_sector': by_sector, 'by_status': by_status, 'by_grad': by_grad})


if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5001))
    key_ok = bool(os.environ.get('ANTHROPIC_API_KEY', '').startswith('sk-'))
    print(f"\n{'✓' if key_ok else '✗'} ANTHROPIC_API_KEY {'found' if key_ok else 'missing'}")
    print(f"→ Operand Intel running at http://localhost:{port}\n")
    app.run(debug=False, host='0.0.0.0', port=port)
