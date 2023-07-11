# Create a virtual environment (optional but recommended): 
 python3 -m venv env

# Activate the virtual environment.

# Install Django for project:
 pip install django

# And then run the command to start the new project:
 
 django-admin startproject <project-name>

 <project-name> defines root directory container for your project.

# Install project dependencies:
 pip install -r requirements.txt

# To Apply database migrations:
 python manage.py migrate

# To run the project:
 python manage.py runserver