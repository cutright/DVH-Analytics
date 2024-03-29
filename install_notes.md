# Installation notes for DVH Analytics

## Pre-requisites
 - [Python >=3.5](https://www.python.org/downloads/release)
 - Additional python libraries as specifed in 
 [requirements.txt](https://github.com/cutright/DVH-Analytics-Desktop/blob/master/requirements.txt)

## Running
Install via pip:
~~~
$ pip install dvha
~~~
If you've installed via pip or setup.py, launch from your terminal with:
~~~
$ dvha
~~~
If you've cloned the project, but did not run the setup.py installer, launch DVHA with:
~~~
$ python dvha_app.py
~~~

### Linux
Most likely, you will need to build wxPython from source with the proper libraries 
already installed. See [Issue 157](https://github.com/cutright/DVH-Analytics/issues/157) for a discussion.  

For example, if you are using Ubuntu 20.04.02 LTS, install the following prior 
to installing/building wxPython:

~~~
sudo apt install git-all
sudo apt install python3-pip
sudo apt install libgtk-3-dev
sudo apt-get install python-wxgtk3.0
sudo apt install libwebkit2gtk-4.0-dev
~~~

Then create your python virtual environment and do a pip install for wxpython (possibly with --no-cache-dir if needed).

Manjaro/Arch Linux users can refer to [this post](https://github.com/cutright/DVH-Analytics/issues/157#issuecomment-826392916) for tips.

## Shapely
The python package Shapely frequently has issues installing on Windows. If your pip install failed, consider installing 
Shapely from [here](https://www.lfd.uci.edu/~gohlke/pythonlibs/#shapely).

## SQL
DVH Analytics now supports both SQLite3 and PostgreSQL. Most users will prefer SQLite due to ease. Advantages are as follows:  
      
SQLite:  
* No admin rights needed on your computer
* No need to figure out how to make user logins and databases in SQL
* Easier to share your database - just zip (and encrypt), send to colleague  
  
PostgreSQL:  
* Supports multiple instances of DVHA accessing the same database at once
* Database may be housed remotely (just need the accessible IP address)
* Supports user login and password

Additional SQLite vs PostgreSQL information can be found [here](https://tableplus.com/blog/2018/08/sqlite-vs-postgresql-which-database-to-use-and-why.html).

SQLite works out-of-the-box, the 'host' field in Settings -> Database Connections is the name of the file, 
located in ~/Apps/dvh_analytics/data

## PostgreSQL
If you have access to a PostgreSQL DB, you simply need to fill in the login information by going to 
the menu bar: Settings -> Database Settings.

If you need PostgreSQL, here are some options for each OS.

#### macOS
Download the PostgreSQL app: http://postgresapp.com/  
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
