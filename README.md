Dev Notes: 

# Virtual Environment
- python -m venv venv
- venv\Scripts\activate

# Pip install Flask apps 
- pip install flask flask_sqlalchemy flask-migrate flask-login

# Set Flask app location 
- Mac/Linux 
    - export FLASK_APP=run.py
- Windows CMD 
    - set FLASK_APP=run.py
- PowerShell
    - $env:FLASK_APP = "run.py"

# Initialize DB (Potentially alr done)
- flask db init
- flask db migrate -m "create user table"
- flask db upgrade

# To Run 
- python run.py 
- open localhost link