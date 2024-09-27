document.getElementById('send-message-text').onkeydown = e => {
    if (e.code == "Enter" && !e.shiftKey) {
        sendMessage();
    }
};


function sendMessage() {
    var messageContainer = document.getElementById('send-message-text');
    var messageText = messageContainer.value.trim();
    if (!messageText) return;
    console.log("Sending", messageText);
    messageContainer.value = "";

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/send_message");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    let channelID = Number(document.location.pathname.split("/")[2]);

    const body = JSON.stringify({
        channel: channelID,
        text: messageText,
    });

    xhr.onload = () => {
        if (xhr.readyState == 4 && xhr.status == 200 || xhr.status == 201) {
            console.log(JSON.parse(xhr.responseText));
        } else {
            console.warn(`Error: ${xhr.status} - ${xhr.statusText}`);
            console.log("Error Message:", JSON.parse(xhr.responseText)['error']);
        }
    };
    xhr.send(body);
}


function replaceMessageAuthorName(username, displayname) {
    let placeholderAuthorNodes = document.getElementsByClassName("message-author-placeholder");
    console.log(`Replacing username ${username} with displayname "${displayname}"`);

    [...placeholderAuthorNodes].forEach(authorNode => {
        if (authorNode.innerText == username) {
            authorNode.innerText = displayname;
            authorNode.classList.remove("message-author-placeholder");
        }
    });
}


function loadAccountMeta(username) {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState != 4) return;
        let response = JSON.parse(xhr.responseText);

        if (xhr.status == 200 || xhr.status == 201) {
            accountMetaCache[username] = response;
            let displayname = response['displayname'];
            replaceMessageAuthorName(username, displayname);
            // return [username, displayname];

        } else {
            console.warn(`Error: ${xhr.status} - ${xhr.statusText}`);
            console.log("Error Message:", response['error']);
            // return [null, null];
        }
    }

    let url = `/users/${username}/about/`;
    xhr.open('GET', url, true);
    xhr.send(null);
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
    // TODO spoilers

    text = text.replaceAll(reCodeBlock, `<pre><code>$1</code></pre>`)
        .replaceAll(reCode, "<code>$1</code>")
        .replaceAll(reBold, "<strong>$1</strong>")
        .replaceAll(reItalic, "<em>$1</em>")
        .replaceAll(reUnderlined, "<u>$1</u>")

    return text;
}



function loadMessages(batchID) {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let messages = JSON.parse(xhr.responseText);
            let messagesDiv = document.getElementById("messages");

            messages.forEach(message => {
                if (!(message['author'] in accountMetaCache)) {
                    // v Placeholder so not every message will trigger this; it takes time to load
                    accountMetaCache[message['author']] = null;
                    loadAccountMeta(message['author']);
                }

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
                nodeText.innerHTML = textFormatting(message['text']);
                nodeText.classList.add("message-text");
                nodeDiv.appendChild(nodeText);

                messagesDiv.appendChild(nodeDiv);
            });
        }

        else if (xhr.readyState == 4) {
            console.warn(xhr.status, xhr.statusText, JSON.parse(xhr.responseText));
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
            console.log(channelAbout);
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


var channelAbout = null;
var accountMetaCache = {};

window.onload = (event) => {
    console.log("Document is loaded. Loading channel about.");
    loadChannelAbout();
}

// worked on: account loading stuff (not tested! async may be scuffed)
// todo: everything ^ server side 