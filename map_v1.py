#!/usr/bin/env python
# coding: utf-8

#equirements anaconda + folium + gpxpy
import os
import math
import pandas as pd
import gpxpy
from folium.plugins import MiniMap
from folium import plugins
import folium

# disable "Line too long"
# pylint: disable=C0301

def process_gpx_to_df(file_name):
    """Retrieves gpx points into dataframe

    Retrieves gpx points from a .gpx file an parses every datapoint into a pandas
    data frame. It also returns all GPS points from each segment of a .gpx file.

    Args:
        file_name: Absolute path to .gpx file
        For example:

        "C:\\Users\\user\\Desktop\\Fahrrad\\tracks\\Kopenhagen\\2015-08-13_10-02_Do.gpx"

    Returns:
        gpx_df: Pandas Dataframe with the columns ['Longitude','Latitude','Altitude','Time','Speed']
                For example:

                    index   Longitude   Latitude   Altitude  Time                      Speed
                0   0       9.947117    53.639672  18        2015-08-13T10:02:00.000Z  6.0249018114
                1   1       9.947997    53.639816  18        2015-08-13T10:02:10.000Z  5.5150763938
                2   2       ....

        points: List of touples containting the GPS points from the .gpx file.
                For example:

                [(53.639672, 9.947117), (53.639816, 9.947997), (latitude, longitude), ....
    """
    # open the .gpx file with gpxpy
    gpx = gpxpy.parse(open(file_name))

    # make DataFrame
    track = gpx.tracks[0]
    segment = track.segments[0]

    # Load the data into a Pandas dataframe
    data = []
    #segment_length = segment.length_3d()
    for point_idx, point in enumerate(segment.points):
        data.append([point.longitude, point.latitude,point.elevation,
                     point.time, segment.get_speed(point_idx)])
    columns = ['Longitude', 'Latitude', 'Altitude', 'Time', 'Speed']
    gpx_df = pd.DataFrame(data, columns=columns)

    # Load points tuple into a list for line plotting
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append(tuple([point.latitude, point.longitude]))
    return gpx_df, points

def get_mid_of_track(x):
    d={}
    mid_point = x['path'].count() /2
    if mid_point == 1:
        mid_point_int = int(mid_point)
        mid_gpx = x.sort_values('camino_order').iloc[mid_point_int].path
        marker = 'mid'
    elif mid_point.is_integer():
        mid_point_int = int(mid_point)
        mid_gpx = x.sort_values('camino_order').iloc[mid_point_int-1].path
        marker = 'end'
    else:
        mid_point_int = math.ceil(mid_point)
        mid_gpx = x.sort_values('camino_order').iloc[mid_point_int-1].path
        marker = 'mid'
    d['mid_gpx'] = mid_gpx
    d['marker'] = marker
    d['start_gpx'] = x.sort_values('camino_order').iloc[0].path
    d['end_gpx'] = x.sort_values('camino_order').iloc[-1].path

    return pd.Series(d, index=['mid_gpx', 'marker', 'start_gpx', 'end_gpx' ])


def calc_track_summary(x):
    """Create pandas Series

    Creates a summary of important informations for a track. It acts on a grouped
    dataframe an sums over the distances and elevations and counts the days.

    Args:
        x: Dataframe with the colums date, distance_km, elevation

    Returns:
        pd.Series: One-dimensional ndarray with axis labels
        For example:

            camino_name     Days on Track   Distance (km)   Elevation (m)
        1   Amsterdam       7               572.3           1581
        2   Kopenhagen      9               585.66          2183
    """
    d = {}
    d['Days on Track'] = x['date'].count()
    d['Distance (km)'] = x['distance_km'].sum()
    d['Elevation (m)'] = x['elevation'].sum()
    #d['Elapsed Time (hours)'] = x['elapsed_time_sec'].sum() / 3600
    #d['Elevation Gain (m)'] = x['elevationGain'].sum()
    #d['Elevation Loss (m)'] = x['elevationLoss'].sum()
    #d['Elapsed Speed (km/h)'] = x['distance_km'].sum() / x['elapsed_time_sec'].sum() * 3600
    #d['Average Speed (km/h)'] = x['averageMovingSpeed'].median() * 3600 / 1000
    #pdb.set_trace()
    #d['Max Speed (km/hr)'] = x['maxSpeed'].median() * 3600 / 1000
    #d['Average Heartrate'] = x['averageHR'].median()
    #d['Max Heartrate'] = x['maxHR'].max()
    return pd.Series(d)

# read csv file to get the information for the Path, camino_name, distance , date ....
tracks = pd.read_csv('C:\\Users\\JP\\Documents\\Code\\gpx_viewer\\gpx_viewer\\Fahrradtouren.csv',sep=';',encoding='latin')

# create a mask to check if the track should be evaluated
mask = tracks.use_track == True

# remove all tracks that should not be evaluated with the mask
all_tracks_sorted = tracks[mask].sort_values(['family', 'camino_name','camino_order']).path.to_list()
                    #tracks.mask(mask)
def make_folium_map(gpx_files,
                    activity_reference_df,
                    map_name='my_folium_map.html',
                    plot_method='poly_line',
                    zoom_level=12,
                    add_track_info=False,
                    mark_track_terminals=False,
                    track_terminal_radius_size=2000,
                    show_minimap=False,
                    map_type='regular',
                    fullscreen=False):

    pd.set_option('display.precision', 0)
    i=0
    for file_name in gpx_files:
        if os.path.getsize(file_name) == 0:
            print('skipping this file due to it being EMPTY: ' + file_name)
            continue

        #convert to DF and points tuple
        df, points = process_gpx_to_df(file_name)
        print('dataframe and points created for ' + file_name)

        #get start and end lat/long
        lat_start = df.iloc[0].Latitude
        long_start = df.iloc[0].Longitude
        lat_end = df.iloc[-1].Latitude
        long_end = df.iloc[-1].Longitude

        #get activity type
        activity = activity_reference_df[activity_reference_df.path==file_name].iloc[0].activity_name
        if activity=='cycling':
            activity_color='red'
            activity_icon='bicycle'
        elif activity=='hiking':
            activity_color='green'
            activity_icon='blind'
        elif activity=='planned':
            activity_color='blue'
            activity_icon='pencil'
        else:
            activity_color='blue'

        if i==0:
            if map_type=='regular':
                mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ],
                                    zoom_start=zoom_level,
                                    tiles=None)

                folium.TileLayer( 'openstreetmap',
                                  name='OpenStreet Map').add_to(mymap)

                folium.TileLayer( 'https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
                                  attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC",
                                  name='Nat Geo Map').add_to(mymap)

                folium.TileLayer( 'https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
                                  attr='<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                                  name='Cycle OSM').add_to(mymap)


            elif map_type=='terrain':
                mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ],
                                    tiles='http://tile.stamen.com/terrain/{z}/{x}/{y}.jpg',
                                    attr="terrain-bcg",
                                    zoom_start=zoom_level)

            elif map_type=='nat_geo':
                mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ],
                                    tiles='https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}',
                                    attr="Tiles &copy; Esri &mdash; National Geographic, Esri, DeLorme, NAVTEQ, UNEP-WCMC, USGS, NASA, ESA, METI, NRCAN, GEBCO, NOAA, iPC",
                                    zoom_start=zoom_level)

            elif map_type=='opencycle':
                mymap = folium.Map( location=[ df.Latitude.mean(), df.Longitude.mean() ],
                                    tiles='https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png',
                                    attr = '<a href="https://github.com/cyclosm/cyclosm-cartocss-style/releases" title="CyclOSM - Open Bicycle render">CyclOSM</a> | Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                                    zoom_start=zoom_level)                     

        camino_order_df = activity_reference_df.groupby('camino_name').apply(get_mid_of_track)

        camino_name = activity_reference_df.loc[activity_reference_df.path == file_name,:].camino_name.iloc[0]
        camino_distance = activity_reference_df.loc[activity_reference_df.path == file_name,:].distance_km.iloc[0].round(1)
        camino_day = activity_reference_df.loc[activity_reference_df.path == file_name,:].camino_order.iloc[0].round(0)

        if plot_method == 'poly_line':
            if file_name in camino_order_df.start_gpx.to_list() and add_track_info is True:

                #CREATE GROUP - FIRST TRACK IN CAMINO
                fg = folium.FeatureGroup(name=camino_name, show=True, overlay=True)

                mymap.add_child(fg)
                folium.PolyLine( points,
                                 color=activity_color,
                                 weight=4.5,
                                 opacity=.5).add_to(mymap).add_to(fg)

                #build starting marker
                html_camino_start = """
                Start of {camino_name}
                """.format(camino_name=camino_name)
                popup = folium.Popup(html_camino_start, max_width=400)
                #nice green circle
                folium.vector_layers.CircleMarker( location=[lat_start, long_start],
                                                   radius=9,
                                                   color='white',
                                                   weight=1,
                                                   fill_color='green',
                                                   fill_opacity=1,
                                                   popup=html_camino_start).add_to(mymap).add_to(fg)
                #OVERLAY triangle
                folium.RegularPolygonMarker( location=[lat_start, long_start],
                                             fill_color='white',
                                             fill_opacity=1,
                                             color='white',
                                             number_of_sides=3,
                                             radius=3,
                                             rotation=0,
                                             popup=html_camino_start).add_to(mymap).add_to(fg)

            elif file_name in camino_order_df.mid_gpx.to_list() and add_track_info is True:
                activity_reference_df.groupby('camino_name')
                camino_summary = activity_reference_df.groupby('camino_name').apply(calc_track_summary)
                #add 'mid' or 'end' marker, depending on how many tracks there are on camino (to approximate midpoint)
                marker_location = camino_order_df.loc[camino_order_df.mid_gpx==file_name,'marker'][0]
                mask_2 = (camino_summary.index==camino_name)
                camino_summary_for_icon = camino_summary[mask_2].melt().rename(columns={'variable':'Metric'}).set_index('Metric').round(1)
                melt_mask = (camino_summary_for_icon['value'].notnull()) & (camino_summary_for_icon['value']!=0)
                camino_summary_for_icon = pd.DataFrame(camino_summary_for_icon[melt_mask]['value'].apply(lambda x : "{:,}".format(x)))

                html_camino_name = """
                <div align="justify">
                <h5>{camino_name}</h5><br>
                </div>

                """.format(camino_name=camino_name)
                html = html_camino_name + """<div align="center">""" + camino_summary_for_icon.to_html(justify='center', header=False, index=True, index_names=False, col_space=300, classes='table-condensed table-responsive table-success') + """</div>""" #
                popup = folium.Popup(html, max_width=300)

                if marker_location=='mid':
                    #get midpoint long / lad
                    length = df.shape[0]
                    mid_index= math.ceil(length / 2)

                    lat = df.iloc[mid_index]['Latitude']
                    long = df.iloc[mid_index]['Longitude']
                else:
                    lat = lat_end
                    long = long_end
                mymap.add_child(fg)
                #create line:
                folium.PolyLine( points,
                                 color=activity_color,
                                 weight=4.5,
                                 opacity=.5).add_to(mymap).add_to(fg)

                folium.Marker( [lat, long],
                               popup=popup,
                               icon=folium.Icon( color=activity_color,
                                                 icon_color='white',
                                                 icon=activity_icon,
                                                 prefix='fa')).add_to(mymap).add_to(fg)

            #CAMINO END:
            elif file_name in  camino_order_df.end_gpx.to_list() and add_track_info is True:
                mymap.add_child(fg)
                #create line:
                folium.PolyLine( points,
                                 color=activity_color,
                                 weight=4.5,
                                 opacity=.5).add_to(mymap).add_to(fg)

                #camino end marker ORIGINAL THAT WORKS
                html_camino_end = """
                End of {camino_name}
                """.format(camino_name=camino_name)
                popup = html_camino_end

                #nice red circleTRACK ADDED
                folium.vector_layers.CircleMarker( location=[lat_end, long_end],
                                                   radius=9,
                                                   color='white',
                                                   weight=1,
                                                   fill_color='red',
                                                   fill_opacity=1,
                                                   popup=popup).add_to(mymap).add_to(fg)
                #OVERLAY square
                folium.RegularPolygonMarker( location=[lat_end, long_end],
                                             fill_color='white',
                                             fill_opacity=1,
                                             color='white',
                                             number_of_sides=4,
                                             radius=3,
                                             rotation=45,
                                             popup=popup).add_to(mymap).add_to(fg)
            elif add_track_info is True:
                mymap.add_child(fg)
                folium.PolyLine( points,
                                 color=activity_color,
                                 weight=4.5,
                                 opacity=.5).add_to(mymap).add_to(fg)

        if mark_track_terminals is True and (file_name not in  camino_order_df.end_gpx.to_list()):
            day_terminal_message = 'End of Day ' +str(camino_day)[:-2]+ '.  Distance: ' + str(camino_distance) + ' km.'
            mymap.add_child(fg)
            folium.vector_layers.Circle(location=[lat_end, long_end], radius=track_terminal_radius_size, color=activity_color, fill_color=activity_color, weight=2, fill_opacity=0.3,  tooltip=day_terminal_message).add_to(mymap).add_to(fg)
        if plot_method == 'circle_marker':
            coordinate_counter = 30
            for coord in df[['Latitude','Longitude']].values:
                if 1==1:
                    #every 10th element, mark
                    folium.CircleMarker(location=[coord[0],coord[1]], radius=1,color=activity_color).add_to(mymap)
                coordinate_counter += 1

        i+=1
        print('TRACK ADDED FOR created for ' + file_name)
    if show_minimap is True:
        minimap = MiniMap(zoom_level_offset=-4)
        mymap.add_child(minimap)

    #fullscreen option
    if fullscreen is True:
        plugins.Fullscreen(
            position='topright',
            title='Expand me',
            title_cancel='Exit me',
            force_separate_button=True
        ).add_to(mymap)

    folium.LayerControl(collapsed=True).add_to(mymap)
    # saves to html file for display below
    mymap.save(map_name)

make_folium_map(all_tracks_sorted,tracks, map_name='all_tracks.html', plot_method='poly_line', zoom_level=6, add_track_info=True, mark_track_terminals=True, track_terminal_radius_size=1750, fullscreen = True, show_minimap=False)#, map_type='nat_geo')
