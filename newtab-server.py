import flask
import getpass
import logging
import urllib2
import chartkick
import importlib
import datetime
import ConfigParser
app = flask.Flask(__name__)

try:
    import dbus
    APP_WITHOUT_DBUS=False
except ImportError:
    APP_WITHOUT_DBUS=True

ck = flask.Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension("chartkick.ext.charts")

'''
holds 1+ Column objects
defines a method to autocalculate column
widths and runs it before passing the columns on
'''
class Row(object):
    def __init__(self, num_columns, columns):
        self.num_columns = num_columns
        self.columns = columns

    def calculate_column_width(self):
        pass

'''
Base class for all Columns
defines a method get_data() which returns a 
dictionary that can be merged into the general
request context for rendering
'''
class Column(object):
    coltype = None

    def __init__(self, size):
        self.size = size

    def get_data(self):
        raise NotImplementedError('Must subclass Column!')

'''
read some memory stats from proc. all numbers are in kilobytes
'''
class MemoryColumn(Column):
    coltype = "Memory"

    def proc_mem(self):
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

    def get_data(self):
        return {'mem_data': self.proc_mem()}

'''
This is as blank as you can get, a static column
'''
class LinksColumn(Column):
    coltype = "Links"

    def get_data(self):
        return {}

'''
Read the config file, create Row objects for everything
return a list of Row objects that we can pass off to the
view
'''
def parse_config(config_file='newtab-server.cfg'):
    #c = ConfigParser.RawConfigParser()
    #c.read(config_file)
    #numrows = len(c.sections())
    rows = []
    m = MemoryColumn(size="six")
    l = LinksColumn(size="six")
    r1 = Row(2, [m, l])
    rows.append(r1)
    #for row_name in c.sections():
    #    for col_name in c.options(row_name):
    #        opt = c.get(row_name, col_name)
    #        mod = importlib.import_module(opt.split(',')[-1])
    #        row = mod.Row()
    #        rows.append(row)
    #return numrows
    return rows

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
    rows = flask.g.get('rows', None)
    context = {'rows': rows,
            'settings': get_settings(),
            'user': getpass.getuser(),
            'time': get_time(),
            'host': getpass.os.uname()[1],
            }
    for row in rows:
        # for item in columns:
        for column in row.columns:
            # call item's get_data() method, which returns a dict like {'mem_data': {}}
            col_data = column.get_data()
            # merge its dict into context
            context.update(col_data)
    return flask.render_template('dynamic.html', **context)

#TODO: Find a way for this to happen on the first app load and persist the objects
@app.before_request
def get_rows():
    rows = parse_config()
    flask.g.rows = rows

if (__name__ == '__main__'):
    import argparse
    p = argparse.ArgumentParser(description='run the server with different behavior')
    p.add_argument('-b', '--bind-host', help='set the host to run on', default='127.0.0.1')
    p.add_argument('-p', '--port', help='set the port to run on', type=int, default=9001)
    args = p.parse_args()
    # this should hopefully allow us to bind rows to the global 'g'
    app.run(host=args.bind_host, debug=True, port=args.port)
