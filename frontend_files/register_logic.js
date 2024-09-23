
function submitRegister() {
    var username = document.getElementById('form-username').value;
    var displayname = document.getElementById('form-displayname').value;
    var password = document.getElementById('form-password').value;

    var errorMessage = document.getElementById('error-message');
    var infoMessage = document.getElementById('info-message');
    errorMessage.style['display'] = 'none';
    infoMessage.style['display'] = 'none';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/register");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    const body = JSON.stringify({
        username: username,
        displayname: displayname,
        password: password,
    });

    xhr.onload = () => {
        let response = JSON.parse(xhr.responseText);

        if (xhr.readyState == 4 && xhr.status == 200 || xhr.status == 201) {
            console.log(response);
            errorMessage.style['display'] = 'none';
            infoMessage.style['display'] = 'flex';
        } else {
            console.log(`Error: ${xhr.status}`);
            errorMessage.style['display'] = 'flex';
            infoMessage.style['display'] = 'none';
            // fuck it
            errorMessage.children[1].textContent = `Response ${xhr.status} - ${xhr.statusText}`;
            errorMessage.children[2].textContent = response['error'];  // what is html injection
        }
    };
    xhr.send(body);

}