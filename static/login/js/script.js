const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => document.querySelectorAll(selector);
document.addEventListener("DOMContentLoaded", () => {
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
const loginForm = $("#loginForm");

if (loginForm) {

    loginForm.addEventListener(
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

const createAccountButton =
    $("#createAccountButton");

if (createAccountButton) {

    createAccountButton.addEventListener(
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
}

}
// =================================================
// CREATE ACCOUNT FROM LOGIN
// =================================================

const createFromLogin =
    $("#createFromLogin");

if (createFromLogin) {

    createFromLogin.addEventListener(
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
}

// =================================================
// REGISTRATION
// =================================================
const registrationForm = $("#registrationForm");
if (registrationForm) {
    registrationForm.addEventListener(
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
}

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

}// =================================================
// FORGOT PASSWORD FLOW
// =================================================

let resetEmail = "";


// -------------------------------------------------
// STEP 1: CLICK FORGOT PASSWORD
// -------------------------------------------------

$("#forgotPassword").addEventListener(
    "click",
    () => {

        showForgotPasswordPage();

    }
);


// -------------------------------------------------
// STEP 2: SHOW FORGOT PASSWORD PAGE
// -------------------------------------------------

function showForgotPasswordPage() {

    $(".login-content").innerHTML = `

        <div class="reset-content">

            <button
                type="button"
                class="reset-back-button"
                id="backToLogin"
            >
                ← Back to Login
            </button>

            <div class="small-title">
                PASSWORD RECOVERY
            </div>

            <h1>
                Forgot Password?
            </h1>

            <p class="subtitle">
                Enter your registered Gmail and
                we'll send you a verification OTP.
            </p>

            <div class="input-group">

                <label>
                    Student Gmail
                </label>

                <input
                    type="email"
                    id="resetEmail"
                    placeholder="Enter your Gmail"
                    required
                >

            </div>

            <p
                id="resetMessage"
                class="message">
            </p>

            <button
                type="button"
                class="login-button"
                id="sendResetOTP"
            >
                Send OTP <span>→</span>
            </button>

        </div>
    `;


    // Back to Login
    $("#backToLogin").addEventListener(
        "click",
        () => {

            location.reload();

        }
    );


    // Send OTP
    $("#sendResetOTP").addEventListener(
        "click",
        sendResetOTP
    );

}


// -------------------------------------------------
// STEP 3: SEND OTP
// -------------------------------------------------
async function sendResetOTP() {

    const email =
        $("#resetEmail")
        .value
        .trim()
        .toLowerCase();

    const message =
        $("#resetMessage");

    if (!email) {

        showMessage(
            message,
            "Please enter your Gmail."
        );

        $("#resetEmail").focus();

        return;
    }

    const button =
        $("#sendResetOTP");

    // Show loading state
    button.disabled = true;
    button.innerHTML = "Sending OTP...";

    try {

        const result =
            await postJSON(
                "/api/forgot-password",
                {
                    email: email
                }
            );

        if (!result.ok) {

            showMessage(
                message,
                result.message ||
                "Unable to send OTP."
            );

            // Restore button
            button.disabled = false;
            button.innerHTML =
                'Send OTP <span>→</span>';

            return;
        }

        // OTP successfully sent
        resetEmail = email;

        // Move to OTP verification page
        showOTPResetPage();

    } catch (error) {

        console.error(error);

        showMessage(
            message,
            "Unable to connect to the server."
        );

        // Restore button
        button.disabled = false;
        button.innerHTML =
            'Send OTP <span>→</span>';
    }
}
// -------------------------------------------------
// STEP 4: SHOW OTP PAGE
// -------------------------------------------------

function showOTPResetPage() {

    $(".login-content").innerHTML = `

        <div class="reset-content">

            <button
                type="button"
                class="reset-back-button"
                id="backToForgot"
            >
                ← Back
            </button>

            <div class="small-title">
                VERIFY OTP
            </div>

            <h1>
                Check Your Gmail
            </h1>

            <p class="subtitle">
                We sent a 6-digit verification code to
                <strong class="reset-email">
                    ${escapeHTML(resetEmail)}
                </strong>
            </p>

            <div class="input-group">

                <label>
                    Verification OTP
                </label>

                <input
                    type="text"
                    id="resetOTP"
                    placeholder="Enter 6-digit OTP"
                    maxlength="6"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                >

            </div>

            <p
                id="otpResetMessage"
                class="message">
            </p>

            <button
                type="button"
                class="login-button"
                id="verifyResetOTP"
            >
                Verify OTP <span>→</span>
            </button>

        </div>
    `;


    $("#backToForgot").addEventListener(
        "click",
        showForgotPasswordPage
    );


    $("#verifyResetOTP").addEventListener(
        "click",
        verifyResetOTP
    );


    $("#resetOTP").focus();

}


// -------------------------------------------------
// STEP 5: VERIFY OTP
// -------------------------------------------------

async function verifyResetOTP() {

    const otp =
        $("#resetOTP")
        .value
        .trim();

    const message =
        $("#otpResetMessage");


    if (!/^\d{6}$/.test(otp)) {

        showMessage(
            message,
            "Please enter the complete 6-digit OTP."
        );

        return;
    }


    try {

        const result =
            await postJSON(
                "/api/verify-password-reset-otp",
                {
                    email: resetEmail,
                    otp: otp
                }
            );


        if (!result.ok) {

            showMessage(
                message,
                result.message ||
                "Incorrect OTP."
            );

            return;
        }


        showResetPasswordPage();


    } catch (error) {

        console.error(error);

        showMessage(
            message,
            "Unable to connect to the server."
        );

    }

}


// -------------------------------------------------
// STEP 6: SHOW RESET PASSWORD PAGE
// -------------------------------------------------

function showResetPasswordPage() {

    $(".login-content").innerHTML = `

        <div class="reset-content">

            <div class="small-title">
                NEW PASSWORD
            </div>

            <h1>
                Reset Password
            </h1>

            <p class="subtitle">
                Create a new password for your
                Nexora account.
            </p>


            <div class="input-group">

                <label>
                    New Password
                </label>

                <input
                    type="password"
                    id="newResetPassword"
                    placeholder="Minimum 8 characters"
                >

            </div>


            <div class="input-group">

                <label>
                    Confirm Password
                </label>

                <input
                    type="password"
                    id="confirmResetPassword"
                    placeholder="Confirm your password"
                >

            </div>


            <p
                id="passwordResetMessage"
                class="message">
            </p>


            <button
                type="button"
                class="login-button"
                id="resetPasswordButton"
            >
                Reset Password <span>→</span>
            </button>

        </div>
    `;


    $("#resetPasswordButton")
        .addEventListener(
            "click",
            resetPassword
        );

}


// -------------------------------------------------
// STEP 7: RESET PASSWORD
// -------------------------------------------------

async function resetPassword() {

    const password =
        $("#newResetPassword").value;

    const confirmPassword =
        $("#confirmResetPassword").value;

    const message =
        $("#passwordResetMessage");


    if (password.length < 8) {

        showMessage(
            message,
            "Password must contain at least 8 characters."
        );

        return;
    }


    if (password !== confirmPassword) {

        showMessage(
            message,
            "Passwords do not match."
        );

        return;
    }


    try {

        const result =
            await postJSON(
                "/api/reset-password",
                {
                    password: password,
                    confirm_password: confirmPassword
                }
            );


        if (!result.ok) {

            showMessage(
                message,
                result.message ||
                "Unable to reset password."
            );

            return;
        }


        showMessage(
            message,
            "Password changed successfully!",
            "success"
        );


        setTimeout(
            () => {

                location.reload();

            },
            1500
        );


    } catch (error) {

        console.error(error);

        showMessage(
            message,
            "Unable to connect to the server."
        );

    }

}
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
                to Nexora.
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
// ======================================================
// VIDEO LEARNING
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    const videoButtons = document.querySelectorAll(
        ".video-card .course-btn"
    );

    videoButtons.forEach(button => {

        button.addEventListener("click", function () {

            const card = button.closest(".video-card");

            if (!card) {
                return;
            }

            const videoTitle =
                card.dataset.videoTitle ||
                card.querySelector("h3")?.textContent.trim() ||
                "";

            const videoTopic =
                card.dataset.videoTopic ||
                "";

            openVideoLearning(
                videoTitle,
                videoTopic
            );

        });

    });

});


// ======================================================
// VIDEO LEARNING DATA
// ======================================================

function openVideoLearning(title, topic) {

    const videoData = {

        "Understanding Linked Lists": {

            reference: "nptel_linked_list",

            subtopics: [

                {
                    title: "Introduction to Linked List in C",
                    videoUrl: ""
                },

                {
                    title: "Insertion at the Beginning in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Insertion at a Position in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Insertion at the End in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Traversal of a Linked List in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Deletion at the Beginning in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Deletion at a Position in Singly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Deletion at the End in Singly Linked List",
                    videoUrl: ""
                }

            ]

        },


        "Understanding Doubly Linked List": {

            reference: "nptel_doubly_linked_list",

            subtopics: [

                {
                    title: "Insertion at the Beginning in Doubly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Insertion at a Position in Doubly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Insertion at the End in Doubly Linked List",
                    videoUrl: ""
                },

                {
                    title: "Deletion at the Beginning in Doubly Linked List",
                    videoUrl: ""
                }

            ]

        },


        "Circular Linked List": {

            reference: null,

            subtopics: [

                {
                    title: "Deletion at the End in Circular Linked List",
                    videoUrl: ""
                },

                {
                    title: "Insertion at the End in Circular Linked List",
                    videoUrl: ""
                }

            ]

        }

    };


    const selectedVideo =
        videoData[title];


    if (!selectedVideo) {

        console.error(
            "Video data not found:",
            title
        );

        return;

    }


    window.currentVideoLearning = {

        title: title,

        topic: topic,

        reference:
            selectedVideo.reference,

        subtopics:
            selectedVideo.subtopics

    };


    console.log(
        "Selected video:",
        window.currentVideoLearning
    );


    // ==================================================
    // OPEN EXISTING VIDEO LEARNING SECTION
    // ==================================================

    const videoSection =
        document.getElementById(
            "videoLearningSection"
        );


    if (videoSection) {

        videoSection.classList.add("active");

        videoSection.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }


    // ==================================================
    // OPEN EXISTING VIDEO MODAL
    // ==================================================

    const videoModal =
        document.getElementById(
            "videoLearningModal"
        );


    if (videoModal) {

        videoModal.classList.add("active");

    }


    // ==================================================
    // UPDATE EXISTING TITLE
    // ==================================================

    const titleElement =
        document.getElementById(
            "videoLearningTitle"
        );


    if (titleElement) {

        titleElement.textContent =
            title;

    }


    // ==================================================
    // UPDATE EXISTING TOPIC
    // ==================================================

    const topicElement =
        document.getElementById(
            "videoLearningTopic"
        );


    if (topicElement) {

        topicElement.textContent =
            topic;

    }


    // ==================================================
    // NPTEL REFERENCE
    // ==================================================

    const referenceElement =
        document.getElementById(
            "videoReference"
        );


    if (referenceElement) {

        referenceElement.dataset.reference =
            selectedVideo.reference || "";

    }


    // ==================================================
    // SUBTOPICS
    // ==================================================

    const subtopicContainer =
        document.getElementById(
            "videoSubtopics"
        );


    if (subtopicContainer) {

        subtopicContainer.innerHTML = "";

        selectedVideo.subtopics.forEach(
            (subtopic, index) => {

                const item =
                    document.createElement("div");

                item.className =
                    "video-subtopic";

                item.innerHTML = `

                    <span>
                        ${index + 1}.
                        ${subtopic.title}
                    </span>

                    <button
                        class="course-btn"
                        type="button"
                        data-video-url="${subtopic.videoUrl}"
                    >
                        Watch Video →
                    </button>

                `;

                subtopicContainer.appendChild(
                    item
                );

            }
        );

    }

}



    function startSimulation(type) {
    console.log("Starting simulation:", type);

    if (type === "coding") {
        window.location.href = "/simulation/coding";
    }

    else if (type === "data-structures") {
        window.location.href = "/simulation/data-structures";
    }

    else if (type === "ai-learning") {
        window.location.href = "/simulation/ai-learning";
    }
}
// =================================================
// EDIT PROFILE
// =================================================

const editProfileButton =
    document.getElementById("editProfileButton");

const editProfilePanel =
    document.getElementById("editProfilePanel");

const cancelEditProfile =
    document.getElementById("cancelEditProfile");


if (editProfileButton && editProfilePanel) {

    editProfileButton.addEventListener(
        "click",
        () => {

            editProfilePanel.style.display = "block";

            editProfilePanel.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

        }
    );

}


if (cancelEditProfile && editProfilePanel) {

    cancelEditProfile.addEventListener(
        "click",
        () => {

            editProfilePanel.style.display = "none";

        }
    );

}
// =================================================
// PROFILE PICTURE PREVIEW
// =================================================

const profilePictureInput =
    document.getElementById("profilePictureInput");

const profileAvatarPreview =
    document.getElementById("profileAvatarPreview");


if (profilePictureInput && profileAvatarPreview) {

    profilePictureInput.addEventListener(
        "change",
        (event) => {

            const file =
                event.target.files[0];

            if (!file) {
                return;
            }

            if (!file.type.startsWith("image/")) {

                alert("Please select an image file.");

                return;
            }

            const reader =
                new FileReader();

            reader.onload = (e) => {

                profileAvatarPreview.style.backgroundImage =
                    `url("${e.target.result}")`;

                profileAvatarPreview.style.backgroundSize =
                    "cover";

                profileAvatarPreview.style.backgroundPosition =
                    "center";

                profileAvatarPreview.style.backgroundRepeat =
                    "no-repeat";

                profileAvatarPreview.textContent = "";

            };

            reader.readAsDataURL(file);

        }
    );
}
});
// =================================================
// EDIT PROFILE
// =================================================

document.addEventListener("DOMContentLoaded", () => {

    const editProfileButton =
        document.getElementById("editProfileButton");

    const editProfilePanel =
        document.getElementById("editProfilePanel");

    const cancelEditProfile =
        document.getElementById("cancelEditProfile");


    // OPEN EDIT PROFILE
    if (editProfileButton && editProfilePanel) {

        editProfileButton.addEventListener(
            "click",
            () => {

                editProfilePanel.style.display = "block";

                editProfilePanel.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });

            }
        );

    }


    // CANCEL EDIT PROFILE
    if (cancelEditProfile && editProfilePanel) {

        cancelEditProfile.addEventListener(
            "click",
            () => {

                editProfilePanel.style.display = "none";

            }
        );

    }

});