from flask import Flask, request, render_template
import logging
import platform
import threading
import urllib2
import sqlite3
import time
app = Flask(__name__)

HALT_EVENT = threading.Event()

'''
functionality
    statistics about the machine it's running on
    ability to issue arbitrary shell commands and display the output
    generalized statistics like ping to a site, your server load, etc
    fuzzy search of bookmarks
design
    simple white or grey background, colorful graphs
    some kind of a JS graphing library for the frontend
    read most of the info directly off proc so it's fast
poll proc every few seconds, put information into a DB w/ timestamp
    frontend is a separate thread/process that renders the app
    queries the DB through JS for information
    need to periodically remove entries older than a day or so from the DB
'''

'''
utility functions
'''

def check_http_resp(url, code):
    logging.info('utility,check_http_resp,{u}'.format(u=url))
    try:
        req = urllib2.urlopen(url)
        return req.code
    except Exception:
        return 404

def gen_nonempty(iterative):
    for item in iterative:
        if item.strip() != '':
            yield item

# read /proc/cpuinfo, parse the data into a dict
def proc_cpuinfo():
    logging.info('utility,proc_cpuinfo')
    with open('/proc/cpuinfo', 'r') as info:
        information = {'proc_count': 0}
        for entry in gen_nonempty(info.readlines()):
            sep = [i.strip() for i in entry.split(':')]
            cat = sep[0]
            datum = sep[1]
            if cat == 'processor':
                information['proc_count'] += 1
            elif cat == 'model name':
                information['model'] = datum
            elif cat == 'BogoMIPS':
                information['speed'] = datum
            elif cat == 'Hardware':
                information['name'] = datum
    return information

# read loadavg from proc
def proc_load():
    logging.info('utility,proc_load')
    with open('/proc/loadavg', 'r') as info:
        data = info.read().split()
        return {'1': data[0], '5': data[1], '15': data[2]}

# read some memory stats from proc. all numbers are in kilobytes
def proc_mem():
    logging.info('utility,proc_mem')
    with open('/proc/meminfo', 'r') as info:
        information = {}
        for memstat in gen_nonempty(info.readlines()):
            sep = [i.strip() for i in memstat.split(':')]
            cat = sep[0]
            datum = sep[1].rstrip(' kB')
            if cat == 'MemTotal':
                information['total'] = datum
            elif cat == 'MemFree':
                information['free'] = datum
            elif cat == 'Buffers':
                information['buffers'] = datum
            elif cat == 'Cached':
                information['cache'] = datum
            elif cat == 'SwapCached':
                information['swap'] = datum
            elif cat == 'Active':
                information['active'] = datum
    return information

'''
database logic
'''

# connect to the database and do the needful
def init_db(schemaname='newtab-schema.sql',
        dbname='newtab-db.sqlite3'):
    logging.info('database,init_db')
    db_conn = sqlite3.connect(dbname)
    cur = db_conn.cursor()
    with open(schemaname, 'r') as f:
        cur.executescript(f.read())
    db_conn.close()

# worker thread which collects statistics every five minutes
def db_worker():
    dbname='newtab-db.sqlite3'
    while not HALT_EVENT.is_set():
        memstats = proc_mem()
        load = proc_load()
        timestamp = None
        # TODO: timestamp = timestamp.blah, put it into a sqlite timestamp struct
        db_conn = sqlite3.connect(dbname)
        cur = db_conn.cursor()
        logging.info('Periodic update')
        cur.execute("INSERT INTO Stats values('{t}','{l1}','{l5}','{l15}','{mT}','{mB}','{mF}','{mC}','{mS}','{mA}')".format(t=timestamp,
            l1=load['1'],
            l5=load['5'],
            l15=load['15'],
            mT=memstats['total'],
            mB=memstats['buffers'],
            mF=memstats['free'],
            mC=memstats['cache'],
            mS=memstats['swap'],
            mA=memstats['active']))
        cur.close()
        db_conn.close()
        time.sleep(60)

'''
application logic
'''

@app.route('/')
def render_dashboard():
    return render_template('index.html')

if (__name__ == '__main__'):
    init_db()
    logging.basicConfig(level=logging.INFO, filename='debug.log')
    worker = threading.Thread(target=db_worker)
    worker.start()
    app.run(host='127.0.0.1', debug=True, port=9001) # this blocks
    HALT_EVENT.set()
