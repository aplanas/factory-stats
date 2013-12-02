#!/usr/bin/env python

import argparse
import csv
import re

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fix CSV tables for blog publication.')
    parser.add_argument('csv', help='CSV file')
    args = parser.parse_args()

    table = []
    with open(args.csv) as f:
        reader = csv.reader(f)
        for row in reader:
            name, order = row
            name = re.sub(r'\s+<[^>]+>', '', name).strip()
            order = int(order)
            if len(table) and table[-1][1] == order:
                table[-1][0] += ', ' + name
            else:
                table.append([name, order])

    for row in table:
        print '%s, %d' % (row[0], row[1])
