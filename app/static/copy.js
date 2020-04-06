$('#copy-button').tooltip({
    trigger: 'click',
    placement: 'bottom'
});

function setTooltip(message) {
    $('#copy-button').tooltip('hide')
        .attr('data-original-title', message)
        .tooltip('show');
}

function hideTooltip() {
    setTimeout(function () {
        $('#copy-button').tooltip('hide');
    }, 1000);
}

var clipboard = new ClipboardJS('#copy-button');

clipboard.on('success', function (e) {
    setTooltip('Copied!');
    hideTooltip();
});

clipboard.on('error', function (e) {
    setTooltip('Failed!');
    hideTooltip();
});