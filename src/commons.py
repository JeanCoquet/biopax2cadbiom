# -*- coding: utf-8 -*-

# Standard imports
from logging.handlers import RotatingFileHandler
import logging

# Paths
DIR_LOGS            = 'logs/'
DIR_DATA            = 'data/'
DIR_PICKLE          = 'backupPickle/'
DIR_OUTPUT          = 'output/'
DIR_TEST_CASES      = 'testCases/'
FILE_README         = 'README.md'

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
formatter = logging.Formatter(
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
