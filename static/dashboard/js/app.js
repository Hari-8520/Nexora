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
// =================================================
// VIDEO LEARNING
// =================================================

document.addEventListener("DOMContentLoaded", () => {

    const videoButtons = document.querySelectorAll(
        ".video-card .course-btn"
    );

    videoButtons.forEach(button => {

        button.addEventListener("click", () => {

            const card = button.closest(".video-card");

            if (!card) {
                return;
            }

            const videoTitle =
                card.dataset.videoTitle || "";

            const videoTopic =
                card.dataset.videoTopic || "";

            // Send the selected video card information
            // to the video learning section.
            openVideoLearning(
                videoTitle,
                videoTopic
            );

        });

    });

});


// =================================================
// OPEN VIDEO LEARNING
// =================================================

function openVideoLearning(title, topic) {

    /*
     * The actual video URLs will be added later.
     *
     * Do NOT add invented URLs here.
     */

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
        return;
    }


    /*
     * Store the selected data so the existing
     * video/reference UI can use it.
     */
    window.currentVideoLearning = {
        title: title,
        topic: topic,
        reference: selectedVideo.reference,
        subtopics: selectedVideo.subtopics
    };


    /*
     * If your project already has a video modal/
     * reference system, call it here.
     *
     * Example:
     *
     * openVideoModal(
     *     window.currentVideoLearning
     * );
     *
     * Do NOT add a new UI here if your project
     * already has one.
     */


    console.log(
        "Selected video:",
        window.currentVideoLearning
    );

}
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


// ======================================================
// NEXORA - QUIZ / MCQ SYSTEM
// ------------------------------------------------------
// Connects the existing frontend to:
//   GET  /api/quiz/<course>
//   POST /api/quiz/submit
//   GET  /api/quiz/result/<course>
// ======================================================

(function () {
    "use strict";

    const QUIZ_LENGTH = 15;

    function getQuizCourse() {
        const params = new URLSearchParams(window.location.search);
        return (
            params.get("course") ||
            document.body.dataset.quizCourse ||
            "data-structures"
        );
    }

    function quizElements() {
        return {
            container: document.getElementById("quizContainer"),
            form: document.getElementById("quizForm"),
            question: document.getElementById("quizQuestion"),
            questionNumber: document.getElementById("quizQuestionNumber"),
            options: document.getElementById("quizOptions"),
            progress: document.getElementById("quizProgress"),
            progressText: document.getElementById("quizProgressText"),
            previous: document.getElementById("quizPrevious"),
            next: document.getElementById("quizNext"),
            submit: document.getElementById("quizSubmit"),
            result: document.getElementById("quizResult"),
            score: document.getElementById("quizScore"),
            resultMessage: document.getElementById("quizResultMessage"),
            error: document.getElementById("quizError")
        };
    }

    let quizState = {
        course: "",
        questions: [],
        current: 0,
        answers: {}
    };

    function showQuizError(message) {
        const el = quizElements().error;

        if (!el) {
            alert(message);
            return;
        }

        el.textContent = message;
        el.style.display = "block";
    }

    function clearQuizError() {
        const el = quizElements().error;

        if (el) {
            el.textContent = "";
            el.style.display = "none";
        }
    }

    function renderQuestion() {
        const el = quizElements();
        const item = quizState.questions[quizState.current];

        if (!item || !el.question || !el.options) {
            return;
        }

        clearQuizError();

        const number = quizState.current + 1;

        if (el.questionNumber) {
            el.questionNumber.textContent =
                `Question ${number} of ${QUIZ_LENGTH}`;
        }

        el.question.textContent = item.question;

        el.options.innerHTML = "";

        item.options.forEach((option, index) => {
            const wrapper = document.createElement("div");
            wrapper.className = "quiz-option";

            const input = document.createElement("input");
            input.type = "radio";
            input.name = `question-${item.id}`;
            input.id = `quiz-option-${item.id}-${index}`;
            input.value = String(index);

            if (quizState.answers[item.id] === index) {
                input.checked = true;
            }

            const label = document.createElement("label");
            label.htmlFor = input.id;
            label.textContent = option;

            input.addEventListener("change", function () {
                quizState.answers[item.id] = index;
                clearQuizError();
            });

            wrapper.appendChild(input);
            wrapper.appendChild(label);
            el.options.appendChild(wrapper);
        });

        updateQuizProgress();
        updateQuizButtons();
    }

    function updateQuizProgress() {
        const el = quizElements();
        const completed = Object.keys(quizState.answers).length;
        const currentNumber = quizState.current + 1;
        const percentage =
            Math.round((currentNumber / QUIZ_LENGTH) * 100);

        if (el.progress) {
            el.progress.style.setProperty(
                "--progress",
                `${percentage}%`
            );
            el.progress.style.width = `${percentage}%`;
        }

        if (el.progressText) {
            el.progressText.textContent =
                `${currentNumber} / ${QUIZ_LENGTH}`;
        }
    }

    function updateQuizButtons() {
        const el = quizElements();
        const isFirst = quizState.current === 0;
        const isLast =
            quizState.current === quizState.questions.length - 1;

        if (el.previous) {
            el.previous.style.display =
                isFirst ? "none" : "inline-flex";
        }

        if (el.next) {
            el.next.style.display =
                isLast ? "none" : "inline-flex";
        }

        if (el.submit) {
            el.submit.style.display =
                isLast ? "inline-flex" : "none";
        }
    }

    function currentAnswerSelected() {
        const item = quizState.questions[quizState.current];

        if (!item) {
            return false;
        }

        return Object.prototype.hasOwnProperty.call(
            quizState.answers,
            item.id
        );
    }

    async function loadQuiz() {
        const el = quizElements();

        if (!el.container && !el.form) {
            return;
        }

        quizState.course = getQuizCourse();

        try {
            const response = await fetch(
                `/api/quiz/${encodeURIComponent(quizState.course)}`
            );

            const data = await response.json();

            if (!response.ok || !data.ok) {
                throw new Error(
                    data.message || "Unable to load the quiz."
                );
            }

            if (
                !Array.isArray(data.questions) ||
                data.questions.length !== QUIZ_LENGTH
            ) {
                throw new Error(
                    `Quiz must contain exactly ${QUIZ_LENGTH} questions.`
                );
            }

            quizState.questions = data.questions;
            quizState.current = 0;
            quizState.answers = {};

            if (el.result) {
                el.result.style.display = "none";
            }

            if (el.form) {
                el.form.style.display = "";
            }

            renderQuestion();

        } catch (error) {
            console.error("Quiz loading error:", error);
            showQuizError(
                error.message || "Could not load the quiz."
            );
        }
    }

    async function submitQuiz() {
        const el = quizElements();

        if (Object.keys(quizState.answers).length !== QUIZ_LENGTH) {
            showQuizError(
                "Please answer all 15 questions before submitting."
            );
            return;
        }

        if (el.submit) {
            el.submit.disabled = true;
            el.submit.textContent = "Submitting...";
        }

        clearQuizError();

        try {
            const response = await fetch("/api/quiz/submit", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    course: quizState.course,
                    answers: quizState.answers
                })
            });

            const data = await response.json();

            if (!response.ok || !data.ok) {
                throw new Error(
                    data.message || "Quiz submission failed."
                );
            }

            showQuizResult(data);

        } catch (error) {
            console.error("Quiz submission error:", error);
            showQuizError(
                error.message || "Could not submit the quiz."
            );

        } finally {
            if (el.submit) {
                el.submit.disabled = false;
                el.submit.textContent = "Submit Answer ✓";
            }
        }
    }

    function showQuizResult(data) {
        const el = quizElements();

        if (el.form) {
            el.form.style.display = "none";
        }

        if (el.result) {
            el.result.style.display = "block";
        }

        if (el.score) {
            const score =
                Number.isFinite(Number(data.score))
                    ? data.score
                    : 0;

            const total =
                Number.isFinite(Number(data.total))
                    ? data.total
                    : QUIZ_LENGTH;

            el.score.textContent = `${score} / ${total}`;
        }

        if (el.resultMessage) {
            const percentage = Number(data.percentage || 0);

            el.resultMessage.textContent =
                percentage >= 60
                    ? "Quiz completed successfully. The course is now unlocked."
                    : "Quiz completed. Review the topic and try again.";
        }

        const checkButton =
            document.getElementById("quizCheckAnswer");

        const answerReview =
            document.getElementById("quizAnswerReview");

        if (checkButton) {
            checkButton.style.display = "inline-flex";

            const freshButton = checkButton.cloneNode(true);

            checkButton.parentNode.replaceChild(
                freshButton,
                checkButton
            );

            freshButton.addEventListener(
                "click",
                function () {
                    showAllQuizAnswers(
                        data.correct_answers || {}
                    );
                }
            );
        }

        if (answerReview) {
            answerReview.style.display = "none";
            answerReview.innerHTML = "";
        }

        window.dispatchEvent(
            new CustomEvent("nexoraQuizCompleted", {
                detail: data
            })
        );
    }


    // ======================================================
    // SHOW ALL 15 ANSWERS
    // ======================================================

    function showAllQuizAnswers(correctAnswers) {
        const review =
            document.getElementById("quizAnswerReview");

        const checkButton =
            document.getElementById("quizCheckAnswer");

        if (!review || quizState.questions.length !== QUIZ_LENGTH) {
            return;
        }

        review.innerHTML = "";
        review.style.display = "grid";

        quizState.questions.forEach(
            function (item, questionIndex) {

                const card =
                    document.createElement("div");

                card.className = "quiz-answer-card";

                const heading =
                    document.createElement("div");

                heading.className = "quiz-answer-number";
                heading.textContent =
                    `Question ${questionIndex + 1} of ${QUIZ_LENGTH}`;

                const question =
                    document.createElement("h3");

                question.className = "quiz-answer-question";
                question.textContent = item.question;

                const options =
                    document.createElement("div");

                options.className = "quiz-answer-options";

                const correctIndex =
                    Number(correctAnswers[String(item.id)]);

                const selectedValue =
                    quizState.answers[item.id];

                const selectedIndex =
                    selectedValue === undefined
                        ? -1
                        : Number(selectedValue);

                item.options.forEach(
                    function (option, optionIndex) {

                        const optionBox =
                            document.createElement("div");

                        optionBox.className =
                            "quiz-answer-option";

                        optionBox.textContent = option;

                        if (optionIndex === correctIndex) {
                            optionBox.classList.add(
                                "quiz-correct-answer"
                            );

                            optionBox.textContent =
                                "✓ Correct answer: " + option;
                        }

                        if (
                            optionIndex === selectedIndex &&
                            optionIndex !== correctIndex
                        ) {
                            optionBox.classList.add(
                                "quiz-answer-wrong"
                            );

                            optionBox.textContent =
                                "✗ Your answer: " + option;
                        }

                        if (
                            optionIndex === selectedIndex &&
                            optionIndex === correctIndex
                        ) {
                            optionBox.classList.add(
                                "quiz-answer-correct"
                            );
                        }

                        options.appendChild(optionBox);
                    }
                );

                const result =
                    document.createElement("p");

                result.className =
                    selectedIndex === correctIndex
                        ? "quiz-answer-correct"
                        : "quiz-answer-wrong";

                result.textContent =
                    selectedIndex === correctIndex
                        ? "Your answer is correct."
                        : "Your answer is incorrect.";

                card.appendChild(heading);
                card.appendChild(question);
                card.appendChild(options);
                card.appendChild(result);

                review.appendChild(card);
            }
        );

        if (checkButton) {
            checkButton.style.display = "none";
        }

        review.scrollIntoView({
            behavior: "smooth",
            block: "start"
        });
    }


    function changeQuestion(direction) {
        if (!currentAnswerSelected()) {
            showQuizError(
                "Please select an answer before continuing."
            );
            return;
        }

        const nextIndex =
            quizState.current + direction;

        if (
            nextIndex < 0 ||
            nextIndex >= quizState.questions.length
        ) {
            return;
        }

        quizState.current = nextIndex;
        renderQuestion();
    }

    function setupQuiz() {
        const el = quizElements();

        if (!el.container && !el.form) {
            return;
        }

        if (el.previous) {
            el.previous.addEventListener(
                "click",
                function () {
                    changeQuestion(-1);
                }
            );
        }

        if (el.next) {
            el.next.addEventListener(
                "click",
                function () {
                    changeQuestion(1);
                }
            );
        }

        if (el.submit) {
            el.submit.addEventListener(
                "click",
                function (event) {
                    event.preventDefault();
                    submitQuiz();
                }
            );
        }

        if (el.form) {
            el.form.addEventListener(
                "submit",
                function (event) {
                    event.preventDefault();
                    submitQuiz();
                }
            );
        }

        loadQuiz();
    }

    // ------------------------------------------------------
    // COURSE QUIZ STATUS / LOCKED CARDS
    // ------------------------------------------------------

    async function updateCourseQuizStatus() {
        const cards =
            document.querySelectorAll(
                "[data-quiz-course]"
            );

        if (!cards.length) {
            return;
        }

        for (const card of cards) {
            const course =
                card.dataset.quizCourse;

            if (!course) {
                continue;
            }

            try {
                const response = await fetch(
                    `/api/quiz/result/${encodeURIComponent(course)}`
                );

                const data = await response.json();

                const completed =
                    response.ok &&
                    data.ok &&
                    data.completed === true;

                card.classList.toggle(
                    "quiz-lock",
                    !completed
                );

                card.classList.toggle(
                    "locked",
                    !completed
                );

                const button =
                    card.querySelector(".course-btn");

                if (button) {
                    button.disabled = false;

                    if (completed) {
                        button.textContent =
                            "Continue Course";
                    } else {
                        button.textContent =
                            "Take Quiz to Unlock";
                    }
                }
            } catch (error) {
                console.error(
                    "Quiz status error:",
                    error
                );
            }
        }
    }

    document.addEventListener(
        "DOMContentLoaded",
        function () {
            setupQuiz();
            updateCourseQuizStatus();
        }
    );

})();
