Dev Notes: 

# To Run 
- python run.py 
- open localhost link

# Config
- pip install flask-login 
- pip install flask-migrate

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
