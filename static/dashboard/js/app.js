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