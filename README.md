# Cviz 
Web-based visualisation tool for Python. Cviz has two visualisation modes: canvas and Map. 

<table>
  <tr>
    <td>
      <video src="https://github.com/user-attachments/assets/0bbb7911-3b68-49cb-8aa0-923fb4b55a2e" controls width="100%"></video>
    </td>
    <td>
      <video src="https://github.com/user-attachments/assets/f1e7431e-fa74-42c8-94ed-3c19645f5573" controls width="100%"></video>
    </td>
  </tr>
</table>


<table>
  <tr>
    <td>
      <video src="https://github.com/user-attachments/assets/78cd4763-3d5e-4d8d-a868-a443a2e0aeea" controls width="100%"></video>
    </td>
    <td>
      <video src="https://github.com/user-attachments/assets/e8c191e0-3ce3-415d-8374-5a6815bdeb25" controls width="100%"></video>
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