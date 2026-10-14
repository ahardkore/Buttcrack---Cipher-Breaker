/* The requested operation runs off the main thread; Stop terminates it. */
'use strict';
importScripts('model.js','paradigm.js','solver.js','examples.js','browser-request.js');
self.onmessage=e=>{
  const started=Date.now();
  try{
    const text=e.data.text;
    self.postMessage({type:'identified',info:identify(text)});
    const report=BrowserRequest.run(text,e.data.options || {depth:e.data.depth ?? 3});
    self.postMessage({type:'done',...report,elapsed:(Date.now()-started)/1000});
  }catch(error){self.postMessage({type:'error',message:String(error.message || error)});}
};
