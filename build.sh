#!/bin/bash
# Install system dependencies for psycopg2-binary
apt-get update
apt-get install -y libpq-dev gcc
pip install -r requirements.txt
