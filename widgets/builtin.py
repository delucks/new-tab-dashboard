import getpass 
import logging
import datetime

'''
This file defines all built-in widget objects that subclass from Column
To define your own, edit widgets/custom.py
'''

# initialize the flask logger so this still works
FLASK_LOGGER = logging.getLogger('newtab')
gen_nonempty = lambda it: [element for element in it if element.strip() != '']

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
        FLASK_LOGGER.info('MemoryColumn reading proc')
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
    Windows-specific way to grab memory stats
    Uses the win32 api ugh
    '''
    def win_mem(self):
        import ctypes
        class MemStatStruct(ctypes.Structure):
            _fields_ = [('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', ctypes.c_ulonglong),
                        ('ullAvailPhys', ctypes.c_ulonglong),
                        ('ullTotalPageFile', ctypes.c_ulonglong),
                        ('ullAvailPageFile', ctypes.c_ulonglong),
                        ('ullTotalVirtual', ctypes.c_ulonglong),
                        ('ullAvailVirtual', ctypes.c_ulonglong),
                        ('sullAvailExtendedVirtual', ctypes.c_ulonglong)]

            def __init__(self):
                self.dwLength = ctypes.sizeof(self)
                super(MemStatStruct, self).__init__()

        struct = MemStatStruct()
        # this is so readable
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(struct))
        free = struct.ullAvailPhys
        active = struct.ullTotalPhys - free
        free = int(free / 1024)
        active = int(active / 1024)
        return {'free': free, 'active': active}

    def get_data(self):
        if getpass.os.name == 'nt':
            return {'mem_data': self.win_mem()}
        else:
            return {'mem_data': self.proc_mem()}


'''
read /proc/cpuinfo, parse the data into a dict
'''
class CPUInfoColumn(Column):
    template_path = 'cpu.html'

    def proc_cpuinfo(self):
        FLASK_LOGGER.info('CPUInfoColumn reading proc')
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
        FLASK_LOGGER.info('LoadColumn reading proc')
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
        import dbus
        FLASK_LOGGER.info('MusicColumn reading dbus')
        bus = dbus.SessionBus()
        try:
            player = bus.get_object('org.mpris.MediaPlayer2.spotify', '/org/mpris/MediaPlayer2')
            properties_manager = dbus.Interface(player, 'org.freedesktop.DBus.Properties')
            meta = properties_manager.Get('org.mpris.MediaPlayer2.Player', 'Metadata')
            meta['xesam:artist'] = meta['xesam:artist'][0] # remove the unnecessary array
            return [v for k, v in meta.iteritems() if ('album' in k or 'title' in k or 'artist' in k or 'art' in k)]
        except dbus.DBusException:
            # returning None will prevent this whole draw element from being displayed
            FLASK_LOGGER.error('Hit an unexpected DBusException')
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
