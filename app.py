from flask import Flask, render_template, request, session, templating, url_for, redirect
from bs4 import BeautifulSoup
from selenium import webdriver
import re
from selenium.webdriver.chrome.options import Options
from flask_mysqldb import MySQL
import MySQLdb.cursors
from webdriver_manager.chrome import ChromeDriverManager
import smtplib


app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecret'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'spartanvs'
app.config['MYSQL_DB'] = 'profiles'

mysql = MySQL(app)


@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('home.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == "POST" and "email" in request.form and "password" in request.form:

        browser = webdriver.Chrome('drivers/chromedriver')

        chrome_options = Options()
        chrome_options.headless = True
        browser.set_window_position(-10000,0)
        browser.get("https://www.linkedin.com/uas/login")

        elementID = browser.find_element_by_id("username")
        elementID.send_keys(request.form['email'])

        elementID = browser.find_element_by_id("password")
        elementID.send_keys(request.form['password'])

        elementID.submit()

        soup = BeautifulSoup(browser.page_source, features='lxml')
        result = soup.find('div', {'class':'t-16 t-black t-bold'})
        if result is None:
            session['message'] = "Invalid Credentials"
            return redirect(url_for('home'))
        
        session['logged_in_username'] = result.text
        session['username'] = request.form['email']
        session['password'] = request.form['password']

        return redirect(url_for('search_profile'))

    return render_template('index.html')

@app.route('/search_profile', methods=['GET', 'POST'])
def search_profile():
    if request.method == "POST" and "url" in request.form:

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM userinfo WHERE url='{}'".format(request.form['url']))
        

        account = cursor.fetchone()

        if account:
            session['name'] = account['username']
            session['skills'] = account['skills'].split("'")
            session['education'] = account['education'].split("'")
            session['companies'] = account['companies'].split("'")
            session['info'] = account['info']
            session['email'] = account['email']
            return redirect(url_for('user_profile'))
        
        
        
        browser = webdriver.Chrome('drivers/chromedriver')

        chrome_options = Options()
        chrome_options.headless = True
        browser.set_window_position(-10000,0)
        browser.get("https://www.linkedin.com/uas/login")

        elementID = browser.find_element_by_id("username")
        elementID.send_keys(session['username'])

        elementID = browser.find_element_by_id("password")
        elementID.send_keys(session['password'])

        elementID.submit()


        url = request.form['url']
        browser.get(url)
        soup = (BeautifulSoup(browser.page_source, features='lxml'))


            

        
        # Name Logic
        result = soup.find('h1', {'class':'text-heading-xlarge inline t-24 v-align-middle break-words'})
        message = ""
        if result is None:
            session['message'] = "Invalid profile URL"
            return redirect(url_for('invalid_search_profile'))
        session['name'] = result.text

        # Skills logic
        soup = str(soup)
        result = re.findall('{"entityUrn":"urn:li:fsd_skill:\([a-zA-Z0-9,-_]*\)","name":"([A-Za-z-/\(\)\.\+ ]*)"', soup)
        if len(result)==0:
            result.append("N/A")
        session['skills'] = result

        
        # Company logic
        company = list()
        result = re.findall(',"companyName":"([A-Z][A-Za-z0-9-,\(\)\. ]*)"', soup)
        if len(result) == 0:
            result.append("N/A")
            session['companies'] = result
        else:
            for comp in result:
                if comp not in company:
                    company.append(comp)
            session['companies'] = company

        # School logic
        result = re.findall('"schoolName":"([A-Z][A-Za-z0-9-,\(\)\.&; ]*)"', soup)
        school = list()
        if len(result) == 0:
            result.append("N/A")
            session['education'] = result
        else:
            for sch in result:
                if sch not in school:
                    school.append(sch)
            session['education'] = school

        # Info logic
        result = BeautifulSoup(soup, features='lxml').find('div', {'class':'text-body-medium break-words'})
        if result is None:
            session['info'] = ""
        else:
            session['info'] = result.text

        # Contact info logic
        url = request.form['url']+'detail/contact-info/'

        browser.get(url)
        soup = (BeautifulSoup(browser.page_source, features='lxml'))
        soup = str(soup)
        result = re.findall(',"emailAddress":"([a-z0-9@\.]*)"', soup)
        session['email'] = result[0]

        cursor.execute("INSERT INTO userinfo VALUES (% s, % s, % s, % s, % s, % s, % s)", (request.form['url'], session['name'], session['email'], session['info'], str(session['education']), str(session['companies']), str(session['skills'])))

        mysql.connection.commit()
        return redirect(url_for('user_profile'))
    
    return render_template("search_profile.html")

@app.route('/invalid_search_profile', methods=['GET', 'POST'])
def invalid_search_profile():
    return render_template('invalid_search_profile.html')

@app.route('/user_profile', methods=['GET', 'POST'])
def user_profile():
    return render_template('user_profile.html')

@app.route('/logged_out', methods=['GET', 'POST'])
def logout():
    message = "Thank you "+session['logged_in_username'].split()[0]+" for using my web scrapper"
    session.pop('username', None)
    session.pop('password', None)
    session.pop('url', None)
    session.pop('name', None)
    session.pop('email', None)
    session.pop('info', None)
    session.pop('education', None)
    session.pop('companies', None)
    session.pop('skills', None)
    session.pop('message', None)
    return render_template('index.html', message=message)

@app.route('/email', methods=['GET', 'POST']) 
def mail():
    if request.method == "POST" and "mail" in request.form:
        mail = request.form['mail']
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(session['username'], session['password'])
        server.sendmail(session['username'], session['email'], mail)    
        server.quit()
        return render_template('user_profile.html')
    return render_template('email.html')
if __name__ == "__main__":
    app.run(debug=True)
