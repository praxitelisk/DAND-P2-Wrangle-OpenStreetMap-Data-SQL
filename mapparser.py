import xml.etree.cElementTree as ET
import pprint
from collections import defaultdict


def count_tags(filename):
    """ The top tags and how many of each"""
    counts = defaultdict(int)
    for event, node in ET.iterparse(filename):
        if event == 'end':
            counts[node.tag] += 1
        node.clear()
    return counts


filename = "maps-xml/London_full.osm"
pprint.pprint(count_tags(filename))
