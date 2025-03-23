# Cviz 
Web-based visualisation tool for Python. Cviz has two visualisation modes: canvas and Map. 

<table>
  <tr>
    <td>
      <video src="https://github.com/user-attachments/assets/294b6d65-13e6-4107-8e75-a9d15721a730" controls width="100%"></video>
    </td>
    <td>
      <video src="https://github.com/user-attachments/assets/d10e15f6-00d1-42fc-888f-335f79cc4044" controls width="100%"></video>
    </td>
  </tr>
</table>




## Data type
Cviz supports GeoJson format. See https://geojson.org/.

- [ ] Position
- [x] Point
- [x] MultiPoint
- [x] LineString
- [x] MultiLineString
- [x] Polygon
- [x] MultiPolygon
- [ ] GeometryCollection
- [ ] Antimeridian Cutting
- [ ] Uncertainty and Precision 

## Mapbox
Cviz renders geometries based on Mapbox. You can use your own Mapbox token by replacing the placeholder in `map-app.js` with your token.
```javascript
 mapboxAccessToken = 'YOUR_MAPBOX_TOKEN';
```


## Demo
tested with Python3.12, 3.13

```bash
pip install zmq json numpy websockets
npm install pixi.js
```
Run app:
```bash
vicorn app:app --host 0.0.0.0 --reload --port 8000
```

and visit `localhost:8000`

## How it works

write something here
