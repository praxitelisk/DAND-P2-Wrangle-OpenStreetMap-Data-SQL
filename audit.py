"""
Your task in this exercise has two steps:

- audit the OSMFILE and change the variable 'mapping' to reflect the changes needed to fix 
    the unexpected street types to the appropriate ones in the expected list.
    You have to add mappings only for the actual problems you find in this OSMFILE,
    not a generalized solution, since that may and will depend on the particular area you are auditing.
- write the update_name function, to actually fix the street name.
    The function takes a string with street name as an argument and should return the fixed name
    We have provided a simple test so that you see what exactly is expected
"""
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import time

# Pinpointing the OSM input file
OSMFILE = "maps-xml/london_full.osm"

# Dictionaries to store data types
node_field_types = defaultdict(set)
node_tag_field_types = defaultdict(set)
way_field_types = defaultdict(set)
way_tag_field_types = defaultdict(set)
way_node_field_types = defaultdict(set)

# Data structure used to store wrong coordinates
coordinates_out_of_area = {}

# Data structure to store street types
street_types = defaultdict(set)

# Data structure to store postal code types
postal_code_types = defaultdict(set)

# Counter for postal code types
counter_postal_code_types = {'postal_code_no_space': 0, 'postal_code_with_space': 0, 'unknown': 0}

# Counter for address name types
counter_address_types = {"uppercase": 0, "capitalized": 0, "lower": 0, "uppercase_colon": 0, "capitalized_colon": 0,
                "lower_colon": 0, "problem_chars": 0, "other": 0}

# a list of regular expressions for auditing and cleaning street types
street_type_re = re.compile(r'\b\S+\.?$', re.IGNORECASE)
cleaning_re_omit_streets_ending_with_numbers_re = re.compile(r'\s*\d+\S*$', re.IGNORECASE)
cleaning_re_at_least_three_words_re = re.compile(r'[A-Z][a-z]{2,}$')

# regular expressions for auditing the different ways that a address is stored in OSM xml file
capitalized_re = re.compile(r'^[A-Z][a-z]*\s+([A-Z]?[a-z]*|\s+)*$')
uppercase_re = re.compile(r'^([A-Z|_|\s+])+$')
lower_re = re.compile(r'^([a-z]|_|\s+)+$')
capitalized_colon_re = re.compile(r'^[A-Z][a-z]+\s+([A-Z][a-z]*|\s+|:)*$')
uppercase_colon_re = re.compile(r'^([A-Z|_|\s+|:])+$')
lower_colon_re = re.compile(r'^([a-z]|_)*:([a-z]|_)*$')
problem_chars_re = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

# another list of regular expressions for auditing and cleaning postal codes
# kudos to https://en.wikipedia.org/wiki/Postcodes_in_the_United_Kingdom#validation
postal_code_no_space_re = re.compile(r'^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) [0-9][A-Za-z]{2})$')
postal_code_with_space_re = re.compile(r'^([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z])))) {0,1}[0-9][A-Za-z]{2})$')


# a set with all the candidate street types
candidate_street_type_set = set()

# expected street endings
expected_list = ["Street", "Road", "Avenue", "Boulevard"]

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


# the function audit the street names, extracts the street type and corrects possible street type abbreviations
def audit_street_type(street_name):

    # debug print
    # print(street_name)

    # get the final word which will be the street type from the address
    candidate_street_type = street_type_re.search(street_name)

    if candidate_street_type:
        street_type = candidate_street_type.group()
        street_type = street_type.strip()

        # add the candidate street type into a set
        candidate_street_type_set.add(street_type)

        # cleaning process:
        # omit street types that end with numbers or numbers with letters
        check_for_strange_ending_address = cleaning_re_omit_streets_ending_with_numbers_re.search(street_type)
        if not check_for_strange_ending_address:

            # if the newly found street type is in the expected_list, then append to the dict with key
            # the street type and value the street name
            if street_type in expected_list:
                # debug print
                # print("expected street:", street_type, ",", street_name)
                street_types[street_type].add(street_name)

            # else if the newly found street type is not in expected list then search it in mapping list
            elif street_type not in expected_list and street_type in mapping:

                street_name = update_name(street_name)
                # debug print
                # print("mapping new key:", street_type, ",", street_name)
                street_types[mapping[street_type]].add(street_name)

            # else check if is a valid written in english street type then add it to expected list
            elif street_type not in expected_list and street_type not in mapping:

                if cleaning_re_at_least_three_words_re.search(street_type) and is_english_word(street_type):
                    # debug print
                    # print("Adding new key:", street_type, ",", street_name)
                    street_types[street_type].add(street_name)
                    expected_list.append(street_type)


# A function which checks whether or not a string is written in english or not
def is_english_word(s):
    try:
        s.encode(encoding='utf-8').decode('ascii')
    except UnicodeDecodeError:
        return False
    else:
        return True


# A function which checks whether the 'k' attribute for an xml element is addr:street type
def is_street_name(elem):
    return elem.attrib['k'] == "addr:street"


# A function to detect whether the values is an integer or a float
def is_number(v):
    try:
        int(v)
        return True
    except ValueError:
        try:
            float(v)
            return True
        except ValueError:
            return False


# A function which categorizes an address based on the way is written
def audit_address_name(element):

        if lower_re.search(element):
            counter_address_types['lower'] = counter_address_types['lower'] + 1
        elif uppercase_re.search(element):
            counter_address_types['uppercase'] = counter_address_types['uppercase'] + 1
        elif capitalized_re.search(element):
            counter_address_types['capitalized'] = counter_address_types['capitalized'] + 1
        elif lower_colon_re.search(element):
            counter_address_types['lower_colon'] = counter_address_types['lower_colon'] + 1
        elif uppercase_colon_re.search(element):
            counter_address_types['uppercase_colon'] = counter_address_types['uppercase_colon'] + 1
        elif capitalized_colon_re.search(element):
            counter_address_types['capitalized_colon'] = counter_address_types['capitalized_colon'] + 1
        elif problem_chars_re.search(element):
            counter_address_types['problem_chars'] = counter_address_types['problem_chars'] + 1
        else:
            counter_address_types['other'] = counter_address_types['other'] + 1


# A function to audits the type of the attributes of an element
def audit_attribute_type(types_dictionary, attributes):
    for attribute in attributes:
        value = attributes[attribute]
        if value == "NULL" or value == "" or value == None or value == type(None):
            types_dictionary[attribute].add(type(None))
        elif value.startswith("{") and value.endswith("}"):
            types_dictionary[attribute].add(type([]))
        elif is_number(value):
            try:
                int(value)
                types_dictionary[attribute].add(type(1))
            except ValueError:
                float(value)
                types_dictionary[attribute].add(type(1.1))
        else:
            types_dictionary[attribute].add(type("a"))


# A function which audits the node's coordinates and stores those who do not belong to the area from the map
def audit_coordinates(coordinates_out_area, element_attributes):
    node_id = element_attributes['id']
    lati = float(element_attributes['lat'])
    longi = float(element_attributes['lon'])
    # Evaluates if the latitude and longitude fall outside the area of interest
    if not (51.7573 < lati < 51.2550) or not (-0.8253 < longi < 0.5699):
        coordinates_out_area[node_id] = (lati, longi)


# A function which audits postal codes and catagorizes based on the way are written
def audit_postal_code(child_attributes):
    if child_attributes['k'] == 'postal_code':
        postal_code = child_attributes['v']
        if postal_code_no_space_re.match(postal_code):
            postal_code_types['postal_code_no_space'].add(postal_code)
            counter_postal_code_types['postal_code_no_space'] += 1
        elif postal_code_with_space_re.match(postal_code):
            postal_code_types['postal_code_with_space'].add(postal_code)
            counter_postal_code_types['postal_code_with_space'] += 1
        else:
            postal_code_types['unknown'].add(postal_code)
            counter_postal_code_types['unknown'] += 1


# The main audit node function
def audit_node(element):
    # get element's attributes
    element_attribute = element.attrib

    # audit node's attributes types
    audit_attribute_type(node_field_types, element_attribute)

    # audit node's coordinates if they are valid
    audit_coordinates(coordinates_out_of_area, element_attribute)

    for tag in element.iter("tag"):

        # get children Attributes
        child_attributes = tag.attrib

        # audit child Type
        audit_attribute_type(node_tag_field_types, child_attributes)

        # audit postal codes
        audit_postal_code(child_attributes)

        # audit way Streets
        if is_street_name(tag):
            audit_address_name(tag.attrib['v'])
            audit_street_type(tag.attrib['v'])


# The main audit way function
def audit_way(element):
    # get element attributes
    element_attributes = element.attrib

    # check element attribute types
    audit_attribute_type(way_field_types, element_attributes)

    for tag in element.iter("tag"):

        # get children attributes
        child_attributes = tag.attrib

        # audit child type
        audit_attribute_type(way_tag_field_types, child_attributes)

        # audit postal codes
        audit_postal_code(child_attributes)

        # audit nodes Streets
        if is_street_name(tag):
            audit_address_name(tag.attrib['v'])
            audit_street_type(tag.attrib['v'])

    # get way children nd tags
    for child in element.iter('nd'):

        # get children attributes
        child_attributes = child.attrib
        # print(child_attributes)

        # audit nd types
        audit_attribute_type(way_node_field_types, child_attributes)


# The main audit function
def audit(osmfile):
    # open the file with encoding = utf8 for windows
    osm_file = open(osmfile, "r", encoding="utf8")

    # iterate through every main tag from the xml file
    for event, elem in ET.iterparse(osm_file, events=("start",)):

        if elem.tag == "node":
            audit_node(elem)
        elif elem.tag == "way":
            audit_way(elem)

        elem.clear()
    osm_file.close()


def update_name(name):
    m = street_type_re.search(name)
    if m:
        street_type = m.group()
        if street_type not in expected_list and street_type in mapping:
            name = re.sub(street_type_re, mapping[street_type], name)

    return name


if __name__ == '__main__':
    # here is the __main__ area where the auditing procedure will be executed

    start_time = time.time()

    # start the main audit function
    audit(OSMFILE)
    #
    #
    print()
    print("expected list:")
    pprint.pprint(sorted(expected_list))
    #
    #
    print()
    print("mapping list:")
    pprint.pprint(mapping)
    #
    #
    print()
    print("street_types:")
    pprint.pprint(street_types)
    #
    #
    print()
    print("counter_postal_code_types:")
    pprint.pprint(counter_postal_code_types)
    #
    #
    print()
    print("counter_address_types:")
    pprint.pprint(counter_address_types)
    #
    #
    print()
    print("number of coordinates_out_of_area:")
    pprint.pprint(len(coordinates_out_of_area))
    #
    #
    print()
    print("node_field_types:")
    pprint.pprint(node_field_types)
    #
    #
    print()
    print("node_tag_field_types:")
    pprint.pprint(node_tag_field_types)
    #
    #
    print()
    print("was_fields_types:")
    pprint.pprint(way_field_types)
    #
    #
    print()
    print("way_tag_field_types:")
    pprint.pprint(way_tag_field_types)
    #
    #
    print()
    print("way_node_field_types:")
    pprint.pprint(way_node_field_types)
    #
    #
    print()
    elapsed_time = time.time() - start_time
    print("minutes elapsed {:.3}".format(elapsed_time/60))
