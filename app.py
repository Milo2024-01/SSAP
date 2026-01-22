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
    # Provide initial data for the index page to render the curriculum
    # This ensures the page shows data even if the client-side API calls fail
    program = 'BSCS'

    # Load years
    try:
        years_rows = query_db(f"SELECT DISTINCT year_level FROM {program} ORDER BY CASE year_level WHEN 'First Year' THEN 1 WHEN 'Second Year' THEN 2 WHEN 'Third Year' THEN 3 WHEN 'Fourth Year' THEN 4 WHEN 'ELECTIVES' THEN 5 ELSE 6 END")
        years = [row['year_level'] for row in years_rows]
    except Exception:
        years = []

    # Load terms
    try:
        terms_rows = query_db(f"SELECT DISTINCT term FROM {program} ORDER BY CASE term WHEN 'FIRST TRIMESTER' THEN 1 WHEN 'SECOND TRIMESTER' THEN 2 WHEN 'THIRD TRIMESTER' THEN 3 WHEN 'OJT TERM' THEN 4 WHEN 'ELECTIVES' THEN 5 ELSE 6 END")
        terms = [row['term'] for row in terms_rows]
    except Exception:
        terms = []

    # Load courses (default: no filters)
    try:
        courses_rows = query_db(f"SELECT * FROM {program} ORDER BY code")
        courses = [dict(r) for r in courses_rows]
    except Exception:
        courses = []

    # Load basic stats
    try:
        stat_row = query_db(f"SELECT COUNT(*) as total_courses, SUM(lec_units) as total_lec_units, SUM(lab_units) as total_lab_units, SUM(total_units) as total_units FROM {program}", one=True)
        stats = dict(stat_row) if stat_row else {'total_courses': 0, 'total_lec_units': 0, 'total_lab_units': 0, 'total_units': 0}
        for k in list(stats.keys()):
            if stats[k] is None:
                stats[k] = 0
    except Exception:
        stats = {'total_courses': 0, 'total_lec_units': 0, 'total_lab_units': 0, 'total_units': 0}

    # Database info (include table counts)
    try:
        import os
        db_size = os.path.getsize(DATABASE) if os.path.exists(DATABASE) else 0
        conn = get_db_connection()
        tables_counts = {}
        total_records = 0
        for tbl in ['BSCS', 'BSIS', 'BSIT']:
            cur = conn.execute(f"SELECT COUNT(*) as cnt FROM {tbl}")
            cnt = cur.fetchone()['cnt']
            tables_counts[tbl] = cnt
            total_records += cnt
        conn.close()
        db_info = {
            'tables': tables_counts,
            'total_records': total_records,
            'database_size_kb': round(db_size / 1024, 2),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception:
        db_info = {'tables': {}, 'total_records': 0, 'database_size_kb': 0, 'last_updated': ''}

    initial_data = {
        'program': program,
        'years': years,
        'terms': terms,
        'courses': courses,
        'stats': stats,
        'db_info': db_info
    }

    return render_template('index.html', initial_data=initial_data)

# Get all courses for a specific program
@app.route('/api/courses/<program>')
def get_courses(program):
    # Validate program
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    # Get query parameters
    year = request.args.get('year', 'all')
    term = request.args.get('term', 'all')
    search = request.args.get('search', '')
    
    # Build query
    query = f"SELECT * FROM {table_name} WHERE 1=1"
    params = []
    
    # Add filters
    if year and year != 'all':
        query += " AND year_level = ?"
        params.append(year)
    
    if term and term != 'all':
        query += " AND term = ?"
        params.append(term)
    
    if search:
        query += " AND (code LIKE ? OR subject_course LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    # Order by year, term, and code
    query += """
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
        results = query_db(query, params)
        courses = [dict(row) for row in results]
        return jsonify(courses)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Get statistics for a program
@app.route('/api/stats/<program>')
def get_stats(program):
    valid_programs = ['BSCS', 'BSIS', 'BSIT']
    if program.upper() not in valid_programs:
        return jsonify({'error': 'Invalid program'}), 400
    
    table_name = program.upper()
    
    # Get query parameters
    year = request.args.get('year', 'all')
    term = request.args.get('term', 'all')
    search = request.args.get('search', '')
    
    # Build query
    query = f"""
        SELECT 
            COUNT(*) as total_courses,
            SUM(lec_units) as total_lec_units,
            SUM(lab_units) as total_lab_units,
            SUM(total_units) as total_units
        FROM {table_name} 
        WHERE 1=1
    """
    
    params = []
    
    # Add filters
    if year and year != 'all':
        query += " AND year_level = ?"
        params.append(year)
    
    if term and term != 'all':
        query += " AND term = ?"
        params.append(term)
    
    if search:
        query += " AND (code LIKE ? OR subject_course LIKE ?)"
        search_term = f"%{search}%"
        params.extend([search_term, search_term])
    
    try:
        result = query_db(query, params, one=True)
        if result:
            stats = dict(result)
            # Convert None to 0
            for key in stats:
                if stats[key] is None:
                    stats[key] = 0
            return jsonify(stats)
        return jsonify({
            'total_courses': 0,
            'total_lec_units': 0,
            'total_lab_units': 0,
            'total_units': 0
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