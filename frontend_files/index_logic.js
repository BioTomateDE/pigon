document.getElementById('send-message-text').onkeydown = e => {
    if (e.code == "Enter" && !e.shiftKey) {
        sendMessage();
    }
};


function getChannelID() {
    return Number(document.location.pathname.split("/")[2]);
}


function sendMessage() {
    var messageContainer = document.getElementById('send-message-text');
    var messageText = messageContainer.value.trim();
    if (!messageText) return;
    console.log("Sending", messageText);
    messageContainer.value = "";

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/send_message");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    let channelID = getChannelID();

    const body = JSON.stringify({
        channel: channelID,
        text: messageText,
    });

    xhr.onload = () => {
        if (xhr.readyState == 4 && xhr.status == 200 || xhr.status == 201) {
            console.log("Response to /send_message:", JSON.parse(xhr.responseText));
        } else {
            console.warn(`Error to /send_message: ${xhr.status} - ${xhr.statusText}`);
            console.log("Error Message to /send_message:", JSON.parse(xhr.responseText)['error']);
        }
    };
    xhr.send(body);
}


function replaceMessageAuthorName(username, displayname) {
    let placeholderAuthorNodes = document.getElementsByClassName("message-author-placeholder");
    console.log(`Replacing username ${username} with displayname "${displayname}"`);
    // console.log([...placeholderAuthorNodes][0].innerHTML);

    [...placeholderAuthorNodes].forEach(authorNode => {
        if (authorNode.innerText == username) {
            authorNode.innerText = displayname;
            authorNode.classList.remove("message-author-placeholder");
        }
    });
}


function loadAccountMeta(username) {
    // console.log("abasfhfbhasbasdgfj", username, Object.keys(accountMetaCache))
    if (username in accountMetaCache) {
        let displayname = accountMetaCache[username]['displayname'];
        replaceMessageAuthorName(username, displayname);
        if (username == selfUsername) {
            insertSelfDisplayname(displayname);
        }
        return;
    }

    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState != 4) return;
        let response = JSON.parse(xhr.responseText);

        if (xhr.status == 200 || xhr.status == 201) {
            accountMetaCache[username] = response;
            let displayname = response['displayname'];
            replaceMessageAuthorName(username, displayname);
            if (username == selfUsername) {
                insertSelfDisplayname(displayname);
            }
            // return [username, displayname];

        } else {
            console.warn(`Error to /USER/about: ${xhr.status} - ${xhr.statusText}`);
            console.log("Error Message to USER/about:", response['error']);
            // return [null, null];
        }
    }

    let url = `/users/${username}/about/`;
    xhr.open('GET', url, true);
    xhr.send(null);
}


function insertSelfDisplayname(displayname) {
    let displaynameNode = document.getElementById("sidebar-loginfo-displayname");
    displaynameNode.innerText = displayname;
}



function textFormatting(text) {
    // TODO what the hell is going on in the regex
    text = escapeHTML(text);

    // https://stackoverflow.com/questions/11819059/regex-match-character-which-is-not-escaped

    const reCodeBlock = /``([^\s]+?)``/g;
    const reCode = /`([^\s]+?)`/g;
    const reBold = /(?<!\\)(?:\\\\)*\*(?<!\\)(?:\\\\)*\*([^\s]+?)(?<!\\)(?:\\\\)*\*(?<!\\)(?:\\\\)*\*/g;
    const reItalic = /(?<!\\)(?:\\\\)*\*([^\s]+?)(?<!\\)(?:\\\\)*\*/g;
    const reUnderlined = /(?<!\\)(?:\\\\)*_([^\s]+?)(?<!\\)(?:\\\\)*_/g;
    const reEscaping = /\\([\*_`])/g;
    const reDoubleBackslashes = /\\\\/g;
    // TODO spoilers

    text = text.replaceAll(reCodeBlock, `<pre><code>$1</code></pre>`)
        .replaceAll(reCode, "<code>$1</code>")
        .replaceAll(reBold, "<strong>$1</strong>")
        .replaceAll(reItalic, "<em>$1</em>")
        .replaceAll(reUnderlined, "<u>$1</u>")
        .replaceAll(reEscaping, "$1")
        .replaceAll(reDoubleBackslashes, "\\")

    return text;
}



function loadMessages(batchID) {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let messages = JSON.parse(xhr.responseText);
            let messagesDiv = document.getElementById("messages");

            messages.forEach(message => {
                // if (!(message['author'] in accountMetaCache)) {
                //     // v Placeholder so not every message will trigger this; it takes time to load
                //     accountMetaCache[message['author']] = null;
                //     loadAccountMeta(message['author']);
                // }
                loadAccountMeta(message['author']);

                let nodeDiv = document.createElement("div");
                nodeDiv.classList.add("message");

                let nodeAuthor = document.createElement("span");
                nodeAuthor.innerText = message['author'];
                nodeAuthor.classList.add("message-author");
                nodeAuthor.classList.add("message-author-placeholder");
                nodeDiv.appendChild(nodeAuthor);

                let nodeTimestamp = document.createElement("span");

                let date = new Date(message['timestamp'] * 1000);
                let dateFormatted = formatDate(date);

                nodeTimestamp.innerText = dateFormatted;
                nodeTimestamp.classList.add("message-timestamp");
                nodeDiv.appendChild(nodeTimestamp);

                let nodeBr = document.createElement("br");
                nodeDiv.appendChild(nodeBr);

                let nodeText = document.createElement("span");
                nodeText.innerHTML = textParser(message['text']);
                nodeText.classList.add("message-text");
                nodeDiv.appendChild(nodeText);

                messagesDiv.appendChild(nodeDiv);
            });
        }

        else if (xhr.readyState == 4) {
            console.warn(`Error to /channels/CHANNEL/messages: ${xhr.status} - ${xhr.statusText}`);
            console.log("Error Message to /channels/CHANNEL/messages:", response['error']);
        }
    }

    let url = fixLocalURL(`messages?batch=${batchID}`);
    xhr.open('GET', url, true);
    xhr.send(null);
}


function loadChannelAbout() {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            channelAbout = JSON.parse(xhr.responseText);
            console.log("Channel about:", channelAbout);
            console.log("Got channel about. Loading messages.");
            loadMessages(channelAbout['latestMessageBatch']);
        }

        else if (xhr.readyState == 4) {
            let response = JSON.parse(xhr.responseText);
            console.warn(xhr.status, xhr.statusText, response);
            if (xhr.status == 401) {
                deleteCookie("token");
                deleteCookie("username");
                console.log("Token was deleted.");
            }
        }
    }

    let url = fixLocalURL("about");
    xhr.open('GET', url, true);
    xhr.send(null);
}


function connectWebSocket() {
    const sock = new WebSocket(`ws://${window.location.hostname}:8982`);
    
    sock.onopen = (event) => {
        console.log("WebSocket opened. Sent token and username.");
        sock.send(`${token} ${username} ${channelID}`);
    };

    sock.onerror = (event) => {
        console.warn("WebSocket connection closed with error:", event);
    };

    sock.onclose = (event) => {
        console.warn("WebSocket connection closed by server:", event);
        // TODO reconnect potentially
    }

    sock.onmessage = (event) => {
        console.log("Received message from WebSocket:", event.data);
    }

    let token = getCookie("token");
    let username = getCookie("username");
    let channelID = getChannelID();
}


function logout() {
    console.log("Logging out");
    deleteCookie("token");
    deleteCookie("username");
    window.location.replace("/login.html");
}


function deleteAccount() {
    if (confirm("Delete your account?\nThis action is irreversible!")) {
        alert("hawk tuah");
    }
}



var channelAbout = null;
var accountMetaCache = {};
var selfUsername = getCookie("username");

window.onload = (event) => {
    console.log("Document is loaded. Loading channel about.");
    loadChannelAbout();
    console.log("Channel about loaded. Loading self username.");
    loadAccountMeta(selfUsername);
    // console.log("Self username loaded. Connecting WebSocket.");
    connectWebSocket();
}