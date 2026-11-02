import time
import urllib.request
import json

def benchmark():
    s = time.time()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/syllabus/71992341-ca73-4ec7-9f97-87008a908b0a/approve-third-channel',
        data=b'{"approve": true}',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    elapsed = (time.time() - s) * 1000
    print(f"Approve 3rd channel took: {elapsed:.1f}ms, channels: {len(data.get('selected_channels', []))}, requires_approval: {data.get('requires_third_channel_approval')}")

    # Channel discovery benchmark
    s = time.time()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/syllabus/71992341-ca73-4ec7-9f97-87008a908b0a/channel-discovery',
        data=b'{"languages": ["English"], "force_refresh": false}',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    elapsed = (time.time() - s) * 1000
    print(f"Channel discovery took: {elapsed:.1f}ms, discovered: {len(data.get('discovered_channels', []))}")

    # Strategy preview benchmark
    s = time.time()
    req = urllib.request.Request(
        'http://127.0.0.1:8000/api/syllabus/71992341-ca73-4ec7-9f97-87008a908b0a/preview-strategy',
        data=b'{"strategy": "two_channels", "languages": ["English"]}',
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    elapsed = (time.time() - s) * 1000
    print(f"Strategy preview took: {elapsed:.1f}ms, items: {len(data.get('preview_items', []))}")

if __name__ == '__main__':
    benchmark()

