# Import libraries
import csv
import codecs
import pprint
import re
import xml.etree.cElementTree as ET
import cerberus
from collections import defaultdict

# Import Schema for validation

import schema

# OSM fil path
OSM_PATH = "maps-xml/london_full.osm"

# CSV path names
NODES_PATH = "center_of_london_nodes.csv"
NODE_TAGS_PATH = "center_of_london_nodes_tags.csv"
WAYS_PATH = "center_of_london_ways.csv"
WAY_NODES_PATH = "center_of_london_ways_nodes.csv"
WAY_TAGS_PATH = "center_of_london_ways_tags.csv"

# Regular expressions
LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# a list of regular expressions for parsing and cleaning street types
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
omit_streets_ending_with_abbreviations = re.compile(r'\s*\d+\S*$', re.IGNORECASE)
at_least_three_words_re = re.compile(r'[A-Z][a-z]{2,}$')

# another list of regular expressions for auditing and cleaning postal codes
# kudos to https://en.wikipedia.org/wiki/Postcodes_in_the_United_Kingdom#validation
postal_code_no_space_re = re.compile(r'^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) [0-9][A-Za-z]{2})$')
postal_code_with_space_re = re.compile(r'^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) {0,1}[0-9][A-Za-z]{2})$')


street_types = defaultdict(set)

# Expected street values
expected = ['Street', 'Avenue', 'Road', 'Lane']

# expected street endings
expected_list = ["Street", "Road"]

# UPDATE THIS VARIABLE, this variable contains address' endings writen in different forms and have the same meaning
# in order to contain this issue a mapping variable was created in order to map the different endings who have the
# same meaning
# UPDATE THIS VARIABLE, this variable contains address' endings writen in different forms and have the same meaning
# in order to contain this issue a mapping variable was created in order to map the different endings who have the
# same meaning
mapping = {"St": "Street", "street": "Street", "road": "Road", "St.": "Street", "st": "Street",
           "Ave": "Avenue", "HIll": "Hill", "boulevard": "Boulevard", "close": "Close",
           "drive": "Drive", "footway": "Footway", "house": "House", "lane": "Lane",
           "market": "Market", "parade": "Parade", "park": "Park", "passage": "Passage",
           "place": "Place", "residential": "Residential", "Sq": "Square", "Road)": "Road",
           "Rd)": "Road", "Rd": "Road", "Rd,": "Road", "ROAD": "Road", "ROAD,": "Road", "Pl": "Place",
           "North)": "North", "James'": "James", "James's": "James", "GROVE": "Grove", "station": "Station",
           "square": "Square", "shops": "Shops", "row": "Row", "STREET": "Street", "Park,": "Park",
           "Lower)": "Lower"}

# Schema
SCHEMA = schema.schema

# CSV fields
NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

counterNone = {'nod': 0, 'nod_tags': 0, 'wy': 0, 'wy_tag': 0, 'way_nod': 0}


# Clean and shape node or way XML element to Python dict
def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS,
                  problem_chars=PROBLEMCHARS, default_tag_type='regular'):
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []  # Handle secondary tags the same way for both node and way elements

    # YOUR CODE HERE
    # Node tag elements
    if element.tag == 'node':

        # Get element attributes
        element_attributes = element.attrib
        # Set attribute types
        node_attribs['id'] = int(element_attributes['id'])  # int
        node_attribs['lat'] = float(element_attributes['lat'])  # float
        node_attribs['lon'] = float(element_attributes['lon'])  # float
        try:
            node_attribs['user'] = element_attributes['user']
            node_attribs['uid'] = int(element_attributes['uid'])  # int
        except:
            node_attribs['user'] = "unknown"
            node_attribs['uid'] = -1
        node_attribs['version'] = element_attributes['version']
        node_attribs['changeset'] = int(element_attributes['changeset'])  # int
        node_attribs['timestamp'] = element_attributes['timestamp']

        # Node tag elements
        children = element.iter('tag')
        for child in children:
            # Get child attributes (tag)
            node_tags_dict = {}
            child_attributes = child.attrib
            # Set tag child attributes and update street and postal code attributes
            node_tags_dict['id'] = int(element_attributes['id'])
            child_attr_key = child_attributes['k']
            child_attr_value = child_attributes['v']

            # Get rid of attribute keys with problematic characters
            if PROBLEMCHARS.match(child_attr_key):
                continue
            # Clean attribute keys with colons
            elif LOWER_COLON.match(child_attr_key):
                attribute_list = child_attr_key.split(':')
                node_tags_dict['type'] = attribute_list[0]
                node_tags_dict['key'] = attribute_list[1]
                if node_tags_dict['key'] == "street":
                    node_tags_dict['value'] = update_street_name(child_attr_value)
                elif node_tags_dict['key'] == "postal_code":
                    node_tags_dict['value'] = update_postal_code(child_attr_value)
                else:
                    node_tags_dict['value'] = child_attr_value
            # Deal with all attributes
            else:
                node_tags_dict['type'] = default_tag_type
                node_tags_dict['key'] = child_attr_key
                if node_tags_dict['key'] == "street":
                    node_tags_dict['value'] = update_street_name(child_attr_value)
                elif node_tags_dict['key'] == "postal_code":
                    node_tags_dict['value'] = update_postal_code(child_attr_value)
                else:
                    node_tags_dict['value'] = child_attr_value

            # Append new tag row
            tags.append(node_tags_dict)

        # print {'node': node_attribs, 'node_tags': tags}
        return {'node': node_attribs, 'node_tags': tags}

    # Way tag elements
    elif element.tag == 'way':
        # Get element attributes
        element_attributes = element.attrib

        # Get element way attributes
        way_attribs['id'] = int(element_attributes['id'])
        way_attribs['user'] = element_attributes['user']
        way_attribs['uid'] = int(element_attributes['uid'])
        way_attribs['version'] = element_attributes['version']
        way_attribs['changeset'] = int(element_attributes['changeset'])
        way_attribs['timestamp'] = element_attributes['timestamp']

        # Get tag child elements
        tag_children = element.iter('tag')
        for tag in tag_children:
            way_tags_dict = {}
            # Get child attributes
            tag_attributes = tag.attrib

            # Set child attributes
            way_tags_dict['id'] = int(element_attributes['id'])
            tag_attr_key = tag_attributes['k']
            tag_attr_value = tag_attributes['v']

            # Get rid of attribute keys with problematic characters
            if PROBLEMCHARS.match(tag_attr_key):
                continue
            # Clean attribute keys with colons
            elif LOWER_COLON.match(tag_attr_key):
                attribute_list = tag_attr_key.split(':')
                way_tags_dict['type'] = attribute_list[0]
                way_tags_dict['key'] = attribute_list[1]
                if way_tags_dict['key'] == "street":
                    way_tags_dict['value'] = update_street_name(tag_attr_value)
                elif way_tags_dict['key'] == "postal_code":
                    way_tags_dict['value'] = update_postal_code(tag_attr_value)
                else:
                    way_tags_dict['value'] = tag_attr_value
            # Deal with all attributes
            else:
                way_tags_dict['type'] = default_tag_type
                way_tags_dict['key'] = tag_attr_key
                if way_tags_dict['key'] == "street":
                    way_tags_dict['value'] = update_street_name(tag_attr_value)
                elif way_tags_dict['key'] == "postal_code":
                    way_tags_dict['value'] = update_postal_code(tag_attr_value)
                else:
                    way_tags_dict['value'] = tag_attr_value
            # Append new tag row
            tags.append(way_tags_dict)

        # Way-node tags
        pos = -1
        # Get nd child elements
        children_nd = element.iter('nd')

        for nd in children_nd:
            nd_tags_dict = {}
            # Get child attributes
            nd_attributes = nd.attrib

            nd_tags_dict['id'] = int(element_attributes['id'])
            nd_tags_dict['node_id'] = int(nd_attributes['ref'])

            pos += 1
            nd_tags_dict['position'] = int(pos)
            # Append new nd row
            way_nodes.append(nd_tags_dict)

        return {'way': way_attribs, 'way_nodes': way_nodes, 'way_tags': tags}

    # ================================================== #


#               Helper Functions                     #
# ================================================== #

# Function that updates postal code value
def update_postal_code(postal_code):

    if postal_code_no_space_re.match(postal_code):
        return postal_code
    elif postal_code_with_space_re.match(postal_code):
        return postal_code
    # Any other string different than a postal code
    else:
        return 'Not a postal code'


# Function that updates street value
def update_street_name(street_name):
    # the function audit the street names, extracts the street type and corrects possible street type abbreviations

    # get the final word which will be the street type from the address
    candidate_street_type = street_type_re.search(street_name)
    if candidate_street_type:
        street_type = candidate_street_type.group()
        # street_type = street_type.strip()

        # omit street types that end with numbers or numbers with letters and in general are abbreviations
        check_for_strange_ending_address = omit_streets_ending_with_abbreviations.search(street_type)
        if not check_for_strange_ending_address:

            # if the newly found street type is in the expected_list, then append to the dict with key
            # the street type and value the street name
            if street_type in expected_list:
                # debug print
                # print("expected street type:", street_type, ",", street_name)
                street_types[street_type].add(street_name)

            # else if the newly found street type is not in expected list then search it in mapping list
            elif street_type not in expected_list and street_type in mapping:

                street_name = update_name(street_name)
                # debug print
                # print("mapping new street type:", street_type, ",", street_name)
                street_types[mapping[street_type]].add(street_name)

            # else check if is a valid written in english street type then add it to expected list
            elif street_type not in expected_list and street_type not in mapping:

                if at_least_three_words_re.search(street_type) and is_english_word(street_type):
                    # debug print
                    # print("Adding new street type:", street_type, ",", street_name)
                    street_types[street_type].add(street_name)
                    expected_list.append(street_type)

    return street_name


def is_english_word(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True


def update_name(name):
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        if street_type not in expected_list and street_type in mapping:
            name = re.sub(street_type_re, mapping[street_type], name)

    return name


# Function that updates street value
# def update_street(street_name):
#     # Case 1: Abbreviations
#     if street_type1_re.search(street_name):
#         street_name = re.sub(street_type1_re, ' Street', street_name)
#         return street_name
#     # Case 2: Complete address
#     elif street_type2_re.search(street_name):
#         street_list = street_name.split(',')
#         for street_item in street_list:
#             for expected_item in expected:
#                 if expected_item in street_item:
#                     street_name = street_item.strip()
#         return street_name
#     # case 3: Postal code
#     elif postal_code_re.search(street_name):
#         return ''
#     # case 4: Any normal case
#     else:
#         return street_name


def get_element(osm_file, tags=('node', 'way', 'relation')):
    """Yield element if it is the right type of tag"""

    context = ET.iterparse(osm_file, events=('start', 'end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()


def validate_element(element, validator, schema=SCHEMA):
    """Raise ValidationError if element does not match schema"""
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{0}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))


class UnicodeDictWriter(csv.DictWriter, object):
    """Extend csv.DictWriter to handle Unicode input"""
    '''
    The method has been modified in order to work in windows environment
    '''

    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: v for k, v in row.items()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


# ================================================== #
#               Main Function                        #
# ================================================== #
def process_map(file_in, validate):
    """Iteratively process each XML element and write to csv(s)"""
    '''
    encoding = 'utf8' has been addedd
    '''

    with codecs.open(NODES_PATH, 'w', encoding='utf8') as nodes_file, \
            codecs.open(NODE_TAGS_PATH, 'w', encoding='utf8') as nodes_tags_file, \
            codecs.open(WAYS_PATH, 'w', encoding='utf8') as ways_file, \
            codecs.open(WAY_NODES_PATH, 'w', encoding='utf8') as way_nodes_file, \
            codecs.open(WAY_TAGS_PATH, 'w', encoding='utf8') as way_tags_file:

        nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
        node_tags_writer = UnicodeDictWriter(nodes_tags_file, NODE_TAGS_FIELDS)
        ways_writer = UnicodeDictWriter(ways_file, WAY_FIELDS)
        way_nodes_writer = UnicodeDictWriter(way_nodes_file, WAY_NODES_FIELDS)
        way_tags_writer = UnicodeDictWriter(way_tags_file, WAY_TAGS_FIELDS)

        nodes_writer.writeheader()
        node_tags_writer.writeheader()
        ways_writer.writeheader()
        way_nodes_writer.writeheader()
        way_tags_writer.writeheader()

        validator = cerberus.Validator()

        for element in get_element(file_in, tags=('node', 'way')):
            el = shape_element(element)
            if el:
                if validate is True:
                    validate_element(el, validator)

                if element.tag == 'node':
                    nodes_writer.writerow(el['node'])
                    node_tags_writer.writerows(el['node_tags'])
                elif element.tag == 'way':
                    ways_writer.writerow(el['way'])
                    way_nodes_writer.writerows(el['way_nodes'])
                    way_tags_writer.writerows(el['way_tags'])


if __name__ == '__main__':
    # Note: Validation is ~ 10X slower. For the project consider using a small
    # sample of the map when validating.
    process_map(OSM_PATH, validate=False)
