var apiEndpoints = {
    "emulators": "/api/v1/androidTrigger/emulators",
    "challenge_config": "/api/v1/androidTrigger/challenge_config"
};


var loadingHTML = `<div class="d-flex justify-content-center"><div class="spinner-border" role="status"></div></div>`;

var emulatorModalHTML = `
        <!-- Collapsible Content -->
            <div class="card card-body">
                <form>
                    <!-- URL Input -->
                    <div class="mb-3">
                        <label for="url" class="form-label">URL</label>
                        <input type="text" class="form-control" id="url" name="url" value="{{url}}" required>
                    </div>

                    <!-- Username Input -->
                    <div class="mb-3">
                        <label for="username" class="form-label">Username</label>
                        <input type="text" class="form-control" id="username" name="username" value="{{username}}" required>
                    </div>

                    <!-- Password Input -->
                    <div class="mb-3">
                        <label for="password" class="form-label">Password</label>
                        <input type="password" class="form-control" id="password" name="password" value="{{password}}" required>
                    </div>

                    <!-- Verify TLS Input -->
                    <div class="form-check">
                        <input class="form-check-input" type="checkbox" id="verify_tls" {{checked}}>
                        <label class="form-check-label" for="verify_tls">
                            Verify TLS Certificate
                        </label>
                    </div>

                </form>
            </div>
`;


function emulatorConfigModal(id = null) {
    var alertifyConfig = alertify.prompt();
    alertifyConfig.setHeader("Emulator Config");
    alertifyConfig.setContent(loadingHTML);
    alertifyConfig.elements.buttons.primary.firstChild.disabled = true;
    alertifyConfig.elements.buttons.primary.firstChild.innerText = "Loading...";
    alertifyConfig.show();

    if (id) {
        $.ajax({
            url: `${apiEndpoints.emulators}/${id}`,
            type: 'GET',
            dataType: 'json',
            success: function(data) {
                var content = emulatorModalHTML;
                content = data.verify_ssl ? content.replace("{{checked}}", "checked") : content.replace("{{checked}}", "");
                content = content.replace("{{url}}", data.url).replace("{{username}}", data.username).replace("{{password}}", data.password);
                alertifyConfig.setContent(content);
                alertifyConfig.elements.buttons.primary.firstChild.disabled = false;
                alertifyConfig.elements.buttons.primary.firstChild.innerText = "Save";
            },
            error: function(error) {
                // Handle errors
            }
        });
    } else {
        alertifyConfig.elements.buttons.primary.firstChild.disabled = false;
        alertifyConfig.elements.buttons.primary.firstChild.innerText = "Create";
        content = emulatorModalHTML.replace("{{url}}", "").replace("{{username}}", "").replace("{{password}}", "").replace("{{checked}}", "checked");
        alertifyConfig.setContent(content);
    }
    alertifyConfig.settings.onok = function() {
        var formData = {
            url: $("#url").val(),
            username: $("#username").val(),
            password: $("#password").val(),
            verify_tls: $("#verify_tls").prop("checked"),
            nonce: init.csrfNonce
        }
        $.ajax({
            url: apiEndpoints.emulators + (id ? '/' + id : ''),
            type: id ? 'POST' : 'PUT',
            data: formData,
            contentType: 'application/x-www-form-urlencoded',
            xhrFields: {
                withCredentials: true
            },
            success: function(data) {
                alertify.notify(id ? 'Entry updated successfully.' : 'Entry created successfully.', 'success', 5, function() {
                    window.location.href = window.location.href;
                    console.log('dismissed');
                })
            }
        });
    }
}

function deleteEmulator(id) {
    $.ajax({
        url: apiEndpoints.emulators + `/${id}`,
        method: 'DELETE',
        data: {
            nonce: init.csrfNonce
        },
        xhrFields: {
            withCredentials: true
        },
        success: function(data) {
            alertify.notify('Deleted', 'success', 5, function() {
                window.location.href = window.location.href;
                console.log('dismissed');
            })
        }
    })
}