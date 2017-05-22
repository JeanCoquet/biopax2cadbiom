# -*- coding: utf-8 -*-

# Standard imports
from logging.handlers import RotatingFileHandler
import logging
import itertools as it
from collections import defaultdict

# Paths
DIR_LOGS            = 'logs/'
DIR_DATA            = 'data/'
DIR_PICKLE          = 'backupPickle/'

# Logging
LOGGER_NAME         = "biopax2cadbiom"
LOG_LEVEL           = logging.DEBUG

# SPARQL endpoint
SPARQL_PATH         = "https://openstack-192-168-100-241.genouest.org/sparql/"


################################################################################

def logger(name=LOGGER_NAME, logfilename=None):
    """Return logger of given name, without initialize it.

    Equivalent of logging.getLogger() call.
    """
    return logging.getLogger(name)

_logger = logging.getLogger(LOGGER_NAME)
_logger.setLevel(LOG_LEVEL)

# log file
formatter    = logging.Formatter(
    '%(asctime)s :: %(levelname)s :: %(message)s'
)
file_handler = RotatingFileHandler(
    DIR_LOGS + LOGGER_NAME + '.log',
    'a', 10000000, 1
)
file_handler.setLevel(LOG_LEVEL)
file_handler.setFormatter(formatter)
_logger.addHandler(file_handler)

# terminal log
stream_handler = logging.StreamHandler()
formatter      = logging.Formatter('%(levelname)s: %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(LOG_LEVEL)
_logger.addHandler(stream_handler)

def log_level(level):
    """Set terminal log level to given one"""
    handlers = (_ for _ in _logger.handlers
                if _.__class__ is logging.StreamHandler
               )
    for handler in handlers:
        handler.setLevel(level.upper())


# Some convenient functions
def chunk_this(iterable, length):
    """Split iterable in chunks of equal sizes"""
    iterator = iter(iterable)

    # For dictionnaries
    if (type(iterable) == type(dict())) or (type(iterable) == type(defaultdict())):
        # + 1: adjust length
        for i in range(0, len(iterable), length):
            yield {k:iterable[k] for k in it.islice(iterator, length + 1)}
    else:
        # For (all) other iterables (?)
        while True:
            # + 1: adjust length
            chunk = tuple(it.islice(iterator, length + 1))
            if not chunk:
               return
            yield chunk


def merge_dicts(*dict_args):
    """Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    """
    # Syntax for Python 3.5
    # result = {**dict1, **dict2}
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result

