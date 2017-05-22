# -*- coding: utf-8 -*-
# Standard imports
import argparse
from src.biopax2cadbiom import main
from src.commons import DIR_PICKLE, DIR_OUTPUT


if __name__ == "__main__" :
    parser = argparse.ArgumentParser(
        description='biopax2cabiom.py is a script to transforme a Biopax data \
        from a RDBMS to a Cabiom model.'
    )
    parser.add_argument('--pickleBackup', type=str, nargs='?',
                        default=DIR_PICKLE + 'backup.p',
                        help='enter a file path to save the script variables.'
    )
    parser.add_argument('--listOfGraphUri', nargs='+',
                        help='enter a list of RDF graph.'
    )
    parser.add_argument('--cadbiomFile', type=str, nargs='?',
                        default=DIR_OUTPUT + 'model.bcx',
                        help='enter a file path to generate the Cadbiom model.'
    )
    parser.set_defaults(func=main)

    # get program args and launch associated command
    args = parser.parse_args()

    # Set log level
    #LOGGER.setLevel(cm.LOG_LEVELS[vars(args)['verbose']])
    # launch associated command
    args.func(args)
