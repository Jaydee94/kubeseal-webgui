async function fetchNamespaces() {
    let response = await fetch('http://localhost:5000/namespaces');
    let data = await response.text();
    console.log(data);
}