from flask import Flask, request, render_template, Blueprint
import getpass
import logging
import urllib2
import chartkick
import datetime
import ConfigParser
app = Flask(__name__)

try:
    import dbus
    APP_WITHOUT_DBUS=False
except ImportError:
    APP_WITHOUT_DBUS=True

ck = Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")

'''
split up each box into it's own "module" that outputs the HTML for it
have a custom configuration template file that you can read in to generate
the page
each method which returns data is totally contained in the module, and they're
dynamically loaded in order to conserve memory
the base module doesn't display anything
except holding all the styling and stuff 
should be room for text boxes

maybe have everything put into render_template, but have some of the methods it calls
return None
these None-returning methods would be caught by the template and just not displayed
but how do we do order?

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

def parse_config(config_file='newtab-server.cfg'):
    c = ConfigParser.RawConfigParser()
    c.read(config_file)
    for item in c.sections():
        continue
        # import the file using __import__()
        # call its constructor using the size of the column

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

'''
read from spotify's DBUS api
'''
def now_playing():
    bus = dbus.SessionBus()
    try:
        player = bus.get_object('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
        properties_manager = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
        meta = properties_manager.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
        meta['xesam:artist'] = meta['xesam:artist'][0] # remove the unnecessary array
        return [v for k, v in meta.iteritems() if ('album' in k or 'title' in k or 'artist' in k or 'art' in k)]
    except dbus.DBusException:
        # returning None will prevent this whole draw element from being displayed
        return None

def get_settings():
    return {
            "backgroundColor": "#111",
            "colors": ["#E84F4F", "#9B64FB", "#526f33"],
            "titleColor": "#fff",
            "borderColor": "#333",
            "axisColor": "#333",
            "axisBackgroundColor": "#333",
            "fontName": "monospace",
           }

def get_time():
    curr = datetime.datetime.now()
    return curr.strftime('%A %b %w at %H:%M:%S')

'''
render the graphs, display all the info!
'''
@app.route('/')
def render_dashboard():
    cpu_info = proc_cpuinfo()
    cpu_load = proc_load()
    if APP_WITHOUT_DBUS:
        music_info = None # dern platform compat
    else:
        music_info = now_playing()
    return render_template('index.html',
            load_data=cpu_load,
            mem_data=proc_mem(),
            settings=get_settings(),
            music=music_info,
            user=getpass.getuser(),
            time=get_time(),
            host=getpass.os.uname()[1],
            overview = cpu_load[cpu_load.keys()[0]],
            cpu_info=cpu_info)

if (__name__ == '__main__'):
    import argparse
    p = argparse.ArgumentParser(description='run the server with different behavior')
    p.add_argument('-b', '--bind-host', help='set the host to run on', default='127.0.0.1')
    p.add_argument('-p', '--port', help='set the port to run on', type=int, default=9001)
    args = p.parse_args()
    #logging.basicConfig(level=logging.INFO, filename='debug.log')
    app.run(host=args.bind_host, debug=True, port=args.port)
