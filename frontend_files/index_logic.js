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
    console.log("Sending message:", messageText);
    messageContainer.value = "";

    let nowSeconds = Math.floor(new Date() / 1000);
    let tempID = Math.floor(new Date());

    let message = {
        author: selfUsername,
        text: messageText,
        timestamp: nowSeconds,
        tempID: tempID
    }
    let hideHeader = shouldHideHeader(message, messagesBuffer[messagesBuffer.length - 1]);
    appendMessage(message, { unconfirmed: true, displayname: selfDisplayname, hideHeader: hideHeader });
 
    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/send_message");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    let channelID = getChannelID();

    const body = JSON.stringify({
        channel: channelID,
        text: messageText,
        tempID: tempID,
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
        console.log(username, displayname, authorNode.innerText)
        if (authorNode.innerText == username) {
            authorNode.innerText = displayname;
            authorNode.classList.remove("message-author-placeholder");
        }
    });
}


function loadAccountMeta(username) {
    if (username in accountMetaCache) {
        if (accountMetaCache.username == null) return;
        
        let displayname = accountMetaCache[username].displayname;
        replaceMessageAuthorName(username, displayname);
        if (username == selfUsername) {
            insertSelfDisplayname(displayname);
        }
        return;
    }

    accountMetaCache[username] = null;  // Placeholder
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState != 4) return;

        if (xhr.status == 200 || xhr.status == 201) {
            let response = JSON.parse(xhr.responseText);
            accountMetaCache[username] = response;
            let displayname = response['displayname'];
            replaceMessageAuthorName(username, displayname);
            if (username == selfUsername) {
                selfDisplayname = displayname;
                insertSelfDisplayname(displayname);
            }

        } else {
            console.warn(`Error to /users/USER/about: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /users/USER/about:", response['error']);
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


function appendMessage(message, options={}) {
    // default options: {unconfirmed: false, hideHeader: false, displayname: undefined, start: false}

    let msgDiv = document.getElementById("messages");
    let nodeDiv = document.createElement("div");
    nodeDiv.classList.add("message");
    if (options.unconfirmed) {
        nodeDiv.classList.add("message-unconfirmed");
    }
    if (options.hideHeader) {
        nodeDiv.classList.add("message-hideheader");
    }

    if (!options.hideHeader) {
        let nodeAuthor = document.createElement("span");
        if (typeof options.displayname === "undefined") {
            nodeAuthor.innerText = message['author'];
            nodeAuthor.classList.add("message-author-placeholder");
        }
        else {
            nodeAuthor.innerText = options.displayname;
        }
        nodeAuthor.classList.add("message-author");
        nodeDiv.appendChild(nodeAuthor);

        let nodeTimestamp = document.createElement("span");
        let date = new Date(message['timestamp'] * 1000);
        let dateFormatted = formatDate(date);
        nodeTimestamp.innerText = dateFormatted;
        nodeTimestamp.classList.add("message-timestamp");
        nodeDiv.appendChild(nodeTimestamp);

        if (options.unconfirmed && typeof message.tempID !== "undefined") {
            console.log("fsasffasfdaafd")
            let nodeTempID = document.createElement("span");
            nodeTempID.innerText = message.tempID;
            nodeTempID.classList.add("message-tempid");
            nodeDiv.appendChild(nodeTempID);
        }

        let nodeBr = document.createElement("br");
        nodeDiv.appendChild(nodeBr);
    }

    let nodeText = document.createElement("span");
    nodeText.innerHTML = textParser(message['text']);
    nodeText.classList.add("message-text");
    nodeDiv.appendChild(nodeText);

    if (options.start) {
        msgDiv.insertBefore(nodeDiv, msgDiv.firstChild);
        messagesBuffer.splice(0, 0, message);
    } else {
        msgDiv.appendChild(nodeDiv);
        messagesBuffer.push(message);
    }

    if (msgDiv.scrollHeight - msgDiv.clientHeight - msgDiv.scrollTop > 100) {
        msgDiv.scrollTo(0, msgDiv.scrollHeight);
    }
    initializeScroller();
}


function shouldHideHeader(message, lastMessage) {
    return (
        message.author == lastMessage.author &&
        message.timestamp - lastMessage.timestamp < 420
    );
}


function loadMessages(batchID) {
    loadingMessages = true;
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4 && xhr.status == 200) {
            let messages = JSON.parse(xhr.responseText);

            for (let i = messages.length - 1; i >= 0; i--) {
                let message = messages[i];
                if (i > 0 && shouldHideHeader(message, messages[i-1]))
                    appendMessage(message, { start: true, hideHeader: true });
                else
                    appendMessage(message, {start: true});

                loadAccountMeta(message['author']);
            }
            loadingMessages = false;
        }

        else if (xhr.readyState == 4) {
            console.warn(`Error to /channels/CHANNEL/messages: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
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
            currentBatchID = channelAbout['latestMessageBatch'];
            const channelHeaderDiv = document.querySelector("#channel-header");
            const channelNameNode = channelHeaderDiv.querySelector("#channel-header-name");
            const channelMembersNode = channelHeaderDiv.querySelector("#channel-header-members");
            channelNameNode.innerText = channelAbout['name'];
            channelMembersNode.innerText = channelAbout['members'].join(", ");

            console.log("Channel about:", channelAbout);
            console.log("Got channel about. Loading messages.");
            loadMessages(currentBatchID);
            currentBatchID--;
        }

        else if (xhr.readyState == 4) {
            let response = JSON.parse(xhr.responseText);
            console.warn(xhr.status, xhr.statusText, response);
            if (xhr.status == 401) {
                deleteCookie("token");
                deleteCookie("username");
                console.log("Token was deleted.");
                // window.location.pathname = "/login.html";
                window.location.replace("/login.html");
                // TODO display error message
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
        console.log("[WS] Connection opened. Sent token and username.");
        sock.send(`${token} ${username} ${channelID}`);
    };

    sock.onclose = (event) => {
        console.warn("[WS] Connection closed:", event);
        setTimeout(connectWebSocket, 1000);
    }

    sock.onmessage = (event) => {
        let response = JSON.parse(event.data);
        if (response['error']) {
            console.warn("[WS] Received error:", response['error']);
            return;
        }

        console.log("[WS] Received message:", response);
        let hideHeader = shouldHideHeader(response, messagesBuffer[messagesBuffer.length - 1]);
        appendMessage(response, {hideHeader: hideHeader});
        loadAccountMeta(response.author);
        if (typeof response.tempID !== "undefined") {
            removeUnconfirmedMessage(response.tempID);
        }
    }

    let token = getCookie("token");
    let username = getCookie("username");
    let channelID = getChannelID();
}


function removeUnconfirmedMessage(tempID) {
    const messageTempIDNodes = document.querySelectorAll(".message .message-tempid");

    messageTempIDNodes.forEach(messageTempIDNode => {
        if (messageTempIDNode.innerText == tempID) {
            messageTempIDNode.parentNode.remove();
        }
    });

    messagesBuffer.forEach((msg, index, arr) => {
        if (msg.tempID == tempID) {
            arr.splice(index, 1);  // removes the element
        }
    });
}


function logout() {
    if (!confirm("Are you sure you want to log out?\nYou will lose your private key!")) return;
    console.log("Logging out.");
    deleteCookie("token");
    deleteCookie("username");
    localStorage.removeItem("privateKey");
    window.location.replace("/login.html");
}


function logoutAll() {
    if (!confirm("Log out of all other devices?")) return;

    console.log("Logging out of all other devices.");
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState == 4 && xhr.status == 200) {
            response = JSON.parse(xhr.responseText);
            alert("Logged out of all other devices.");
            console.log("Response to /logout_all_other_devices:", response);
        }

        else if (xhr.readyState == 4) {
            console.warn(`Error to /logout_all_other_devices: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /logout_all_other_devices:", response['error']);
        }
    }

    xhr.open("POST", "/logout_all_other_devices", true);
    xhr.send(null);
}


function deleteAccount() {
    if (!confirm("Delete your account?\nThis action is irreversible!")) return;

    alert("hawk tuah");
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState == 4 && xhr.status == 200) {
            response = JSON.parse(xhr.responseText);
            alert("Account was deleted.");
            console.log("Response to /delete_account:", response);
            window.location.replace("/login.html");
        }

        else if (xhr.readyState == 4) {
            alert("Could not delete account.\n(Check console for error message.)")
            console.warn(`Error to /delete_account: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /delete_account:", response['error']);
        }
    }

    xhr.open("POST", "/delete_account", true);
    xhr.send(null);
}


function loadSelfChannels() {
    var xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState != 4) return;

        if (xhr.status == 200) {
            response = JSON.parse(xhr.responseText);
            console.log("Response to /get_self_channels:", response);

            // put in sidebar
            let sidebarChannels = document.querySelector("#sidebar-channels");
            for (const [channelID, channelName] of Object.entries(response)) {
                let nodeDiv = document.createElement("div");
                nodeDiv.classList.add("sidebar-channel");

                let nodeLink = document.createElement("a");
                nodeLink.classList.add("unstyled-link");
                nodeLink.href = `/channels/${channelID}/`;

                let nodeName = document.createElement("p");
                nodeName.classList.add("sidebar-channel-name");
                nodeName.innerText = channelName;

                let nodeDivider = document.createElement("span");
                nodeDivider.classList.add("divider-small");

                nodeLink.appendChild(nodeName);
                nodeDiv.appendChild(nodeLink);
                sidebarChannels.appendChild(nodeDiv);
                sidebarChannels.appendChild(nodeDivider);
            }
        }

        else {
            console.warn(`Error to /get_self_channels: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /get_self_channels:", response['error']);
        }
    }

    xhr.open("GET", "/get_self_channels", true);
    xhr.send(null);
}

function messagesAutoLoader() {
    if (loadingMessages) {
        setTimeout(messagesAutoLoader, 300);
        return;
    }

    var messagesDiv = document.querySelector("#messages");
    // if (messagesDiv.children.length == 0) {
    //     setTimeout(messagesAutoLoader, )
    // }

    var oldestMessage = messagesDiv.children[messagesDiv.children.length - 1];

    let rectElem = oldestMessage.getBoundingClientRect();
    let rectContainer = messagesDiv.getBoundingClientRect();

    if (rectElem.top - 1 > rectContainer.top) {
        setTimeout(messagesAutoLoader, 300);
        return;
    }

    loadMessages(currentBatchID);
    currentBatchID--;
    if (currentBatchID > 0) {
        setTimeout(messagesAutoLoader, 300);
    }
}


function scrollerListener() {
    var initialPointerY = null;
    var initialScrollerTop = null;
    var usingScrollbar = false;

    var msgDivWrapper = document.querySelector("#messages-wrapper");
    var msgDiv = document.querySelector("#messages");
    var scrollbar = document.querySelector("#messages-wrapper .scrollbar");
    var scroller = scrollbar.querySelector(".scrollbar-scroller");

    var messageLoader = _.throttle(() => {
        if (currentBatchID < 1) return;
        console.log("Checking if messages need to be loaded");

        if (scroller.offsetTop / scrollbar.clientHeight < 0.5) {
            loadMessages(currentBatchID);
            currentBatchID--;
        }
    }, 200);

    var mousemoveCallback = (event2) => {
        const scrollbarHeight = scrollbar.clientHeight;
        const scrollerHeight = scroller.clientHeight;
        const msgHeightTotal = msgDiv.scrollHeight;
        const msgHeightVisible = msgDivWrapper.clientHeight;

        let mouseYOffset = event2.y - initialPointerY;
        let scrollerTopRaw = initialScrollerTop + mouseYOffset;
        let scrollerTop = clamp(0, scrollerTopRaw, scrollbarHeight - scrollerHeight);

        scroller.style['top'] = scrollerTop + 'px';
        let ratio = scrollerTop / (scrollbarHeight - scrollerHeight);
        let msgScrollTop = ratio * (msgHeightTotal - msgHeightVisible);

        msgDiv.scrollTo({ top: msgScrollTop });
        messageLoader();
    };

    scroller.addEventListener("mousedown", (event) => {
        initialPointerY = event.y;
        initialScrollerTop = scroller.offsetTop;
        usingScrollbar = true;
        document.addEventListener("mousemove", mousemoveCallback);
        event.preventDefault();    // Prevents selecting while scrolling
    });

    document.addEventListener("mouseup", (event) => {
        document.removeEventListener("mousemove", mousemoveCallback);
        initialPointerY = null;
        initialScrollerTop = null;
        usingScrollbar = false;
        // _.throttle(() => { console.log(usingScrollbar); usingScrollbar = false; }, 10);
        event.preventDefault();    // Prevents selecting while scrolling
    });

    msgDiv.addEventListener('scroll', _.throttle((event) => {
        if (usingScrollbar) return;

        const scrollbarHeight = scrollbar.clientHeight;
        const scrollerHeight = scroller.clientHeight;
        const msgHeightTotal = msgDiv.scrollHeight;
        const msgHeightVisible = msgDivWrapper.clientHeight;
        const msgScrollTop = msgDiv.scrollTop;

        let ratio = msgScrollTop / (msgHeightTotal - msgHeightVisible);
        let scrollerTop = ratio * (scrollbarHeight - scrollerHeight);

        scroller.style['top'] = scrollerTop + "px";
        messageLoader();
    }, 30));    // lower this value for more updates --> smoother but more performance heavy
}


function initializeScroller() {
    const msgDivWrapper = document.querySelector("#messages-wrapper");
    const msgDiv = document.querySelector("#messages");
    const scrollbar = document.querySelector("#messages-wrapper .scrollbar");
    const scroller = scrollbar.querySelector(".scrollbar-scroller");

    let msgHeightVisible = msgDivWrapper.clientHeight;
    let msgHeightTotal = msgDiv.scrollHeight;
    const scrollbarHeight = scrollbar.clientHeight;
    let ratio = msgHeightVisible / msgHeightTotal;
    let scrollerHeight = ratio * scrollbarHeight;

    scroller.style['height'] = scrollerHeight + 'px';
    scroller.style['top'] = (scrollbarHeight - scrollerHeight) + 'px';
    scrollbar.style['visibility'] = (ratio < 0.98) ? 'visible' : 'hidden';
}


// variables and stuff
var channelAbout = null;
var currentBatchID = null;
var accountMetaCache = {};
var selfUsername = getCookie("username");
var selfDisplayname = null;
var loadingMessages = true;
var messagesBuffer = [];


window.onload = (event) => {
    console.log("Document is loaded. Loading channel about.");
    loadChannelAbout();
    console.log("Channel about loaded. Loading self displayname and channels.");
    loadAccountMeta(selfUsername);
    loadSelfChannels();
    // console.log("Self displayname loaded. Connecting WebSocket.");
    connectWebSocket();
    initializeScroller();
    scrollerListener();
}
