from flask import Flask, request, render_template, Blueprint
import shlex
from subprocess import Popen, PIPE
import logging
import urllib2
import chartkick
import datetime
app = Flask(__name__)

ck = Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")

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

'''
read /proc/cpuinfo, parse the data into a dict
'''
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
            elif cat.lower() == 'bogomips':
                information['speed'] = datum
            elif cat.lower() == 'hardware':
                information['name'] = datum
            elif cat == 'cache size':
                information['cache'] = datum
            elif cat == 'address sizes':
                information['address'] = datum
    return information

'''
read loadavg from proc
'''
def proc_load():
    logging.info('utility,proc_load')
    with open('/proc/loadavg', 'r') as info:
        data = info.read().split()
        now = datetime.datetime.now()
        five = now - datetime.timedelta(minutes=5)
        fifteen = now - datetime.timedelta(minutes=15)
        return {str(now): data[0], str(five): data[1], str(fifteen): data[2]}

'''
read some memory stats from proc. all numbers are in kilobytes
'''
def proc_mem():
    logging.info('utility,proc_mem')
    with open('/proc/meminfo', 'r') as info:
        information = {}
        for memstat in gen_nonempty(info.readlines()):
            sep = [i.strip() for i in memstat.split(':')]
            cat = sep[0]
            datum = sep[1].rstrip(' kB')
            #if cat == 'MemTotal':
            #    information['total'] = datum
            if cat == 'MemFree':
                information['free'] = datum
            #elif cat == 'Buffers':
            #    information['buffers'] = datum
            elif cat == 'Cached':
                information['cache'] = datum
            #elif cat == 'SwapCached':
            #    information['swap'] = datum
            elif cat == 'Active':
                information['active'] = datum
    return information

def weather():
    pass

'''
read from spotify's DBUS api
'''
def now_playing():
    #TODO: Rewrite this using pydbus instead of using a Popen() call
    remove_junk = lambda x: x.split('"')[1]
    cmd = "dbus-send --print-reply --dest=org.mpris.MediaPlayer2.spotify /org/mpris/MediaPlayer2 org.freedesktop.DBus.Properties.Get string:'org.mpris.MediaPlayer2.Player' string:'Metadata'"
    proc = Popen(shlex.split(cmd), stdout=PIPE, stderr=PIPE)
    stdout, stderr = proc.communicate()
    strs = [line.strip() for line in stdout.splitlines() if 'string' in line]
    for idx, item in enumerate(strs):
        if 'xesam:artist' in item:
            artist = strs[idx+1]
        elif 'xesam:album' in item:
            album = strs[idx+1]
        elif 'xesam:title' in item:
            title = strs[idx+1]
        elif 'mpris:artUrl' in item:
            art_link = strs[idx+1]
    return [remove_junk(item) for item in [artist, album, title, art_link]]

'''
application logic
'''

def get_settings():
    return {
            "backgroundColor": "#111",
            "colors": ["#526f33", "#E84F4F", "#9B64FB"],
            "titleColor": "#fff",
            "borderColor": "#333",
            "axisColor": "#333",
            "axisBackgroundColor": "#333",
           }

'''
this method renders a template of graphs without data
using chartkick and skeleton.css for frontend
'''
@app.route('/')
def render_dashboard():
    cpu_info = proc_cpuinfo()
    print cpu_info
    return render_template('index.html',
            load_data=proc_load(),
            mem_data=proc_mem(),
            settings=get_settings(),
            music=now_playing(),
            cpu_info=cpu_info)

if (__name__ == '__main__'):
    import argparse
    p = argparse.ArgumentParser(description='run the server with different behavior')
    p.add_argument('-b', '--bind-host', help='set the host to run on', default='127.0.0.1')
    p.add_argument('-p', '--port', help='set the port to run on', type=int, default=9001)
    args = p.parse_args()
    #logging.basicConfig(level=logging.INFO, filename='debug.log')
    app.run(host=args.bind_host, debug=True, port=args.port)
