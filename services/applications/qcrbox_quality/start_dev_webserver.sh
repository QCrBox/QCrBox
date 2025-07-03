#!/bin/bash

# Exit on any error
set -e

micromamba run -n qcrbox python /opt/qcrbox/django_minimal.py runserver 0.0.0.0:8080