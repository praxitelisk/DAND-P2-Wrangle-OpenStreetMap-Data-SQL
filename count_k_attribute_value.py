import pprint
import xml.etree.cElementTree as ET


def get_types_of_k_attrib(filename, k_attrib_values_dict):
    for _, element in ET.iterparse(filename):
        if element.tag == "node" or element.tag == "way":
            for tag in element.iter("tag"):
                # print(tag.attrib['k'])
                if tag.attrib['k'] not in k_attrib_values_dict:
                    k_attrib_values_dict[tag.attrib['k']] = 1
                else:
                    k_attrib_values_dict[tag.attrib['k']] += 1
                tag.clear()
            element.clear()


if __name__ == '__main__':
    k_attrib_values_dict = {}

    filename = "maps-xml/london_full.osm"
    get_types_of_k_attrib(filename, k_attrib_values_dict)

    # print the top 20 k values appeared in the center of London
    import operator

    pprint.pprint(sorted(k_attrib_values_dict.items(), key=operator.itemgetter(1), reverse=True)[1:21])
