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
const ticket_prices = { 'adults': 20, 'seniors': 15, 'children': 15 }
function calculate_subtotal() {
    document.querySelector("#products").innerHTML = "";
    let inputs = document.querySelectorAll("#ticket-form input[type='number']");
    for (let input of inputs) {
        if (input.value == 0) {
            continue;
        }
        else {
            let price = ticket_prices[input.id];
            let product_string = input.id;
            let products = document.querySelector("#products");
            products.innerHTML += `<tr><td>${product_string} ticket</td><td>${price}</td><td>${input.value}</td><td>${price * input.value}</td></tr>`;
        }
    }
}
function validate_ticket_form() {
    let fields = document.querySelectorAll("#ticket-form input[type='number']");
    let ok = false;
    let number_tickets = 0;
    let error = false;
    for (let field of fields) {
        if (field.value != 0 && field.value) {
            ok = true;
            for (let i = 0; i < field.value.length; i++) {
                if (!(field.value[i] >= '0' && field.value[i] <= '9')) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;
            number_tickets += parseInt(field.value);
        }
    }
    if (!ok) {
        document.querySelector("#ticket-form .btn-success").disabled = true;
        document.querySelector("#products").innerHTML = "";
        error = true;
    }
    else {
        let seats_chosen = document.querySelectorAll("#ticket-form input[type='checkbox']");
        let num_seats = 0;
        for (let seat of seats_chosen) {
            if (seat.checked) {
                num_seats++;
            }
        }
        if (num_seats <= 10 && number_tickets <= 10) {
            remove_message("more-than-10");
        }
        else {
            alert_message("Too many tickets! You may only select 10 at most.", "more-than-10");
            document.querySelector("#ticket-form .btn-success").disabled = true;
            document.querySelector("#products").innerHTML = "";
            error = true;
        }
        if (num_seats != number_tickets) {
            document.querySelector("#ticket-form .btn-success").disabled = true;
            document.querySelector("#products").innerHTML = "";
            error = true;
            alert_message("Number of seats does not match.", "unmatching-seats");
        }
        else {
            remove_message("unmatching-seats");
        }
        if (parseInt(document.querySelector("#capacity").innerHTML) < number_tickets) {
            document.querySelector("#ticket-form .btn-success").disabled = true;
            document.querySelector("#products").innerHTML = "";
            error = true;
            alert_message("Exceeded capacity.", "exceeded-capacity");
        }
        else {
            remove_message("exceeded-capacity");
        }
        if (!error) {
            document.querySelector("#ticket-form .btn-success").disabled = false;
            calculate_subtotal();
        }
    }
}
document.addEventListener("DOMContentLoaded", function () {
    // Validate login and register forms
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
    // Validate password length
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
    // Handle buy webpage validation
    document.querySelector("#ticket-form").addEventListener("click", function () {
        validate_ticket_form();
    });
    document.querySelector("#ticket-form").addEventListener("keyup", function () {
        validate_ticket_form();
    });
});