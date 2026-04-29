"""
Generate ~3000 synthetic deal_companies records with realistic owner profiles.
Run: python3 generate_universe.py
"""
import sqlite3, random, os, json
from itertools import cycle

DB_PATH = os.path.join(os.path.dirname(__file__), 'operand.db')

# ── Reference data ─────────────────────────────────────────────────────────────

FIRST_M = ['James','Robert','John','Michael','William','David','Richard','Joseph',
           'Thomas','Charles','Christopher','Daniel','Matthew','Anthony','Mark',
           'Donald','Steven','Paul','Andrew','Kenneth','Kevin','Brian','George',
           'Edward','Ronald','Timothy','Jason','Jeffrey','Ryan','Jacob','Gary',
           'Nicholas','Eric','Jonathan','Stephen','Larry','Justin','Scott','Brandon',
           'Raymond','Frank','Gregory','Samuel','Raymond','Patrick','Alexander',
           'Jack','Dennis','Jerry','Tyler','Aaron','Jose','Henry','Adam','Douglas',
           'Nathan','Peter','Zachary','Kyle','Walter','Harold','Jeremy','Ethan',
           'Carl','Keith','Roger','Gerald','Christian','Terry','Sean','Arthur',
           'Austin','Noah','Lawrence','Jesse','Joe','Bryan','Billy','Jordan','Albert']

FIRST_F = ['Mary','Patricia','Jennifer','Linda','Barbara','Elizabeth','Susan',
           'Jessica','Sarah','Karen','Lisa','Nancy','Betty','Margaret','Sandra',
           'Ashley','Dorothy','Kimberly','Emily','Donna','Michelle','Carol',
           'Amanda','Melissa','Deborah','Stephanie','Rebecca','Sharon','Laura',
           'Cynthia','Kathleen','Amy','Angela','Shirley','Anna','Brenda','Pamela',
           'Emma','Nicole','Helen','Samantha','Katherine','Christine','Debra',
           'Rachel','Carolyn','Janet','Catherine','Maria','Heather','Diane','Julie',
           'Joyce','Victoria','Kelly','Christina','Joan','Evelyn','Lauren','Judith',
           'Olivia','Martha','Cheryl','Megan','Andrea','Hannah','Jacqueline',
           'Gloria','Teresa','Sara','Janice','Ann','Alice','Jean','Kathryn','Grace',
           'Amber','Danielle','Brittany','Diana','Abigail','Virginia']

LAST = ['Smith','Johnson','Williams','Brown','Jones','Garcia','Miller','Davis',
        'Rodriguez','Martinez','Hernandez','Lopez','Gonzalez','Wilson','Anderson',
        'Thomas','Taylor','Moore','Jackson','Martin','Lee','Perez','Thompson',
        'White','Harris','Sanchez','Clark','Ramirez','Lewis','Robinson','Walker',
        'Young','Allen','King','Wright','Scott','Torres','Nguyen','Hill','Flores',
        'Green','Adams','Nelson','Baker','Hall','Rivera','Campbell','Mitchell',
        'Carter','Roberts','Phillips','Evans','Turner','Torres','Parker','Collins',
        'Edwards','Stewart','Flores','Morris','Nguyen','Murphy','Rivera','Cook',
        'Rogers','Morgan','Peterson','Cooper','Reed','Bailey','Bell','Gomez',
        'Kelly','Howard','Ward','Cox','Diaz','Richardson','Wood','Watson','Brooks',
        'Bennett','Gray','James','Reyes','Hughes','Price','Myers','Long','Foster',
        'Sanders','Ross','Morales','Powell','Sullivan','Russell','Ortiz','Jenkins',
        'Gutierrez','Perry','Butler','Barnes','Fisher','Henderson','Coleman','Simmons',
        'Patterson','Jordan','Reynolds','Hamilton','Graham','Kim','Gonzales','Alexander',
        'Ramos','Wallace','Griffin','West','Cole','Hayes','Chavez','Gibson','Bryant']

# Business school weightings (realistic for ETA/search fund universe)
GRAD_SCHOOLS = [
    ('University of Chicago (Booth)', 9),
    ('Northwestern (Kellogg)', 8),
    ('Harvard Business School', 10),
    ('Stanford GSB', 7),
    ('Wharton (UPenn)', 9),
    ('Columbia Business School', 6),
    ('MIT (Sloan)', 6),
    ('Dartmouth (Tuck)', 5),
    ('Michigan (Ross)', 5),
    ('Duke (Fuqua)', 5),
    ('UVA (Darden)', 4),
    ('Yale SOM', 4),
    ('UC Berkeley (Haas)', 4),
    ('UCLA (Anderson)', 3),
    ('Cornell (Johnson)', 3),
    ('Georgetown (McDonough)', 3),
    ('Notre Dame (Mendoza)', 2),
    ('Vanderbilt (Owen)', 2),
    ('Texas (McCombs)', 2),
    ('Indiana (Kelley)', 2),
    ('Emory (Goizueta)', 2),
    ('Georgetown (McDonough)', 2),
    ('Carnegie Mellon (Tepper)', 2),
    ('Washington University (Olin)', 2),
    ('University of Southern California (Marshall)', 2),
    ('Rice (Jones)', 2),
    ('Brigham Young (Marriott)', 1),
    ('Arizona State (Carey)', 1),
    ('Ohio State (Fisher)', 1),
    (None, 18),  # No grad degree
]

UNDERGRAD_SCHOOLS = [
    ('University of Michigan', 7),
    ('University of Illinois', 6),
    ('Indiana University', 5),
    ('University of Texas', 6),
    ('Ohio State University', 5),
    ('University of Wisconsin', 5),
    ('Penn State University', 5),
    ('Purdue University', 4),
    ('University of Florida', 5),
    ('University of Georgia', 4),
    ('University of North Carolina', 4),
    ('University of Virginia', 4),
    ('Georgetown University', 3),
    ('Boston College', 3),
    ('Notre Dame', 3),
    ('Vanderbilt University', 3),
    ('Emory University', 3),
    ('University of Southern California', 3),
    ('UC Berkeley', 3),
    ('UCLA', 3),
    ('Northwestern University', 3),
    ('Harvard University', 2),
    ('Yale University', 2),
    ('Princeton University', 2),
    ('Duke University', 2),
    ('Stanford University', 2),
    ('Cornell University', 3),
    ('Dartmouth College', 2),
    ('Washington University in St. Louis', 2),
    ('University of Chicago', 2),
    ('Tulane University', 2),
    ('Wake Forest University', 2),
    ('University of Miami', 2),
    ('Texas A&M University', 3),
    ('Michigan State University', 3),
    ('University of Minnesota', 3),
    ('University of Colorado', 2),
    ('University of Arizona', 2),
    ('Florida State University', 2),
    ('Auburn University', 2),
    ('Howard University', 1),
    ('Spelman College', 1),
    ('Morehouse College', 1),
    ('Hampton University', 1),
]

UNDERGRAD_MAJORS = [
    ('Finance', 12), ('Accounting', 10), ('Business Administration', 10),
    ('Economics', 9), ('Engineering (Mechanical)', 5), ('Engineering (Civil)', 4),
    ('Engineering (Electrical)', 4), ('Computer Science', 5), ('Marketing', 6),
    ('Management', 7), ('Political Science', 4), ('Psychology', 3),
    ('Communications', 3), ('Mathematics', 3), ('Chemistry', 2),
    ('Biology', 2), ('History', 2), ('English', 2), ('Information Systems', 3),
    ('Supply Chain Management', 2), ('Real Estate', 2), ('Healthcare Administration', 2),
]

PREV_COMPANIES = [
    'McKinsey & Company', 'Bain & Company', 'Boston Consulting Group',
    'Deloitte', 'PwC', 'KPMG', 'Ernst & Young', 'Accenture',
    'Goldman Sachs', 'Morgan Stanley', 'JP Morgan', 'Bank of America',
    'Wells Fargo', 'Citi', 'Blackstone', 'KKR', 'Apollo Global',
    'Carlyle Group', 'Warburg Pincus', 'General Atlantic',
    'Amazon', 'Google', 'Microsoft', 'Apple', 'Meta', 'Salesforce',
    'Oracle', 'SAP', 'IBM', 'Cisco',
    'General Electric', 'Honeywell', 'Emerson Electric', '3M', 'Parker Hannifin',
    'UnitedHealth Group', 'HCA Healthcare', 'Humana', 'Aetna',
    'ADP', 'Paychex', 'Robert Half', 'ManpowerGroup',
    'Sysco', 'US Foods', 'Aramark', 'Cintas',
    'Waste Management', 'Republic Services', 'Clean Harbors',
    'Fastenal', 'W.W. Grainger', 'MSC Industrial',
    'First Data', 'Fidelity National Information Services', 'NCR',
    'Private Equity Fund (lower-middle market)', 'Family Office',
    'Regional Bank', 'Community Bank', 'Insurance Company',
    'Startup (exited)', 'Family Business', 'Military (Officer)',
]

ETHNICITY_DIST = [
    ('White', 52), ('Hispanic / Latino', 12), ('Black / African American', 9),
    ('Asian', 14), ('South Asian', 7), ('Middle Eastern', 3),
    ('Mixed / Other', 2), ('Not Disclosed', 1),
]

SECTORS = [
    ('Business Services', 18), ('Healthcare Services', 14), ('Industrial Services', 13),
    ('Technology / SaaS', 9), ('Specialty Manufacturing', 10), ('Distribution', 8),
    ('Construction & Trades', 7), ('Consumer Services', 6), ('Education', 5),
    ('Logistics & Transportation', 5), ('Environmental Services', 3),
    ('Financial Services', 2),
]

INDUSTRIES = {
    'Business Services': ['Staffing & Recruiting', 'Payroll Services', 'Facilities Management',
                          'Commercial Cleaning', 'Security Services', 'Testing & Inspection',
                          'Compliance & Regulatory', 'Document Management', 'Printing Services',
                          'Office Equipment Services', 'Pest Control', 'Landscaping B2B'],
    'Healthcare Services': ['Home Health', 'Behavioral Health', 'Physical Therapy',
                             'Dental Services', 'Veterinary Services', 'Medical Staffing',
                             'Durable Medical Equipment', 'Pharmacy Services', 'Hospice',
                             'Laboratory Services', 'Diagnostic Imaging', 'Senior Care'],
    'Industrial Services': ['HVAC Services', 'Plumbing Services', 'Electrical Contracting',
                             'Fire Protection', 'Elevator Services', 'Industrial Maintenance',
                             'Equipment Rental', 'Calibration Services', 'NDT Inspection',
                             'Environmental Remediation', 'Waste Handling', 'Welding Services'],
    'Technology / SaaS': ['Vertical SaaS', 'Managed IT Services', 'Cybersecurity',
                          'IT Staffing', 'Data Analytics', 'ERP Implementation',
                          'Cloud Services', 'Field Service Software', 'Fleet Telematics'],
    'Specialty Manufacturing': ['Precision Machining', 'Metal Fabrication', 'Plastic Components',
                                 'Electronics Assembly', 'Specialty Chemicals', 'Packaging',
                                 'Rubber & Gaskets', 'Fasteners & Hardware', 'Filtration Products',
                                 'Safety Equipment', 'Custom Signage', 'Foam Products'],
    'Distribution': ['Industrial Distribution', 'Food Distribution', 'Safety Products',
                     'Janitorial Supplies', 'MRO Distribution', 'Electrical Distribution',
                     'Plumbing Supply', 'HVAC Supply', 'Paper & Packaging Supply'],
    'Construction & Trades': ['Specialty Contracting', 'Roofing', 'Flooring',
                               'Painting Contractor', 'Insulation', 'Waterproofing',
                               'Concrete', 'Demolition', 'Restoration Services'],
    'Consumer Services': ['Residential HVAC', 'Residential Plumbing', 'Pool Services',
                          'Auto Services', 'Pet Services', 'Moving & Storage',
                          'Tutoring', 'Fitness', 'Photography'],
    'Education': ['K-12 Tutoring', 'Vocational Training', 'Test Prep', 'Online Learning',
                  'Corporate Training', 'Language Schools', 'Childcare'],
    'Logistics & Transportation': ['Last-Mile Delivery', 'Freight Brokerage', 'Cold Chain',
                                    'Warehousing', 'Courier Services', 'Equipment Transport'],
    'Environmental Services': ['Environmental Consulting', 'Hazmat Services', 'Air Quality',
                               'Water Treatment', 'Soil Remediation', 'Recycling'],
    'Financial Services': ['Insurance Agency', 'Tax Preparation', 'Bookkeeping',
                           'Financial Planning', 'Mortgage Brokerage'],
}

STATES_CITIES = [
    ('TX', ['Houston', 'Dallas', 'Austin', 'San Antonio', 'Fort Worth']),
    ('FL', ['Miami', 'Tampa', 'Orlando', 'Jacksonville', 'Fort Lauderdale']),
    ('CA', ['Los Angeles', 'San Diego', 'Sacramento', 'San Jose', 'Fresno']),
    ('IL', ['Chicago', 'Naperville', 'Rockford', 'Aurora', 'Joliet']),
    ('OH', ['Columbus', 'Cleveland', 'Cincinnati', 'Dayton', 'Toledo']),
    ('GA', ['Atlanta', 'Savannah', 'Augusta', 'Columbus', 'Marietta']),
    ('NC', ['Charlotte', 'Raleigh', 'Greensboro', 'Durham', 'Winston-Salem']),
    ('PA', ['Philadelphia', 'Pittsburgh', 'Allentown', 'Erie', 'Reading']),
    ('MI', ['Detroit', 'Grand Rapids', 'Warren', 'Sterling Heights', 'Lansing']),
    ('NY', ['Buffalo', 'Rochester', 'Yonkers', 'Syracuse', 'Albany']),
    ('AZ', ['Phoenix', 'Tucson', 'Scottsdale', 'Mesa', 'Chandler']),
    ('TN', ['Nashville', 'Memphis', 'Knoxville', 'Chattanooga', 'Clarksville']),
    ('IN', ['Indianapolis', 'Fort Wayne', 'Evansville', 'South Bend', 'Carmel']),
    ('MO', ['Kansas City', 'St. Louis', 'Springfield', 'Columbia', 'Independence']),
    ('WI', ['Milwaukee', 'Madison', 'Green Bay', 'Kenosha', 'Racine']),
    ('MN', ['Minneapolis', 'Saint Paul', 'Rochester', 'Duluth', 'Bloomington']),
    ('CO', ['Denver', 'Colorado Springs', 'Aurora', 'Fort Collins', 'Lakewood']),
    ('VA', ['Virginia Beach', 'Richmond', 'Norfolk', 'Chesapeake', 'Arlington']),
    ('WA', ['Seattle', 'Spokane', 'Tacoma', 'Vancouver', 'Bellevue']),
    ('SC', ['Columbia', 'Charleston', 'Greenville', 'Rock Hill', 'Spartanburg']),
    ('AL', ['Birmingham', 'Montgomery', 'Huntsville', 'Mobile', 'Tuscaloosa']),
    ('KY', ['Louisville', 'Lexington', 'Bowling Green', 'Owensboro', 'Covington']),
    ('MD', ['Baltimore', 'Frederick', 'Rockville', 'Gaithersburg', 'Bowie']),
    ('KS', ['Wichita', 'Overland Park', 'Kansas City', 'Olathe', 'Topeka']),
    ('NE', ['Omaha', 'Lincoln', 'Bellevue', 'Grand Island', 'Kearney']),
    ('OK', ['Oklahoma City', 'Tulsa', 'Norman', 'Broken Arrow', 'Edmond']),
    ('LA', ['New Orleans', 'Baton Rouge', 'Shreveport', 'Lafayette', 'Metairie']),
    ('NV', ['Las Vegas', 'Henderson', 'Reno', 'North Las Vegas', 'Sparks']),
    ('UT', ['Salt Lake City', 'West Valley City', 'Provo', 'West Jordan', 'Orem']),
    ('AR', ['Little Rock', 'Fort Smith', 'Fayetteville', 'Springdale', 'Jonesboro']),
]

SOURCES = ['Broker (Axial)', 'Broker (BizBuySell)', 'Broker (Independent)', 'Direct Outreach',
           'Referral (Accountant)', 'Referral (Attorney)', 'Referral (Banker)',
           'Conference', 'Cold Email', 'LinkedIn', 'SBA Listing']

STATUSES = [('PROSPECT', 40), ('PASSED', 30), ('ACTIVE DILIGENCE', 12),
            ('LOI SIGNED', 5), ('ACQUIRED', 8), ('DEAD', 5)]

GRAD_DEGREES = ['MBA', 'MBA', 'MBA', 'MBA', 'MBA', 'MBA',
                'JD', 'MS', 'MPA', 'MHA', 'MEng', 'CPA (post-grad)']


def weighted_choice(choices):
    items = [item for item, w in choices for _ in range(w)]
    return random.choice(items)


def make_name(gender):
    first = random.choice(FIRST_F if gender == 'Female' else FIRST_M)
    return f"{first} {random.choice(LAST)}"


def make_company_name(sector, city):
    prefixes = ['Peak', 'Summit', 'Apex', 'Keystone', 'Landmark', 'Meridian', 'Pinnacle',
                'Cornerstone', 'Forge', 'Atlas', 'Beacon', 'Heritage', 'Patriot',
                'Cardinal', 'Sterling', 'Alliance', 'National', 'Midwest', 'Gulf Coast',
                'Tri-State', 'Continental', 'Heartland', 'Lakeside', 'Riverside',
                'Highland', 'Coastal', 'Interior', 'Premier', 'Elite', 'Pro',
                city.split()[0], city.split()[0]]
    suffixes_by_sector = {
        'Business Services': ['Solutions', 'Group', 'Services', 'Partners', 'Associates', 'Consulting'],
        'Healthcare Services': ['Health', 'Care', 'Medical', 'Healthcare', 'Wellness', 'Clinical'],
        'Industrial Services': ['Services', 'Industrial', 'Mechanical', 'Systems', 'Technical', 'Inc.'],
        'Technology / SaaS': ['Technologies', 'Systems', 'Software', 'Digital', 'Tech', 'Analytics'],
        'Specialty Manufacturing': ['Manufacturing', 'Industries', 'Fabrication', 'Products', 'Corp.'],
        'Distribution': ['Distribution', 'Supply', 'Logistics', 'Wholesale', 'Supply Co.'],
        'Construction & Trades': ['Contracting', 'Construction', 'Services', 'Group', 'Builders'],
        'Consumer Services': ['Services', 'Solutions', 'Group', 'Co.', 'Pros'],
        'Education': ['Learning', 'Education', 'Academy', 'Institute', 'Training'],
        'Logistics & Transportation': ['Logistics', 'Transport', 'Freight', 'Delivery', 'Express'],
        'Environmental Services': ['Environmental', 'Services', 'Solutions', 'Group', 'Inc.'],
        'Financial Services': ['Financial', 'Advisors', 'Group', 'Associates', 'Services'],
    }
    suffixes = suffixes_by_sector.get(sector, ['Group', 'Services', 'Solutions'])
    return f"{random.choice(prefixes)} {random.choice(suffixes)}"


BIO_TEMPLATES = [
    "{name} has {years} years of experience in {sector}. Prior to founding {company}, they held roles at {prev1} and {prev2}. {name} earned a {undergrad_major} degree from {undergrad} and {grad_line}.",
    "Before starting {company}, {name} spent {years} years across {prev1} and {prev2} in roles spanning {sector}. {name} holds a {undergrad_major} from {undergrad}{grad_line2}.",
    "{name} founded {company} after {years} years in {sector}, including tenures at {prev1} and {prev2}. Educational background: {undergrad_major}, {undergrad}{grad_line2}.",
    "With {years} years in {sector}, {name} built {company} from the ground up. Previously at {prev1} and {prev2}. {undergrad_major}, {undergrad}{grad_line2}.",
]


def make_bio(name, company, sector, years, undergrad, major, grad_school, grad_deg, prev1, prev2):
    grad_line = f"holds a {grad_deg} from {grad_school}" if grad_school else "did not pursue a graduate degree"
    grad_line2 = f"; {grad_deg} from {grad_school}" if grad_school else ""
    t = random.choice(BIO_TEMPLATES)
    return t.format(name=name, company=company, sector=sector, years=years,
                    prev1=prev1, prev2=prev2, undergrad=undergrad, undergrad_major=major,
                    grad_line=grad_line, grad_line2=grad_line2)


def generate(n=3000):
    conn = sqlite3.connect(DB_PATH)

    # Check if already populated
    existing = conn.execute('SELECT COUNT(*) FROM deal_companies').fetchone()[0]
    if existing >= 500:
        print(f"Already have {existing} records. Delete first to regenerate.")
        conn.close()
        return

    records = []
    for _ in range(n):
        gender = random.choice(['Male', 'Male', 'Male', 'Female', 'Female'])
        owner_name = make_name(gender)
        ethnicity = weighted_choice(ETHNICITY_DIST)
        sector = weighted_choice(SECTORS)
        industry = random.choice(INDUSTRIES.get(sector, ['General']))
        state, cities = random.choice(STATES_CITIES)
        city = random.choice(cities)

        undergrad = weighted_choice(UNDERGRAD_SCHOOLS)
        major = weighted_choice(UNDERGRAD_MAJORS)
        grad_raw = weighted_choice(GRAD_SCHOOLS)
        grad_school = grad_raw
        grad_degree = random.choice(GRAD_DEGREES) if grad_school else None

        prev1 = random.choice(PREV_COMPANIES)
        prev2 = random.choice([p for p in PREV_COMPANIES if p != prev1])
        prev_companies = f"{prev1}; {prev2}"

        age = random.randint(35, 68)
        years_exp = random.randint(8, age - 25)
        founded = random.randint(1985, 2018)

        employees = random.choice([
            random.randint(5, 25), random.randint(25, 75), random.randint(75, 200),
            random.randint(200, 500)
        ])
        rev_base = random.choice([
            random.uniform(1.5, 5), random.uniform(5, 15), random.uniform(15, 40),
            random.uniform(40, 80)
        ])
        revenue = round(rev_base * 1_000_000, -3)
        margin = round(random.uniform(0.08, 0.28), 3)
        ebitda = round(revenue * margin, -3)
        ebitda_margin = round(margin * 100, 1)
        mult = round(random.uniform(3.5, 8.5), 1)
        asking_price = round(ebitda * mult, -3)
        rev_mult = round(asking_price / revenue, 2) if revenue else None

        company_name = make_company_name(sector, city)
        bio = make_bio(owner_name, company_name, sector, years_exp, undergrad, major,
                       grad_school, grad_degree, prev1, prev2)

        status = weighted_choice(STATUSES)
        source = random.choice(SOURCES)

        records.append((
            company_name, sector, industry, None, state, city, founded, employees,
            revenue, ebitda, ebitda_margin, asking_price, rev_mult, mult,
            status, source,
            f"{industry} company serving {city} and surrounding {state} market.",
            owner_name, age, gender, ethnicity,
            undergrad, major, grad_school, grad_degree,
            years_exp, prev_companies, bio, None
        ))

    conn.executemany('''INSERT INTO deal_companies
        (name,sector,industry,sub_industry,state,city,founded_year,employees,
         revenue,ebitda,ebitda_margin,asking_price,revenue_multiple,ebitda_multiple,
         status,source,business_description,
         owner_name,owner_age,owner_gender,owner_ethnicity,
         owner_undergrad_school,owner_undergrad_major,owner_grad_school,owner_grad_degree,
         owner_years_experience,owner_prev_companies,owner_bio,notes)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', records)

    conn.commit()
    count = conn.execute('SELECT COUNT(*) FROM deal_companies').fetchone()[0]
    conn.close()
    print(f"Generated {len(records)} records. Total in DB: {count}")

    # Print quick distribution check
    conn2 = sqlite3.connect(DB_PATH)
    print("\nTop grad schools:")
    for row in conn2.execute('''SELECT owner_grad_school, COUNT(*) as n FROM deal_companies
        WHERE owner_grad_school IS NOT NULL
        GROUP BY owner_grad_school ORDER BY n DESC LIMIT 10''').fetchall():
        print(f"  {row[0]}: {row[1]}")
    conn2.close()


if __name__ == '__main__':
    generate(3000)
