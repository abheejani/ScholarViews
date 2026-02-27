from flask import Flask, render_template, request, redirect, url_for, session, get_flashed_messages, flash
import os

app = Flask(__name__, template_folder='templates')
app.secret_key = 'password'

UPLOAD_FOLDER = 'uploads'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def create_upload_folder():
    # Create the 'uploads' directory if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)


user_credentials = {}
user_interviews = {}
search_interviews = {
    'options': [
        {'name': 'Dave', 'company': 'Netflix', 'years_exp': 15, 'field': 'Technology'},
        {'name': 'Smith', 'company': 'Google', 'years_exp': 10, 'field': 'Marketing'},
        {'name': 'Adam', 'company': 'Amazon', 'years_exp': 8, 'field': 'Development'}, 
        {'name': 'Felix', 'company': 'Microsoft', 'years_exp': 12, 'field': 'Engineering'},
        {'name': 'Anothony', 'company': 'Apple', 'years_exp': 7, 'field': 'HR'},
        {'name': 'Leo', 'company': 'Facebook', 'years_exp': 5, 'field': 'Education'}
    ]
}

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error_message = None
    if request.method == 'GET':
        return render_template('signup.html', error_message=error_message)
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in user_credentials:
            error_message = f'Username already exists. Please choose a different username.'
            return render_template('signup.html', error_message=error_message)
        else:
            user_credentials[username] = password
            return render_template('login.html', reg_message='Successful Sign Up')

@app.route('/resume-review', methods=['GET', 'POST'])
def resume_review():
    return render_template('resume-review.html')

@app.route('/upload_resume', methods=['POST'])
def upload_resume():
    create_upload_folder()  # Call the function to ensure the directory exists

    if 'resume' in request.files:
        resume = request.files['resume']
        name = request.form['name']
        if resume.filename != '':
            try:
                resume.save(os.path.join(app.config['UPLOAD_FOLDER'], f'{name}_resume.pdf'))
                flash('Resume uploaded successfully!', 'success')
            except Exception as e:
                flash('Error uploading resume. Please try again.', 'error')
    return render_template('resume-review.html', messages=get_flashed_messages())

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     error_message = None
#     if request.method == 'GET':
#         return render_template('login.html', error_message=error_message)
#     elif request.method == 'POST':
#         username = request.form.get('username')
#         password = request.form.get('password')

#         if username in user_credentials and user_credentials[username] == password:
#             session['username'] = username
#             return render_template('user_dashboard.html', interviews=user_interviews)
#         elif username not in user_credentials:
#             error_message = 'Username not found'
#             return render_template('login.html', error_message=error_message)
#         else:
#             error_message = 'Password did not match your username'
#             return render_template('login.html', error_message=error_message)


@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if request.method == 'GET':
        username = session.get('username')
        return render_template('user_dashboard.html', username=username, interviews=user_interviews)


@app.route('/select_interviews', methods=['GET', 'POST'])
def select_interviews():
    search_results = []

    if request.method == 'GET':
        return render_template('select_interviews.html', search_results=search_results)
    
    elif request.method == 'POST':
        if request.form['action'] == 'Search':
            search_keyword = request.form.get('interview_name').lower()
            company_filter = request.form.get('company').lower()
            years_exp_filter = request.form.get('years_exp').lower()
            field_filter = request.form.get('field').lower()

            search_results = []

            for interviews in search_interviews.values():
                for interview in interviews:
                    if isinstance(interview, dict):
                        name_matches = search_keyword in interview['name'].lower()
                        company_matches = company_filter in interview['company'].lower() if company_filter else True
                        years_exp_matches = years_exp_filter in str(interview['years_exp']).lower() if years_exp_filter else True
                        field_matches = field_filter in interview['field'].lower() if field_filter else True

                        if name_matches and company_matches and years_exp_matches and field_matches:
                            search_results.append(interview)

            return render_template('select_interviews.html', search_results=search_results)
        
        elif request.form['action'] == 'Add Interview':
            username = session.get('username')
            if not username:
                return redirect(url_for('login'))

            selected_interview = request.form.get('selected_interview')
            if username not in user_interviews:
                user_interviews[username] = []

            user_interviews[username].append({'name': selected_interview})
            return redirect(url_for('user_dashboard'))

    return render_template('select_interviews.html', search_results=search_results)



def fetch_search_interviews(username):
    return search_interviews.get(username, [])

@app.route('/user_dashboard/my_interviews')
def my_interviews():
    username = session.get('username')
    
    if username:
        user_specific_interviews = user_interviews.get(username, [])
        return render_template('my_interviews.html', interviews=user_specific_interviews)
    else:
        return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None
    if request.method == 'GET':
        return render_template('login.html', error_message=error_message)
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username in user_credentials and user_credentials[username] == password:
            session['username'] = username  # Store username in session
            return render_template('user_dashboard.html', interviews=user_interviews)
        elif username not in user_credentials:
            error_message = 'Username not found'
            return render_template('login.html', error_message=error_message)
        else:
            error_message = 'Password did not match your username'
            return render_template('login.html', error_message=error_message)

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/faq")
def faq():
    return render_template('faq.html')

@app.route("/setup-interview")
def setup_interview():
    return render_template('setup-interview.html')

if __name__ == '__main__':
    app.run(debug=True)
