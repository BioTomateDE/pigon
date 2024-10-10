
async function submitRegister() {
    const username = document.getElementById('form-username').value.trim();
    const displayname = document.getElementById('form-displayname').value.trim();
    const password = document.getElementById('form-password').value;
    const passwordConfirm = document.getElementById('form-password-confirm').value;
    if (!( username && displayname && password && passwordConfirm )) return;

    const errorMessage = document.getElementById('error-message');
    const infoMessage = document.getElementById('info-message');
    errorMessage.style['display'] = 'none';
    infoMessage.style['display'] = 'none';

    if (password != passwordConfirm) {
        errorMessage.style['display'] = 'flex';
        errorMessage.children[1].innerText = "Passwords do not match!";
        errorMessage.children[2].innerText = "The password you entered does not match with password confirmation you entered.\nPlease try again.";
        return;
    }

    let keyPair = await generateKeyPair();
    try {
        await storePrivateKey(keyPair.privateKey);
    } catch (error) {
        errorMessage.style['display'] = 'flex';
        errorMessage.children[1].innerText = "Already registered!";
        errorMessage.children[2].innerText = "There is already a private key stored in localstorage.\nYou can log in probably.";
        return;
    }

    let publicKeyJWK = await crypto.subtle.exportKey("jwk", keyPair.publicKey);

    const xhr = new XMLHttpRequest();
    // xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    const body = JSON.stringify({
        username: username,
        displayname: displayname,
        password: password,
        publicKey: publicKeyJWK,
    });

    xhr.onload = () => {
        if (xhr.readyState != 4) return;

        if (xhr.status == 200 || xhr.status == 201) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response from /register:", response);
            errorMessage.style['display'] = 'none';
            infoMessage.style['display'] = 'flex';

            let generatedToken = response['generatedToken']
            let tokenExpiryDate = new Date();
            tokenExpiryDate.setFullYear(tokenExpiryDate.getFullYear() + 1);
            setCookie('token', generatedToken, tokenExpiryDate);
            setCookie('username', username, tokenExpiryDate);

        } else {
            console.warn(`Error from /register: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log(`Error message from /register: ${response}`);
            errorMessage.style['display'] = 'flex';
            infoMessage.style['display'] = 'none';
            errorMessage.children[1].innerText = `Response ${xhr.status} - ${xhr.statusText}`;
            errorMessage.children[2].innerText = response['error'];
        }
    };

    xhr.open('POST', "/register");
    xhr.send(body);
}


window.onload = () => {
    if (getCookie("token") || getCookie("username")) {
        console.log("Redirected from register page to index.");
        window.location.replace("/");
    }
}