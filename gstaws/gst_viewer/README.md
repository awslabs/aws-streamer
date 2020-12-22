# Simple Flask HLS Player

## Prerequsites

```bash
pip3 install -r ../../requirements.txt
```

## Usage

From command line:
```bash
python3 stream_client.py
```

or:

```bash
FLASK_APP=stream_client.py flask run --no-reload --host=0.0.0.0
```

or with SDK:
```python
import gstaws

client = gstaws.client("viewer")
```

Go to [http://localhost:5000](http://localhost:5000) and click on it to play.
