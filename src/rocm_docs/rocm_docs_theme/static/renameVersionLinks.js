$(document).ready(() => {
    $('div.rst-other-versions dl:first-child a').each( function () {
        var text = $(this).text();
        var versionRegEx = /^.*((?:[0-9]+\.){2}[0-9]+).*$/;
        if (versionRegEx.test(text)) {
            $(this).text(text.replaceAll(versionRegEx, '$1'));
        }
    })
})
