function setCookie(name, value, exdate) {
    document.cookie = name + "=" + value + "; expires=" + exdate.toUTCString();
};

