import re
import os
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, url_for, escape, session, flash, make_response

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
DATABASEURI = "postgresql://sm4241:u9pbm@104.196.175.120/postgres"
engine = create_engine(DATABASEURI)
engine.execute("""DROP TABLE IF EXISTS test;""")
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")

# set the secret key.  keep this really secret:
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass

    
@app.route('/')
def index():
    return render_template("index.html")


@app.route('/customerLogin', methods=['POST', 'GET'])
def gotoCustomerLogin():
    error = None
    if request.method == 'POST':
        ssn = request.form['username']
        print ssn
        query = 'SELECT u.password,u.name FROM users as u, customers as c WHERE u.ssn=%s and u.ssn=c.ssn;'
        cursor = g.conn.execute(query, ssn)
        if cursor.rowcount == 0 :
            error = 'Invalid username/password'
        else:
            row = cursor.fetchone()
            print row[0]
            if row[0] == request.form['password']:
                session['logged_in'] = True
                session['username'] = ssn
                return redirect(url_for('ordersDisplay'))
            else:
                error = 'Invalid username/password'
    
    return render_template('loginCustomer.html', error=error)


@app.route('/employeeLogin', methods=['POST','GET'])
def gotoEmployeeLogin():
    error = None
    if request.method == 'POST':
        ssn = request.form['username']
        print ssn
        cursor = g.conn.execute("SELECT u.password,u.name FROM users as u, employees as e WHERE u.ssn=e.ssn and u.ssn=%s;", ssn)
        if cursor.rowcount == 0 :
            error = 'Invalid username/password'
        else:
            row = cursor.fetchone()
            print row[0]
            if row[0] == request.form['password']:
                session['logged_in'] = True
                session['username'] = ssn
                return redirect(url_for('employeeDashboard'))
            else:
                error = 'Invalid username/password'
    
    return render_template('loginEmployee.html', error=error)
    

@app.route('/orders') 
def ordersDisplay():
    error = None
    ssn = session['username']
    print ssn
    query = 'SELECT o.order_id, o.submitted_date, o.est_delivery_date FROM orders as o, users_orders as uo WHERE o.order_id = uo.order_id and uo.ssn=%s;'
    curr = g.conn.execute(query, ssn)
    if curr.rowcount == 0:
        error = 'No Orders Found'
        context = dict(error=error)
    else:
        order_ids = curr.fetchall()
        print order_ids
        context = dict(data = order_ids, error=error)
        print context
    return render_template('orders.html', **context)


@app.route('/deleteOrder', methods=['POST']) 
def deleteOrder():
    orderid = request.form['orderid']
    ssn = session['username']
    query1 = 'DELETE FROM order_line WHERE order_line_id IN (SELECT order_line_id FROM orders_orderline WHERE order_id=%s);'
    curr1 = g.conn.execute(query1, orderid)
    query2 = 'DELETE FROM orders WHERE order_id=%s;'
    curr2 = g.conn.execute(query2, orderid)
    return redirect(url_for('ordersDisplay'))


@app.route('/orderDetails', methods=['GET']) 
def orderDetails():
    print request.args
    orderid = request.args['orderid']
    query = 'SELECT ool.order_id, p.name, p.product_type, ol.quantity,  p.price, p.price*ol.quantity as total_price, ol.product_id FROM orders_orderline as ool, order_line as ol, products as p WHERE ool.order_line_id = ol.order_line_id and ool.order_id=%s and ol.product_id = p.product_id;'
    curr = g.conn.execute(query, orderid)
    order_details = curr.fetchall()
    context = dict(orderdetails=order_details)
    return render_template('orderDetails.html', **context)


@app.route('/employeeDashboard') 
def employeeDashboard():
    error = None
    if 'username' in session:
        ssn = session['username']
        print ssn
        query='SELECT u.name, e.designation, d.dept_name, u.phone_number, u.email_id FROM department as d, employees_department as ed, employees as e, users as u WHERE e.ssn=u.ssn and e.ssn=ed.ssn and d.dept_id=ed.dept_id and u.ssn = %s;'
        curr = g.conn.execute(query, ssn)
        empDetail = curr.fetchone()
        context = dict(empdata = empDetail, error=error)
        return render_template('employeeDashboard.html', **context)
    else: return redirect(url_for('index'))


@app.route('/products', methods=['GET'])
def products():
    query='SELECT p.product_id, p.name, p.product_type, p.price, p.qty_in_stock, SUM(ol.quantity), f.name, f.region FROM product_factory as pf, factory as f,products as p LEFT JOIN order_line as ol ON p.product_id=ol.product_id WHERE p.product_id=pf.product_id and pf.factory_id=f.factory_id GROUP BY p.product_id,f.name,f.region ORDER BY p.name ASC;'
    curr = g.conn.execute(query)
    products = curr.fetchall()
    context = dict(products=products)
    return render_template('products.html', **context)


@app.route('/addNewProduct', methods=['GET'])
def addNewProduct():
    m = request.args.getlist("messages")
    print m
    if m is None:
        print "No message"
    query2 = 'SELECT ssn from employees'
    cursor = g.conn.execute(query2)
    ssnlist = []
    for s in cursor.fetchall():
        ssnlist.append(s[0])
    context = dict(slist = ssnlist, messages=m)    
    return render_template('addNewProduct.html', **context)


@app.route('/addProduct', methods=['POST'])
def addProduct():
    print "inside addProduct"
    messages = []
    productName = request.form['productName']
    if len(productName) ==0:
        messages.append("Please fill Product Name")
    print productName
    
    productType = request.form['productType']
    if len(productType) ==0:
        messages.append("Please fill Product Type")
    print productType
    
    price = request.form['price']
    if len(price) ==0:
        messages.append("Please fill Product Price")
    print price
    
    qtyinstock = request.form['qtyinstock']
    if len(qtyinstock) ==0:
        messages.append("Please fill Quantity in Stock")
    print qtyinstock
    
    factoryname = request.form['factoryname']
    if len(factoryname) ==0:
        messages.append("Please fill Factory Name")
    print factoryname
    
    brand = request.form['brand']
    if len(brand) ==0:
        messages.append("Please fill Factory Brand")
    print brand
    
    factoryregion = request.form['factoryregion']
    if len(factoryregion) ==0:
        messages.append("Please fill Factory Region")
    print factoryregion
    
    employeessn = request.form['employeessn']
    if len(employeessn) ==0:
        messages.append("Please select Employee SSN")
    print employeessn
    
    ssn = session['username']
    print ssn
    
    if len(messages) ==0:
        query = 'INSERT INTO products(name, product_type, price, qty_in_stock) VALUES (%s,%s,%s,%s) RETURNING product_id;'
        curr = g.conn.execute(query, productName,productType,price,qtyinstock)
        print "product insert successful"
        pid = curr.fetchone()[0]
        print pid

        query = 'INSERT INTO factory(name, brand, region) VALUES (%s,%s,%s) RETURNING factory_id;'
        curr = g.conn.execute(query,factoryname,brand,factoryregion)
        print "factory insert successful"
        fid = curr.fetchone()[0]
        print fid

        query = 'INSERT INTO product_factory(product_id, factory_id) VALUES (%s,%s);'
        curr = g.conn.execute(query, pid,fid)
        print "product factory insert successful"

        query = 'INSERT INTO employees_products(ssn, product_id) VALUES (%s,%s);'
        curr = g.conn.execute(query, employeessn, pid)
        messages.append("Product Added Successfully")
        
    context = dict(messages=messages)
    return redirect(url_for('addNewProduct', **context))


@app.route('/searchDirectory')
def searchDirectory():
    return render_template('search.html')


@app.route('/search', methods=['POST', 'GET'])
def search():
    error = None
    if request.method == 'POST':
        searchBy = request.form['searchBy']
        searchValue = request.form['searchValue']
        if searchBy=='name':
            query='SELECT u.name, e.designation, d.dept_name, u.phone_number, u.email_id FROM department as d, employees_department as ed, employees as e, users as u WHERE e.ssn=u.ssn and e.ssn=ed.ssn and d.dept_id=ed.dept_id and u.name LIKE %s;'
        elif searchBy=='designation':
            query='SELECT u.name, e.designation, d.dept_name, u.phone_number, u.email_id FROM department as d, employees_department as ed, employees as e, users as u WHERE e.ssn=u.ssn and e.ssn=ed.ssn and d.dept_id=ed.dept_id and e.designation LIKE %s;'
        elif searchBy=='department':
            query='SELECT u.name, e.designation, d.dept_name, u.phone_number, u.email_id FROM department as d, employees_department as ed, employees as e, users as u WHERE e.ssn=u.ssn and e.ssn=ed.ssn and d.dept_id=ed.dept_id and d.dept_name LIKE %s;'
        else: 
            error = 'Please select a valid Search option'
            context = dict(error=error)
            return render_template('search.html', **context)
        
        if searchValue=='':
            error = 'Please enter a valid Search value'
            context = dict(error=error)
            return render_template('search.html', **context)
        
        curr = g.conn.execute(query, '%'+searchValue+'%')
        if curr.rowcount == 0:
            error = 'No Results Found'
            context = dict(error=error)
            return render_template('search.html', **context)

        searchResults = curr.fetchall()
        context = dict(searchResults=searchResults, error=error)
        print searchResults
        return render_template('search.html', **context)


@app.route('/editProfile')
def editProfile():
    return render_template('editProfile.html')


@app.route('/saveProfileChanges', methods=['POST'])
def saveProfileChanges():
    ssn = session['username']
    emailid = request.form['emailid']
    phoneNumber = request.form['phoneNumber']
    address = request.form['address']
    messages=[]
    
    if emailid != "":
        if re.match(r"[^@]+@[^@]+\.[^@]+", emailid):
            query = 'UPDATE users SET email_id=%s WHERE ssn=%s;'
            curr = g.conn.execute(query, emailid, ssn)
            messages.append("Email Id updated successfully")
        else:
            messages.append("Please enter a valid email address")
    
    if phoneNumber != "":
        if len(phoneNumber) == 11:
            query = 'UPDATE users SET phone_number=%s WHERE ssn=%s;'
            curr = g.conn.execute(query, phoneNumber, ssn)
            messages.append("Phone Number updated successfully")
        else:
            messages.append("Please enter a valid 11- digit phone number")
    
    if address != "":
        if len(address) <= 255:
            query = 'UPDATE users SET address=%s WHERE ssn=%s;'
            curr = g.conn.execute(query, address, ssn)
            messages.append("Address updated successfully")
        else:
            messages.append("Address exceeded 255 characters limit")
    
    context = dict(messages = messages)
    return render_template('editProfile.html', **context)


@app.route('/orderDetailsByProduct', methods=['GET'])
def orderDetailsByProduct():
    productid = request.args['productid']
    productname = request.args['productname']
    query='SELECT o.*, ol.quantity FROM orders as o, orders_orderline as ool, order_line as ol WHERE ool.order_line_id = ol.order_line_id and o.order_id = ool.order_id and ol.product_id =%s;'
    curr = g.conn.execute(query, productid)
    orderdetails = curr.fetchall()
    
    query2 ='SELECT u.name, d.dept_name FROM products as p, employees_products as ep, department as d, employees_department as ed, users as u WHERE ep.ssn = ed.ssn and ep.ssn=u.ssn  and ed.dept_id = d.dept_id and ep.product_id =%s;'
    curr = g.conn.execute(query2, productid)
    handlingDetails = curr.fetchone()
    
    context = dict(data = orderdetails, productname=productname, handlingDetails=handlingDetails)
    return render_template('orderDetailsByProduct.html', **context)


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect(url_for('index'))


if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()