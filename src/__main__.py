# -*- coding: utf-8 -*-
# Standard imports
import argparse, os
from src.biopax2cadbiom import main
from src.commons import DIR_PICKLE, DIR_OUTPUT


class ReadableFile(argparse.Action):
    """
    http://stackoverflow.com/questions/11415570/directory-path-types-with-argparse
    """

    def __call__(self, parser, namespace, values, option_string=None):
        prospective_file = values

        if not os.path.isfile(prospective_file):
            raise argparse.ArgumentTypeError(
                "readable_file:{0} is not a valid path".format(
                    prospective_file)
                )

        if os.access(prospective_file, os.R_OK):
            setattr(namespace, self.dest, prospective_file)
        else:
            raise argparse.ArgumentTypeError(
                "readable_file:{0} is not a readable file".format(
                    prospective_file)
                )


if __name__ == "__main__" :
    parser = argparse.ArgumentParser(
        description='biopax2cabiom.py is a script to transforme a Biopax data \
        from a RDBMS to a Cabiom model.'
    )
    parser.add_argument('--pickleBackup', type=str, nargs='?',
                        default=DIR_PICKLE + 'backup.p', action=ReadableFile,
                        help='enter a file path to save the script variables.'
    )
    parser.add_argument('--listOfGraphUri', nargs='+',
                        help='enter a list of RDF graph.'
    )
    parser.add_argument('--cadbiomFile', type=str, nargs='?',
                        default=DIR_OUTPUT + 'model.bcx', action=ReadableFile,
                        help='enter a file path to generate the Cadbiom model.'
    )
    parser.set_defaults(func=main)

    # get program args and launch associated command
    args = parser.parse_args()

    # Set log level
    #LOGGER.setLevel(cm.LOG_LEVELS[vars(args)['verbose']])
    # launch associated command
    args.func(args)
