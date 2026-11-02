import { spawn } from 'child_process';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const chrome = spawn(CHROME_PATH, ['--headless=new', '--remote-debugging-port=9225', 'about:blank']);

setTimeout(async () => {
  try {
    const v = await (await fetch('http://127.0.0.1:9225/json/version')).json();
    const ws = new WebSocket(v.webSocketDebuggerUrl);
    ws.onopen = () => {
      ws.send(JSON.stringify({ id: 1, method: 'Target.createTarget', params: { url: 'http://localhost:5174/' } }));
    };
    ws.onmessage = async (e) => {
      const d = JSON.parse(e.data);
      if (d.id === 1) {
        const pageWs = new WebSocket('ws://127.0.0.1:9225/devtools/page/' + d.result.targetId);
        pageWs.onopen = () => {
          pageWs.send(JSON.stringify({ id: 2, method: 'Runtime.enable' }));
          pageWs.send(JSON.stringify({ id: 3, method: 'Network.enable' }));
        };
        pageWs.onmessage = (pe) => {
          const pd = JSON.parse(pe.data);
          if (pd.method === 'Network.loadingFailed') {
            console.log('NETWORK LOADING FAILED:', pd.params.requestId, pd.params.errorText, pd.params.canceled, pd.params.corsErrorStatus);
          }
          if (pd.method === 'Network.responseReceived') {
            console.log('NETWORK RESPONSE:', pd.params.response.url, pd.params.response.status, pd.params.response.headers);
          }
          if (pd.method === 'Runtime.consoleAPICalled') {
            console.log('CONSOLE:', pd.params.type, pd.params.args.map(a => a.value || a.description).join(' '));
          }
          if (pd.method === 'Runtime.exceptionThrown') {
            console.log('EXCEPTION:', pd.params.exceptionDetails.text, pd.params.exceptionDetails.exception?.description);
          }
          if (pd.id === 4) {
            console.log('FETCH RESULT IN CHROME:', pd.result.result.value);
            chrome.kill();
            process.exit(0);
          }
        };

        setTimeout(() => {
          pageWs.send(JSON.stringify({
            id: 4,
            method: 'Runtime.evaluate',
            params: {
              awaitPromise: true,
              returnByValue: true,
              expression: `
                (async () => {
                  try {
                    const res = await window.fetch('http://localhost:8000/api/health');
                    const text = await res.text();
                    return { ok: res.ok, status: res.status, body: text };
                  } catch (err) {
                    return { error: err.name + ': ' + err.message };
                  }
                })()
              `
            }
          }));
        }, 2000);
      }
    };
  } catch (err) {
    console.error(err);
    chrome.kill();
  }
}, 1000);
