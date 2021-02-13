const fetch = require('node-fetch');
async function get_namespaces(){
  const url = 'http://localhost:5000/namespaces'
  const res = await fetch(url);
  const data = await res.json();//assuming data is json
  var namespaces = JSON.parse(data);
  renderNamespaces(namespaces);
  pushNamespaceOptions(namespaces);
}

function renderNamespaces(ns){
    ns.forEach(element => {
      console.log(element);    
    });
}

function pushNamespaceOptions(namespaces) {
    var namespaceOptions = [];
    namespaces.forEach(element => {
        namespaceOptions.push({
        text: element,
        value: element,
        })
    });
    console.log(namespaceOptions)
}

get_namespaces();