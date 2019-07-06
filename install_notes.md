# Installation notes for DVH Analytics

## Pre-requisites
 - [PostgreSQL](https://www.postgresql.org/)
 - [Python >=3.5](https://www.python.org/downloads/release)
 - Additional python libraries as specifed in 
 [requirements.txt](https://github.com/cutright/DVH-Analytics-Desktop/blob/master/requirements.txt)

## Running
Clone this project to a location of your choice.  In a terminal and from the DVH-Analytics directory (i.e., top-level 
for the project), run (assuming python points to an instance of python 3):
~~~
python dvha_app.py
~~~

## PostgreSQL
If you have access to a PostgreSQL DB, you simply need to fill in the login information by going to 
the menu bar: Settings -> Database Settings.

If you need PostgreSQL, here are some options for each OS.

#### Mac OS
Simply download the PostgreSQL app: http://postgresapp.com/  
 - Open the app
 - Click "Start"
 - Double-click "postgres" with the cylindrical database icon
 - Type the following in the SQL terminal:
~~~~
create database dvh;
~~~~
Then quit by typing:
~~~~
\q
~~~~

NOTE: You may replace dvh with any database name you wish, but you must update dbname in settings to reflect what 
database name you chose.  

#### Ubuntu
You probably already have PostgreSQL installed, but if you don't, type the following in a terminal:
~~~~
$ sudo apt-get install postgresql postgresql-client postgresql-contrib libpq-dev
$ sudo apt-get install pgadmin3
~~~~
Upon successful installation, open type 'pgadmin3' in the terminal to open the graphical admin.  
Then, create a user and database of your choice (same instructions found below for Windows)

#### Windows
Download the installer for BigSQL: https://www.bigsql.org/postgresql/installers.jsp/

 - Be sure to include pgAdmin3 LTS
 - After installation, launch pgAdmin3 LTS from the Windows Start Menu.
   - Right-click localhost and then click connect.
   - Right-click Login Roles and then click New Login Role.
   - Fill in Role name (e.g., dvh), click OK
   - Right-click Databases then click New Database
   - Fill in Name (e.g., dvh), set owner to the Role name you just created. Click OK.
