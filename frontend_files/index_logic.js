document.getElementById('send-message-text').onkeydown = e => {
    if (e.code === "Enter" && !e.shiftKey) {
        sendMessage();
    }
};


function getCurrentChannelID() {
    return document.location.pathname.split("/")[2];
}


function sendMessage() {
    const messageContainer = document.getElementById('send-message-text');
    const messageText = messageContainer.value.trim();
    if (!messageText) return;
    console.log("Sending message:", messageText);
    messageContainer.value = "";

    let nowSeconds = Math.floor(new Date() / 1000);
    let tempID = Math.floor(+new Date() + Math.random() * 1000);

    let message = {
        author: selfUsername,
        text: messageText,
        timestamp: nowSeconds,
        tempID: tempID
    }
    let hideHeader = false;
    if (messagesBuffer.length >= 1) {
        hideHeader = shouldHideHeader(message, messagesBuffer[messagesBuffer.length - 1]);
    }
    appendMessage(message, { unconfirmed: true, displayname: selfDisplayname, hideHeader: hideHeader });
 
    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/send_message");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    let channelID = getCurrentChannelID();

    const body = JSON.stringify({
        channel: channelID,
        text: messageText,
        tempID: tempID,
    });

    xhr.onload = () => {
        if (xhr.readyState === 4 && xhr.status === 200 || xhr.status === 201) {
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
        if (authorNode.innerText === username) {
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
        if (username === selfUsername) {
            insertSelfDisplayname(displayname);
        }
        return;
    }

    accountMetaCache[username] = null;  // Placeholder
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200 || xhr.status === 201) {
            let response = JSON.parse(xhr.responseText);
            accountMetaCache[username] = response;
            let displayname = response['displayname'];
            replaceMessageAuthorName(username, displayname);
            if (username === selfUsername) {
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
        nodeTimestamp.innerText = formatDate(date);
        nodeTimestamp.classList.add("message-timestamp");
        nodeDiv.appendChild(nodeTimestamp);
    }

    if (options.unconfirmed && typeof message.tempID !== "undefined") {
        console.log("fsasffasfdaafd")
        let nodeTempID = document.createElement("span");
        nodeTempID.innerText = message.tempID;
        nodeTempID.classList.add("message-tempid");
        nodeDiv.appendChild(nodeTempID);
    }

    if (!options.hideHeader) {
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
        message.author === lastMessage.author &&
        message.timestamp - lastMessage.timestamp < 420
    );
}


function loadMessages(batchID) {
    loadingMessages = true;
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
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

        else if (xhr.readyState === 4) {
            console.warn(`Error to /channels/CHANNEL/messages: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /channels/CHANNEL/messages:", response['error']);
        }
    }

    let url = fixLocalURL(`messages?batch=${batchID}`);
    xhr.open('GET', url, true);
    xhr.send(null);
}


function loadChannelAbout(alsoLoadMessages=false) {
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = function () {
        if (xhr.readyState === 4 && xhr.status === 200) {
            channelAbout = JSON.parse(xhr.responseText);
            currentBatchID = channelAbout['latestMessageBatch'];
            const channelHeaderDiv = document.querySelector("#channel-header");
            const channelNameNode = channelHeaderDiv.querySelector("#channel-header-name");
            const channelMembersNode = channelHeaderDiv.querySelector("#channel-header-members");
            channelNameNode.innerText = channelAbout['name'];
            channelMembersNode.innerText = channelAbout['members'].join(", ");

            if (alsoLoadMessages) {
                console.log("Channel about:", channelAbout);
                console.log("Got channel about. Loading messages.");
                loadMessages(currentBatchID);
                currentBatchID--;
                loadMessages(currentBatchID);
                currentBatchID--;
            }
        }

        else if (xhr.readyState === 4) {
            let response = JSON.parse(xhr.responseText);
            console.warn(xhr.status, xhr.statusText, response);
            if (xhr.status === 401) {
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

    sock.onopen = () => {
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
        let hideHeader = false;
        if (messagesBuffer.length >= 1) {
            hideHeader = shouldHideHeader(response, messagesBuffer[messagesBuffer.length - 1]);
        }
        appendMessage(response, {hideHeader: hideHeader});
        loadAccountMeta(response.author);
        if (typeof response.tempID !== "undefined") {
            removeUnconfirmedMessage(response.tempID);
        }
    }

    let token = getCookie("token");
    let username = getCookie("username");
    let channelID = getCurrentChannelID();
}


function removeUnconfirmedMessage(tempID) {
    const messageTempIDNodes = document.querySelectorAll(".message .message-tempid");
    console.log(messageTempIDNodes);

    messageTempIDNodes.forEach(messageTempIDNode => {
        console.log(messageTempIDNode.innerText, tempID);
        if (messageTempIDNode.innerText == tempID) {
            messageTempIDNode.parentNode.remove();
        }
    });

    messagesBuffer.forEach((msg, index, arr) => {
        if (msg.tempID === tempID) {
            arr.splice(index, 1);  // removes the element
        }
    });
}


function logout(noConfirm) {
    if (!noConfirm) {
        if (!confirm("Are you sure you want to log out?\nYou will lose your private key!")) return;
    }
    console.log("Logging out.");
    deleteCookie("token");
    deleteCookie("username");
    localStorage.removeItem("privateKey");
    window.location.replace("/login.html");
}


function logoutAll() {
    if (!confirm("Log out of all other devices?")) return;

    console.log("Logging out of all other devices.");
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            alert("Logged out of all other devices.");
            console.log("Response to /logout_all_other_sessions:", response);
        }

        else if (xhr.readyState === 4) {
            console.warn(`Error to /logout_all_other_sessions: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /logout_all_other_sessions:", response['error']);
        }
    }

    xhr.open("POST", "/logout_all_other_sessions", true);
    xhr.send(null);
}


function deleteAccount() {
    if (!confirm("Delete your account?\nThis action is irreversible!")) return;
    if (!confirm("Really delete it forever?")) return;
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState === 4 && xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /delete_account:", response);
            alert("Your account was deleted.");
            logout(true);
        }

        else if (xhr.readyState === 4) {
            console.warn(`Error to /delete_account: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /delete_account:", response['error']);
            alert(`Could not delete account: ${response['error']}`);
        }
    }

    xhr.open("POST", "/delete_account", true);
    xhr.send(null);
}

function addChannelToSidebar(channelID, channelName) {
    let sidebarChannels = document.querySelector("#sidebar-channels");

    let nodeDiv = document.createElement("div");
    nodeDiv.classList.add("sidebar-channel");

    let nodeLink = document.createElement("a");
    nodeLink.classList.add("unstyled-link");
    nodeLink.href = `/channels/${channelID}/`;

    let nodeName = document.createElement("p");
    nodeName.classList.add("sidebar-channel-name");
    nodeName.innerText = `${channelName}`;

    let nodeDivider = document.createElement("span");
    nodeDivider.classList.add("divider-small");

    nodeLink.appendChild(nodeName);
    nodeDiv.appendChild(nodeLink);
    sidebarChannels.appendChild(nodeDiv);
    sidebarChannels.appendChild(nodeDivider);
}


function removeChannelFromSidebar(channelID) {
    let sidebarChannels = document.querySelector("#sidebar-channels");

    for (let i = 0; i < sidebarChannels.children.length; i++) {
        const sidebarChannel = sidebarChannels.children[i];
        let sidebarChannelHref = sidebarChannel.querySelector("a").getAttribute("href");
        let sidebarChannelID = sidebarChannelHref.substring(0, sidebarChannelHref.length-1).substring(sidebarChannelHref.lastIndexOf("/") + 1);
        console.log("remvoeFromASidebar", sidebarChannelID);
        if (sidebarChannelID === channelID) {
            sidebarChannels.removeChild(sidebarChannels.children[i]);
            return;
        }

    }
}



function loadSelfChannels() {
    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /get_self_channels:", response);

            // put in sidebar
            for (const [channelID, channelName] of Object.entries(response)) {
                addChannelToSidebar(channelID, channelName);
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

// function messagesAutoLoader() {
//     if (loadingMessages) {
//         setTimeout(messagesAutoLoader, 300);
//         return;
//     }
//
//     const messagesDiv = document.querySelector("#messages");
//     // if (messagesDiv.children.length == 0) {
//     //     setTimeout(messagesAutoLoader, )
//     // }
//
//     const oldestMessage = messagesDiv.children[messagesDiv.children.length - 1];
//
//     let rectElem = oldestMessage.getBoundingClientRect();
//     let rectContainer = messagesDiv.getBoundingClientRect();
//
//     if (rectElem.top - 1 > rectContainer.top) {
//         setTimeout(messagesAutoLoader, 300);
//         return;
//     }
//
//     loadMessages(currentBatchID);
//     currentBatchID--;
//     if (currentBatchID > 0) {
//         setTimeout(messagesAutoLoader, 300);
//     }
// }


function scrollerListener() {
    let initialPointerY = null;
    let initialScrollerTop = null;
    let usingScrollbar = false;

    const msgDivWrapper = document.querySelector("#messages-wrapper");
    const msgDiv = document.querySelector("#messages");
    const scrollbar = document.querySelector("#messages-wrapper .scrollbar");
    const scroller = scrollbar.querySelector(".scrollbar-scroller");

    const messageLoader = _.throttle(() => {
        if (currentBatchID < 1) return;
        console.log("Checking if messages need to be loaded");

        if (scroller.offsetTop / scrollbar.clientHeight < 0.5) {
            loadMessages(currentBatchID);
            currentBatchID--;
        }
    }, 200);

    const mousemoveCallback = (event2) => {
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

        msgDiv.scrollTo({top: msgScrollTop});
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

    msgDiv.addEventListener('scroll', _.throttle(() => {
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


function createChannel() {
    let channelName = prompt("Name for the new channel:")
    if (!channelName) return;
    channelName = channelName.trim();

    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /create_channel:", response);
            let channelID = response['channelID'];
            window.location.replace(`/channels/${channelID}/`);
            addChannelToSidebar(channelID, channelName);
        }
        else {
            console.warn(`Error to /create_channel: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /create_channel:", response['error']);
        }
    }

    xhr.open("POST", "/create_channel", true);
    let body = JSON.stringify({
        channelName: channelName
    })
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
    xhr.send(body);
}



function deleteChannel() {
    if (!confirm("Are you sure you want to delete this channel?")) return;

    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /delete_channel:", response);
            let channelID = response['channelID'];
            window.location.replace(`/`);
            removeChannelFromSidebar(channelID);
        }
        else {
            console.warn(`Error to /delete_channel: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /delete_channel:", response['error']);
            alert(`Could not delete channel because: ${response['error']}`);
        }
    }

    xhr.open("POST", "/delete_channel", true);
    let body = JSON.stringify({
        channelID: getCurrentChannelID()
    })
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
    xhr.send(body);
}


function addMember() {
    let memberUsername = prompt("Username of the member you want to add:");
    if (!memberUsername) return;
    memberUsername = memberUsername.trim().toLowerCase();

    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /add_member_to_channel:", response);
            loadChannelAbout();
        }
        else {
            console.warn(`Error to /add_member_to_channel: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /add_member_to_channel:", response['error']);
            alert(`Could not add member to this channel because: ${response['error']}`);
        }
    }

    xhr.open("POST", "/add_member_to_channel", true);
    let body = JSON.stringify({
        channelID: getCurrentChannelID(),
        newMember: memberUsername,
    })
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
    xhr.send(body);
}


function removeMember() {
    let memberUsername = prompt("Username of the member you want to remove:");
    if (!memberUsername) return;
    memberUsername = memberUsername.trim().toLowerCase();

    const xhr = new XMLHttpRequest();

    xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;

        if (xhr.status === 200) {
            let response = JSON.parse(xhr.responseText);
            console.log("Response to /remove_member_from_channel:", response);
            loadChannelAbout();
        }
        else {
            console.warn(`Error to /remove_member_from_channel: ${xhr.status} - ${xhr.statusText}`);
            let response = JSON.parse(xhr.responseText);
            console.log("Error Message to /remove_member_from_channel:", response['error']);
            alert(`Could not remove member from channel because: ${response['error']}`);
        }
    }

    xhr.open("POST", "/remove_member_from_channel", true);
    let body = JSON.stringify({
        channelID: getCurrentChannelID(),
        newMember: memberUsername,
    })
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");
    xhr.send(body);
}



window.onload = () => {
    // variables and stuff
    channelAbout = null;
    currentBatchID = null;
    accountMetaCache = {};
    selfUsername = getCookie("username");
    selfDisplayname = null;
    loadingMessages = true;
    messagesBuffer = [];

    console.log("Document is loaded. Loading channel about.");
    loadChannelAbout(true);
    console.log("Channel about loaded. Loading self displayname and channels.");
    loadAccountMeta(selfUsername);
    loadSelfChannels();
    // console.log("Self displayname loaded. Connecting WebSocket.");
    connectWebSocket();
    initializeScroller();
    scrollerListener();
}

// TODO: self username not replacing in message
