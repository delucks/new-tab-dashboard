import flask
import argparse
import getpass
import logging
import urllib2
import chartkick
import importlib
import datetime
import ConfigParser

try:
    import dbus
    APP_WITHOUT_DBUS=False
except ImportError:
    APP_WITHOUT_DBUS=True

app = flask.Flask(__name__)
ck = flask.Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension('chartkick.ext.charts')

'''
Global Utility Functions
'''

gen_nonempty = lambda it: [element for element in it if element.strip() != '']

'''
holds 1+ Column objects
defines a method to autocalculate column
widths and runs it before passing the columns on
'''
class Row(object):
    def __init__(self, columns):
        self.columns = columns
        self.translation = {
                1: 'one',
                2: 'two',
                3: 'three',
                4: 'four',
                5: 'five',
                6: 'six',
                7: 'seven',
                8: 'eight',
                9: 'nine',
               10: 'ten',
               11: 'eleven',
               12: 'twelve'}

    def change_column_width(self):
        each = int(12 / len(self.columns))
        remainder = 12 % len(self.columns)
        first = each + remainder
        each = self.translation[each] # make it english
        first = self.translation[first]
        for idx, col in enumerate(self.columns):
            if idx == 0:
                col.set_size(first)
            else:
                col.set_size(each)

'''
Base class for all Columns
defines a method get_data() which returns a 
dictionary that can be merged into the general
request context for rendering
'''
class Column(object):
    template_path = None

    def __init__(self, size='six'):
        self.size = size

    def set_size(self, new_size):
        self.size = new_size

    def get_data(self):
        raise NotImplementedError('Must subclass Column!')

'''
read some memory stats from proc. all numbers are in kilobytes
'''
class MemoryColumn(Column):
    template_path = 'memory.html'

    def proc_mem(self):
        app.logger.info('MemoryColumn reading proc')
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
read /proc/cpuinfo, parse the data into a dict
'''
class CPUInfoColumn(Column):
    template_path = 'cpu.html'

    def proc_cpuinfo(self):
        app.logger.info('CPUInfoColumn reading proc')
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

    def get_data(self):
        return {'cpu_info': self.proc_cpuinfo()}

'''
read loadavg from proc
'''
class LoadColumn(Column):
    template_path = 'load.html'

    def proc_load(self):
        app.logger.info('LoadColumn reading proc')
        with open('/proc/loadavg', 'r') as info:
            data = info.read().split()
            now = datetime.datetime.now()
            five = now - datetime.timedelta(minutes=5)
            fifteen = now - datetime.timedelta(minutes=15)
            return {str(now): data[0], str(five): data[1], str(fifteen): data[2]}

    def get_data(self):
        return {'load_data': self.proc_load()}

'''
read from spotify's DBUS api
'''
class MusicColumn(Column):
    template_path = 'music.html'

    def now_playing(self):
        app.logger.info('MusicColumn reading dbus')
        bus = dbus.SessionBus()
        try:
            player = bus.get_object('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
            properties_manager = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            meta = properties_manager.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
            meta['xesam:artist'] = meta['xesam:artist'][0] # remove the unnecessary array
            return [v for k, v in meta.iteritems() if ('album' in k or 'title' in k or 'artist' in k or 'art' in k)]
        except dbus.DBusException:
            # returning None will prevent this whole draw element from being displayed
            app.logger.error('Hit a DBusException')
            raise
            return None

    def get_data(self):
        return {'music': self.now_playing()}

'''
This is as blank as you can get, a static column
'''
class LinksColumn(Column):
    template_path = 'links.html'

    def get_data(self):
        return {}

'''
Read the config file, create Row objects for everything
return a list of Row objects that we can pass off to the
view
'''
def parse_config(config_file='newtab-server.cfg'):
    app.logger.info('Reading config file {}'.format(config_file))
    c = ConfigParser.RawConfigParser()
    c.read(config_file)
    rows = []
    # TODO error handling for malformed config
    for row in c.sections():
        mods = []
        for config_entry in c.options(row):
            mod_name = c.get(row, config_entry).lower()
            m = None
            if mod_name == 'memory':
                m = MemoryColumn()
            elif mod_name == 'load':
                m = LoadColumn()
            elif mod_name == 'music':
                if APP_WITHOUT_DBUS:
                    continue
                m = MusicColumn()
            elif mod_name == 'cpu':
                m = CPUInfoColumn()
            else: #mod_name == 'links':
                m = LinksColumn()
            mods.append(m)
        r = Row(mods)
        r.change_column_width()
        rows.append(r)
    return rows

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
    # handle arguments
    p = argparse.ArgumentParser(description='run the server with different behavior')
    p.add_argument('-b', '--bind-host', help='set the host to run on', default='127.0.0.1')
    p.add_argument('-p', '--port', help='set the port to run on', type=int, default=9001)
    p.add_argument('-c', '--configfile', help='specify an alternate config file', default='newtab.cfg')
    p.add_argument('-d', '--debug', help='enable debugging output', action='store_true')
    args = p.parse_args()
    # initialize the application
    app.logger.info('Starting application')
    app.run(host=args.bind_host, debug=args.debug, port=args.port)
