from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from database import get_db, init_db, ensure_columns
import io
import pandas as pd
from flask import send_file
import os
from datetime import datetime, date, timedelta
import shutil

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'devsecret')

DB_PATH = os.path.join('database', 'leads.db')
BACKUP_DIR = 'backups'


def setup():
    os.makedirs('database', exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    init_db(DB_PATH)
    # ensure schema migrations (add columns) on existing DBs
    ensure_columns(DB_PATH)

# Ensure DB and folders exist on startup (call at import/run time)
setup()


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, '%Y-%m-%d').date()
    except ValueError:
        return None


@app.route('/')
def dashboard():
    db = get_db(DB_PATH)
    cur = db.cursor()
    stats = {}
    cur.execute('SELECT COUNT(*) FROM leads')
    stats['total_leads'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leads WHERE status = 'New'")
    stats['new_leads'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leads WHERE status = 'Interested'")
    stats['interested_leads'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leads WHERE status = 'Converted'")
    stats['converted_leads'] = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM leads WHERE status = 'Lost'")
    stats['lost_leads'] = cur.fetchone()[0]

    today = date.today()
    tomorrow = today + timedelta(days=1)
    cur.execute('SELECT COUNT(*) FROM leads WHERE call_on = ?', (today.isoformat(),))
    stats['calls_today'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM leads WHERE call_on < ? AND status NOT IN ("Converted","Lost")', (today.isoformat(),))
    stats['overdue_calls'] = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM leads WHERE call_on = ?', (tomorrow.isoformat(),))
    stats['calls_tomorrow'] = cur.fetchone()[0]

    return render_template('dashboard.html', stats=stats)


@app.route('/leads')
def leads():
    db = get_db(DB_PATH)
    cur = db.cursor()
    cur.execute('''
        SELECT l.lead_id, c.name, c.mobile, l.product, l.status, l.call_on, l.call_type, l.priority, l.updated_at,
               (SELECT COUNT(*) FROM follow_up_notes n WHERE n.lead_id = l.lead_id) as notes_count
        FROM leads l
        JOIN clients c ON c.client_id = l.client_id
        ORDER BY l.updated_at DESC
    ''')
    rows = cur.fetchall()
    return render_template('leads.html', leads=rows)


@app.route('/lead/<int:lead_id>')
def lead_detail(lead_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    cur.execute('''
        SELECT l.*, c.name, c.mobile FROM leads l JOIN clients c ON c.client_id = l.client_id WHERE l.lead_id = ?
    ''', (lead_id,))
    lead = cur.fetchone()
    if not lead:
        flash('Lead not found', 'danger')
        return redirect(url_for('leads'))
    cur.execute('SELECT * FROM follow_up_notes WHERE lead_id = ? ORDER BY created_at ASC', (lead_id,))
    notes = cur.fetchall()
    return render_template('lead_detail.html', lead=lead, notes=notes)


@app.route('/lead/<int:lead_id>/notes_json')
def lead_notes_json(lead_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    cur.execute('SELECT note, created_at FROM follow_up_notes WHERE lead_id = ? ORDER BY created_at ASC', (lead_id,))
    rows = cur.fetchall()
    notes = [{'note': r['note'], 'created_at': r['created_at']} for r in rows]
    from flask import jsonify
    return jsonify(notes)


@app.route('/add', methods=['GET', 'POST'])
def add_lead():
    db = get_db(DB_PATH)
    cur = db.cursor()
    statuses = ['New','Contacted','Interested','Quotation Sent','Negotiating','Converted','Not Interested','Lost']
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        mobile = request.form.get('mobile','').strip()
        product = request.form.get('product','').strip()
        status = request.form.get('status')
        call_type = request.form.get('call_type','Call')
        priority = request.form.get('priority','Normal')
        call_on = parse_date(request.form.get('call_on'))
        note = request.form.get('note','').strip()
        errors = []
        if not name:
            errors.append('Client name is required')
        if not mobile:
            errors.append('Mobile number is required')
        if not product:
            errors.append('Product is required')
        if status not in statuses:
            errors.append('Invalid status')
        if errors:
            for e in errors:
                flash(e, 'danger')
            return render_template('add_lead.html', statuses=statuses, form=request.form)

        # find or create client by mobile
        cur.execute('SELECT client_id FROM clients WHERE mobile = ?', (mobile,))
        r = cur.fetchone()
        if r:
            client_id = r[0]
        else:
            created_at = datetime.utcnow().isoformat()
            cur.execute('INSERT INTO clients (name,mobile,created_at) VALUES (?,?,?)', (name,mobile,created_at))
            client_id = cur.lastrowid

        now = datetime.utcnow().isoformat()
        call_on_val = call_on.isoformat() if call_on else None
        cur.execute('INSERT INTO leads (client_id,product,status,call_on,call_type,priority,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)',
                (client_id, product, status, call_on_val, call_type, priority, now, now))
        lead_id = cur.lastrowid
        if note:
            cur.execute('INSERT INTO follow_up_notes (lead_id,note,created_at) VALUES (?,?,?)', (lead_id,note,now))
        db.commit()
        flash('Lead added', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    return render_template('add_lead.html', statuses=statuses)


@app.route('/edit/<int:lead_id>', methods=['GET','POST'])
def edit_lead(lead_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    statuses = ['New','Contacted','Interested','Quotation Sent','Negotiating','Converted','Not Interested','Lost']
    cur.execute('SELECT l.*, c.name, c.mobile FROM leads l JOIN clients c ON c.client_id = l.client_id WHERE l.lead_id = ?', (lead_id,))
    lead = cur.fetchone()
    if not lead:
        flash('Lead not found', 'danger')
        return redirect(url_for('leads'))

    if request.method == 'POST':
        product = request.form.get('product','').strip()
        status = request.form.get('status')
        call_type = request.form.get('call_type','Call')
        priority = request.form.get('priority','Normal')
        call_on = parse_date(request.form.get('call_on'))
        client_name = request.form.get('name','').strip()
        client_mobile = request.form.get('mobile','').strip()
        errors = []
        if not client_name:
            errors.append('Client name is required')
        if not client_mobile:
            errors.append('Mobile is required')
        if not product:
            errors.append('Product is required')
        if status not in statuses:
            errors.append('Invalid status')
        if errors:
            for e in errors:
                flash(e,'danger')
            return render_template('edit_lead.html', lead=lead, statuses=statuses)

        # update client
        cur.execute('UPDATE clients SET name = ?, mobile = ? WHERE client_id = ?', (client_name, client_mobile, lead['client_id']))
        now = datetime.utcnow().isoformat()
        call_on_val = call_on.isoformat() if call_on else None
        cur.execute('UPDATE leads SET product = ?, status = ?, call_on = ?, call_type = ?, priority = ?, updated_at = ? WHERE lead_id = ?', (product, status, call_on_val, call_type, priority, now, lead_id))
        db.commit()
        flash('Lead updated', 'success')
        return redirect(url_for('lead_detail', lead_id=lead_id))

    return render_template('edit_lead.html', lead=lead, statuses=statuses)


@app.route('/lead/<int:lead_id>/add_note', methods=['POST'])
def add_note(lead_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    note = request.form.get('note','').strip()
    if not note:
        flash('Note cannot be empty', 'danger')
        return redirect(url_for('lead_detail', lead_id=lead_id))
    now = datetime.utcnow().isoformat()
    cur.execute('INSERT INTO follow_up_notes (lead_id,note,created_at) VALUES (?,?,?)', (lead_id,note,now))
    cur.execute('UPDATE leads SET updated_at = ? WHERE lead_id = ?', (now, lead_id))
    db.commit()
    flash('Note added', 'success')
    return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/note/<int:note_id>/delete', methods=['POST'])
def delete_note(note_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    # find lead_id for redirect and ensure note exists
    cur.execute('SELECT lead_id FROM follow_up_notes WHERE note_id = ?', (note_id,))
    r = cur.fetchone()
    if not r:
        flash('Note not found', 'danger')
        return redirect(url_for('leads'))
    lead_id = r['lead_id']
    cur.execute('DELETE FROM follow_up_notes WHERE note_id = ?', (note_id,))
    now = datetime.utcnow().isoformat()
    cur.execute('UPDATE leads SET updated_at = ? WHERE lead_id = ?', (now, lead_id))
    db.commit()
    flash('Note deleted', 'success')
    return redirect(url_for('lead_detail', lead_id=lead_id))


@app.route('/delete/<int:lead_id>', methods=['POST'])
def delete_lead(lead_id):
    db = get_db(DB_PATH)
    cur = db.cursor()
    cur.execute('SELECT lead_id FROM leads WHERE lead_id = ?', (lead_id,))
    if not cur.fetchone():
        flash('Lead not found', 'danger')
        return redirect(url_for('leads'))
    cur.execute('DELETE FROM leads WHERE lead_id = ?', (lead_id,))
    db.commit()
    flash('Lead deleted', 'success')
    return redirect(url_for('leads'))


@app.route('/search')
def search():
    db = get_db(DB_PATH)
    cur = db.cursor()
    name = request.args.get('name','').strip()
    mobile = request.args.get('mobile','').strip()
    product = request.args.get('product','').strip()
    status = request.args.get('status','').strip()
    call_on = request.args.get('call_on','').strip()
    call_type = request.args.get('call_type','').strip()
    priority = request.args.get('priority','').strip()
    lead_id = request.args.get('lead_id','').strip()

    query = '''
        SELECT l.lead_id, c.name, c.mobile, l.product, l.status, l.call_on, l.updated_at,
               (SELECT COUNT(*) FROM follow_up_notes n WHERE n.lead_id = l.lead_id) as notes_count
        FROM leads l JOIN clients c ON c.client_id = l.client_id
        WHERE 1=1
    '''
    params = []
    if name:
        query += ' AND c.name LIKE ?'
        params.append(f'%{name}%')
    if mobile:
        query += ' AND c.mobile LIKE ?'
        params.append(f'%{mobile}%')
    if product:
        query += ' AND l.product LIKE ?'
        params.append(f'%{product}%')
    if status:
        query += ' AND l.status = ?'
        params.append(status)
    if call_on:
        query += ' AND l.call_on = ?'
        params.append(call_on)
    if call_type:
        query += ' AND l.call_type = ?'
        params.append(call_type)
    if priority:
        query += ' AND l.priority = ?'
        params.append(priority)
    if lead_id:
        query += ' AND l.lead_id = ?'
        params.append(lead_id)
    query += ' ORDER BY l.updated_at DESC'
    cur.execute(query, tuple(params))
    rows = cur.fetchall()
    statuses = ['New','Contacted','Interested','Quotation Sent','Negotiating','Converted','Not Interested','Lost']
    return render_template('search.html', leads=rows, statuses=statuses, form=request.args)


@app.route('/calls')
def calls():
    try:
        db = get_db(DB_PATH)
        cur = db.cursor()
        filter_type = request.args.get('filter','today')
        d = request.args.get('date')
        type_filter = request.args.get('type','all')
        today = date.today()
        if d:
            target = parse_date(d)
            filter_type = 'date'
        else:
            target = today

        base_q = "SELECT l.lead_id, c.name, c.mobile, l.product, l.status, l.call_on, l.call_type, l.priority FROM leads l JOIN clients c ON c.client_id = l.client_id"
        where = []
        params = []
        if filter_type == 'today':
            where.append('l.call_on = ?')
            params.append(today.isoformat())
        elif filter_type == 'tomorrow':
            t = today + timedelta(days=1)
            where.append('l.call_on = ?')
            params.append(t.isoformat())
        elif filter_type == 'overdue':
            where.append("l.call_on < ? AND l.status NOT IN ('Converted','Lost')")
            params.append(today.isoformat())
        elif filter_type == 'upcoming':
            where.append('l.call_on > ?')
            params.append(today.isoformat())
        elif filter_type == 'all':
            where.append('l.call_on IS NOT NULL')
        elif filter_type == 'date' and target:
            where.append('l.call_on = ?')
            params.append(target.isoformat())
        else:
            where.append('l.call_on = ?')
            params.append(today.isoformat())

        if type_filter and type_filter.lower() in ('call', 'meet'):
            where.append('l.call_type = ?')
            params.append(type_filter.capitalize())

        query = base_q + (' WHERE ' + ' AND '.join(where) if where else '') + ' ORDER BY l.call_on'
        cur.execute(query, tuple(params))
        rows = cur.fetchall()
        # convert call_on from string to date where possible for template comparisons
        processed = []
        for r in rows:
            rd = dict(r)
            co = rd.get('call_on')
            if co:
                try:
                    rd['call_on'] = datetime.fromisoformat(co).date()
                except Exception:
                    # leave as-is if cannot parse
                    rd['call_on'] = co
            processed.append(rd)
        return render_template('calls.html', leads=processed, filter=filter_type, date=target, today_date=today, type_filter=type_filter)
    except Exception as e:
        import traceback, sys
        traceback.print_exc(file=sys.stderr)
        flash('Error loading Calls: ' + str(e), 'danger')
        return redirect(url_for('dashboard'))


@app.route('/backup', methods=['GET'])
def backup():
    src = DB_PATH
    if not os.path.exists(src):
        flash('Database not found to backup', 'danger')
        return redirect(url_for('dashboard'))
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    dst = os.path.join(BACKUP_DIR, f'leads_{ts}.db')
    shutil.copy(src, dst)
    flash('Backup created: ' + dst, 'success')
    return redirect(url_for('dashboard'))


@app.route('/backups')
def list_backups():
    files = []
    for fn in sorted(os.listdir(BACKUP_DIR), reverse=True):
        files.append(fn)
    return render_template('backups.html', files=files)


@app.route('/export')
def export_leads():
    db = get_db(DB_PATH)
    cur = db.cursor()
    cur.execute('''
        SELECT l.lead_id, c.name as client_name, c.mobile as client_mobile, l.product, l.status, l.call_on, l.call_type, l.priority, l.created_at, l.updated_at
        FROM leads l JOIN clients c ON c.client_id = l.client_id
        ORDER BY l.lead_id
    ''')
    rows = cur.fetchall()
    data = []
    for r in rows:
        cur.execute('SELECT note, created_at FROM follow_up_notes WHERE lead_id = ? ORDER BY created_at ASC', (r['lead_id'],))
        notes = cur.fetchall()
        notes_text = ''
        if notes:
            notes_text = '\n\n'.join([f"{n['created_at']} - {n['note']}" for n in notes])
        data.append({
            'lead_id': r['lead_id'],
            'client_name': r['client_name'],
            'client_mobile': r['client_mobile'],
            'product': r['product'],
            'status': r['status'],
            'call_on': r['call_on'],
            'call_type': r['call_type'],
            'priority': r['priority'],
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
            'notes': notes_text
        })
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='leads')
    output.seek(0)
    return send_file(output, download_name='leads_export.xlsx', as_attachment=True, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/import', methods=['GET','POST'])
def import_leads():
    if request.method == 'GET':
        return render_template('import.html')
    f = request.files.get('file')
    if not f:
        flash('No file uploaded', 'danger')
        return redirect(url_for('import_leads'))
    try:
        if f.filename.lower().endswith('.csv'):
            df = pd.read_csv(f)
        else:
            df = pd.read_excel(f)
    except Exception as e:
        flash('Failed to read file: ' + str(e), 'danger')
        return redirect(url_for('import_leads'))

    db = get_db(DB_PATH)
    cur = db.cursor()
    inserted = 0
    for _, row in df.iterrows():
        name = str(row.get('client_name') or row.get('name') or '').strip()
        mobile = str(row.get('client_mobile') or row.get('mobile') or '').strip()
        product = str(row.get('product') or '').strip()
        status = str(row.get('status') or 'New').strip()
        call_on = row.get('call_on')
        if pd.isna(call_on):
            call_on_val = None
        else:
            try:
                if isinstance(call_on, pd.Timestamp):
                    call_on_val = call_on.date().isoformat()
                else:
                    call_on_val = str(call_on)
            except Exception:
                call_on_val = str(call_on)
        call_type = str(row.get('call_type') or 'Call')
        priority = str(row.get('priority') or 'Normal')
        note = str(row.get('notes') or '')
        if not name or not mobile or not product:
            continue
        cur.execute('SELECT client_id FROM clients WHERE mobile = ?', (mobile,))
        r = cur.fetchone()
        if r:
            client_id = r['client_id']
        else:
            created_at = datetime.utcnow().isoformat()
            cur.execute('INSERT INTO clients (name,mobile,created_at) VALUES (?,?,?)', (name,mobile,created_at))
            client_id = cur.lastrowid
        now = datetime.utcnow().isoformat()
        cur.execute('INSERT INTO leads (client_id,product,status,call_on,call_type,priority,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)', (client_id,product,status,call_on_val,call_type,priority,now,now))
        lead_id = cur.lastrowid
        if note and note.strip():
            # split imported notes on double newlines if present
            parts = [p.strip() for p in note.split('\n\n') if p.strip()]
            for p in parts:
                cur.execute('INSERT INTO follow_up_notes (lead_id,note,created_at) VALUES (?,?,?)', (lead_id,p,now))
        inserted += 1
    db.commit()
    flash(f'Imported {inserted} leads', 'success')
    return redirect(url_for('leads'))


@app.route('/backups/download/<path:filename>')
def download_backup(filename):
    return send_from_directory(BACKUP_DIR, filename, as_attachment=True)


@app.route('/restore', methods=['POST'])
def restore():
    f = request.files.get('file')
    if not f:
        flash('No file uploaded', 'danger')
        return redirect(url_for('list_backups'))
    dst = DB_PATH
    f.save(dst)
    flash('Database restored', 'success')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
