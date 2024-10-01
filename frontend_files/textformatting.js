

function textParser(text) {
    let tokens = [];
    let i = 0;
    let escaping = false;

    let italicStarOpenIndex = -1;
    let boldOpenIndex = -1;
    let codeOpenIndex = -1;
    let codeBlockOpenIndex = -1;
    let italicUnderOpenIndex = -1;
    let underlineOpenIndex = -1;

    while (i < text.length) {
        switch (text[i]) {

            case '\\':
                if (codeOpenIndex == -1 || codeBlockOpenIndex == -1) {
                    escaping = !escaping;
                    if (!escaping) {
                        tokens.push('\\');
                        i += 1;
                    }
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
                if (escaping || codeBlockOpenIndex != -1 || codeOpenIndex != -1) {
                    tokens.push('*');
                    i += 1;
                }
                else if (italicStarOpenIndex != -1 || boldOpenIndex != -1) {
                    // close the inner one first
                    if (italicStarOpenIndex > boldOpenIndex || i + 1 >= text.length || text[i + 1] != '*') {
                        italicStarOpenIndex = -1;
                        tokens.push('</em>');
                    }
                    else {
                        boldOpenIndex = -1;
                        tokens.push('</strong>');
                    }
                    i += 1;
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
                        italicUnderOpenIndex = -1;
                        tokens.push('</em>');
                    }
                    else {
                        underlineOpenIndex = -1;
                        tokens.push('</u>');
                    }
                    i += 1;
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
                    codeOpenIndex = -1;
                    tokens.push('</code>');
                    i += 1;
                }
                else if (codeBlockOpenIndex != -1 && i+1 < text.length && text[i+1] == '`') {
                    codeBlockOpenIndex = -1;
                    tokens.push('</code></pre>');
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