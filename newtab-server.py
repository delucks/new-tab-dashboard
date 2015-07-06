import flask
import argparse
import logging
import urllib2
import chartkick
import ConfigParser
from socket import gethostname

# attempt to import dbus and connect to spotify
try:
    import dbus
    APP_WITHOUT_DBUS=False
    try:
        bus = dbus.SystemBus()
        player = bus.get_object('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
    except dbus.DBusException:
        APP_WITHOUT_DBUS=True
except ImportError:
    APP_WITHOUT_DBUS=True

'''
Global Variables / Utility Functions
'''

app = flask.Flask(__name__)
app.config['LOGGER_NAME'] = 'newtab'
app.debug_log_format = '%(asctime)s:%(filename)s:%(levelname)s:%(message)s'
ck = flask.Blueprint('ck_page', __name__, static_folder=chartkick.js(), static_url_path='/static')
app.register_blueprint(ck, url_prefix='/ck')
app.jinja_env.add_extension('chartkick.ext.charts')

# initialize all builtin widgets
from widgets.builtin import *
# initialize all custom widgets
from widgets.custom import *

# register your custom widgets here
available_widgets = {
        'memory': MemoryColumn,
        'load': LoadColumn,
        'links': LinksColumn,
        'music': MusicColumn,
        'cpu': CPUInfoColumn,
}

'''
holds 1+ Column objects
defines a method to autocalculate column
widths and runs it before passing the columns on
'''
class Row(object):
    def __init__(self, columns):
        self.columns = columns
        # this is needed for skeleton.css
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
    if not 'row0' in c.sections():
        app.logger.fatal('Configuration file {} doesn\'t contain any definition for row0!'.format(config_file))
        raise SystemExit
    for row in c.sections():
        mods = []
        for config_entry in c.options(row):
            mod_name = c.get(row, config_entry).lower()
            if not mod_name in available_widgets:
                app.logger.error('Malformed widget name in config file! {} is not valid.'.format(mod_name))
                continue # try again with the next opt
            else:
                if APP_WITHOUT_DBUS and mod_name == 'music':
                    continue
                app.logger.info('Loading widget {}'.format(mod_name))
                m = available_widgets[mod_name]()
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
    return curr.strftime('%A %b %d at %H:%M:%S')

# TODO: get rid of this global variable, find a better way to only parse once
rows = parse_config()

'''
render the graphs, display all the info!
'''
@app.route('/')
def render_dashboard():
    context = {'rows': rows,
            'settings': get_settings(),
            'user': getpass.getuser(),
            'time': get_time(),
            'host': gethostname(),
            }
    for row in rows:
        for column in row.columns:
            # call item's get_data() method, which returns a dict like {'mem_data': {}}
            col_data = column.get_data()
            # merge its dict into context
            context.update(col_data)
    return flask.render_template('dynamic.html', **context)

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
