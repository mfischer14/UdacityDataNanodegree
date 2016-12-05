#!/usr/bin/env python
# -*- coding: utf-8 -*-
import xml.etree.cElementTree as ET
from collections import defaultdict
import re
import pprint
import pandas as pd
import sqlite3
import csv
import codecs as cdc
import cerberus
import schema

##################### FILES THAT ARE USED #######################################
SOURCE_OSM = "new-york_new-york.osm"
#SOURCE_OSM = "sample.osm"
DESTINATION_DB = SOURCE_OSM.replace(".osm", ".db")
osm_file = open(SOURCE_OSM, "r")
NODES_PATH = "nodes.csv"
NODE_TAGS_PATH = "nodes_tags.csv"
WAYS_PATH = "ways.csv"
WAY_NODES_PATH = "ways_nodes.csv"
WAY_TAGS_PATH = "ways_tags.csv"
SCHEMA = schema.schema

#################### REGULAR EXPRESSION AND TYPES ##############################
street_type_re = re.compile(r'\S+\.?$', re.IGNORECASE)
amenity_type_re = re.compile(r'\S+\.?$', re.IGNORECASE)
street_types = defaultdict(set)
amenity_types = defaultdict(set)

LOWER_COLON = re.compile(r'^([a-z]|_)+:([a-z]|_)+')
PROBLEMCHARS = re.compile(r'[=\+/&<>;\'"\?%#$@\,\. \t\r\n]')

NODE_FIELDS = ['id', 'lat', 'lon', 'user', 'uid', 'version', 'changeset', 'timestamp']
NODE_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_FIELDS = ['id', 'user', 'uid', 'version', 'changeset', 'timestamp']
WAY_TAGS_FIELDS = ['id', 'key', 'value', 'type']
WAY_NODES_FIELDS = ['id', 'node_id', 'position']

expectedStreetNames = ["Street", "Avenue", "Boulevard", "Drive", "Court", "Place","Circle","Lane","Expressway", "Broadway","Parkway", "Path", "Plaza","Road", "Roadbed", "Row", "Square", "Terrace","Turnpike", "Way", "Walk"]

expectedAmenityNames = ["school", "bank", "bar", "bench", "bicycle_parking", "cafe", "embassy", "fuel", "grave_yard", "place_of_worship", "post_box","toilets"]

streetMapping = {"AVENUE":"Avenue",
           "AVenue":"Avenue",
           "Ave":"Avenue",
           "Ave.":"Avenue",
           "Avenue,":"Avenue",
           "avenue":"Avenue",
           "Blvd":"Boulevard",
           "Blvd.":"Boulevard",
           "Broadwat":"Broadway",
           "CIRCLE":"Circle",
           "Ct":"Court",
           "Ct.":"Court",
           "DRIVE":"Drive",
           "Dr":"Drive",
           "Expy":"Expressway",
           "LANE":"Lane",
           "Plz":"Plaza",
           "ROAD":"Road",
           "Rd":"Road",
           "ST":"Street",
           "STREET":"Street",
           "St":"Street",
           "St.":"Street",
           "st":"Street",
           "street":"Street",
           "Tirnpike":"Turnpike",
           "Tpke":"Turnpike",
           "Tunpike":"Turnpike",
           "Tunrpike":"Turnpike",
           "Turnlike":"Turnpike"}


#################### VIUALIZATION FUNCTIONS #############################################
def print_sorted_dict(d):
    keys = d.keys()
    keys = sorted(keys, key=lambda s: s.lower())
    for k in keys:
        v = d[k]
        print(k, v)

#################### AUDIT FUNCTIONS ############### ##############################
def audit_street_type(street_types, street_name):
    m = street_type_re.search(street_name)
    if m:
        street_type = m.group()
        if street_type not in expectedStreetNames:
            street_types[street_type].add(street_name)

def audit_amenity_type(amenity_types, amenity_name):
    m = amenity_type_re.search(amenity_name)
    if m:
        amenity_type = m.group()
        if amenity_type not in expectedAmenityNames:
            amenity_types[amenity_type].add(amenity_name)

def is_street_name(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "addr:street")

def is_amenity_name(elem):
    return (elem.tag == "tag") and (elem.attrib['k'] == "amenity")

def auditWay(elem):
    for tag in elem.iter("tag"):
        if is_street_name(tag):
            audit_street_type(street_types, tag.attrib['v'])

def auditAmenities(elem):
    for tag in elem.iter("tag"):
        if is_amenity_name(tag):
            audit_amenity_type(amenity_types, tag.attrib['v'])

def audit():
    for event, elem in ET.iterparse(osm_file, events=("start",)):
        if elem.tag == "way":
            auditWay(elem)
        elif elem.tag == "node":
            auditAmenities(elem)
            #auditLeisureAreas(elem)

    with open("street_types_audit.txt","w") as fout:
        pprint.pprint(dict(street_types),fout)

    with open("amenity_types_audit.txt","w") as fout:
        pprint.pprint(dict(amenity_types),fout)

    #print_sorted_dict(street_types)

######################## GET DATA READY FOR SQL ################################
def getAttribs(element, fields):
    attribs = {}
    for attribute in element.attrib:
        if attribute in fields:
            attribs.update({attribute:element.attrib[attribute]})
    return attribs

def getKeyType(keyString):
    stringArray = []
    stringArray = keyString.split(":")
    if len(stringArray) == 1:
        return stringArray[0], "regular"
    else:
        return keyString.replace(stringArray[0] + ':', ''), stringArray[0]

def getTags(element, fields):
    tags = []

    for elem in element:
        tagAttributes = {}
        if elem.tag == 'tag':

            tagAttributes.update({"id":element.attrib['id']})
            for attribute in elem.attrib:
                if attribute == 'k':
                    #print elem.attrib[attribute]
                    if PROBLEMCHARS.match(elem.attrib[attribute]) != None:
                        next
                    key, keyType = getKeyType(elem.attrib[attribute])
                    tagAttributes.update({"key":key})
                    tagAttributes.update({"type":keyType})
                elif attribute == 'v':
                    tagAttributes.update({"value":elem.attrib[attribute]})
            tags.append(tagAttributes)


    return tags

def getNodes(element, fields):
    nodes = []
    n = 0
    for elem in element:
        nodeAttributes = {}
        if elem.tag =='nd':
            nodeAttributes.update({"id":element.attrib['id']})
            nodeAttributes.update({"position":n})
            for attribute in elem.attrib:
                if attribute =="ref":
                    nodeAttributes.update({"node_id":elem.attrib[attribute]})
            nodes.append(nodeAttributes)
        n = n + 1
    return nodes

def shape_element(element, node_attr_fields=NODE_FIELDS, way_attr_fields=WAY_FIELDS, problem_chars =PROBLEMCHARS, default_tag_type='regular'):
    node_attribs = {}
    way_attribs = {}
    way_nodes = []
    tags = []

    if element.tag == 'node':
        node_attribs = getAttribs(element, NODE_FIELDS)
        tags = getTags(element, NODE_TAGS_FIELDS)
        return {'node': node_attribs, 'node_tags':tags}
    elif element.tag == 'way':
        way_attribs - getATtribs(element, WAY_FIELDS)
        tags = getTags(element, WAY_TAGS_FIELDS)
        way_nodes = getNodes(element, WAY_NODES_FIELDS)
        return {'way': way_attribs, 'way_ndoes': way_nodes, 'way_tags': tags}

######################## HELPER FUNCTIONS #######################################
def get_element(osm_file, tags=('node','way','relation')):
    ''' Yield element if it is the right type of tag'''
    context = ET.iterparse(osm_file, events=('start','end'))
    _, root = next(context)
    for event, elem in context:
        if event == 'end' and elem.tag in tags:
            yield elem
            root.clear()

def validate_element(element, validator, schema=SCHEMA):
    ''' Raise ValidationError if element does not match schema'''
    if validator.validate(element, schema) is not True:
        field, errors = next(validator.errors.iteritems())
        message_string = "\nElement of type '{}' has the following errors:\n{1}"
        error_string = pprint.pformat(errors)

        raise Exception(message_string.format(field, error_string))

class UnicodeDictWriter(csv.DictWriter, object):
    '''Extend csv.DictWriter to handle Unicode input'''
    def writerow(self, row):
        super(UnicodeDictWriter, self).writerow({
            k: (v.encode('utf-8') if isinstance(v,unicode) else v) for k, v in row.iteritems()
        })

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

######################## CREATE SQL DATABASE ####################################
''' CREATE SQL TABLES: '''
def createSQLDB():
    db = sqlite3.connect(DESTINATION_DB)
    c = db.cursor()

    QUERY = '''CREATE TABLE [nodes]
    (
        [id] INTEGER PRIMARY KEY NOT NULL
        [lat] REAL,
        [lon] REAL,
        [user] TEXT,
        [uid] INTEGER,
        [version] INTEGER,
        [changeset] INTEGER,
        [timestamp] TEXT
    );

    CREATE TABLE [nodes_tags] (
        [id] INTEGER,
        [key] TEXT
        [value] TEXT,
        [type] TEXT,
        FOREIGN KEY ([id]) REFERENCES nodes([id])
    );

    CREATE TABLE [ways] (
        [id] INTEGER PRIMARY KEY NOT NULL,
        [user] TEXT,
        [uid] INTEGER,
        [version] TEXT,
        [changeset] INTEGER,
        [timestampe] TEXT
    );

    CREATE TABLE [ways_tags] (
        [id] INTEGER NOT NULL,
        [key] TEXT NOT NULL,
        [value] TEXT NOT NULL,
        [type] TEXT,
        FOREIGN KEY ([id]) REFERENCES [ways]([id])
    );

    CREATE TABLE [ways_nodes] (
        [id] INTEGER NOT NULL,
        [node_id] INTEGER NOT NULL,
        [position] INTEGER NOT NULL,
        FOREIGN KEY ([id]) REFERENCES [ways]([id]),
        FOREIGN KEY ([node_id]) REFERENCES [nodes]([id])
    );
    '''

    c.execute(QUERY)
    ### rows = c.fetchall()
    ### import pandas as pd
    ### df = pd.DataFrame(rows)
    ### print df
    db.close

def importCSVToSQLDB(csvfile, tablename):
    db = sqlite3.connect(DESTINATION_DB)
    df = pandas.read_csv(csvfile)
    df.to_sql(tablename, db, if_exists='append', index=False)
    db.close

################ MAIN FUNCTION ###################################################
def process_map(file_in, validate):
    import codecs
    ''' Iteratively Process each XML element and write to CSV'''
    nodes_file = cdc.open(NODES_PATH, 'w')
    node_tags_file = cdc.open(NODE_TAGS_PATH, 'w')
    ways_file = cdc.open(WAYS_PATH, 'w')
    way_nodes_file = cdc.open(WAY_NODES_PATH, 'w')
    way_tags_file = cdc.open(WAY_TAGS_PATH, 'w')

    nodes_writer = UnicodeDictWriter(nodes_file, NODE_FIELDS)
    node_tags_writer = UnicodeDictWriter(node_tags_file, NODE_TAGS_FIELDS)
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
                validate_element(el,validator)
            if element.tag == 'node':
                nodes_writer.writerow(el['node'])
                node_tags_writer.writerows(el['node_tags'])
            elif element.tag == 'way':
                ways_writer.writerow(el['way'])
                way_nodes_writer.writerows(el['way_nodes'])
                way_tags_writer.writerows(el['way_tags'])

    nodes_file.close()
    nodes_tags_file.close()
    ways_file.close()
    way_nodes_file.close()
    way_tags_file.close()



def get_root(fname):
    tree = ET.parse(fname)
    return tree.getroot()

def count_tags(filename):
    tags = {}
    root = get_root(filename)
    for child in root.iter():
        # print child.tag
        if child.tag in tags:
            tags[child.tag] = tags[child.tag] + 1
        else:
            tags.update({child.tag:1})
    return tags
                # YOUR CODE HERE


def test():

    tags = count_tags(osm_file)
    pprint.pprint(tags)
    audit()

if __name__ == '__main__':
    #test()
    #audit()
    process_map(SOURCE_OSM, validate=True)
