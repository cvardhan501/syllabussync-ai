import { spawn } from 'child_process';

const CHROME_PATH = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const chrome = spawn(CHROME_PATH, ['--headless=new', '--remote-debugging-port=9228', 'about:blank']);

function delay(ms) {
  return new Promise(r => setTimeout(r, ms));
}

setTimeout(async () => {
  try {
    const v = await (await fetch('http://127.0.0.1:9228/json/version')).json();
    const ws = new WebSocket(v.webSocketDebuggerUrl);

    ws.onopen = () => {
      ws.send(JSON.stringify({ id: 1, method: 'Target.createTarget', params: { url: 'http://localhost:5174/' } }));
    };

    ws.onmessage = async (e) => {
      const d = JSON.parse(e.data);
      if (d.id === 1) {
        const pageWs = new WebSocket('ws://127.0.0.1:9228/devtools/page/' + d.result.targetId);
        
        pageWs.onopen = async () => {
          await delay(2500);
          console.log('[Step 1] Clicking Local Guest...');
          pageWs.send(JSON.stringify({
            id: 2,
            method: 'Runtime.evaluate',
            params: {
              expression: `
                (() => {
                  const btn = Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Local Guest'));
                  if (btn) btn.click();
                  return !!btn;
                })()
              `
            }
          }));

          await delay(3000);

          console.log('[Step 2] Checking Dashboard DOM...');
          pageWs.send(JSON.stringify({
            id: 3,
            method: 'Runtime.evaluate',
            params: {
              expression: `
                (() => {
                  const text = document.body.innerText;
                  return {
                    textSnippet: text.substring(0, 400),
                    hasOnlineVersion: text.includes('Online (v0.2.0)'),
                    hasOnlineUpper: text.includes('ONLINE'),
                    hasOffline: text.includes('Offline')
                  };
                })()
              `,
              returnByValue: true
            }
          }));
        };

        pageWs.onmessage = async (pe) => {
          const pd = JSON.parse(pe.data);

          if (pd.id === 3) {
            const res = pd.result.result.value;
            console.log('Dashboard text snippet:\n', res.textSnippet);
            console.log('Includes "Online (v0.2.0)":', res.hasOnlineVersion);
            console.log('Includes "ONLINE":', res.hasOnlineUpper);
            console.log('Includes "Offline":', res.hasOffline);

            console.log('\n[Step 3] Clicking Settings Tab...');
            pageWs.send(JSON.stringify({
              id: 4,
              method: 'Runtime.evaluate',
              params: {
                expression: `
                  (() => {
                    const btn = Array.from(document.querySelectorAll('button, a')).find(b => b.innerText.includes('Settings'));
                    if (btn) btn.click();
                    return !!btn;
                  })()
                `
              }
            }));

            await delay(3000);

            pageWs.send(JSON.stringify({
              id: 5,
              method: 'Runtime.evaluate',
              params: {
                expression: `
                  (() => {
                    const text = document.body.innerText;
                    return {
                      textSnippet: text.substring(0, 600),
                      hasFastApiService: text.includes('FastAPI Service'),
                      hasOnline: text.includes('online') || text.includes('Online'),
                      hasOnlineUpper: text.includes('ONLINE')
                    };
                  })()
                `,
                returnByValue: true
              }
            }));
          }

          if (pd.id === 5) {
            const res = pd.result.result.value;
            console.log('\nSettings Page text snippet:\n', res.textSnippet);
            console.log('Settings has FastAPI Service:', res.hasFastApiService);
            console.log('Settings has online/Online:', res.hasOnline);
            console.log('Settings has ONLINE badge:', res.hasOnlineUpper);

            console.log('\n[Step 4] Reloading page to test persistence...');
            pageWs.send(JSON.stringify({ id: 6, method: 'Page.reload' }));
            await delay(3500);

            pageWs.send(JSON.stringify({
              id: 7,
              method: 'Runtime.evaluate',
              params: {
                expression: `
                  (() => {
                    const text = document.body.innerText;
                    return {
                      textSnippet: text.substring(0, 300),
                      hasOnlineVersion: text.includes('Online (v0.2.0)'),
                      hasOnlineUpper: text.includes('ONLINE'),
                      hasOffline: text.includes('Offline')
                    };
                  })()
                `,
                returnByValue: true
              }
            }));
          }

          if (pd.id === 7) {
            const res = pd.result.result.value;
            console.log('\nAfter Refresh persistence check:');
            console.log('DOM Text snippet after reload:\n', res.textSnippet);
            console.log('Persists "Online (v0.2.0)":', res.hasOnlineVersion);
            console.log('Persists "ONLINE":', res.hasOnlineUpper);
            console.log('Has "Offline":', res.hasOffline);

            console.log('\nSUCCESS: Browser verification complete!');
            chrome.kill();
            process.exit(0);
          }
        };
      }
    };
  } catch (err) {
    console.error(err);
    chrome.kill();
    process.exit(1);
  }
}, 1000);
