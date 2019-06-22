# Vanilla WOW Character Calculator
----
Character calculator give an ability to make a character of any class, put on armor and weapon and know character's characterists. Also there is a native ability to search in database for an item with particular characterists.
### Data
------------
All data come from [Classic DB](https://github.com/classicdb/database) databases. A content database is compatible with World of Warcraft Client Patch 1.12. 
### Getting started
------------
This project assumes that you can work in shell and with jupyter notebooks.
* Firstly you need to create new user for MySQL.
* Secondly you need to create new empy database and grant all privileges to the user.
* Thirdly run command ```python3 ./fill_db.py ``` in shell from directory of project to fill your database with data. The script will ask username, password and database name.
And you  are all done. Now you can check `example.ipynb` notebook to see how to work with Character class.
### Dependencies
------------
* **[MySQL](https://www.mysql.com/)**
* **[Python 3](https://www.python.org/)**
* **[Jupyter](https://jupyter.org/)**
* **Common libraries for python**: [pandas](https://pandas.pydata.org/), [numpy](https://www.numpy.org/) and [sqlalchemy](https://www.sqlalchemy.org/) with [driver](https://github.com/PyMySQL/PyMySQL) for MySQL

