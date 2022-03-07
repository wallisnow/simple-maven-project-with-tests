void echoWithColor(String color, String txt) {

    switch ( color ) {
        case "red":
            echo "\033[31;1;1m" + txt + "\033[0m"
            break
        case "blue":
            echo "\033[34;1;1m" + txt + "\033[0m"
            break
        default:
            echo txt
    }
}
void basicSummary(String icon, String txt) {

    createSummary(icon).appendText(
            txt, // text
            true,    // escapeHtml
            false,   // bold
            false,   // italic
            "black"   // color
    )
}
void addError(String message, String useLog='true', String useIcon='true') {
    String icon = ""

    if (useLog == 'true') {
        echoWithColor("red", "ERROR: " + message )
    }
    addErrorBadge("ERROR")
    addShortText(
            text: message,
            color: "black",
            background: "yellow",
            border: 0
    )
    if (useIcon == 'true') {
        icon = "error.gif"
    }
    basicSummary(icon, message)
}
void addInfo(String message, String useLog='true', String useIcon='true') {
    String icon = ""

    if (useLog == 'true') {
        echoWithColor("blue", "INFO: " + message )
    }
    addInfoBadge("INFO")
    addShortText(
            text: message,
            color: "black",
            background: "white",
            border: 0
    )
    if (useIcon == 'true') {
        icon = "orange-square.gif"
    }
    basicSummary(icon, message)
}

void addWarning(String message, String useLog='true', String useIcon='true') {
    String icon = ""

    if (useLog == 'true') {
        echoWithColor("red", "WARNING: " + message )
    }
    addWarningBadge("WARNING")
    addShortText(
            text: message,
            color: "black",
            background: "yellow",
            border: 0
    )
    if (useIcon == 'true') {
        icon = "warning.gif"
    }
    basicSummary(icon, message)
}

return this
