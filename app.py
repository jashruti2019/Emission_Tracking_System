from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = os.urandom(24)

mysql = MySQL(app)

# Hardcoded admin credentials
ADMIN_ID = "1920"
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = generate_password_hash("shruti123")

@app.route('/')
def home():
    return render_template('home.html')

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        industry_id = request.form['industry_id']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT Password FROM Users WHERE IndustryID = %s", (industry_id,))
        user = cur.fetchone()
        cur.close()

        if user and check_password_hash(user[0], password):
            session['industry_id'] = industry_id
            flash('Login Successful! Welcome to the Emission Tracking System.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid Industry ID or Password. Please try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

# User signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        industry_id = request.form['industry_id']
        zip_code = request.form['zip_code']
        email = request.form['email']
        password = request.form['password']

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Users WHERE Email = %s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('User already exists. Please use a different email address.', 'danger')
            return redirect(url_for('signup'))

        cur.execute("SELECT * FROM Industry WHERE IndustryID = %s", (industry_id,))
        industry = cur.fetchone()

        if not industry:
            try:
                cur.execute("INSERT INTO Industry (IndustryID) VALUES (%s)", (industry_id,))
                mysql.connection.commit()
                flash('Industry added successfully!', 'success')
            except Exception as e:
                mysql.connection.rollback()
                flash(f'Error adding industry: {str(e)}', 'danger')
                return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        try:
            cur.execute("INSERT INTO Users (IndustryID, ZipCode, Email, Password) VALUES (%s, %s, %s, %s)",
                        (industry_id, zip_code, email, hashed_password))
            mysql.connection.commit()
            flash('You have signed up successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Signup failed: {str(e)}', 'danger')
        finally:
            cur.close()

    return render_template('signup.html')

# Forgot password
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT IndustryID FROM Users WHERE Email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            flash('Password reset link has been sent to your email (mocked).', 'info')
        else:
            flash('No account associated with this email.', 'danger')
        
    return render_template('forgot_password.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# Admin login
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        admin_id = request.form['admin_id']
        password = request.form['password']

        if admin_id == ADMIN_ID and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_id'] = admin_id
            session['admin_role'] = 'admin'
            flash("Admin login successful.", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid admin ID or password.", "danger")
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

# Admin dashboard to view all registered users
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash("Please log in as an admin to access the admin dashboard.", "warning")
        return redirect(url_for('admin_login'))
    
    # Fetch user data excluding the Role column
    cur = mysql.connection.cursor()
    cur.execute("SELECT UserID, IndustryID, ZipCode, Email FROM Users")  # Include more columns here
    users = cur.fetchall()
    cur.close()
    
    return render_template('admin_dashboard.html', users=users)


# Unified route for logging out
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

# Route to display facilities
# Route to display facilities
@app.route('/facilities')
def facilities():
    if 'industry_id' in session:
        # Fetch all the facilities from the database
        cur = mysql.connection.cursor()
        cur.execute("SELECT FacilityID, FacilityName, Address, NAICSCode FROM Facility")  # Query to get facility details
        facilities = cur.fetchall()
        cur.close()
        
        return render_template('facilities.html', facilities=facilities)
    else:
        flash('Please log in to access Facilities.', 'warning')
        return redirect(url_for('login'))


# Route to add a new facility
@app.route('/add_facility', methods=['GET', 'POST'])
def add_facility():
    if 'industry_id' not in session:
        flash('Please log in to add facilities.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        facility_id = request.form['facility_id']
        name = request.form['facility_name']  # Ensure this matches the HTML form's field name
        address = request.form['address']
        naics_code = request.form['naics_code']

        # Insert new facility into the database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO Facility (FacilityID, FacilityName, Address, NAICSCode)
                VALUES (%s, %s, %s, %s)
            """, (facility_id, name, address, naics_code))
            mysql.connection.commit()
            flash('Facility saved successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error saving facility: {str(e)}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('facilities'))
    
    return render_template('add_facility.html')



# Route to display emissions data
@app.route('/emissions')
def emissions():
    if 'industry_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM Emission")
        emissions = cur.fetchall()
        cur.close()
        return render_template('emissions.html', emissions=emissions)
    else:
        flash('Please log in to access Emissions.', 'warning')
        return redirect(url_for('login'))

@app.route('/add_emissions', methods=['GET', 'POST'])
def add_emissions():
    if 'industry_id' not in session:
        flash('Please log in to add emissions data.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get form data
        emission_id = request.form['emission_id']
        n2o = float(request.form['n2o'])
        ch4 = float(request.form['ch4'])
        co2 = float(request.form['co2'])
        year = int(request.form['year'])
        
        # Calculate total emission
        total_emission = n2o + ch4 + co2

        # Save data to the database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO Emission (EmissionID, N2O, CH4, CO2, Year, TotalEmission)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (emission_id, n2o, ch4, co2, year, total_emission))
            mysql.connection.commit()
            flash('Emission saved successfully!', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error saving emission: {str(e)}', 'danger')
        finally:
            cur.close()

        return redirect(url_for('emissions'))
    
    return render_template('add_emission.html')


@app.route('/companies')
def companies():
    if 'industry_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM ParentCompany")
        companies = cur.fetchall()
        cur.close()
        return render_template('companies.html', companies=companies)
    else:
        flash('Please log in to access Companies.', 'warning')
        return redirect(url_for('login'))

# Route to add a new basin
@app.route('/add_basin', methods=['GET', 'POST'])
def add_basin():
    if request.method == 'POST':
        # Retrieve form data
        basin_id = request.form['basin_id']
        basin_name = request.form['basin_name']
        basin_latitude = request.form['basin_latitude']
        basin_longitude = request.form['basin_longitude']

        # Insert into database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO Basin (BasinID, BasinName, B_Latitude, B_Longitude)
                VALUES (%s, %s, %s, %s)
            """, (basin_id, basin_name, basin_latitude, basin_longitude))
            mysql.connection.commit()
            flash('Basin added successfully!', 'success')
            return redirect(url_for('basins'))  # Redirect to 'basins' view after success
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error saving basin: {str(e)}', 'danger')
        finally:
            cur.close()

    return render_template('add_basin.html')


# Single route to display all basins
@app.route('/basins')
def basins():
    if 'industry_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT BasinID, BasinName, B_Latitude, B_Longitude FROM Basin")

        basins = cur.fetchall()
        cur.close()
        return render_template('basins.html', basins=basins)
    else:
        flash('Please log in to access Basins.', 'warning')
        return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
