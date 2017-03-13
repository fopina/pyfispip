"""
An attempt to support both py2 and py3
"""
import sys


PY3 = sys.version_info[0] > 2

if PY3:
    _basestring = str
    _range = range

    def makestring(x):
        if x is not None:
            if isinstance(x, bytes):
                x = x.decode('latin-1')
        return x

    def makebytes(x):
        if x is not None:
            if isinstance(x, str):
                return x.encode('latin-1')
        return x
else:
    _basestring = basestring
    _range = xrange

    def makestring(x):
        return x

    def makebytes(x):
        return x
