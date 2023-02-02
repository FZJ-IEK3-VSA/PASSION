import requests
import json
import time

import passion.util

OVERPASS_URL = "http://overpass-api.de/api/interpreter"

def get_footprints_latlon(bbox: tuple, osm_request_interval: float = 5, num_retries: int = 5):
  '''Given a bounding box, requests the OSM buildings of the area
  and returns them as a list of outlines.'''
  latlon1, latlon2 = bbox

  min_lat, max_lat = min(latlon1[0], latlon2[0]), max(latlon1[0], latlon2[0])
  min_lon, max_lon = min(latlon1[1], latlon2[1]), max(latlon1[1], latlon2[1])

  overpass_query = """
  [out:json];
  way
    ["building"]
    ({0},{1},{2},{3});
  (._;>;);
  out;
  """.format(min_lat, min_lon, max_lat, max_lon)

  #TODO: handle if empty request

  # workaround for hitting request limit (error 429) from overpass
  #time.sleep(osm_request_interval)
  num_retries = 5
  for i in range(num_retries):
    try:
      response = requests.get(OVERPASS_URL, params={'data': overpass_query})
      results = response.json()
      print(f'Successful request {i}.')
      break
    except:
      print(f'Error in request {i}, retrying {num_retries - 1 - i} more times.')
      results = None
      print(f'Waiting {osm_request_interval} seconds.')
      time.sleep(osm_request_interval)
  
  if not results: return []

  nodes = []
  ways = []
  for result in results['elements']:
    if result['type'] == 'way':
      ways.append(result)
    elif result['type'] == 'node':
      nodes.append(result)
    else:
      print(f'Other Overpass type: {result["type"]}')

  buildings = []
  if (ways and nodes):
    #get_node_latlon(ways['elements'][0]['nodes'][0], nodes['elements'])
    buildings = get_buildings(ways, nodes)

  return buildings

def get_nearest_osm_building(outline_lonlat: list, latlon: tuple):
  '''Given a building outline as a list of longitudes and latitudes and
  a given center latitude, returns the closest overlapping OSM building
  with its properties.
  '''
  lat, lon = latlon
  distance = 50

  ways_query = """
  [out:json];
  way
  ["building"="yes"]
  (around:{0}, {1}, {2});
  out;
  """.format(distance, lat, lon)

  all_query = """
  [out:json];
  way
  ["building"="yes"]
  (around:{0}, {1}, {2});
  (._;>;);
  out;""".format(distance, lat, lon)

  response_ways = requests.get(OVERPASS_URL,
                    params={'data': ways_query})
  response_elements = requests.get(OVERPASS_URL,
                    params={'data': all_query})

  try:
    ways = response_ways.json()
    elements = response_elements.json()
  except Exception:
    print(response_ways.content)
    print(response_elements.content)
    return None, None

  nearby_buildings = []
  intersecting_buildings = []
  node_map = dict()
  way_map = dict()
  nearest_building = None

  for way in ways['elements']:
    way_nodes = []
    for node in elements['elements']:
      if node['id'] in way['nodes']:
        way_nodes.append(node)
    way_map[way['id']] = way
    node_map[way['id']] = way_nodes

  closest_distance = 99999
  for ident in node_map.keys():
    way = way_map[ident]

    b = []
    for node in node_map[ident]:
      b.append((node['lat'], node['lon']))
    
    if passion.util.gis.polygons_intersect(outline_lonlat, b):
      intersecting_buildings.append(way)
    
    x, y = Polygon(b).centroid.coords.xy
    x = x[0]
    y = y[0]

    if (math.sqrt( (x - lat)**2 + (y - lon)**2 )) < closest_distance:
      nearest_building = way
    
    nearby_buildings.append(way)

  return nearest_building, len(intersecting_buildings)

def get_node_latlon(id: int, nodes: list):
  '''Given an OSM list of nodes and the id of a node,
  returns its latitude and longitude.
  '''
  return next((node['lat'], node['lon']) for node in nodes if (node['id'] == id))

def get_way_coords(way_nodes: list, nodes: list):
  '''Given an OSM list of nodes and a list of nodes of a way,
  returns the latitude and longitude of the nodes of the way.
  '''
  return list(get_node_latlon(id, nodes) for id in way_nodes)

def get_buildings(ways: list, nodes: list):
  '''Given an OSM list of nodes and ways, returns the coordinates of
  the ways in a latitude longitude representation.
  '''
  return list(get_way_coords(way['nodes'], nodes) for way in ways)