#! /usr/bin/python3
import configparser
import os
import subprocess

from sqlalchemy import create_engine, text

DB_PATH = './Full_DB'
UPDATES_PATH = './updates'

if 'main.ini' not in os.listdir():
    config = configparser.ConfigParser()
    print('Type username, password and database name separated with whitespace')
    print('If you didn\'t create new user and new database you can leave and create them')
    print('Press CTRL + C to leave')
    username, password, database = input().split(' ')
    
    config['SQL'] = {'username': username, 'password': password, 'database': database}
    with open('main.ini', 'w') as configfile:
        config.write(configfile)

config = configparser.ConfigParser()
config.read('main.ini')


engine = create_engine('mysql+pymysql://{}:{}@localhost/{}'.format(config['SQL']['username'],
                                                                   config['SQL']['password'],
                                                                   config['SQL']['database']))

# main database
with open(os.path.join(DB_PATH, 'ClassicDB_1_7_z2684.sql'), 'rb') as f_in:
    cmd = f_in.read()

subprocess.run(['mysql', '-u', config['SQL']['username'],
                '-p' + config['SQL']['password'],
                '-D', config['SQL']['database']],
               input=cmd)


# updates for database
for file in os.listdir(UPDATES_PATH):
    try:
        with open(os.path.join(UPDATES_PATH, file), 'rb') as f_in:
            cmd = f_in.read()
        subprocess.run(['mysql', '-u', config['SQL']['username'],
                        '-p' + config['SQL']['password'],
                        '-D', config['SQL']['database']],
                       input=cmd)
    except:
        print('An exception occurred with update: {}'.format(file))