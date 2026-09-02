// ======================================================
// NEXORA - MAIN JAVASCRIPT
// ======================================================


// ======================================================
// PROFILE DROPDOWN
// ======================================================

const profileButton = document.getElementById("profileButton");
const profileMenu = document.getElementById("profileMenu");

if (profileButton && profileMenu) {

    profileButton.addEventListener("click", function (event) {

        event.stopPropagation();

        profileMenu.classList.toggle("show");

    });

    document.addEventListener("click", function () {

        profileMenu.classList.remove("show");

    });
}


// ======================================================
// GITHUB-STYLE LEARNING ACTIVITY HEATMAP
// ======================================================

function createHeatmap() {

    const heatmap = document.getElementById("heatmap");
    const monthLabels = document.getElementById("monthLabels");

    if (!heatmap || !monthLabels) {
        return;
    }

    // Clear old content
    heatmap.innerHTML = "";
    monthLabels.innerHTML = "";


    // --------------------------------------------------
    // TODAY
    // --------------------------------------------------

    const today = new Date();

    today.setHours(0, 0, 0, 0);


    // --------------------------------------------------
    // START DATE
    // Approximately one year ago
    // --------------------------------------------------

    const startDate = new Date(today);

    startDate.setFullYear(
        today.getFullYear() - 1
    );


    // Move to Sunday
    // GitHub-style week starts on Sunday

    startDate.setDate(
        startDate.getDate() - startDate.getDay()
    );


    // --------------------------------------------------
    // TOTAL WEEKS
    // --------------------------------------------------

    const totalWeeks = 53;

    const totalDays = totalWeeks * 7;


    // --------------------------------------------------
    // CREATE MONTH LABELS
    // --------------------------------------------------

    const firstMonth = new Date(
        today.getFullYear(),
        today.getMonth() - 11,
        1
    );

    for (let i = 0; i < 12; i++) {

        const monthDate = new Date(
            firstMonth.getFullYear(),
            firstMonth.getMonth() + i,
            1
        );


        // Calculate which week contains
        // the first day of this month

        const difference =
            monthDate.getTime() -
            startDate.getTime();

        const weekIndex =
            Math.floor(
                difference /
                (7 * 24 * 60 * 60 * 1000)
            );


        if (
            weekIndex >= 0 &&
            weekIndex < totalWeeks
        ) {

            const label =
                document.createElement("span");

            label.textContent =
                monthDate.toLocaleString(
                    "en-US",
                    {
                        month: "short"
                    }
                );

            // Position label according
            // to actual calendar week

            label.style.gridColumn =
                `${weekIndex + 1}`;


            monthLabels.appendChild(label);
        }
    }


    // --------------------------------------------------
    // CREATE 53 WEEKS × 7 DAYS
    // --------------------------------------------------

    for (let week = 0; week < totalWeeks; week++) {

        for (let day = 0; day < 7; day++) {

            const currentDate = new Date(
                startDate
            );

            currentDate.setDate(
                startDate.getDate() +
                (week * 7) +
                day
            );


            // Create square

            const square =
                document.createElement("div");

            square.classList.add("heat");


            // --------------------------------------------------
            // DON'T SHOW FUTURE DATES
            // --------------------------------------------------

            if (currentDate > today) {

                square.classList.add(
                    "future"
                );

            } else {

                // --------------------------------------------------
                // ACTIVITY LEVEL
                // 0 = no activity
                // 1 = low
                // 2 = medium
                // 3 = high
                // 4 = very high
                // --------------------------------------------------

                const activity =
                    Math.floor(
                        Math.random() * 5
                    );


                if (activity > 0) {

                    square.classList.add(
                        `l${activity}`
                    );

                }


                // --------------------------------------------------
                // TOOLTIP
                // --------------------------------------------------

                square.title =
                    currentDate.toLocaleDateString(
                        "en-IN",
                        {
                            weekday: "short",
                            day: "numeric",
                            month: "short",
                            year: "numeric"
                        }
                    )
                    +
                    " • "
                    +
                    activity
                    +
                    " learning activities";
            }


            // Add square

            heatmap.appendChild(square);
        }
    }
}


// Run heatmap after page loads

document.addEventListener(
    "DOMContentLoaded",
    function () {

        createHeatmap();

        updateGreeting();

    }
);


// ======================================================
// CHATBOT
// ======================================================

function appendMessage(text, type) {

    const chatBody =
        document.getElementById("chatBody");

    if (!chatBody) {
        return;
    }


    const message =
        document.createElement("div");


    message.classList.add(
        "message"
    );


    if (type === "user") {

        message.classList.add(
            "user-message"
        );

    } else {

        message.classList.add(
            "ai-message"
        );

    }


    message.innerText = text;


    chatBody.appendChild(
        message
    );


    chatBody.scrollTop =
        chatBody.scrollHeight;
}


// ======================================================
// AI RESPONSE
// ======================================================

async function aiReply(text) {

    try {

        const response = await fetch("/api/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: text
            })
        });

        const data = await response.json();

        if (!response.ok || !data.ok) {
            appendMessage(
                data.message || "Something went wrong.",
                "ai"
            );
            return;
        }

        appendMessage(
            data.response,
            "ai"
        );

    } catch (error) {

        console.error("Chatbot error:", error);

        appendMessage(
            "I couldn't connect to NEXORA AI. Please try again.",
            "ai"
        );
    }
}


// ======================================================
// SEND MESSAGE
// ======================================================

function sendMessage() {

    const input =
        document.getElementById("chatInput");


    if (!input) {
        return;
    }


    const text =
        input.value.trim();


    if (!text) {
        return;
    }


    appendMessage(
        text,
        "user"
    );


    input.value = "";


    aiReply(text);
}


// ======================================================
// CHAT SUGGESTIONS
// ======================================================

function sendSuggestion(text) {

    const input =
        document.getElementById("chatInput");


    if (!input) {
        return;
    }


    input.value = text;


    sendMessage();
}


// ======================================================
// ENTER KEY FOR CHAT
// ======================================================

document.addEventListener(
    "keydown",
    function (event) {

        if (
            event.key === "Enter" &&
            document.activeElement &&
            document.activeElement.id ===
                "chatInput"
        ) {

            event.preventDefault();

            sendMessage();

        }

    }
);


// ======================================================
// DYNAMIC GREETING
// ======================================================

function updateGreeting() {

    const greeting =
        document.getElementById("greeting");


    if (!greeting) {
        return;
    }


    const hour =
        new Date().getHours();


    if (
        hour >= 5 &&
        hour < 12
    ) {

        greeting.textContent =
            "Stay Curious";

    }


    else if (
        hour >= 12 &&
        hour < 17
    ) {

        greeting.textContent =
            "Keep Learning";

    }


    else if (
        hour >= 17 &&
        hour < 21
    ) {

        greeting.textContent =
            "Stay Focused";

    }


    else {

        greeting.textContent =
            "Dream Big";

    }
}


// Update greeting every minute

setInterval(
    updateGreeting,
    60000
);
// ======================================================
// EDIT PROFILE
// ======================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const editProfileButton =
            document.getElementById(
                "editProfileButton"
            );

        const editProfilePanel =
            document.getElementById(
                "editProfilePanel"
            );

        const cancelEditProfile =
            document.getElementById(
                "cancelEditProfile"
            );

        const saveProfileButton =
            document.getElementById(
                "saveProfileButton"
            );

        const editFullName =
            document.getElementById(
                "editFullName"
            );

        const editStudentId =
            document.getElementById(
                "editStudentId"
            );

        const editYear =
            document.getElementById(
                "editYear"
            );

        const editEmail =
            document.getElementById(
                "editEmail"
            );

        const editProfileMessage =
            document.getElementById(
                "editProfileMessage"
            );

        const profilePictureInput =
            document.getElementById(
                "profilePictureInput"
            );

        const profileAvatarPreview =
            document.getElementById(
                "profileAvatarPreview"
            );


        // ==================================================
        // OPEN EDIT PROFILE
        // ==================================================

        if (
            editProfileButton &&
            editProfilePanel
        ) {

            editProfileButton.addEventListener(
                "click",
                function () {

                    editProfilePanel.style.display =
                        "block";

                    editProfilePanel.scrollIntoView({
                        behavior: "smooth",
                        block: "start"
                    });

                }
            );

        }


        // ==================================================
        // CANCEL
        // ==================================================

        if (
            cancelEditProfile &&
            editProfilePanel
        ) {

            cancelEditProfile.addEventListener(
                "click",
                function () {

                    editProfilePanel.style.display =
                        "none";

                }
            );

        }


        // ==================================================
        // PROFILE PICTURE PREVIEW
        // ==================================================

        if (
            profilePictureInput &&
            profileAvatarPreview
        ) {

            profilePictureInput.addEventListener(
                "change",
                function (event) {

                    const file =
                        event.target.files[0];

                    if (!file) {
                        return;
                    }


                    if (
                        !file.type.startsWith(
                            "image/"
                        )
                    ) {

                        alert(
                            "Please select an image."
                        );

                        profilePictureInput.value =
                            "";

                        return;
                    }


                    const reader =
                        new FileReader();


                    reader.onload =
                        function (e) {

                            profileAvatarPreview.style.backgroundImage =
                                `url("${e.target.result}")`;

                            profileAvatarPreview.style.backgroundSize =
                                "cover";

                            profileAvatarPreview.style.backgroundPosition =
                                "center";

                            profileAvatarPreview.style.backgroundRepeat =
                                "no-repeat";

                            profileAvatarPreview.textContent =
                                "";

                        };


                    reader.readAsDataURL(file);

                }
            );

        }


        // ==================================================
        // SAVE PROFILE
        // ==================================================

        if (saveProfileButton) {

            saveProfileButton.addEventListener(
                "click",
                async function () {

                    const fullName =
                        editFullName.value.trim();

                    const studentId =
                        editStudentId.value.trim();

                    const year =
                        editYear.value;

                    const email =
                        editEmail.value
                            .trim()
                            .toLowerCase();


                    // --------------------------------------
                    // VALIDATION
                    // --------------------------------------

                    if (
                        !fullName ||
                        !studentId ||
                        !year ||
                        !email
                    ) {

                        editProfileMessage.textContent =
                            "Please fill in all fields.";

                        editProfileMessage.style.color =
                            "#dc3545";

                        return;
                    }


                    saveProfileButton.disabled =
                        true;

                    saveProfileButton.textContent =
                        "Saving...";


                    let profilePicture =
                        null;


                    // --------------------------------------
                    // CONVERT IMAGE TO BASE64
                    // --------------------------------------

                    if (
                        profilePictureInput &&
                        profilePictureInput.files.length > 0
                    ) {

                        const file =
                            profilePictureInput.files[0];


                        profilePicture =
                            await new Promise(
                                function (
                                    resolve,
                                    reject
                                ) {

                                    const reader =
                                        new FileReader();


                                    reader.onload =
                                        function () {

                                            resolve(
                                                reader.result
                                            );

                                        };


                                    reader.onerror =
                                        reject;


                                    reader.readAsDataURL(
                                        file
                                    );

                                }
                            );

                    }


                    // --------------------------------------
                    // SEND DATA TO FLASK
                    // --------------------------------------

                    try {

                        const response =
                            await fetch(
                                "/api/profile/update",
                                {
                                    method: "POST",

                                    headers: {
                                        "Content-Type":
                                            "application/json"
                                    },

                                    body: JSON.stringify({

                                        full_name:
                                            fullName,

                                        student_id:
                                            studentId,

                                        year:
                                            year,

                                        email:
                                            email,

                                        profile_picture:
                                            profilePicture

                                    })

                                }
                            );


                        const result =
                            await response.json();


                        if (!response.ok) {

                            throw new Error(
                                result.message ||
                                "Profile update failed."
                            );

                        }


                        // ----------------------------------
                        // SUCCESS
                        // ----------------------------------

                        editProfileMessage.textContent =
                            "Profile updated successfully.";

                        editProfileMessage.style.color =
                            "#35a95f";


                        // ----------------------------------
                        // UPDATE NAME
                        // ----------------------------------

                        const profileName =
                            document.querySelector(
                                ".profile-title h1"
                            );

                        if (profileName) {

                            profileName.textContent =
                                fullName;

                        }


                        // ----------------------------------
                        // UPDATE EMAIL
                        // ----------------------------------

                        const profileEmail =
                            document.querySelector(
                                ".profile-title p"
                            );

                        if (profileEmail) {

                            profileEmail.textContent =
                                email;

                        }


                        // ----------------------------------
                        // UPDATE PROFILE AVATAR
                        // ----------------------------------

                        if (profilePicture) {

                            const largeAvatar =
                                document.querySelector(
                                    ".profile-avatar-large"
                                );

                            if (largeAvatar) {

                                largeAvatar.style.backgroundImage =
                                    `url("${profilePicture}")`;

                                largeAvatar.style.backgroundSize =
                                    "cover";

                                largeAvatar.style.backgroundPosition =
                                    "center";

                                largeAvatar.style.backgroundRepeat =
                                    "no-repeat";

                                largeAvatar.textContent =
                                    "";

                            }


                            const topAvatar =
                                document.querySelector(
                                    ".avatar"
                                );

                            if (topAvatar) {

                                topAvatar.style.backgroundImage =
                                    `url("${profilePicture}")`;

                                topAvatar.style.backgroundSize =
                                    "cover";

                                topAvatar.style.backgroundPosition =
                                    "center";

                                topAvatar.style.backgroundRepeat =
                                    "no-repeat";

                                topAvatar.textContent =
                                    "";

                            }

                        }


                        // ----------------------------------
                        // UPDATE STUDENT ID + YEAR
                        // ----------------------------------

                        const infoBoxes =
                            document.querySelectorAll(
                                ".info-grid .info-box strong"
                            );


                        if (
                            infoBoxes.length >= 2
                        ) {

                            infoBoxes[0].textContent =
                                studentId;

                            infoBoxes[1].textContent =
                                year;

                        }


                        // ----------------------------------
                        // CLOSE PANEL
                        // ----------------------------------

                        setTimeout(
                            function () {

                                editProfilePanel.style.display =
                                    "none";

                            },
                            1000
                        );


                    } catch (error) {

                        console.error(
                            "Profile update error:",
                            error
                        );


                        editProfileMessage.textContent =
                            error.message ||
                            "Could not update profile.";

                        editProfileMessage.style.color =
                            "#dc3545";


                    } finally {

                        saveProfileButton.disabled =
                            false;

                        saveProfileButton.textContent =
                            "Save Changes →";

                    }

                }
            );

        }

    }
);