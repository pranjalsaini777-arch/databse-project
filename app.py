from flask import Flask, request, jsonify, render_template
import os, secrets, threading
try:
    import oracledb
    DRIVER_ERROR = None
except ImportError:
    oracledb = None
    DRIVER_ERROR = "The Oracle driver could not load. Install requirements.txt in the active Python environment and restart the server."
from decimal import Decimal, InvalidOperation
from pathlib import Path

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16384
TOKEN = secrets.token_urlsafe(32)
pool = None
lock = threading.Lock()
REPORTS = []
for section in Path(__file__).with_name('sql').joinpath('reports.sql').read_text().split('-- Q')[1:]:
    title, sql = section.split('\n',1)
    REPORTS.append((title.strip(),sql.strip().rstrip(';')))

def query(c, sql, params=None):
    with c.cursor() as cur:
        cur.execute(sql,params or {})
        names = [d[0].lower() for d in cur.description]
        return [dict(zip(names,[v.isoformat(sep=' ') if hasattr(v,'isoformat') else float(v) if isinstance(v,Decimal) else v for v in row])) for row in cur.fetchall()]

def connection():
    if pool is None: raise ValueError('Connect your Oracle database using the Connection button first.')
    c = pool.acquire()
    c.call_timeout = 20000
    return c

def integer(data,key):
    v=data.get(key)
    if isinstance(v,bool): raise ValueError('Invalid '+key)
    try:
        n=int(str(v))
        if n<=0: raise ValueError()
        return n
    except (ValueError,TypeError): raise ValueError('Provide a positive integer for '+key)

@app.before_request
def guard():
    from urllib.parse import urlsplit
    allowed = {'localhost', '127.0.0.1'}
    codespace = os.environ.get('CODESPACE_NAME')
    domain = os.environ.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')
    if os.environ.get('CODESPACES') == 'true' and codespace:
        allowed.add(f'{codespace}-5000.{domain}')
    if urlsplit('//' + request.host).hostname not in allowed:
        return jsonify(error='Unrecognized website address.'),403
    if request.method != 'GET' and request.headers.get('X-App-Token') != TOKEN: return jsonify(error='Reload the page and try again.'),403

@app.errorhandler(Exception)
def error(e):
    if oracledb is not None and isinstance(e,oracledb.Error):
        obj=e.args[0]
        msg=getattr(obj,'message','Oracle operation failed').split('\n')[0]
        return jsonify(error=msg),400
    if isinstance(e,ValueError): return jsonify(error=str(e)),400
    from werkzeug.exceptions import HTTPException
    if isinstance(e,HTTPException): return jsonify(error=e.description),e.code
    app.logger.error('Request failed: %s',type(e).__name__)
    return jsonify(error='The request failed. Check the server terminal.'),500

@app.get('/')
def home(): return render_template('index.html',token=TOKEN)

@app.get('/api/health')
def health():
    if pool is None: return jsonify(connected=False)
    with connection() as c:
        user=query(c,'SELECT USER AS schema_name FROM dual')[0]['schema_name']
        counts=query(c,'SELECT (SELECT COUNT(*) FROM shipment) shipments, (SELECT COUNT(*) FROM inventory_movement) movements FROM dual')[0]
        return jsonify(connected=True,schema=user,**counts)

@app.post('/api/connect')
def connect():
    global pool
    data=request.get_json()
    if not all(str(data.get(k,'')).strip() for k in ('user','password','dsn')): raise ValueError('Enter database username, database password and connection string.')
    if DRIVER_ERROR: raise ValueError(DRIVER_ERROR)
    candidate=oracledb.create_pool(user=data['user'].strip(),password=data['password'],dsn=data['dsn'].strip(),min=1,max=4,increment=1,tcp_connect_timeout=12)
    try:
        with candidate.acquire() as c:
            query(c,'SELECT shipment_id FROM shipment WHERE 1=0')
            query(c,'SELECT * FROM v_inventory_detail WHERE 1=0')
            rows=query(c,"SELECT status FROM user_objects WHERE object_name='POST_INVENTORY_MOVEMENT' AND object_type='PROCEDURE'")
            if not rows or rows[0]['status']!='VALID': raise ValueError('The project stock procedure is missing or invalid in this schema.')
    except Exception:
        candidate.close(force=True)
        raise
    with lock:
        old,pool=pool,candidate
        if old: old.close(force=True)
    return jsonify(message='Connected to your Oracle project database.')

@app.post('/api/disconnect')
def disconnect():
    global pool
    with lock:
        if pool: pool.close(force=True)
        pool=None
    return jsonify(message='Disconnected.')

@app.get('/api/dashboard')
def dashboard():
    with connection() as c:
        return jsonify(counts=query(c,'SELECT (SELECT COUNT(*) FROM shipment) shipments,(SELECT COUNT(*) FROM warehouse) warehouses,(SELECT COUNT(*) FROM product) products,(SELECT COUNT(*) FROM warehouse_task WHERE status IN (\'OPEN\',\'IN_PROGRESS\')) pending_tasks FROM dual')[0],statuses=query(c,'SELECT status,COUNT(*) total FROM shipment GROUP BY status ORDER BY status'),recent=query(c,REPORTS[0][1]),stock=query(c,'SELECT warehouse_code,COUNT(*) stock_lines FROM v_inventory_detail GROUP BY warehouse_code ORDER BY warehouse_code'))

@app.get('/api/shipments')
def shipments():
    with connection() as c:
        return jsonify(query(c,'SELECT s.shipment_id,s.shipment_ref,c.customer_name,o.city origin_city,d.city destination_city,s.status FROM shipment s JOIN customer c ON c.customer_id=s.customer_id JOIN location o ON o.location_id=s.origin_location_id JOIN location d ON d.location_id=s.destination_location_id ORDER BY s.shipment_id'))

@app.get('/api/shipments/<int:sid>')
def shipment(sid):
    with connection() as c:
        rows=query(c,'SELECT * FROM shipment WHERE shipment_id=:id',{'id':sid})
        if not rows: raise ValueError('Shipment not found.')
        return jsonify(shipment=rows[0],items=query(c,'SELECT p.sku,p.product_name,si.quantity,p.unit_of_measure,si.quantity*p.unit_weight_kg total_weight_kg FROM shipment_item si JOIN product p ON p.product_id=si.product_id WHERE si.shipment_id=:id ORDER BY p.sku',{'id':sid}),route=query(c,'SELECT sl.leg_id,sl.sequence_no,f.location_name from_point,t.location_name to_point,m.mode_name,c.carrier_name,v.registration_no vehicle FROM shipment_leg sl JOIN location f ON f.location_id=sl.from_location_id JOIN location t ON t.location_id=sl.to_location_id JOIN transport_mode m ON m.mode_id=sl.mode_id JOIN carrier c ON c.carrier_id=sl.carrier_id LEFT JOIN vehicle v ON v.vehicle_id=sl.vehicle_id WHERE sl.shipment_id=:id ORDER BY sl.sequence_no',{'id':sid}))

@app.post('/api/shipments/<int:sid>/status')
def status(sid):
    data=request.get_json(); new=data.get('status'); expected=data.get('expected')
    allowed={'DRAFT':['PLANNED','CANCELLED'],'PLANNED':['IN_TRANSIT','CANCELLED'],'IN_TRANSIT':['DELIVERED','CANCELLED'],'DELIVERED':[],'CANCELLED':[]}
    if new not in allowed.get(expected,[]): raise ValueError('That status transition is not allowed.')
    with connection() as c:
        try:
            if new in ('PLANNED','IN_TRANSIT','DELIVERED'):
                legs=query(c,'SELECT from_location_id,to_location_id FROM shipment_leg WHERE shipment_id=:id ORDER BY sequence_no',{'id':sid})
                s=query(c,'SELECT origin_location_id,destination_location_id FROM shipment WHERE shipment_id=:id',{'id':sid})
                items=query(c,'SELECT COUNT(*) n FROM shipment_item WHERE shipment_id=:id',{'id':sid})[0]['n']
                if not s or not items or not legs or legs[0]['from_location_id']!=s[0]['origin_location_id'] or legs[-1]['to_location_id']!=s[0]['destination_location_id'] or any(a['to_location_id']!=b['from_location_id'] for a,b in zip(legs,legs[1:])): raise ValueError('Shipment needs products and a complete connected route.')
            with c.cursor() as cur:
                cur.execute('UPDATE shipment SET status=:new WHERE shipment_id=:id AND status=:expected',{'new':new,'id':sid,'expected':expected})
                if cur.rowcount!=1: raise ValueError('Shipment changed. Refresh before updating.')
            c.commit()
        except Exception: c.rollback(); raise
    return jsonify(message='Shipment status saved in Oracle.')

@app.get('/api/transport')
def transport():
    with connection() as c:
        return jsonify(legs=query(c,'SELECT sl.leg_id,s.shipment_ref,s.status,sl.sequence_no,m.mode_name,c.carrier_name,sl.carrier_id,sl.mode_id,sl.vehicle_id,v.registration_no FROM shipment_leg sl JOIN shipment s ON s.shipment_id=sl.shipment_id JOIN transport_mode m ON m.mode_id=sl.mode_id JOIN carrier c ON c.carrier_id=sl.carrier_id LEFT JOIN vehicle v ON v.vehicle_id=sl.vehicle_id ORDER BY s.shipment_id,sl.sequence_no'),vehicles=query(c,'SELECT * FROM vehicle ORDER BY registration_no'))

@app.post('/api/legs/<int:lid>/vehicle')
def vehicle(lid):
    vid=integer(request.get_json(),'vehicle_id')
    with connection() as c:
        try:
            with c.cursor() as cur:
                cur.execute("UPDATE shipment_leg sl SET vehicle_id=:v WHERE leg_id=:id AND EXISTS (SELECT 1 FROM vehicle v WHERE v.vehicle_id=:v AND v.carrier_id=sl.carrier_id AND v.mode_id=sl.mode_id) AND EXISTS (SELECT 1 FROM shipment s WHERE s.shipment_id=sl.shipment_id AND s.status NOT IN ('DELIVERED','CANCELLED'))",{'v':vid,'id':lid})
                if cur.rowcount!=1: raise ValueError('Choose a matching carrier and transport mode for an active shipment.')
            c.commit()
        except Exception: c.rollback(); raise
    return jsonify(message='Vehicle assignment saved in Oracle.')

@app.get('/api/inventory')
def inventory():
    with connection() as c: return jsonify(query(c,'SELECT * FROM v_inventory_detail ORDER BY warehouse_code,bin_id,sku,lot_code'))

@app.get('/api/tasks')
def tasks():
    with connection() as c: return jsonify(query(c,'SELECT t.*,w.warehouse_code FROM warehouse_task t JOIN warehouse w ON w.warehouse_id=t.warehouse_id ORDER BY task_id'))

@app.get('/api/movements')
def movements():
    with connection() as c: return jsonify(query(c,'SELECT im.movement_id,im.task_id,im.bin_id,p.sku,im.lot_code,im.quantity_change,im.movement_time,im.remarks FROM inventory_movement im JOIN product p ON p.product_id=im.product_id ORDER BY im.movement_id DESC'))

@app.post('/api/movements')
def move():
    data=request.get_json()
    task=integer(data,'task_id'); binid=integer(data,'bin_id'); product=integer(data,'product_id')
    try: amount=Decimal(str(data.get('quantity_change')))
    except InvalidOperation: raise ValueError('Enter a valid quantity.')
    if not amount.is_finite() or amount==0 or abs(amount)>Decimal('999999999.999') or amount!=amount.quantize(Decimal('.001')): raise ValueError('Quantity must be nonzero with at most three decimal places.')
    lot=str(data.get('lot_code','')).strip(); remarks=str(data.get('remarks','')).strip()
    if not lot or len(lot.encode())>30 or len(remarks.encode())>200: raise ValueError('Lot: 1–30 bytes. Remarks: at most 200 bytes.')
    with connection() as c:
        try:
            with c.cursor() as cur: cur.callproc('post_inventory_movement',[task,binid,product,lot,amount,remarks or None])
            balance=query(c,'SELECT quantity_on_hand FROM inventory WHERE bin_id=:b AND product_id=:p AND lot_code=:l',{'b':binid,'p':product,'l':lot})[0]['quantity_on_hand']
            c.commit()
        except Exception: c.rollback(); raise
    return jsonify(message='Stock movement and audit record committed together.',balance=balance)

@app.get('/api/reports')
def reports(): return jsonify([{'id':i,'title':t} for i,(t,q) in enumerate(REPORTS)])

@app.get('/api/reports/<int:rid>')
def report(rid):
    if rid<0 or rid>=len(REPORTS): raise ValueError('Unknown report.')
    with connection() as c: return jsonify(title=REPORTS[rid][0],rows=query(c,REPORTS[rid][1]),sql=REPORTS[rid][1])

if __name__=='__main__':
    print('Freight Logistics: http://127.0.0.1:5000 — keep this terminal open.')
    app.run(host='127.0.0.1',port=5000,debug=False)
