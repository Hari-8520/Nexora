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
// ======================================================
// COURSE LEARNING PAGE
// ======================================================

document.addEventListener("DOMContentLoaded", () => {

    // --------------------------------------------------
    // DATA STRUCTURES COURSE LESSONS
    // --------------------------------------------------

    const dataStructuresLessons = {

        "Singly Linked List": [

            "Introduction to Linked List in C",

            "Insertion at the Beginning in Singly Linked List",

            "Insertion at a Position in Singly Linked List",

            "Insertion at the End in Singly Linked List",

            "Traversal of a Linked List in Singly Linked List",

            "Deletion at the Beginning in Singly Linked List",

            "Deletion at a Position in Singly Linked List",

            "Deletion at the End in Singly Linked List"

        ],


        "Doubly Linked List": [

            "Insertion at the Beginning in Doubly Linked List",

            "Insertion at a Position in Doubly Linked List",

            "Insertion at the End in Doubly Linked List",

            "Deletion at the Beginning in Doubly Linked List"

        ],


        "Circular Linked List": [

            "Deletion at the End in Circular Linked List",

            "Insertion at the End in Circular Linked List"

        ]

    };


    // --------------------------------------------------
    // FIND DATA STRUCTURES COURSE BUTTON
    // --------------------------------------------------

    const courseButtons =
        document.querySelectorAll(
            ".course-card .course-btn"
        );


    courseButtons.forEach(button => {

        button.addEventListener("click", () => {

            const card =
                button.closest(".course-card");

            if (!card) {
                return;
            }


            const title =
                card.querySelector("h3")
                    ?.textContent
                    .trim();


            if (title === "Data Structures") {

                openDataStructuresCourse();

            }

        });

    });


    // --------------------------------------------------
    // OPEN DATA STRUCTURES COURSE
    // --------------------------------------------------

    function openDataStructuresCourse() {

        const coursePage =
            document.getElementById(
                "courseLearningPage"
            );


        if (coursePage) {

            coursePage.style.display = "block";

            coursePage.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });

            return;
        }


        // ------------------------------------------------
        // CREATE COURSE LEARNING PAGE
        // ------------------------------------------------

        const page =
            document.createElement("section");

        page.id =
            "courseLearningPage";


        page.innerHTML = `

            <div class="course-learning-container">

                <button
                    type="button"
                    class="course-back-button"
                    id="backToCourses"
                >
                    ← Back to Courses
                </button>


                <div class="course-learning-header">

                    <div class="course-learning-label">
                        NEXORA LEARNING LIBRARY
                    </div>

                    <h1>
                        Data Structures
                    </h1>

                    <p>
                        Learn data structures step by step
                        through structured lessons.
                    </p>

                </div>


                <div class="course-progress-box">

                    <div>
                        <strong>
                            Course Progress
                        </strong>

                        <span id="courseProgressText">
                            0%
                        </span>
                    </div>

                    <div class="course-progress-bar">

                        <div
                            id="courseProgressBar"
                            class="course-progress-fill">
                        </div>

                    </div>

                </div>


                <div
                    id="courseLessonList"
                    class="course-lesson-list">
                </div>

            </div>
        `;


        // Add after the main page content
        document.body.appendChild(page);


        // ------------------------------------------------
        // DISPLAY LESSONS
        // ------------------------------------------------

        const lessonList =
            document.getElementById(
                "courseLessonList"
            );


        let lessonNumber = 1;


        Object.entries(
            dataStructuresLessons
        ).forEach(
            ([topic, lessons]) => {


                const topicSection =
                    document.createElement("div");

                topicSection.className =
                    "course-topic-section";


                topicSection.innerHTML = `

                    <div class="course-topic-header">

                        <span class="course-topic-icon">
                            ✦
                        </span>

                        <div>

                            <small>
                                TOPIC
                            </small>

                            <h2>
                                ${topic}
                            </h2>

                        </div>

                    </div>

                    <div
                        class="course-topic-lessons">
                    </div>

                `;


                const lessonContainer =
                    topicSection.querySelector(
                        ".course-topic-lessons"
                    );


                lessons.forEach(
                    lessonTitle => {

                        const lesson =
                            document.createElement("button");

                        lesson.type =
                            "button";

                        lesson.className =
                            "course-lesson-item";


                        lesson.dataset.lessonNumber =
                            lessonNumber;


                        lesson.innerHTML = `

                            <span class="lesson-number">
                                ${lessonNumber}
                            </span>

                            <span class="lesson-info">

                                <strong>
                                    ${lessonTitle}
                                </strong>

                                <small>
                                    Lesson ${lessonNumber}
                                </small>

                            </span>

                            <span class="lesson-arrow">
                                →
                            </span>

                        `;


                        lesson.addEventListener(
                            "click",
                            () => {

                                openLesson(
                                    topic,
                                    lessonTitle,
                                    lessonNumber
                                );

                            }
                        );


                        lessonContainer.appendChild(
                            lesson
                        );


                        lessonNumber++;

                    }
                );


                lessonList.appendChild(
                    topicSection
                );

            }
        );


        // ------------------------------------------------
        // BACK TO COURSES
        // ------------------------------------------------

        document
            .getElementById("backToCourses")
            .addEventListener(
                "click",
                () => {

                    page.style.display =
                        "none";

                    window.scrollTo({
                        top: 0,
                        behavior: "smooth"
                    });

                }
            );


        // ------------------------------------------------
        // OPEN PAGE
        // ------------------------------------------------

        page.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });

    }


    // --------------------------------------------------
    // OPEN INDIVIDUAL LESSON
    // --------------------------------------------------
   function openLesson(topic, lessonTitle, lessonNumber) {

    // Remove previous lesson page
    const oldPage =
        document.getElementById("individualLessonPage");

    if (oldPage) {
        oldPage.remove();
    }

    // =====================================================
    // UNIQUE CONTENT FOR EVERY LESSON
    // =====================================================

    const lessonData = {

        // =================================================
        // SINGLY LINKED LIST
        // =================================================

        "Introduction to Linked List in C": {

            explanation:
                "A singly linked list is a dynamic data structure where each node contains data and a pointer to the next node. The last node points to NULL.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `struct Node {
    int data;
    struct Node *next;
};`

        },


        "Insertion at the Beginning in Singly Linked List": {

            explanation:
                "Insertion at the beginning adds a new node before the current first node. The new node points to the current head, and then head is updated to the new node.",

            diagram: `
                <div class="node">
                    <strong>5</strong>
                    <span>New Head</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `struct Node *newNode;

newNode = malloc(sizeof(struct Node));

newNode->data = 5;
newNode->next = head;

head = newNode;`

        },


        "Insertion at a Position in Singly Linked List": {

            explanation:
                "Insertion at a specific position places a new node between two existing nodes. The previous node is connected to the new node, and the new node points to the next node.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>15</strong>
                    <span>Inserted</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `newNode->data = 15;

newNode->next = current->next;

current->next = newNode;`

        },


        "Insertion at the End in Singly Linked List": {

            explanation:
                "Insertion at the end adds a new node after the current last node. The next pointer of the last node is changed to point to the new node.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>New End</span>
                </div>
            `,

            code: `newNode->data = 30;
newNode->next = NULL;

temp = head;

while(temp->next != NULL)
    temp = temp->next;

temp->next = newNode;`

        },


        "Traversal of a Linked List in Singly Linked List": {

            explanation:
                "Traversal means visiting every node from the head until NULL is reached. A temporary pointer is used to move through each node.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Visit 1</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Visit 2</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>Visit 3</span>
                </div>
            `,

            code: `struct Node *temp = head;

while(temp != NULL) {

    printf("%d ", temp->data);

    temp = temp->next;
}`

        },


        "Deletion at the Beginning in Singly Linked List": {

            explanation:
                "Deletion at the beginning removes the first node. The head is moved to the second node and the old first node is released from memory.",

            diagram: `
                <div class="node">
                    <strong>20</strong>
                    <span>New Head</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `struct Node *temp;

temp = head;

head = head->next;

free(temp);`

        },


        "Deletion at a Position in Singly Linked List": {

            explanation:
                "Deletion at a position removes a node from the middle of the list. The previous node is connected directly to the node after the deleted node.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>40</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `temp = head;

for(int i = 1; i < position - 1; i++)
    temp = temp->next;

deleteNode = temp->next;

temp->next =
    deleteNode->next;

free(deleteNode);`

        },


        "Deletion at the End in Singly Linked List": {

            explanation:
                "Deletion at the end removes the last node. The second-last node is changed so that its next pointer becomes NULL.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>NULL</span>
                </div>
            `,

            code: `temp = head;

while(temp->next->next != NULL)
    temp = temp->next;

free(temp->next);

temp->next = NULL;`

        },


        // =================================================
        // DOUBLY LINKED LIST
        // =================================================

        "Insertion at the Beginning in Doubly Linked List": {

            explanation:
                "A doubly linked list node contains three parts: previous address, data and next address. During insertion at the beginning, the new node becomes the head.",

            diagram: `
                <div class="node">
                    <strong>5</strong>
                    <span>Prev: NULL<br>Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>10</strong>
                    <span>Prev ←<br>Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Prev ←<br>Next: NULL</span>
                </div>
            `,

            code: `struct Node {
    int data;
    struct Node *prev;
    struct Node *next;
};

newNode->data = 5;

newNode->prev = NULL;

newNode->next = head;

head->prev = newNode;

head = newNode;`

        },


        "Insertion at a Position in Doubly Linked List": {

            explanation:
                "Insertion at a position in a doubly linked list requires updating both previous and next pointers. The new node is connected between two existing nodes.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Prev ← / Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>15</strong>
                    <span>Inserted Node</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Prev ← / Next →</span>
                </div>
            `,

            code: `newNode->data = 15;

newNode->prev = current;

newNode->next =
    current->next;

current->next->prev =
    newNode;

current->next =
    newNode;`

        },


        "Insertion at the End in Doubly Linked List": {

            explanation:
                "Insertion at the end adds a new node after the current last node. The new node's previous pointer points to the old last node and its next pointer is NULL.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Prev ← / Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Prev ← / Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>30</strong>
                    <span>Prev ←<br>Next: NULL</span>
                </div>
            `,

            code: `newNode->data = 30;

newNode->next = NULL;

newNode->prev = tail;

tail->next = newNode;

tail = newNode;`

        },


        "Deletion at the Beginning in Doubly Linked List": {

            explanation:
                "Deletion at the beginning removes the first node. The head moves to the next node and the new head's previous pointer becomes NULL.",

            diagram: `
                <div class="node">
                    <strong>20</strong>
                    <span>Prev: NULL<br>Next →</span>
                </div>

                <div class="arrow">⇄</div>

                <div class="node">
                    <strong>30</strong>
                    <span>Prev ←<br>Next: NULL</span>
                </div>
            `,

            code: `temp = head;

head = head->next;

head->prev = NULL;

free(temp);`

        },


        // =================================================
        // CIRCULAR LINKED LIST
        // =================================================

        "Deletion at the End in Circular Linked List": {

            explanation:
                "In a circular linked list, the last node does not point to NULL. It points back to the first node. During deletion at the end, the second-last node is connected to the head.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">↘</div>

                <div class="node">
                    <strong>HEAD</strong>
                    <span>↖ Circular</span>
                </div>
            `,

            code: `temp = head;

while(temp->next->next != head)
    temp = temp->next;

free(temp->next);

temp->next = head;`

        },


        "Insertion at the End in Circular Linked List": {

            explanation:
                "Insertion at the end of a circular linked list adds a new node after the current last node. The new node points back to the head, maintaining the circular connection.",

            diagram: `
                <div class="node">
                    <strong>10</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>20</strong>
                    <span>Next →</span>
                </div>

                <div class="arrow">→</div>

                <div class="node">
                    <strong>30</strong>
                    <span>Next → HEAD</span>
                </div>

                <div class="arrow">↖</div>
            `,

            code: `newNode->data = 30;

temp = head;

while(temp->next != head)
    temp = temp->next;

temp->next = newNode;

newNode->next = head;`

        }

    };


    // =====================================================
    // GET SELECTED LESSON CONTENT
    // =====================================================

    const content =
        lessonData[lessonTitle] || {

            explanation:
                "This lesson explains the selected data structures topic.",

            diagram: `
                <div class="node">
                    <strong>Data</strong>
                    <span>Next →</span>
                </div>
            `,

            code:
                "// Example code will appear here"

        };


    // =====================================================
    // CREATE LESSON PAGE
    // =====================================================

    const page =
        document.createElement("section");

    page.id =
        "individualLessonPage";


    page.innerHTML = `

        <div class="individual-lesson-container">

            <button
                type="button"
                class="course-back-button"
                id="backToLessonList"
            >
                ← Back to Lessons
            </button>


            <div class="lesson-breadcrumb">

                Data Structures /
                ${topic}

            </div>


            <div class="lesson-header">

                <div class="lesson-number-badge">

                    Lesson ${lessonNumber}

                </div>

                <h1>
                    ${lessonTitle}
                </h1>

                <p>
                    ${content.explanation}
                </p>

            </div>


            <div class="lesson-content">


                <!-- EXPLANATION -->

                <div class="lesson-text-card">

                    <h2>
                        ${lessonTitle}
                    </h2>

                    <p>
                        ${content.explanation}
                    </p>

                </div>


                <!-- DIAGRAM -->

                <div class="lesson-diagram-card">

                    <h3>
                        Visual Explanation
                    </h3>

                    <div class="linked-list-diagram">

                        ${content.diagram}

                    </div>

                </div>


                <!-- CODE -->

                <div class="lesson-text-card">

                    <h3>
                        C Program Example
                    </h3>

                    <pre class="lesson-code"><code>${content.code}</code></pre>

                </div>


            </div>


            <div class="lesson-navigation">

                <button
                    type="button"
                    class="lesson-nav-button"
                    id="previousLesson"
                >
                    ← Previous
                </button>


                <button
                    type="button"
                    class="lesson-complete-button"
                    id="markLessonComplete"
                >
                    Mark as Complete ✓
                </button>


                <button
                    type="button"
                    class="lesson-nav-button"
                    id="nextLesson"
                >
                    Next →
                </button>

            </div>

        </div>
    `;


    document.body.appendChild(page);


    // =====================================================
    // BACK BUTTON
    // =====================================================

    document
        .getElementById("backToLessonList")
        .addEventListener(
            "click",
            () => {

                page.remove();

                const coursePage =
                    document.getElementById(
                        "courseLearningPage"
                    );

                if (coursePage) {

                    coursePage.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });

                }

            }
        );


    // =====================================================
    // COMPLETE BUTTON
    // =====================================================

    document
        .getElementById("markLessonComplete")
        .addEventListener(
            "click",
            function () {

                this.textContent =
                    "Completed ✓";

                this.classList.add(
                    "completed"
                );

            }
        );


    // =====================================================
    // PREVIOUS LESSON
    // =====================================================

    document
        .getElementById("previousLesson")
        .addEventListener(
            "click",
            () => {

                const allLessons =
                    Object.values(
                        dataStructuresLessons
                    ).flat();

                if (lessonNumber > 1) {

                    const previousTitle =
                        allLessons[
                            lessonNumber - 2
                        ];

                    let previousTopic = "";

                    for (
                        const [topicName, lessons]
                        of Object.entries(
                            dataStructuresLessons
                        )
                    ) {

                        if (
                            lessons.includes(
                                previousTitle
                            )
                        ) {

                            previousTopic =
                                topicName;

                            break;
                        }

                    }

                    openLesson(
                        previousTopic,
                        previousTitle,
                        lessonNumber - 1
                    );

                }

            }
        );


    // =====================================================
    // NEXT LESSON
    // =====================================================

    document
        .getElementById("nextLesson")
        .addEventListener(
            "click",
            () => {

                const allLessons =
                    Object.values(
                        dataStructuresLessons
                    ).flat();

                if (
                    lessonNumber <
                    allLessons.length
                ) {

                    const nextTitle =
                        allLessons[
                            lessonNumber
                        ];

                    let nextTopic = "";

                    for (
                        const [topicName, lessons]
                        of Object.entries(
                            dataStructuresLessons
                        )
                    ) {

                        if (
                            lessons.includes(
                                nextTitle
                            )
                        ) {

                            nextTopic =
                                topicName;

                            break;
                        }

                    }

                    openLesson(
                        nextTopic,
                        nextTitle,
                        lessonNumber + 1
                    );

                }

            }
        );


    // =====================================================
    // SCROLL TO LESSON
    // =====================================================

    page.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });

}

});
