# Cviz 
Web-based visualisation tool for Python. Cviz has two visualisation modes: canvas and Map. 

<table>
  <tr>
    <td>
      <img src="https://github.com/user-attachments/assets/2da16f6a-b033-4fb3-9f5f-024ff07f5005" controls width="100%"></video>
    </td>
    <td>
      <img src="https://github.com/user-attachments/assets/945ca631-0b93-406d-89e8-fe586d11c841" controls width="100%"></video>
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
