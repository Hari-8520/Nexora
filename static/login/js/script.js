const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);


// =================================================
// MODAL FUNCTIONS
// =================================================

function openModal(modal) {
    modal.classList.add("active");
}

function closeModal(modal) {
    modal.classList.remove("active");
}

function closeAllModals() {
    $$(".modal").forEach(modal => {
        closeModal(modal);
    });
}


// =================================================
// MESSAGE
// =================================================

function showMessage(element, text, type = "error") {

    element.textContent = text;

    element.className =
        "message " + type;
}


// =================================================
// API
// =================================================

async function postJSON(url, data) {

    const response = await fetch(url, {

        method: "POST",

        headers: {
            "Content-Type":
                "application/json"
        },

        body: JSON.stringify(data)

    });

    const result =
        await response.json();

    return result;
}
// =================================================
// PASSWORD VISIBILITY
// =================================================

function setupPasswordToggle(button, input) {
    if (!button || !input) {
        return;
    }
    button.addEventListener("click", function () {

        // Show password
        if (input.type === "password") {

            input.type = "text";

            button.setAttribute(
                "aria-label",
                "Hide password"
            );

        }

        // Hide password
        else {

            input.type = "password";

            button.setAttribute(
                "aria-label",
                "Show password"
            );

        }

    });
}
// Login password
setupPasswordToggle(
    document.getElementById("toggleLoginPassword"),
    document.getElementById("loginPassword")
);
// Registration password
setupPasswordToggle(
    document.getElementById("toggleRegisterPassword"),
    document.getElementById("registerPassword")
);
// =================================================
// LOGIN
// =================================================

$("#loginForm").addEventListener(
    "submit",
    async (event) => {

        event.preventDefault();

        const email =
            $("#loginEmail")
            .value
            .trim()
            .toLowerCase();

        const password =
            $("#loginPassword")
            .value;


        showMessage(
            $("#loginMessage"),
            ""
        );


        if (!email || !password) {

            showMessage(
                $("#loginMessage"),
                "Please enter your Gmail and password."
            );

            return;
        }


        const button =
            $("#loginButton");

        button.disabled = true;

        button.innerHTML =
            "Checking...";


        try {

            const result =
                await postJSON(
                    "/api/login",
                    {
                        email,
                        password
                    }
                );


            if (result.ok) {

                showLoginSuccess(
                    result.user
                );

                return;
            }


            // Gmail does not exist
            if (
                result.account_exists ===
                false
            ) {

                $("#accountNotFoundModal")
                    .dataset.email =
                    email;

                openModal(
                    $("#accountNotFoundModal")
                );

                return;
            }


            showMessage(
                $("#loginMessage"),
                result.message
            );

        } catch (error) {

            showMessage(
                $("#loginMessage"),
                "Unable to connect to the server."
            );

        } finally {

            button.disabled =
                false;

            button.innerHTML =
                "Login <span>→</span>";
        }

    }
);


// =================================================
// CREATE ACCOUNT BUTTON
// =================================================

$("#createAccountButton")
    .addEventListener(
        "click",
        () => {

            $("#registrationForm")
                .reset();

            $("#registrationMessage")
                .textContent = "";

            openModal(
                $("#registrationModal")
            );

        }
    );


// =================================================
// CREATE ACCOUNT FROM LOGIN
// =================================================

$("#createFromLogin")
    .addEventListener(
        "click",
        () => {

            const email =
                $("#accountNotFoundModal")
                .dataset.email || "";

            closeModal(
                $("#accountNotFoundModal")
            );


            $("#registrationForm")
                .reset();

            $("#registerEmail")
                .value = email;


            openModal(
                $("#registrationModal")
            );

        }
    );


// =================================================
// REGISTRATION
// =================================================

$("#registrationForm")
    .addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const data = {

                full_name:
                    $("#fullName")
                    .value
                    .trim(),

                student_id:
                    $("#studentId")
                    .value
                    .trim(),

              department:
                        $("#department")?.value?.trim() || "",
                year:
                    $("#year")
                    .value,

                email:
                    $("#registerEmail")
                    .value
                    .trim()
                    .toLowerCase(),

                password:
                    $("#registerPassword")
                    .value,

                confirm_password:
                    $("#confirmPassword")
                    .value

            };


            if (
                data.password.length < 8
            ) {

                showMessage(
                    $("#registrationMessage"),
                    "Password must contain at least 8 characters."
                );

                return;
            }


            if (
                data.password !==
                data.confirm_password
            ) {

                showMessage(
                    $("#registrationMessage"),
                    "Passwords do not match."
                );

                return;
            }


            const button =
                $("#registerButton");

            button.disabled = true;

            button.textContent =
                "Sending OTP...";


            try {

                const result =
                    await postJSON(
                        "/api/register",
                        data
                    );


                if (!result.ok) {

                    if (
                        result.account_exists
                    ) {

                        showMessage(
                            $("#registrationMessage"),
                            "This Gmail is already registered. Please login instead."
                        );

                    } else {

                        showMessage(
                            $("#registrationMessage"),
                            result.message
                        );

                    }

                    return;
                }


                // Save email for OTP
                $("#otpEmail")
                    .textContent =
                    data.email;


                // Save registration email
                $("#otpModal")
                    .dataset.email =
                    data.email;


                closeModal(
                    $("#registrationModal")
                );


                clearOTP();

                showMessage(
                    $("#otpMessage"),
                    "OTP sent successfully. Check your Gmail.",
                    "success"
                );


                openModal(
                    $("#otpModal")
                );


                otpInputs[0].focus();


            } catch (error) {

                showMessage(
                    $("#registrationMessage"),
                    "Unable to connect to the server."
                );

            } finally {

                button.disabled =
                    false;

                button.textContent =
                    "Create Account";

            }

        }
    );


// =================================================
// OTP
// =================================================

const otpInputs =
    [...$$(".otp")];


otpInputs.forEach(
    (input, index) => {

        input.addEventListener(
            "input",
            () => {

                input.value =
                    input.value
                    .replace(/\D/g, "")
                    .slice(0, 1);


                if (
                    input.value &&
                    index <
                    otpInputs.length - 1
                ) {

                    otpInputs[
                        index + 1
                    ].focus();

                }

            }
        );


        input.addEventListener(
            "keydown",
            (event) => {

                if (
                    event.key ===
                    "Backspace" &&
                    !input.value &&
                    index > 0
                ) {

                    otpInputs[
                        index - 1
                    ].focus();

                }

            }
        );

    }
);


function clearOTP() {

    otpInputs.forEach(
        input => {
            input.value = "";
        }
    );

}


function getOTP() {

    return otpInputs
        .map(input =>
            input.value
        )
        .join("");

}


// =================================================
// VERIFY OTP
// =================================================

$("#verifyOtpButton")
    .addEventListener(
        "click",
        async () => {

            const otp =
                getOTP();


            if (
                otp.length !== 6
            ) {

                showMessage(
                    $("#otpMessage"),
                    "Please enter the complete 6-digit OTP."
                );

                return;
            }


            const button =
                $("#verifyOtpButton");

            button.disabled = true;

            button.textContent =
                "Verifying...";


            try {

                const result =
                    await postJSON(
                        "/api/verify-registration-otp",
                        {
                            otp
                        }
                    );


                if (!result.ok) {

                    showMessage(
                        $("#otpMessage"),
                        result.message
                    );

                    return;
                }


                showMessage(
                    $("#otpMessage"),
                    "Account created successfully!",
                    "success"
                );


                setTimeout(
                    () => {

                        closeAllModals();

                        showLoginSuccess(
                            result.user,
                            true
                        );

                    },
                    700
                );


            } catch (error) {

                showMessage(
                    $("#otpMessage"),
                    "Unable to connect to the server."
                );

            } finally {

                button.disabled =
                    false;

                button.textContent =
                    "Verify & Create Account";

            }

        }
    );


// =================================================
// RESEND OTP
// =================================================

let resendTimer;
let resendSeconds = 0;


$("#resendOtpButton")
    .addEventListener(
        "click",
        async () => {

            if (
                resendSeconds > 0
            ) {

                return;
            }


            const button =
                $("#resendOtpButton");

            button.disabled = true;

            button.textContent =
                "Sending...";


            try {

                const result =
                    await postJSON(
                        "/api/resend-registration-otp",
                        {}
                    );


                if (!result.ok) {

                    showMessage(
                        $("#otpMessage"),
                        result.message
                    );

                    button.disabled =
                        false;

                    button.textContent =
                        "Resend OTP";

                    return;
                }


                clearOTP();

                showMessage(
                    $("#otpMessage"),
                    "New OTP sent to your Gmail.",
                    "success"
                );


                startResendTimer();


            } catch {

                showMessage(
                    $("#otpMessage"),
                    "Could not resend OTP."
                );

                button.disabled =
                    false;

                button.textContent =
                    "Resend OTP";

            }

        }
    );


function startResendTimer() {

    resendSeconds = 30;

    const button =
        $("#resendOtpButton");

    button.disabled = true;

    button.textContent =
        `Resend in ${resendSeconds}s`;


    clearInterval(
        resendTimer
    );


    resendTimer =
        setInterval(
            () => {

                resendSeconds--;


                if (
                    resendSeconds <= 0
                ) {

                    clearInterval(
                        resendTimer
                    );

                    button.disabled =
                        false;

                    button.textContent =
                        "Resend OTP";

                    return;

                }


                button.textContent =
                    `Resend in ${resendSeconds}s`;

            },
            1000
        );

}


// =================================================
// FORGOT PASSWORD
// =================================================

$("#forgotPassword")
    .addEventListener(
        "click",
        () => {

            alert(
                "Password reset will be added in the next authentication stage."
            );

        }
    );


// =================================================
// SUCCESS
// =================================================

function showLoginSuccess(
    user,
    accountCreated = false
) {

    const name =
        user?.name ||
        "Student";


    $(".login-content")
        .innerHTML = `

        <div class="success-content">

            <div class="success-icon">
                ✓
            </div>

            <div class="small-title">
                AUTHENTICATION SUCCESSFUL
            </div>

            <h1>
                ${accountCreated
                    ? "Account Created!"
                    : "Welcome Back!"}
            </h1>

            <p class="subtitle">
                Welcome, ${escapeHTML(name)}.
                You are successfully logged in
                to LearnAdapt AI.
            </p>


            <div class="success-box">

                <div>
                    <span>Student</span>
                    <strong>
                        ${escapeHTML(name)}
                    </strong>
                </div>

                <div>
                    <span>Email</span>
                    <strong>
                        ${escapeHTML(user.email)}
                    </strong>
                </div>

            </div>


            <button
                class="login-button"
                id="continueButton">

                Continue to Dashboard →

            </button>


            <button
                class="secondary-button"
                id="logoutButton">

                Logout

            </button>

        </div>
    `;


    $("#continueButton")
        .addEventListener(
            "click",
            () => {

                window.location.href = "/dashboard";

            }
        );


    $("#logoutButton")
        .addEventListener(
            "click",
            async () => {

                await postJSON(
                    "/api/logout",
                    {}
                );

                location.reload();

            }
        );

}


function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


// =================================================
// CLOSE MODALS
// =================================================

$$("[data-close]")
    .forEach(
        button => {

            button.addEventListener(
                "click",
                () => {

                    const modal =
                        document.getElementById(
                            button.dataset.close
                        );

                    closeModal(modal);

                }
            );

        }
    );


$$(".modal")
    .forEach(
        modal => {

            modal.addEventListener(
                "click",
                event => {

                    if (
                        event.target === modal
                    ) {

                        closeModal(modal);

                    }

                }
            );

        }
    );
    