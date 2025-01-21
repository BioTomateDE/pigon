function submitLogin() {
    var username = document.getElementById('form-username').value;
    var password = document.getElementById('form-password').value;

    if (!username || !password) return;

    var errorMessage = document.getElementById('error-message');
    var infoMessage = document.getElementById('info-message');
    errorMessage.style['display'] = 'none';
    infoMessage.style['display'] = 'none';

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/login");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    const body = JSON.stringify({
        username: username,
        password: password,
    });

    xhr.onload = () => {
        let response = JSON.parse(xhr.responseText);

        if (xhr.readyState === 4 && xhr.status === 200 || xhr.status === 201) {
            // console.log(response);
            errorMessage.style['display'] = 'none';
            infoMessage.style['display'] = 'flex';
            storeLoginData(username, response['generatedToken']);
            setTimeout(() => {
                window.location.replace("/");
            }, 1000);

        } else {
            console.log(`Error: ${xhr.status}`);
            errorMessage.style['display'] = 'flex';
            infoMessage.style['display'] = 'none';
            // fuck it
            errorMessage.children[1].innerText = `Response ${xhr.status} - ${xhr.statusText}`;
            errorMessage.children[2].innerText = response['error'];
        }
    };
    xhr.send(body);

}


window.onload = () => {
    if (getCookie("token") || getCookie("username")) {
        console.log("Redirected from login page to index.");
        window.location.replace("/");
    }

    let passwordInput = document.getElementById('form-password');

    passwordInput.addEventListener("keyup", (event) => {
        if (event.key === 'Enter') {
            submitLogin();
        }
    })
}
