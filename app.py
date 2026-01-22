# app.py
from flask import Flask, render_template, jsonify, request
import sqlite3
import json
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATABASE = 'curriculum.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Returns rows as dictionaries
    return conn

# Helper function to execute query and return results
def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.execute(query, args)
    rv = cur.fetchall()
    conn.close()
    return (rv[0] if rv else None) if one else rv

# Home route - serves the HTML page
@app.route('/')
def index():
    # Provide initial data for the page
    program = 'BSCS'
    try:
        # Load courses
        results = query_db(f"""
            SELECT * FROM {program}
            ORDER BY CASE year_level 
                WHEN 'First Year' THEN 1
                WHEN 'Second Year' THEN 2
                WHEN 'Third Year' THEN 3
                WHEN 'Fourth Year' THEN 4
                WHEN 'ELECTIVES' THEN 5
                ELSE 6
            END,
            CASE term 
                WHEN 'FIRST TRIMESTER' THEN 1
                WHEN 'SECOND TRIMESTER' THEN 2
                WHEN 'THIRD TRIMESTER' THEN 3
                WHEN 'OJT TERM' THEN 4
                WHEN 'ELECTIVES' THEN 5
                ELSE 6
            END,
            code
        """)
        courses = [dict(row) for row in results]
        
        # Load years
        years_rows = query_db(f"SELECT DISTINCT year_level FROM {program} ORDER BY CASE year_level WHEN 'First Year' THEN 1 WHEN 'Second Year' THEN 2 WHEN 'Third Year' THEN 3 WHEN 'Fourth Year' THEN 4 WHEN 'ELECTIVES' THEN 5 ELSE 6 END")
        years = [row['year_level'] for row in years_rows]
        
        # Load terms
        terms_rows = query_db(f"SELECT DISTINCT term FROM {program} ORDER BY CASE term WHEN 'FIRST TRIMESTER' THEN 1 WHEN 'SECOND TRIMESTER' THEN 2 WHEN 'THIRD TRIMESTER' THEN 3 WHEN 'OJT TERM' THEN 4 WHEN 'ELECTIVES' THEN 5 ELSE 6 END")
        terms = [row['term'] for row in terms_rows]
        
        initial_data = {
            'program': program,
            'courses': courses,
            'years': years,
            'terms': terms
        }
    except Exception as e:
        print(f"Error loading initial data: {e}")
        initial_data = {'program': program, 'courses': [], 'years': [], 'terms': []}
    
    return render_template('index.html', initial_data=initial_data)

# Get all courses for a specific program
@app.route('/api/courses/<program>')
def get_courses(program):
    # Validate program
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    # Order by year, term, and code
    query = f"""
        SELECT * FROM {table_name}
        ORDER BY CASE year_level 
            WHEN 'First Year' THEN 1
            WHEN 'Second Year' THEN 2
            WHEN 'Third Year' THEN 3
            WHEN 'Fourth Year' THEN 4
            WHEN 'ELECTIVES' THEN 5
            ELSE 6
        END,
        CASE term 
            WHEN 'FIRST TRIMESTER' THEN 1
            WHEN 'SECOND TRIMESTER' THEN 2
            WHEN 'THIRD TRIMESTER' THEN 3
            WHEN 'OJT TERM' THEN 4
            WHEN 'ELECTIVES' THEN 5
            ELSE 6
        END,
        code
    """
    
    try:
        results = query_db(query)
        courses = [dict(row) for row in results]
        return jsonify(courses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get available subjects based on passed subjects
@app.route('/api/available-subjects/<program>', methods=['POST'])
def get_available_subjects(program):
    # Validate program
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    # Get passed subjects from request body
    data = request.get_json()
    passed_subjects = data.get('passed_subjects', [])
    passed_codes = [s.upper().strip() for s in passed_subjects]
    
    try:
        # Get all courses
        results = query_db(f"SELECT * FROM {table_name}")
        all_courses = [dict(row) for row in results]
        
        available = []
        unavailable = []
        passed = []
        
        for course in all_courses:
            code = course['code'].upper().strip() if course['code'] else ''
            prereq = course['prereq'].upper().strip() if course['prereq'] else 'NONE'
            coreq = course['coreq'].upper().strip() if course['coreq'] else 'NONE'
            
            # If already passed
            if code in passed_codes:
                course['status'] = 'passed'
                passed.append(course)
                continue
            
            # Check prerequisites
            prereq_met = True
            missing_prereqs = []
            
            if prereq and prereq != 'NONE' and prereq != '-' and prereq != 'N/A':
                # Split prerequisites by common delimiters
                prereq_list = [p.strip() for p in prereq.replace('&', ',').replace('AND', ',').replace(';', ',').split(',')]
                prereq_list = [p for p in prereq_list if p and p != 'NONE' and p != '-' and p != 'N/A']
                
                for p in prereq_list:
                    # Handle "or" conditions - if any is passed, prereq is met
                    if ' OR ' in p.upper():
                        or_options = [opt.strip() for opt in p.upper().split(' OR ')]
                        if not any(opt in passed_codes for opt in or_options):
                            prereq_met = False
                            missing_prereqs.append(p)
                    elif p.upper() not in passed_codes:
                        prereq_met = False
                        missing_prereqs.append(p)
            
            course['missing_prereqs'] = missing_prereqs
            
            if prereq_met:
                course['status'] = 'available'
                available.append(course)
            else:
                course['status'] = 'locked'
                unavailable.append(course)
        
        # Sort available courses by year and term
        def sort_key(c):
            year_order = {'First Year': 1, 'Second Year': 2, 'Third Year': 3, 'Fourth Year': 4, 'ELECTIVES': 5}
            term_order = {'FIRST TRIMESTER': 1, 'SECOND TRIMESTER': 2, 'THIRD TRIMESTER': 3, 'OJT TERM': 4, 'ELECTIVES': 5}
            return (
                year_order.get(c.get('year_level', ''), 6),
                term_order.get(c.get('term', ''), 6),
                c.get('code', '')
            )
        
        available.sort(key=sort_key)
        unavailable.sort(key=sort_key)
        passed.sort(key=sort_key)
        
        # Determine the next term based on passed subjects
        year_order = {'First Year': 1, 'Second Year': 2, 'Third Year': 3, 'Fourth Year': 4, 'ELECTIVES': 5}
        term_order = {'FIRST TRIMESTER': 1, 'SECOND TRIMESTER': 2, 'THIRD TRIMESTER': 3, 'OJT TERM': 4, 'ELECTIVES': 5}
        reverse_year = {1: 'First Year', 2: 'Second Year', 3: 'Third Year', 4: 'Fourth Year', 5: 'ELECTIVES'}
        reverse_term = {1: 'FIRST TRIMESTER', 2: 'SECOND TRIMESTER', 3: 'THIRD TRIMESTER', 4: 'OJT TERM', 5: 'ELECTIVES'}
        
        # Find the latest term from passed subjects
        latest_year = 0
        latest_term = 0
        for c in passed:
            y = year_order.get(c.get('year_level', ''), 0)
            t = term_order.get(c.get('term', ''), 0)
            if y > latest_year or (y == latest_year and t > latest_term):
                latest_year = y
                latest_term = t
        
        # Calculate next term
        next_year = latest_year
        next_term = latest_term + 1
        if next_term > 3:  # After 3rd term, move to next year 1st term
            next_term = 1
            next_year = latest_year + 1
        
        # If no passed subjects, start with First Year, First Term
        if latest_year == 0:
            next_year = 1
            next_term = 1
        
        next_year_name = reverse_year.get(next_year, 'First Year')
        next_term_name = reverse_term.get(next_term, 'FIRST TRIMESTER')
        
        # Filter available subjects that are in the next term (recommended)
        recommended = []
        for c in available:
            c_year = year_order.get(c.get('year_level', ''), 0)
            c_term = term_order.get(c.get('term', ''), 0)
            if c_year == next_year and c_term == next_term:
                recommended.append(c)
        
        # Calculate statistics
        total_passed_units = sum(c.get('total_units', 0) or 0 for c in passed)
        total_available_units = sum(c.get('total_units', 0) or 0 for c in available)
        total_curriculum_units = sum(c.get('total_units', 0) or 0 for c in all_courses)
        recommended_units = sum(c.get('total_units', 0) or 0 for c in recommended)
        
        return jsonify({
            'available': available,
            'unavailable': unavailable,
            'passed': passed,
            'recommended': recommended,
            'next_term': {
                'year': next_year_name,
                'term': next_term_name,
                'display': f"{next_year_name} - {next_term_name}"
            },
            'current_term': {
                'year': reverse_year.get(latest_year, 'None'),
                'term': reverse_term.get(latest_term, 'None')
            },
            'stats': {
                'total_courses': len(all_courses),
                'passed_count': len(passed),
                'available_count': len(available),
                'locked_count': len(unavailable),
                'recommended_count': len(recommended),
                'total_passed_units': total_passed_units,
                'total_available_units': total_available_units,
                'total_curriculum_units': total_curriculum_units,
                'recommended_units': recommended_units,
                'progress_percentage': round((total_passed_units / total_curriculum_units * 100) if total_curriculum_units > 0 else 0, 1)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get unique year levels for a program
@app.route('/api/years/<program>')
def get_years(program):
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    query = f"""
        SELECT DISTINCT year_level 
        FROM {table_name} 
        ORDER BY CASE year_level 
            WHEN 'First Year' THEN 1
            WHEN 'Second Year' THEN 2
            WHEN 'Third Year' THEN 3
            WHEN 'Fourth Year' THEN 4
            WHEN 'ELECTIVES' THEN 5
            ELSE 6
        END
    """
    
    try:
        results = query_db(query)
        years = [row['year_level'] for row in results]
        return jsonify(years)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get unique terms for a program
@app.route('/api/terms/<program>')
def get_terms(program):
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    query = f"""
        SELECT DISTINCT term 
        FROM {table_name} 
        ORDER BY CASE term 
            WHEN 'FIRST TRIMESTER' THEN 1
            WHEN 'SECOND TRIMESTER' THEN 2
            WHEN 'THIRD TRIMESTER' THEN 3
            WHEN 'OJT TERM' THEN 4
            WHEN 'ELECTIVES' THEN 5
            ELSE 6
        END
    """
    
    try:
        results = query_db(query)
        terms = [row['term'] for row in results]
        return jsonify(terms)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get database info
@app.route('/api/db-info')
def get_db_info():
    try:
        conn = get_db_connection()
        
        # Get table counts
        tables = ['BSCS', 'BSIS', 'BSIT']
        counts = {}
        total_records = 0
        
        for table in tables:
            cur = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            counts[table] = count
            total_records += count
        
        # Get database file info
        import os
        db_size = os.path.getsize(DATABASE) if os.path.exists(DATABASE) else 0
        
        info = {
            'tables': counts,
            'total_records': total_records,
            'database_size_kb': round(db_size / 1024, 2),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        conn.close()
        return jsonify(info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create database if it doesn't exist
    import os
    if not os.path.exists(DATABASE):
        print(f"Database '{DATABASE}' not found. Please run the SQL script to create it.")
        print("Command: sqlite3 curriculum.db < create_database.sql")
    
    # Run without the reloader to avoid child/parent process routing issues
    app.run(debug=True, use_reloader=False, port=5000)