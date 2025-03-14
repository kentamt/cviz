# 👾Cviz 
Web-based visualisation tool for Python

<table style="width:100%; table-layout: fixed; border-collapse: collapse;">
  <tr>
    <td style="width: 50%;">
      <video src="https://github.com/user-attachments/assets/0bbb7911-3b68-49cb-8aa0-923fb4b55a2e" controls style="width: 100%;"></video>
    </td>
    <td style="width: 50%;">
      <video src="https://github.com/user-attachments/assets/f1e7431e-fa74-42c8-94ed-3c19645f5573" controls style="width: 100%;"></video>
    </td>
  </tr>
  <tr>
    <td style="width: 50%;">
      <video src="https://github.com/user-attachments/assets/78cd4763-3d5e-4d8d-a868-a443a2e0aeea" controls style="width: 100%;"></video>
    </td>
    <td style="width: 50%;">
      <video src="https://github.com/user-attachments/assets/ab5b0112-fe0f-410e-83ab-ccff1db41cb6" controls style="width: 100%;"></video>
    </td>
  </tr>
</table>

## Demo
tested with Python3.12
```bash
pip install -r requirements.txt
```

```
uvicorn app:app --host 0.0.0.0 --port 8000
```

Visit `localhost:8000`

## Data type
- [x] Point2Da
- [ ] PointCloud2D
- [x] Polygon
- [x] PolygonVector
- [x] LineString
- [x] LineStringVector
- [x] Text
- [ ] TextVector
- [ ] Arrow
- [ ] ArrowVector
- [ ] SVG
- [ ] SVGVector
- [ ] GridMap

## How it works

In your simulator:
```python
polygon_pub = Publisher(topic_name="polygon", data_type='Polygon')
data = {'points': [{'x': 0, 'y':0}, ...]}
polygon_pub.publish(data)
```

In Cviz server, add the topic you want to visualise:
```python
def main():
    cviz = CvizServer()
    cviz.add_subscriber(topic_name="polygon")
    # cviz.add_subscriber(topic_name="point")
    # cviz.add_subscriber(topic_name="linestring")
    
    try:
        asyncio.run(cviz.start_server())
    except KeyboardInterrupt:
        logging.info("Server stopped")
```

## TODO
- [x] zoom and pan
- [x] lon, lat, map
- [x] history limit
- [x] colour
- [ ] lifetime
- [ ] add GUI to control topics
- [ ] remote 

