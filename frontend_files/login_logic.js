
function submitLogin() {
    var username = document.getElementById('form-username').value;
    var password = document.getElementById('form-password').value;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/login");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    const body = JSON.stringify({
        username: username,
        password: password,
    });

    xhr.onload = () => {
        let errorMessage = document.getElementById('error-message');
        let infoMessage = document.getElementById('info-message');

        if (xhr.readyState == 4 && xhr.status == 200 || xhr.status == 201) {
            console.log(JSON.parse(xhr.responseText));
            errorMessage.style['display'] = 'none';
            infoMessage.style['display'] = 'flex';
        } else {
            console.log(`Error: ${xhr.status}`);
            errorMessage.style['display'] = 'flex';
            infoMessage.style['display'] = 'none';
            // fuck it
            errorMessage.children[1].textContent = `Response ${xhr.status} - ${xhr.statusText}`;
            errorMessage.children[2].textContent = xhr.responseText;  // what is html injection
        }
    };
    xhr.send(body);

}