# Expense Tracker

1. Pull this repo
```shell
git pull https://github.com/w4hf/expense-tracker.git
```

2. Enter the repo dir
```shell
cd expense-tracker/
```

3. Create a python venv
```shell
python3 -m venv .venv
```

4. Activate venv
```shell
source .venv/bin/activate
```

5. Install python packages
```shell
pip3 install -r requirements.txt
```

6. Migrate
```shell
./manage.py migrate
```

7. Launch app
```shell
./manage.py runserver
```