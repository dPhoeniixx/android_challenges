CTFd._internal.challenge.data = undefined;
countdown = 0;
// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.renderer = null;

CTFd._internal.challenge.preRender = function() {};

// TODO: Remove in CTFd v4.0
CTFd._internal.challenge.render = null;

CTFd._internal.challenge.postRender = function() {};

CTFd._internal.challenge.submit = function(preview) {
    var challenge_id = parseInt(CTFd.lib.$("#challenge-id").val());
    var submission = CTFd.lib.$("#challenge-input").val();

    var body = {
        challenge_id: challenge_id,
        submission: submission
    };
    var params = {};
    if (preview) {
        params["preview"] = true;
    }

    return CTFd.api.post_challenge_attempt(params, body).then(function(response) {
        if (response.status === 429) {
            // User was ratelimited but process response
            return response;
        }
        if (response.status === 403) {
            // User is not logged in or CTF is paused.
            return response;
        }
        return response;
    });
};

function uploadApk(id) {
    const fileInput = document.getElementById('apkFile');
    const file = fileInput.files[0];
    var triggerMsg = document.getElementById('triggerMsg');

    if (!file) {
        triggerMsg.style.display = 'block';
        triggerMsg.style.color = 'red';
        triggerMsg.innerHTML = "Please select file.";
        return
    }
    const formData = new FormData();
    formData.append('file', file);
    formData.append('challenge_id', id);
    formData.append('nonce', init.csrfNonce);

    fetch('/api/v1/androidTrigger/install', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    triggerMsg.style.display = 'block';
                    triggerMsg.style.color = 'red';
                    triggerMsg.innerHTML = errorData.message;
                    throw new Error(errorData.message);
                });
            }
            return response.json();
        })
        .then(response => {
            document.getElementById('beforeInstall').style.display = 'none';
            document.getElementById('triggerMsg').style.display = 'none';
            document.getElementById('afterInstall').style.display = 'block';
            countdown = response.data.session_lifetime;
            document.getElementById('divCountdown').innerHTML =
                `
                    <svg viewBox="0 0 24 24" height="100" id="svgCountdown">
                    <circle r="11" cx="12" cy="12" stroke-dasharray="69" stroke-dashoffset="0" stroke-width="0.8px" stroke="black" fill="none" transform="scale(1, -1) translate(0, -24) rotate(90, 12, 12)">
                        <animate
                        attributeType="XML"
                        attributeName="stroke-dashoffset"
                        from="0"
                        to="69"
                        dur="${response.data.session_lifetime}"
                        repeatCount="1"
                        />
                    </circle>
                    <text id="countdownText" x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" fill="black" font-size="7px" font-family="Lato, sans-serif">${response.data.session_lifetime}s</text>
                    </svg>
                    `;
            var countdownInterval = setInterval(function() {
                countdown -= 1;
                countdownText.innerHTML = `${countdown}s`;
                if (countdown == 0) {
                    clearInterval(countdownInterval);
                    document.getElementById('beforeInstall').style.display = 'block';
                    document.getElementById('afterInstall').style.display = 'none';
                    launchBtn.disabled = false;
                }
            }, 1000);
            if (document.getElementById("launchAfter").checked) {
                launchApp(id);
            }
        });
}

function launchApp(id) {
    const formData = new URLSearchParams();
    formData.append('challenge_id', id);
    formData.append('nonce', init.csrfNonce);

    fetch('/api/v1/androidTrigger/launch', {
            method: 'POST',
            body: formData,
            contentType: 'application/x-www-form-urlencoded'
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(errorData => {
                    triggerMsg.style.display = 'block';
                    triggerMsg.style.color = 'red';
                    triggerMsg.innerHTML = errorData.message;
                    throw new Error(errorData.message);
                });
            }
            return response.json();
        })
        .then(response => {
            countdown += response.data.extra_time;
            document.getElementById('divCountdown').innerHTML =
                `
            <svg viewBox="0 0 24 24" height="100" id="svgCountdown">
            <circle r="11" cx="12" cy="12" stroke-dasharray="69" stroke-dashoffset="0" stroke-width="0.8px" stroke="black" fill="none" transform="scale(1, -1) translate(0, -24) rotate(90, 12, 12)">
                <animate
                attributeType="XML"
                attributeName="stroke-dashoffset"
                from="0"
                to="69"
                dur="${countdown}"
                repeatCount="1"
                />
            </circle>
            <text id="countdownText" x="50%" y="50%" text-anchor="middle" dominant-baseline="middle" fill="black" font-size="7px" font-family="Lato, sans-serif">${countdown}s</text>
            </svg>
            `;
            launchBtn.disabled = true;
        })
        .catch(error => console.error('Error:', error));
}

setInterval(() => {
    fetch("/api/v1/androidTrigger/emulators/available")
        .then(response => response.json())
        .then(response => {
            if (response.data) {
                installBtn.disabled = false;
                installBtn.innerHTML = "Install";
            } else {
                installBtn.disabled = true;
                installBtn.innerHTML = "No emulator available right now."
            }
        })
}, 2000);