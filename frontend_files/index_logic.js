document.getElementById('send-message-text').onkeydown = e => {
    if (e.code == "Enter" && !e.shiftKey) {
        sendMessage();
    }
};


function sendMessage() {
    var messageText = document.getElementById('send-message-text').value.trim();
    if (!messageText) return;

    const xhr = new XMLHttpRequest();
    xhr.open('POST', "/send_message");
    xhr.setRequestHeader("Content-Type", "application/json; charset=UTF-8");

    const body = JSON.stringify({
        text: messageText,
    });

    xhr.onload = () => {
        if (xhr.readyState == 4 && xhr.status == 200 || xhr.status == 201) {
            console.log(JSON.parse(xhr.responseText));
        } else {
            console.log(`Error: ${xhr.status}`);
        }
    };
    xhr.send(body);
}