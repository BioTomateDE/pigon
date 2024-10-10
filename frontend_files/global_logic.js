function setCookie(name, value, exdate) {
    document.cookie = name + "=" + value + "; expires=" + exdate.toUTCString();
}

function deleteCookie(name) {
    document.cookie = name + "=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/;"
}

function formatDate(date) {
    // the struggle is real

    let now = new Date();
    // let dateInADay = date + 86400000;
    // let dateInTwoDays = date + 2*86400000;
    // let diff = now - date;

    // // These variables are cumulative! If diffMinutes = 10, then diffSeconds = 600
    // let diffSeconds = diff / 1000;
    // let diffMinutes = diff / 1000 / 60;
    // let diffHours = diff / 1000 / 60 / 60;
    // let diffDays = diff / 1000 / 60 / 60 / 24;
    // let diffMonths = diff / 1000 / 60 / 60 / 24 / 30;
    // let diffYears = diff / 1000 / 60 / 60 / 24 / 365;

    let year = date.getFullYear();
    let month = date.getMonth().toString().padStart(2, "0");
    let day = date.getDate().toString().padStart(2, "0");
    let hours = date.getHours().toString().padStart(2, "0");
    let minutes = date.getMinutes().toString().padStart(2, "0");
    let seconds = date.getSeconds().toString().padStart(2, "0");

    // console.log(date)
    // console.log(now)
    // console.log(diffDays)
    // console.log(1)
    // console.log(diff, diff.getFullYear(), diff.getDate(), diff.getDay());

    // Note: .getDate() refers to day of the MONTH while .getDay() refers to day of the WEEK even though .getWeek doesn't even exist

    if (date.getFullYear() == now.getFullYear() && date.getMonth() == now.getMonth() && date.getDate() == now.getDate()) {
        // Today at Time
        return `Today at ${hours}:${minutes}:${seconds}`
    }

    else if (date.getFullYear() == now.getFullYear() && date.getMonth() == now.getMonth() && date.getDate() == now.getDate() - 1) {
        // Yesterday at Time
        return `Yesterday at ${hours}:${minutes}`;
    }

    else {
        // Full ISO date + time
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    }
}

function fixLocalURL(sub) {
    // https://stackoverflow.com/questions/31712808/how-to-force-javascript-to-deep-copy-a-string
    // another example why this language is cancer
    let url = (' ' + window.location.pathname).slice(1);

    if (url.charAt(url.length - 1) !== "/") {
        url += "/";
    }
    url += sub;
    return url;
}

const escapeHTML = (unsafe) => {
    return unsafe.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;');
}


function getCookie(cname) {
    let name = cname + "=";
    let decodedCookie = decodeURIComponent(document.cookie);
    let ca = decodedCookie.split(';');
    for (let i = 0; i < ca.length; i++) {
        let c = ca[i];
        while (c.charAt(0) == ' ') {
            c = c.substring(1);
        }
        if (c.indexOf(name) == 0) {
            return c.substring(name.length, c.length);
        }
    }
    return "";
}


function lastNonWhitespaceToken(tokens) {
    const re = /^\s*$/g;
    let i = tokens.length - 1;
    while (tokens[i].match(re) != null) {
        i -= 1;
    }
    return i;
}



function textParser(text) {
    text = escapeHTML(text);

    let tokens = [];
    let i = 0;
    let escaping = false;

    let italicStarOpenIndex = -1;
    let boldOpenIndex = -1;
    let codeOpenIndex = -1;
    let codeBlockOpenIndex = -1;
    let italicUnderOpenIndex = -1;
    let underlineOpenIndex = -1;
    
    // console.warn(text)

    while (i < text.length) {
        let escapingNow = false;

        switch (text[i]) {
            case '\\':
                if (codeOpenIndex == -1 && codeBlockOpenIndex == -1) {
                    escaping = !escaping;
                    if (!escaping) {
                        tokens.push('\\');
                    }
                    escapingNow = escaping;
                    i += 1;
                }
                else if (i+1 < text.length && text[i+1] == '`') {
                    tokens.push('`');
                    i += 2;
                }
                else {
                    tokens.push('\\');
                    i += 1;
                }
                break;


            case '*':
                // console.log(i, escaping, italicStarOpenIndex, boldOpenIndex, text[i+1])
                if (escaping || codeBlockOpenIndex != -1 || codeOpenIndex != -1) {
                    tokens.push('*');
                    i += 1;
                }
                else if (italicStarOpenIndex != -1 || boldOpenIndex != -1) {
                    // close the inner one first
                    if (italicStarOpenIndex > boldOpenIndex || i + 1 >= text.length || text[i + 1] != '*') {
                        if (italicStarOpenIndex >= lastNonWhitespaceToken(tokens)) {
                            tokens[italicStarOpenIndex] = '*';
                            tokens.push('*');
                        }
                        else {
                            tokens.push('</em>');
                        }
                        italicStarOpenIndex = -1;
                        i += 1;
                    }
                    else {  // TODO verify that next char is actually *
                        if (boldOpenIndex >= lastNonWhitespaceToken(tokens)) {
                            tokens[boldOpenIndex] = '**';
                            tokens.push('**');
                        }
                        else {
                            tokens.push('</strong>');
                        }
                        boldOpenIndex = -1;
                        i += 2;
                    }
                }
                else if (i + 1 < text.length && text[i + 1] == '*') {
                    tokens.push('<strong>');
                    boldOpenIndex = tokens.length - 1;
                    i += 2;
                }
                else {
                    tokens.push('<em>');
                    italicStarOpenIndex = tokens.length - 1;
                    i += 1;
                }
                break;


            case '_':
                if (escaping || codeBlockOpenIndex != -1 || codeOpenIndex != -1) {
                    tokens.push('_');
                    i += 1;
                }
                else if (italicUnderOpenIndex != -1 || underlineOpenIndex != -1) {
                    // close the inner one first
                    if (italicUnderOpenIndex > underlineOpenIndex
                        || i + 1 >= text.length
                        || text[i + 1] != '_'
                    ) {
                        if (italicUnderOpenIndex >= lastNonWhitespaceToken(tokens)) {
                            tokens[italicUnderOpenIndex] = '_';
                            tokens.push('_');
                        }
                        else {
                            tokens.push('</em>');
                        }
                        italicUnderOpenIndex = -1;
                        i += 1;
                    }
                    else {  // TODO verify that the next char is actually _
                        if (underlineOpenIndex >= lastNonWhitespaceToken(tokens)) {
                            tokens[underlineOpenIndex] = '__';
                            tokens.push('__');
                        }
                        else {
                            tokens.push('</u>');
                        }
                        underlineOpenIndex = -1;
                        i += 2;
                    }
                }
                else if (i + 1 < text.length && text[i + 1] == '_') {
                    tokens.push('<u>');
                    underlineOpenIndex = tokens.length - 1;
                    i += 2;
                }
                else {
                    tokens.push('<em>');
                    italicUnderOpenIndex = tokens.length - 1;
                    i += 1;
                }
                break;
            

            case '`':
                if (escaping) {
                    tokens.push('`');
                    i += 1;
                }
                else if (codeOpenIndex != -1) {
                    if (codeOpenIndex == tokens.length - 1) {
                        tokens[codeOpenIndex] = '`';
                        tokens.push('`');
                    }
                    else {
                        tokens.push('</code>');
                    }
                    codeOpenIndex = -1;
                    i += 1;
                }
                else if (codeBlockOpenIndex != -1 && i+1 < text.length && text[i+1] == '`') {
                    if (codeBlockOpenIndex == tokens.length - 1) {
                        tokens[codeBlockOpenIndex] = '``';
                        tokens.push('``');
                    }
                    else {
                        tokens.push('</code></pre>');
                    }
                    codeBlockOpenIndex = -1;
                    i += 2;
                }
                else if (i+1 < text.length && text[i+1] == '`') {
                    tokens.push('<pre><code>');
                    codeBlockOpenIndex = tokens.length - 1;
                    i += 2;
                }
                else {
                    tokens.push('<code>');
                    codeOpenIndex = tokens.length - 1;
                    i += 1;
                }
                break;


            default:
                tokens.push(text[i]);
                i += 1;
        }

        if (!escapingNow) {
            escaping = false;
        }
    }

    // check for opened indexes and pop them from the list
    if (italicStarOpenIndex != -1) {
        tokens[italicStarOpenIndex] = '*';
    }
    if (boldOpenIndex != -1) {
        tokens[boldOpenIndex] = '**';
    }
    if (codeOpenIndex != -1) {
        tokens[codeOpenIndex] = '`';
    }
    if (codeBlockOpenIndex != -1) {
        tokens[codeBlockOpenIndex] = '``';
    }
    if (italicUnderOpenIndex != -1) {
        tokens[italicUnderOpenIndex] = '_';
    }
    if (underlineOpenIndex != -1) {
        tokens[underlineOpenIndex] = '__';
    }

    return tokens.join("");
}


function clamp(minimum, number, maxiumum) {
    if (number < minimum)
        number = minimum;
    if (number > maxiumum)
        number = maxiumum;
    return number;
}