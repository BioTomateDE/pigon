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