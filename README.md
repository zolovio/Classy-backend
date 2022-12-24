# Classy-backend

## ***To run:***
```bash
# clone this repo
$ git clone 'https://github.com/zolovio/Classy-backend.git'
$ git clone 'git@github.com:zolovio/Classy-backend.git'

# create and activate python environment
$ python3 -m venv .classy-venv  
$ source .classy-venv/bin/activate

# change directory
$ cd Classy-backend

# install project requirements
$ pip install wheel
$ pip install -r requirements.txt

# Note: Confirm database configurations in .env project/config.py

# create and seed db
$ python manage.py create-db
$ python manage.py seed-db  # optional

# start application
$ python manage.py run

```
