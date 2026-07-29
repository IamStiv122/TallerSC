#!/usr/bin/env bash
set -e
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='stevenson').exists() or User.objects.create_superuser('stevenson', 'stevenson.celi6741@utc.edu.ec', '123456')"