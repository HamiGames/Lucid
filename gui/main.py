""" Main entry point for Lucid GUI services 

file: /app/gui/main.py
x-lucid-file-path: /app/gui/main.py
x-lucid-file-type: python

about this script:
- this script is the main entry point for the Lucid GUI service
- triggers the use of /app/gui/config/config.py for the GUI services
- triggers the connection to selected gateway based on user criteria

- triggers database connection to selected database based on user criteria
- triggers lucid-auth-services for validation

Container Path: /app/gui/main.py for triggering fast-api connections to other services

"""	

#load imports

# link to config.py for loading config
# define main function

# define gateway criteria function

# define database criteria function

# create class GatewayTrigger 

# create class DatabaseTrigger for database connection


# create class AuthTrigger for lucid-auth-services validation

# link to gui-endpoints.yml for loading endpoints


#run main function (uvicorn)