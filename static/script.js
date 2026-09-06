function alert_message(msg, msg_id) {
    document.querySelector(".alert-danger").style.opacity = 1;
    if (!document.querySelector(".alert-danger").innerHTML.includes(msg_id)) {
        document.querySelector(".alert-danger").innerHTML += `<p id="${msg_id}">${msg}</p>`;
    }
}
function hide_alert() {
    document.querySelector(".alert-danger").style.opacity = 0;
}
function remove_message(msg_id) {
    if (document.querySelector(".alert-danger").innerHTML.includes(msg_id)) {
        document.querySelector(".alert-danger").removeChild(document.querySelector(`#${msg_id}`));
    }
    if (document.querySelector(".alert-danger").children.length == 0) {
        hide_alert();
    }
}
document.addEventListener("DOMContentLoaded", function () {
    if (document.querySelector(".register-form") || document.querySelector(".login-form")) {
        let fields = [{ 'name': 'email', 'length': 254 }, { 'name': 'password', 'length': 50 }];
        if (document.querySelector(".register-form")) {
            fields.push({ 'name': 'username', 'length': 20 });
        }
        for (let field of fields) {
            document.querySelector(`#${field['name']}`).addEventListener("keyup", function () {
                let input = document.querySelector(`#${field['name']}`).value;
                if (input.length > field['length']) {
                    alert_message(`${field['name']} length should not exceed ${field['length']} characters.`, `${field['name']}-length`);
                    document.querySelector(".btn-submit").disabled = true;
                }
                else {
                    document.querySelector(".btn-submit").disabled = false;
                    remove_message(`${field['name']}-length`);
                }

            });
        }
    }
    let password_fields = document.querySelectorAll(".password");
    for (let field of password_fields) {
        field.addEventListener("keyup", function () {
            if (field.value.length < 8) {
                alert_message('Password field(s) should include 8 characters at least', "password-insufficient");
                document.querySelector(".btn-submit").disabled = true;
            }
            else {
                let ok = true;
                for (let field_2 of password_fields) {
                    if (field_2.value.length < 8) {
                        ok = false;
                        break;
                    }
                }
                if (ok) {
                    remove_message("password-insufficient");
                    document.querySelector(".btn-submit").disabled = false;
                }
            }
        });
    }
});