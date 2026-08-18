from flask import Flask, request, jsonify,render_template
from selenium import webdriver
from selenium.webdriver.common.print_page_options import PrintOptions
from selenium.common.exceptions import WebDriverException,TimeoutException, NoSuchElementException
import base64
import sqlite3 
from urllib.parse import urlparse, unquote
import jwt
from functools import wraps
import os
from markupsafe import escape
import ipaddress
import dns.resolver

prefs = {}
prefs["webkit.webprefs.javascript_enabled"] = False
prefs["profile.content_settings.exceptions.javascript.*.setting"] = 2
prefs["profile.default_content_setting_values.javascript"] = 2
prefs["profile.managed_default_content_settings.javascript"] = 2


app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(32).hex()

def validate_url(url):
    parsed_url = urlparse(url)
    protocol = parsed_url.scheme
    if protocol not in ['http', 'https']:
        return False
    if url is None:
        return False
    else:
        return True
def is_request_safe(url, min_ttl=40):
    hostname = urlparse(url).hostname or url
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        pass
    resolver = dns.resolver.Resolver(configure=False)
    resolver.nameservers = ['8.8.8.8']
    try:
        answer = resolver.resolve(hostname, 'A')
        current_ttl = answer.rrset.ttl
        
        if current_ttl >= min_ttl:
            return True
        else:
            return False
    except Exception as e:
        return False
    
def logify(rec):
    row_separator = '\n'
    history = [f"ID: {row[0]} | URL: {row[1]} | Timestamp: {row[2]}" for row in rec]
    history_1 = row_separator.join(history)
    log = history_1.format(logify=logify)
    return log

def peek_website(url,timestamp):
    options = webdriver.ChromeOptions()
    options.add_experimental_option("prefs", prefs)
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-javascript")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-sync")
    options.add_argument("--disable-translate")
    options.add_argument("--safebrowsing-disable-auto-update")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(40)
    try:
        if is_request_safe(url) == False:
            return False
        driver.get(url)
        print_options = PrintOptions()
        print_options.orientation = "portrait"
        print_options.scale = 0.60
        print_options.background = True
        pdf_base64 = driver.print_page(print_options=print_options)
        pdf_bytes = base64.b64decode(pdf_base64)
        print(driver.current_url)
        print(url)
        def check_equiv(url1, url2):
            def normalize(url):
                decoded = unquote(url)
                p = urlparse(decoded)
                return (
                p.scheme.lower(),
                p.netloc.lower(),
                p.path.rstrip('/'),
                p.query
            )
            return normalize(url1) == normalize(url2)
        if check_equiv(driver.current_url,url) == False:
            return False
        with open(f"../service/pdfs/results-{timestamp}.pdf","wb") as pdf:
            pdf.write(pdf_bytes)   
        conn = sqlite3.connect('history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO history (url) VALUES (?)", (url,))
        conn.commit()
        return True
    except (WebDriverException, TimeoutException, NoSuchElementException) as e:
        return False
    finally:
        driver.quit()

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            print(data)
            if not data.get('is_admin') and data.get('username') == 'bartender':
                return jsonify({'message': 'Admin access required!'}), 403
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/bartender', methods=['GET'])
@token_required
def protected_memory():
    conn = sqlite3.connect('history.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, secret FROM secrets")
    secrets = cursor.fetchall()
    conn.close()
    secrets_list = []
    for name, secret in secrets:
        secrets_list.append({'name': name, 'secret': secret})
    return jsonify({'secrets': secrets_list}), 200

@app.route('/generate', methods=['GET'])
def scrape():
    name = escape(request.args.get('name'))
    timestamp=request.args.get('time')
    url = request.args.get('url')
    secret = escape(request.args.get('secret'))
    if not validate_url(url):
        return jsonify({'error':'invalid url provided'}),400
    if not name or not secret:
        return jsonify({'error':'No tricks traveller'}),400
    if(peek_website(url,timestamp) == True):
        conn = sqlite3.connect('history.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO secrets (name, secret) VALUES (?, ?)", (name, secret))
        conn.commit()
        conn.close()
        return jsonify({'success':'task completed'}),200
    else:
        return jsonify({'error':'task failed'}),500

@app.route('/logs', methods=['GET'])
def logs():
        query = f"SELECT * from history"
        try:
            conn = sqlite3.connect('history.db')
            cursor = conn.cursor()
            cursor.execute(query)
            rec = cursor.fetchall()
            log = logify(rec)
            conn.close()
            return render_template("bartender.html",log_data=log)

        except sqlite3.Error as e:
            return jsonify({'error','An error occured while handling memory'})

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({'error': 'system failed'}), 500

@app.errorhandler(404)
def not_found_error(error): 
    return jsonify({'error': 'Not Found'}), 404

if __name__ == '__main__':
    app.run(debug=False)
