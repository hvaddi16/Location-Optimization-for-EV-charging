# Location-Optimization-for-EV-charging
## DESCRIPTION-
We built a plotly dash application using a scattermap box graph object for our main map with a GIS backend
We plot over 170K points including control points for roads and charging stations using WebGL backend utilizing 
GPU resources for render.
Most of our data has already been processed and cleaned for direct usage in our tool. We have included the codes
for Webscraping and the Api calls, as well as the codes for cleaning and merging the data in the folder
"Data Processing" under the "Code" folder.
 
## INSTALLATION-
The following libraries will be required to run the python script.
1) dash
2) dash_bootstrap_components
3) plotly
4) numpy
5) pandas

## EXECUTION-
Run main.py and then open the Dash application on your browser with the address 127.0.0.1 and port number 8000.
The GUI with a 3D GeoJSON of the US with road networks, Sunburst chart and proposed charging stations should open.
