console.log("Latvian Email Security: scanner started");

const API_URL = "http://127.0.0.1:5000/analyze";

const analysisCache = new Map();

function getEmailId(row) {
    const attributes = [
        "data-legacy-thread-id",
        "data-thread-id",
        "data-legacy-message-id"
    ];

    for (const attribute of attributes) {
        const value = row.getAttribute(attribute);
        if (value) return attribute + ":" + value;
    }

    const elementWithId = row.querySelector(
        "[data-legacy-thread-id], " +
        "[data-thread-id], " +
        "[data-legacy-message-id]"
    );

    if (elementWithId) {
        for (const attribute of attributes) {
            const value = elementWithId.getAttribute(attribute);
            if (value) return attribute + ":" + value;
        }
    }

    return "text:" + row.innerText.replace(/\s+/g, " ").trim();
}


// Izveido īsu un saprotamu paskaidrojumu.
function createTooltip(reasons, category) {
    const tooltip = document.createElement("div");

    const titles = {
        phishing: "⚠️ Iespējama krāpniecība",
        spam: "📩 Nevēlams e-pasts",
        advertising: "🛍️ Reklāmas e-pasts",
        normal: "✅ Parasts e-pasts"
    };

    const heading = document.createElement("div");
    heading.textContent = titles[category] || "E-pasta pārbaude";

    Object.assign(heading.style, {
        fontWeight: "bold",
        fontSize: "14px",
        marginBottom: "7px"
    });

    tooltip.appendChild(heading);

    if (reasons.length > 0) {
        reasons.forEach(reason => {
            const item = document.createElement("div");
            item.textContent = "• " + reason;
            item.style.marginBottom = "4px";
            tooltip.appendChild(item);
        });
    } else {
        const item = document.createElement("div");
        item.textContent = "Nav atrasts konkrēts skaidrojums.";
        tooltip.appendChild(item);
    }


    Object.assign(tooltip.style, {
        display: "none",
        position: "fixed",
        width: "260px",
        maxWidth: "calc(100vw - 24px)",
        maxHeight: "300px",
        overflowY: "auto",
        boxSizing: "border-box",
        padding: "10px",
        backgroundColor: "#ffffff",
        color: "#202124",
        border: "1px solid #dadce0",
        borderRadius: "8px",
        boxShadow: "0 4px 14px rgba(0,0,0,0.18)",
        fontSize: "12px",
        fontFamily: "Arial, sans-serif",
        lineHeight: "1.4",
        overflowWrap: "anywhere",
        zIndex: "2147483647",
        pointerEvents: "none"
    });

    document.body.appendChild(tooltip);
    return tooltip;
}


// Izveido krāsainu kategorijas marķējumu.
function createBubble(category, reasons = []) {
    const bubble = document.createElement("span");
    bubble.className = "latvian-email-category";

    const styles = {
        normal: {
            text: "NORMAL",
            color: "#16a34a"
        },
        advertising: {
            text: "ADVERTISING",
            color: "#2563eb"
        },
        spam: {
            text: "SPAM",
            color: "#f59e0b"
        },
        phishing: {
            text: "PHISHING",
            color: "#dc2626"
        }
    };

    const style = styles[category] || {
        text: String(category || "UNKNOWN").toUpperCase(),
        color: "#6b7280"
    };

    bubble.textContent = style.text;

    Object.assign(bubble.style, {
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        height: "26px",
        padding: "0 10px",
        marginLeft: "10px",
        borderRadius: "14px",
        color: "#ffffff",
        backgroundColor: style.color,
        fontSize: "11px",
        fontWeight: "bold",
        fontFamily: "Arial, sans-serif",
        verticalAlign: "middle",
        position: "relative",
        zIndex: "1",
        cursor: "help"
    });

    const tooltip = createTooltip(reasons, category);

    bubble.addEventListener("mouseenter", () => {
        const rect = bubble.getBoundingClientRect();

        tooltip.style.display = "block";

        const tooltipWidth = tooltip.offsetWidth;
        const tooltipHeight = tooltip.offsetHeight;

        let left = Math.min(
            rect.left,
            window.innerWidth - tooltipWidth - 8
        );

        left = Math.max(8, left);

        let top = rect.bottom + 6;

        if (top + tooltipHeight > window.innerHeight - 8) {
            top = rect.top - tooltipHeight - 6;
        }

        top = Math.max(8, top);

        tooltip.style.left = left + "px";
        tooltip.style.top = top + "px";
    });

    bubble.addEventListener("mouseleave", () => {
        tooltip.style.display = "none";
    });

    // Noņem tooltip, ja Gmail izdzēš marķējumu.
    const cleanupObserver = new MutationObserver(() => {
        if (!bubble.isConnected) {
            tooltip.remove();
            cleanupObserver.disconnect();
        }
    });

    cleanupObserver.observe(document.body, {
        childList: true,
        subtree: true
    });

    return bubble;
}


// Pievieno kategoriju Gmail vēstulei.
function showBubble(row, category, reasons = []) {
    if (!category) return;

    if (row.querySelector(".latvian-email-category")) {
        return;
    }

    const cells = row.querySelectorAll("td");
    if (cells.length === 0) return;

    const bubble = createBubble(category, reasons);
    const lastCell = cells[cells.length - 1];

    lastCell.style.whiteSpace = "nowrap";
    lastCell.appendChild(bubble);
}


// Nosūta vēstules tekstu Python API.
async function analyzeRow(row) {
    const emailId = getEmailId(row);

    if (analysisCache.has(emailId)) {
        const result = analysisCache.get(emailId);

        showBubble(row, result.category, result.reasons);
        return;
    }

    if (row.dataset.lesAnalyzing === "true") return;

    row.dataset.lesAnalyzing = "true";

    const text = row.innerText.replace(/\s+/g, " ").trim();

    if (!text) {
        delete row.dataset.lesAnalyzing;
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                subject: "",
                message: text
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        const category = data.category || data.prediction;
        const reasons = Array.isArray(data.reasons)
            ? data.reasons.map(String)
            : [];

        if (!category) {
            throw new Error("Python API neatgrieza kategoriju.");
        }

        analysisCache.set(emailId, {
            category: category,
            reasons: reasons
        });

        showBubble(row, category, reasons);

        console.log("Kategorija:", category);
        console.log("Iemesli:", reasons);

    } catch (error) {
        console.error("Latvian Email Security:", error);
    } finally {
        delete row.dataset.lesAnalyzing;
    }
}


// Skenē Gmail vēstuļu sarakstu.
function scanEmails() {
    const rows = document.querySelectorAll("tr.zA");

    console.log("Atrastas vēstuļu rindas:", rows.length);

    rows.forEach(row => {
        analyzeRow(row);
    });
}

scanEmails();

let scanTimeout = null;

const observer = new MutationObserver(() => {
    if (scanTimeout) clearTimeout(scanTimeout);

    scanTimeout = setTimeout(() => {
        scanEmails();
    }, 300);
});

observer.observe(document.body, {
    childList: true,
    subtree: true
});

setInterval(() => {
    scanEmails();
}, 2000);
