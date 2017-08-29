#!/usr/bin/env python
#
# Author: Tim Thomas (tithomas@cisco.com)
# Created: 8/25/17
#
# Proof of concept for using regular expression-based pattern matching and text replacement
# for Cisco configuration files. Similar to what something like 'sed' could do with REs.

from __future__ import print_function
import argparse
import sys
import re

DEFAULT_CONFIG_FILE = "config.txt"

# Some regex definitions for the config file contents

RE_COMMENT = re.compile(r'^\s*#')
RE_BLANK = re.compile(r'^\s*$')
RE_CONFIG_LINE = re.compile(r'^\s*"(.*)"\s*"(.*)"')


def getArgs():
    parser = argparse.ArgumentParser(description="Find and replace specific patterns in a source Cisco config")
    parser.add_argument('-s', '--source', required=True, action='store', help='Source file name')
    parser.add_argument('-o', '--output', required=False, action='store', help='Output file name', type=str, default=None)
    parser.add_argument('-c', '--config', required=False, action='store', help='Config file', type=str, default=DEFAULT_CONFIG_FILE)
    parser.add_argument('-v', '--verbose', required=False, action='store_true', help='Verbose output', default=False)
    return parser.parse_args()


def readConfig(args):
    if args.verbose:
        sys.stderr.write("Using config file '{}'\n".format(args.config))

    configFile = open(args.config, 'r')
    lineNumber = 0
    patternList = []

    for line in configFile:
        lineNumber += 1

        # Ignore blank lines and lines starting with a '#'

        if re.match(RE_BLANK, line):
            continue
        if re.match(RE_COMMENT, line):
            continue

        # For each config line, expect to see a target pattern followed by the replacement text

        configEntry = re.match(RE_CONFIG_LINE, line)
        if configEntry:
            patternList.append([re.compile(configEntry.group(1)), configEntry.group(2), 0, {}])
        else:
            sys.stderr.write("(readConfig) WARNING: Syntax error in config line {}, ignoring\n".format(lineNumber))

    configFile.close()

    return patternList


def scrubSource(args, patternList, patternCount):
    if args.verbose:
        sys.stderr.write("Loaded {} patterns\n".format(patternCount))

    try:
        sourceFile = open(args.source, 'r')
    except IOError:
        sys.stderr.write("(scrubSource) ERROR: unable to open source file '{}'\n".format(args.source))
        return 1

    replaceCount = 0
    lineNumber = 0

    # Here's the primary loop. For each line of the source, it will look for every loaded pattern.
    # For each pattern that's found in the line, it adds to a list of where the matches occurred
    # and what replacement text to use. That list is then used to construct a new output line.

    for sourceLine in sourceFile:
        scrubLine = sourceLine
        lineNumber += 1
        resultList = []
        for entry in patternList:

            # Iterate over each match of this pattern in the line

            for result in re.finditer(entry[0], sourceLine):
                if args.verbose:
                    sys.stderr.write("Line {}: found match '{}'\n".format(lineNumber, result.group(0)))

                # Has this match been seen before? If not, add it to the dictionary of matches for
                # this pattern with a unique identifier as the value.
                #
                # Note this is making the basic assumption that RE match group 1 is the target

                try:
                    if result.group(1) not in entry[3]:
                        entry[2] += 1
                        entry[3][result.group(1)] = entry[2]
                except IndexError:
                    sys.stderr.write("(scrubSource) ERROR: pattern '{}' needs at least one match group\n".format(entry[0]))
                    continue

                # Add this match and its position to the list of matches for this line

                resultList.append([result.start(1), result.end(1), entry[1], entry[3][result.group(1)]])

        # No more patterns to look for in this line - is there any replacement work to do?

        if len(resultList) != 0:

            # Sort the replacements based on starting position
            #
            # TODO: At least detect and potentially handle overlapping replacements

            resultList.sort(key=lambda item: item[0])

            # Construct a new line that includes all the replacement text. For each replacement,
            # assume the replacement text might want to include the unique id of the original string

            index = 0
            newLine = ""
            for replacement in resultList:
                newLine += sourceLine[index:replacement[0]] + replacement[2].format(replacement[3])
                index = replacement[1]
                replaceCount += 1

            # Use the newly-constructed line for output

            scrubLine = newLine + sourceLine[index:]

        sys.stdout.write(scrubLine)

    sourceFile.close()

    if args.verbose:
        sys.stderr.write("{} replacement{} done\n".format(replaceCount, 's' if replaceCount > 1 else ''))
    return 0


def main():
    args = getArgs()

    # Override stdout if an output file specified

    if args.output is not None and args.output != '-':
        sys.stdout = open(args.output, 'w')

    patternList = readConfig(args)
    patternCount = len(patternList)

    if patternCount == 0:
        sys.stderr.write("No target patterns loaded - exiting\n")
        return 1

    return scrubSource(args, patternList, patternCount)


if __name__ == '__main__':
    sys.exit(main())
