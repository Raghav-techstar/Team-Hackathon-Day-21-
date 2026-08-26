// ============================================================
// DASHBOARD STATE
// ============================================================

let shipments = [];
let summaryData = null;
let dqData = null;
let exceptionPage = 0;
const EXCEPTION_PAGE_SIZE = 50;

const API_BASE = "";

// OAuth2 token
const AUTH_TOKEN = "admin";
async function authenticatedFetch(
    url,
    options = {}
) {

    const headers = {
        ...(options.headers || {}),
        "Authorization": `Bearer ${AUTH_TOKEN}`,
    };

    return fetch(url, {
        ...options,
        headers,
    });
}

// ============================================================
// INITIALIZE
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    setupFilters();

    setupRefresh();

    setupModal();

    setupKPICards();

    loadDashboard();

    startBackgroundRefresh();

    setupAIChat();

    setupNavigation();

});


// ============================================================
// LOAD DASHBOARD
// ============================================================

async function loadDashboard() {

    showLoadingState();

    try {

        const [
            summaryResponse,
            shipmentsResponse,
            dqResponse
       ] = await Promise.all([

    authenticatedFetch(
        `${API_BASE}/status/summary`
    ),

    authenticatedFetch(
        `${API_BASE}/status/shipments?limit=50&offset=0`
    ),

    authenticatedFetch(
        `${API_BASE}/status/dq-report`
    )
]);


        if (!summaryResponse.ok) {
            throw new Error(
                "Failed to load shipment summary."
            );
        }


        if (!shipmentsResponse.ok) {
            throw new Error(
                "Failed to load shipment data."
            );
        }


        if (!dqResponse.ok) {
            throw new Error(
                "Failed to load data-quality report."
            );
        }


        summaryData =
            await summaryResponse.json();


        shipments =
            await shipmentsResponse.json();


        dqData =
            await dqResponse.json();


        renderDashboard();

        await loadExceptions(0);

        updateLastUpdated();


    } catch (error) {

        console.error(error);

        showErrorState(
            error.message
        );

    }

}

async function loadExceptions(page = 0) {

    const offset =
        page * EXCEPTION_PAGE_SIZE;

    try {

        const response =
            await authenticatedFetch(
                `${API_BASE}/status/shipments?status=Delayed&limit=${EXCEPTION_PAGE_SIZE}&offset=${offset}`
            );

        if (!response.ok) {
            throw new Error(
                `Failed to load exceptions: ${response.status}`
            );
        }

        const exceptions =
            await response.json();

        exceptionPage = page;

        renderExceptions(
            exceptions
        );

    } catch (error) {

        console.error(
            "Exception loading error:",
            error
        );
    }
}

function renderExceptions(exceptions) {

    updateShipmentTable(
        exceptions
    );

    updateExceptionPagination(
        exceptions.length
    );
}

function updateExceptionPagination(recordCount) {

    const container =
        document.getElementById(
            "exceptionPagination"
        );

    if (!container) {
        return;
    }

    const previousDisabled =
        exceptionPage === 0
            ? "disabled"
            : "";

    const nextDisabled =
        recordCount < EXCEPTION_PAGE_SIZE
            ? "disabled"
            : "";

    container.innerHTML = `
        <button
            id="exceptionPrevious"
            ${previousDisabled}
        >
            Previous
        </button>

        <span>
            Page ${exceptionPage + 1}
        </span>

        <button
            id="exceptionNext"
            ${nextDisabled}
        >
            Next
        </button>
    `;

    document
        .getElementById("exceptionPrevious")
        ?.addEventListener(
            "click",
            () => loadExceptions(
                exceptionPage - 1
            )
        );

    document
        .getElementById("exceptionNext")
        ?.addEventListener(
            "click",
            () => loadExceptions(
                exceptionPage + 1
            )
        );
}

// ============================================================
// BACKGROUND REFRESH
// ============================================================

function startBackgroundRefresh() {

    const REFRESH_INTERVAL = 15000; // 15 seconds

    setInterval(async () => {

        try {

            await refreshDashboardSilently();

        } catch (error) {

            console.error(
                "Background refresh failed:",
                error
            );

        }

    }, REFRESH_INTERVAL);
}

async function refreshDashboardSilently() {

    try {

        const [
            summaryResponse,
            shipmentsResponse,
            dqResponse
        ] = await Promise.all([

    authenticatedFetch(
        `${API_BASE}/status/summary`
    ),

    authenticatedFetch(
        `${API_BASE}/status/shipments?limit=50&offset=0`
    ),

    authenticatedFetch(
        `${API_BASE}/status/dq-report`
    )
]);


        if (
            !summaryResponse.ok ||
            !shipmentsResponse.ok ||
            !dqResponse.ok
        ) {
            throw new Error(
                "One or more background API requests failed."
            );
        }


        const newSummaryData =
            await summaryResponse.json();

        const newShipments =
            await shipmentsResponse.json();

        const newDQData =
            await dqResponse.json();


        // Update application state

        summaryData =
            newSummaryData;

        shipments =
            newShipments;

        dqData =
            newDQData;


        // Update dashboard without
        // showing the loading screen

        renderDashboard();

        updateLastUpdated();


    } catch (error) {

        console.error(
            "Silent dashboard refresh failed:",
            error
        );

    }
}


// ============================================================
// MAIN RENDER
// ============================================================

function renderDashboard() {

    updateKPIs();

    updateStatusChart();

    updateCarrierPerformance();

    updateRouteAnalysis();

    updateFreightAnalysis();

    populateCarrierFilter();

    updateSystemStatus();

}


// ============================================================
// KPI CARDS
// ============================================================

function updateKPIs() {

    const total =
        summaryData?.total_shipments ?? shipments.length;


    const transit =
        summaryData?.in_transit_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "in transit"
        ).length;


    const delivered =
        summaryData?.delivered_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delivered"
        ).length;


    const delayed =
        summaryData?.delayed_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delayed"
        ).length;


    document.getElementById(
        "totalShipments"
    ).textContent = total;


    document.getElementById(
        "inTransitShipments"
    ).textContent = transit;


    document.getElementById(
        "deliveredShipments"
    ).textContent = delivered;


    document.getElementById(
        "delayedShipments"
    ).textContent = delayed;


    document.getElementById(
        "chartTotal"
    ).textContent = total;

}


// ============================================================
// KPI CARD INTERACTION
// ============================================================

function setupKPICards() {

    const cards =
        document.querySelectorAll(
            ".clickable-card"
        );


    cards.forEach(card => {

        card.addEventListener(
            "click",
            () => {

                const filter =
                    card.dataset.filter;


                document.getElementById(
                    "statusFilter"
                ).value =
                    filter === "all"
                        ? "all"
                        : filter;


                document.getElementById(
                    "carrierFilter"
                ).value = "all";


                document.getElementById(
                    "searchInput"
                ).value = "";


                applyFilters();


                document
                    .getElementById(
                        "exceptions"
                    )
                    .scrollIntoView({
                        behavior: "smooth"
                    });

            }
        );

    });

}


// ============================================================
// STATUS DONUT
// ============================================================

function updateStatusChart() {

    const total =
        summaryData?.total_shipments ?? shipments.length;


    const delivered =
        summaryData?.delivered_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delivered"
        ).length;


    const delayed =
        summaryData?.delayed_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delayed"
        ).length;


    const transit =
        summaryData?.in_transit_shipments ?? shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "in transit"
        ).length;


    const deliveredDeg =
        total
            ? (delivered / total) * 360
            : 0;


    const delayedDeg =
        total
            ? (delayed / total) * 360
            : 0;


    const donut =
        document.querySelector(
            ".donut-chart"
        );


    donut.style.background =
        `conic-gradient(
            #39d98a 0deg ${deliveredDeg}deg,
            #ff5c6c ${deliveredDeg}deg
                ${deliveredDeg + delayedDeg}deg,
            #36d9ff ${deliveredDeg + delayedDeg}deg
                360deg
        )`;


    const legend =
        document.getElementById(
            "statusLegend"
        );


    legend.innerHTML = "";


    createLegendItem(
        legend,
        "Delivered",
        delivered,
        total,
        "#39d98a"
    );


    createLegendItem(
        legend,
        "Delayed",
        delayed,
        total,
        "#ff5c6c"
    );


    createLegendItem(
        legend,
        "In Transit",
        transit,
        total,
        "#36d9ff"
    );

}


function createLegendItem(
    container,
    name,
    value,
    total,
    color
) {

    const percentage =
        total
            ? Math.round(
                (value / total) * 100
            )
            : 0;


    container.innerHTML += `
        <div class="legend-item">

            <div class="legend-left">

                <span
                    class="legend-dot"
                    style="background:${color}"
                ></span>

                <span>
                    ${name}
                </span>

            </div>

            <span class="legend-value">
                ${value}
                <small>
                    (${percentage}%)
                </small>
            </span>

        </div>
    `;

}


// ============================================================
// CARRIER PERFORMANCE
// ============================================================

function updateCarrierPerformance() {

    const carriers = {};


    shipments.forEach(shipment => {

        const carrier =
            String(
                shipment.carrier || "Unknown"
            ).trim().toUpperCase();


        if (!carriers[carrier]) {

            carriers[carrier] = {
                total: 0,
                onTime: 0
            };

        }


        carriers[carrier].total++;


        const delay =
            Number(shipment.delay_days);


        if (
            Number.isNaN(delay) ||
            delay <= 0
        ) {

            carriers[carrier].onTime++;

        }

    });


    const container =
        document.getElementById(
            "carrierPerformance"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    Object.entries(carriers)
        .sort(
            (a, b) =>
                b[1].total -
                a[1].total
        )
        .forEach(
            ([carrier, data]) => {

                const percentage =
                    data.total
                        ? Math.round(
                            (
                                data.onTime /
                                data.total
                            ) * 100
                        )
                        : 0;


                container.innerHTML += `
                    <div
                        class="carrier-row clickable-row"
                        data-carrier="${carrier}"
                    >

                        <span class="carrier-name">
                            ${carrier}
                        </span>

                        <div class="progress-container">

                            <div
                                class="progress-bar"
                                style="width:${percentage}%"
                            ></div>

                        </div>

                        <span class="carrier-value">
                            ${percentage}%
                        </span>

                    </div>
                `;

            }
        );


    setupCarrierClicks();

}


function setupCarrierClicks() {

    document
        .querySelectorAll(
            ".clickable-row"
        )
        .forEach(row => {

            row.addEventListener(
                "click",
                () => {

                    const carrier =
                        row.dataset.carrier;


                    document.getElementById(
                        "carrierFilter"
                    ).value =
                        carrier;


                    document.getElementById(
                        "statusFilter"
                    ).value =
                        "all";


                    document
                        .getElementById(
                            "exceptions"
                        )
                        .scrollIntoView({
                            behavior: "smooth"
                        });


                    applyFilters();

                }
            );

        });

}


// ============================================================
// ROUTE ANALYSIS
// ============================================================

function updateRouteAnalysis() {

    const routes = {};


    shipments.forEach(shipment => {

        const origin =
            shipment.origin || "-";


        const destination =
            shipment.destination || "-";


        const route =
            `${origin} → ${destination}`;


        routes[route] =
            (routes[route] || 0) + 1;

    });


    const container =
        document.getElementById(
            "routeAnalysis"
        );


    container.innerHTML = "";


    Object.entries(routes)
        .sort(
            (a, b) =>
                b[1] - a[1]
        )
        .forEach(
            ([route, count]) => {

                container.innerHTML += `
                    <div
                        class="route-row clickable-route"
                        data-route="${route}"
                    >

                        <span class="route-name">
                            ${route}
                        </span>

                        <span class="route-count">
                            ${count} shipments
                        </span>

                    </div>
                `;

            }
        );


    setupRouteClicks();

}


function setupRouteClicks() {

    document
        .querySelectorAll(
            ".clickable-route"
        )
        .forEach(row => {

            row.addEventListener(
                "click",
                () => {

                    const route =
                        row.dataset.route;


                    document.getElementById(
                        "statusFilter"
                    ).value = "all";


                    document.getElementById(
                        "carrierFilter"
                    ).value = "all";


                    document.getElementById(
                        "searchInput"
                    ).value = "";


                    const filtered =
                        shipments.filter(
                            shipment => {

                                const currentRoute =
                                    `${shipment.origin}
                                    → ${shipment.destination}`
                                    .replace(
                                        /\s+/g,
                                        " "
                                    )
                                    .trim();


                                return (
                                    currentRoute
                                    === route
                                );

                            }
                        );


                    updateShipmentTable(
                        filtered
                    );


                    document
                        .getElementById(
                            "exceptions"
                        )
                        .scrollIntoView({
                            behavior: "smooth"
                        });

                }
            );

        });

}


// ============================================================
// FREIGHT COST
// ============================================================

function updateFreightAnalysis() {

    const costs = {};

    shipments.forEach(shipment => {

        const carrier =
            shipment.carrier || "Unknown";

        const cost =
            Number(shipment.freight_cost || 0);

        costs[carrier] =
            (costs[carrier] || 0) + cost;

    });

    const container =
        document.getElementById("freightAnalysis");

    container.innerHTML = `
        <div class="freight-chart">
            <div class="freight-bars"></div>
        </div>
    `;

    const barsContainer =
        container.querySelector(".freight-bars");

    const maxCost =
        Math.max(...Object.values(costs), 1);

    Object.entries(costs)
        .sort((a, b) => b[1] - a[1])
        .forEach(([carrier, cost]) => {

            const height =
                Math.max(
                    (cost / maxCost) * 100,
                    5
                );

            barsContainer.innerHTML += `
                <div
                    class="freight-column"
                    title="${carrier}: ₹${cost.toFixed(2)}"
                >

                    <div class="freight-value">
                        ₹${cost.toFixed(0)}
                    </div>

                    <div class="freight-bar-area">

                        <div
                            class="freight-bar"
                            style="height:${height}%"
                        ></div>

                    </div>

                    <div class="freight-carrier">
                        ${carrier}
                    </div>

                </div>
            `;

        });

}

// ============================================================
// SIDEBAR NAVIGATION
// ============================================================

function setupNavigation() {

    const navItems =
        document.querySelectorAll(".nav-item");

    function updateActiveNav() {

        let currentHash =
            window.location.hash;

        // Dashboard is the default page
        if (
            !currentHash ||
            currentHash === "#"
        ) {
            currentHash = "#dashboard";
        }

        navItems.forEach(item => {

            const href =
                item.getAttribute("href");

            item.classList.toggle(
                "active",
                href === currentHash ||
                (
                    currentHash === "#dashboard" &&
                    href === "#"
                )
            );

        });
    }

    // Update when a navigation item is clicked
    navItems.forEach(item => {

        item.addEventListener(
            "click",
            () => {

                // Small delay allows the URL hash
                // to update first.
                setTimeout(
                    updateActiveNav,
                    0
                );

            }
        );

    });

    // Also update if hash changes
    window.addEventListener(
        "hashchange",
        updateActiveNav
    );

    // Set correct item when page loads
    updateActiveNav();

    if (window.location.hash === "#exceptions") {
        loadExceptions(0);
    }

    window.addEventListener(
        "hashchange",
        () => {
            if (window.location.hash === "#exceptions") {
                loadExceptions(0);
            }
        }
    );
}


// ============================================================
// SHIPMENT TABLE
// ============================================================

function updateShipmentTable(
    filteredData = shipments
) {

    const tbody =
        document.getElementById(
            "shipmentTableBody"
        );


    tbody.innerHTML = "";


    if (!filteredData.length) {

        tbody.innerHTML = `
            <tr>
                <td
                    colspan="7"
                    class="loading-cell"
                >
                    No shipments found.
                </td>
            </tr>
        `;

        return;

    }


    filteredData.forEach(
        shipment => {

            const status =
                shipment.status || "Unknown";


            const normalized =
                normalizeStatus(status);


            let statusClass =
                "status-transit";


            if (
                normalized === "delivered"
            ) {

                statusClass =
                    "status-delivered";

            } else if (
                normalized === "delayed"
            ) {

                statusClass =
                    "status-delayed";

            }


            const delay =
                Number(
                    shipment.delay_days || 0
                );


            tbody.innerHTML += `
                <tr
                    class="shipment-row"
                    data-shipment-id="${
                    shipment.shipment_id === null ||
                    shipment.shipment_id === undefined ||
                    String(shipment.shipment_id).toLowerCase() === "nan"
                        ? ""
                        : shipment.shipment_id
                    }"
                >

                    <td>
                        <span class="shipment-id">
                            ${
                                shipment.shipment_id === null ||
                                shipment.shipment_id === undefined ||
                                String(shipment.shipment_id).toLowerCase() === "nan"
                                    ? "—"
                                    : shipment.shipment_id
                        }
                        </span>
                    </td>

                    <td>
                        ${shipment.carrier || "-"}
                    </td>

                    <td class="route-cell">
                        ${shipment.origin || "-"}
                        →
                        ${shipment.destination || "-"}
                    </td>

                    <td>

                        <span
                            class="
                                status-badge
                                ${statusClass}
                            "
                        >
                            ${status}
                        </span>

                    </td>

                    <td>
                        ${shipment.expected_delivery_date || "-"}
                    </td>

                    <td>
                        ${shipment.delivered_date || "-"}
                    </td>

                    <td>

                        <span
                            class="${
                                delay > 0
                                    ? "delay-value"
                                    : "on-time"
                            }"
                        >
                            ${
                                delay > 0
                                    ? `${delay} days`
                                    : "On Time"
                            }
                        </span>

                    </td>

                </tr>
            `;

        }
    );


    setupShipmentRowClicks();

}


// ============================================================
// SHIPMENT ROW CLICK
// ============================================================

function setupShipmentRowClicks() {

    document
        .querySelectorAll(
            ".shipment-row"
        )
        .forEach(row => {

            row.addEventListener(
                "click",
                () => {

                    const id =
                        row.dataset.shipmentId;


                    const shipment =
                        shipments.find(
                            s =>
                                String(
                                    s.shipment_id
                                ) === String(id)
                        );


                    if (shipment) {

                        openShipmentModal(
                            shipment
                        );

                    }

                }
            );

        });

}


// ============================================================
// MODAL
// ============================================================

function setupModal() {

    const closeButton =
        document.getElementById(
            "modalClose"
        );


    const overlay =
        document.getElementById(
            "shipmentModal"
        );


    closeButton.addEventListener(
        "click",
        closeShipmentModal
    );


    overlay.addEventListener(
        "click",
        event => {

            if (
                event.target === overlay
            ) {

                closeShipmentModal();

            }

        }
    );


    document.addEventListener(
        "keydown",
        event => {

            if (
                event.key === "Escape"
            ) {

                closeShipmentModal();

            }

        }
    );

}


function openShipmentModal(
    shipment
) {

    document.getElementById(
        "modalShipmentId"
    ).textContent =
        shipment.shipment_id;


    document.getElementById(
        "modalCarrier"
    ).textContent =
        shipment.carrier || "-";


    document.getElementById(
        "modalRoute"
    ).textContent =
        `${shipment.origin || "-"}
         →
         ${shipment.destination || "-"}`;


    document.getElementById(
        "modalShipDate"
    ).textContent =
        shipment.ship_date || "-";


    document.getElementById(
        "modalExpectedDate"
    ).textContent =
        shipment.expected_delivery_date || "-";


    document.getElementById(
        "modalDeliveredDate"
    ).textContent =
        shipment.delivered_date || "-";


    const delay =
        Number(
            shipment.delay_days || 0
        );


    document.getElementById(
        "modalDelay"
    ).textContent =
        delay > 0
            ? `${delay} days`
            : "On Time";


    document.getElementById(
        "modalFreightCost"
    ).textContent =
        shipment.freight_cost !== undefined &&
        shipment.freight_cost !== null
            ? `₹${Number(
                shipment.freight_cost
            ).toFixed(2)}`
            : "-";


    const statusElement =
        document.getElementById(
            "modalStatus"
        );


    statusElement.textContent =
        shipment.status || "Unknown";


    statusElement.className =
        "modal-status";


    const normalized =
        normalizeStatus(
            shipment.status
        );


    if (
        normalized === "delivered"
    ) {

        statusElement.classList.add(
            "modal-delivered"
        );

    } else if (
        normalized === "delayed"
    ) {

        statusElement.classList.add(
            "modal-delayed"
        );

    } else {

        statusElement.classList.add(
            "modal-transit"
        );

    }


    document.getElementById(
        "shipmentModal"
    ).classList.add(
        "show"
    );

}


function closeShipmentModal() {

    document.getElementById(
        "shipmentModal"
    ).classList.remove(
        "show"
    );

}


// ============================================================
// FILTERS
// ============================================================

function setupFilters() {

    const statusFilter =
        document.getElementById(
            "statusFilter"
        );


    const carrierFilter =
        document.getElementById(
            "carrierFilter"
        );


    const searchInput =
        document.getElementById(
            "searchInput"
        );


    statusFilter.addEventListener(
        "change",
        applyFilters
    );


    carrierFilter.addEventListener(
        "change",
        applyFilters
    );


    searchInput.addEventListener(
        "input",
        applyFilters
    );

}


function applyFilters() {

    const status =
        document.getElementById(
            "statusFilter"
        ).value;


    const carrier =
        document.getElementById(
            "carrierFilter"
        ).value;


    const search =
        document.getElementById(
            "searchInput"
        ).value
        .toLowerCase()
        .trim();


    const selectedStatus =
        normalizeStatus(status);


    const filtered =
        shipments.filter(
            shipment => {

                const shipmentStatus =
                    normalizeStatus(
                        shipment.status
                    );


                const statusMatch =
                    status === "all"
                    ||
                    shipmentStatus ===
                    selectedStatus;


                const carrierMatch =
                    carrier === "all"
                    ||
                    shipment.carrier ===
                    carrier;


                const shipmentId =
                    String(
                        shipment.shipment_id
                        || ""
                    ).toLowerCase();


                const route =
                    `${shipment.origin || ""}
                     ${shipment.destination || ""}`
                    .toLowerCase();


                const searchMatch =
                    shipmentId.includes(search)
                    ||
                    route.includes(search);


                return (
                    statusMatch &&
                    carrierMatch &&
                    searchMatch
                );

            }
        );


    updateShipmentTable(
        filtered
    );

}


// ============================================================
// CARRIER FILTER
// ============================================================

function populateCarrierFilter() {

    const select =
        document.getElementById(
            "carrierFilter"
        );


    const currentValue =
        select.value;


    select.innerHTML = `
        <option value="all">
            All Carriers
        </option>
    `;


    const carriers =
        [
            ...new Set(
                shipments
                    .map(
                        s => s.carrier
                    )
                    .filter(Boolean)
            )
        ]
        .sort();


    carriers.forEach(
        carrier => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                carrier;


            option.textContent =
                carrier;


            select.appendChild(
                option
            );

        }
    );


    if (
        carriers.includes(
            currentValue
        )
    ) {

        select.value =
            currentValue;

    }

}


// ============================================================
// REFRESH
// ============================================================

function setupRefresh() {

    document
        .getElementById(
            "refreshButton"
        )
        .addEventListener(
            "click",
            async () => {

                const button =
                    document.getElementById(
                        "refreshButton"
                    );


                button.disabled = true;


                button.textContent =
                    "↻ Loading...";


                await loadDashboard();


                button.disabled = false;


                button.textContent =
                    "↻ Refresh";

            }
        );

}


// ============================================================
// SYSTEM / DQ STATUS
// ============================================================

function updateSystemStatus() {

    const systemCard =
        document.querySelector(".system-status");

    const systemStatus =
        document.querySelector(
            ".system-status strong"
        );


    const systemDescription =
        document.querySelector(
            ".system-status small"
        );

    if (!systemCard || !systemStatus || !systemDescription) {
        return;
        }

    if (!dqData) {
        return;
    }

    const rawStatus =
        String(
            dqData.overall_status ||
            dqData.status ||
            "PASS"
        ).toUpperCase();


    // Remove previous DQ classes
    systemCard.classList.remove(
        "dq-pass",
        "dq-fail"
    );


if (rawStatus === "PASS") {

    systemCard.classList.remove("dq-fail");
    systemCard.classList.add("dq-pass");

    systemStatus.textContent = "System Online";
    systemDescription.textContent = "Data quality passed";

} else {

    systemCard.classList.remove("dq-pass");
    systemCard.classList.add("dq-fail");

    systemStatus.textContent = "DQ Attention";
    systemDescription.textContent = "Check data quality";
}

}


// ============================================================
// TIME
// ============================================================

function updateLastUpdated() {

    const now =
        new Date();


    document.getElementById(
        "lastUpdated"
    ).textContent =
        now.toLocaleTimeString();

}


// ============================================================
// LOADING
// ============================================================

function showLoadingState() {

    document.getElementById(
        "totalShipments"
    ).textContent = "...";


    document.getElementById(
        "inTransitShipments"
    ).textContent = "...";


    document.getElementById(
        "deliveredShipments"
    ).textContent = "...";


    document.getElementById(
        "delayedShipments"
    ).textContent = "...";


    document.getElementById(
        "chartTotal"
    ).textContent = "...";


    document.getElementById(
        "shipmentTableBody"
    ).innerHTML = `
        <tr>
            <td
                colspan="7"
                class="loading-cell"
            >
                Loading shipment data...
            </td>
        </tr>
    `;

}


// ============================================================
// ERROR
// ============================================================

function showErrorState(
    message
) {

    document.getElementById(
        "shipmentTableBody"
    ).innerHTML = `
        <tr>

            <td
                colspan="7"
                class="loading-cell"
            >
                Unable to load shipment data.
                ${message}
            </td>

        </tr>
    `;


    document.getElementById(
        "totalShipments"
    ).textContent = "--";


    document.getElementById(
        "inTransitShipments"
    ).textContent = "--";


    document.getElementById(
        "deliveredShipments"
    ).textContent = "--";


    document.getElementById(
        "delayedShipments"
    ).textContent = "--";

}


// ============================================================
// NORMALIZE STATUS
// ============================================================

function normalizeStatus(
    status
) {

    return String(
        status || ""
    )
        .trim()
        .toLowerCase();

}

// ============================================================
// AI CHATBOT
// ============================================================

function setupAIChat() {

    const chatButton =
        document.getElementById(
            "ai-chat-button"
        );

    const chatWindow =
        document.getElementById(
            "ai-chat-window"
        );

    const closeButton =
        document.getElementById(
            "ai-chat-close"
        );

    const sendButton =
        document.getElementById(
            "ai-chat-send"
        );

    const input =
        document.getElementById(
            "ai-chat-input"
        );

    if (
        !chatButton ||
        !chatWindow ||
        !closeButton ||
        !sendButton ||
        !input
    ) {
        return;
    }


    // --------------------------------------------------------
    // OPEN CHAT
    // --------------------------------------------------------

    chatButton.addEventListener(
    "click",
    () => {

        if (chatWindow.classList.contains("open")) {

            // Close chatbot
            chatWindow.classList.remove("open");

        } else {

            // Open chatbot
            chatWindow.classList.add("open");
            input.focus();

        }

    }
);


    // --------------------------------------------------------
    // CLOSE CHAT
    // --------------------------------------------------------

    closeButton.addEventListener(
        "click",
        () => {

            chatWindow.classList.remove(
                "open"
            );
        }
    );


    // --------------------------------------------------------
    // SEND BUTTON
    // --------------------------------------------------------

    sendButton.addEventListener(
        "click",
        sendAIMessage
    );


    // --------------------------------------------------------
    // ENTER KEY
    // --------------------------------------------------------

    input.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendAIMessage();
            }
        }
    );


    // --------------------------------------------------------
    // SEND MESSAGE
    // --------------------------------------------------------

    async function sendAIMessage() {

        const message =
            input.value.trim();


        if (!message) {
            return;
        }


        // Show user message

        addAIMessage(
            message,
            "user"
        );


        input.value = "";

        sendButton.disabled = true;


        // Show typing indicator

        const typingElement =
            showAITyping();


        try {

            const response =
                await authenticatedFetch(
                    `${API_BASE}/ai/chat`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json",
                        },

                        body: JSON.stringify({
                            message: message,
                        }),
                    }
                );


            if (!response.ok) {

                const errorText =
                    await response.text();

                throw new Error(
                    `AI request failed: ${response.status} ${errorText}`
                );
            }


            const data =
                await response.json();


            typingElement.remove();


            addAIMessage(
                data.answer,
                "assistant"
            );


        } catch (error) {

            console.error(
                "AI chatbot error:",
                error
            );


            typingElement.remove();


            addAIMessage(
                "Sorry, I couldn't process that request. Please try again.",
                "assistant"
            );

        } finally {

            sendButton.disabled = false;

            input.focus();
        }
    }
}
function addAIMessage(
    message,
    type
) {

    const messages =
        document.getElementById(
            "ai-chat-messages"
        );


    const wrapper =
        document.createElement("div");

    wrapper.className =
        `ai-message ${type}`;


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        type === "user"
            ? "You"
            : "✦";


    const content =
        document.createElement("div");

    content.className =
        "message-content";

    content.textContent =
        message;


    wrapper.appendChild(
        avatar
    );

    wrapper.appendChild(
        content
    );


    messages.appendChild(
        wrapper
    );


    messages.scrollTop =
        messages.scrollHeight;
}
function showAITyping() {

    const messages =
        document.getElementById(
            "ai-chat-messages"
        );


    const wrapper =
        document.createElement("div");

    wrapper.className =
        "ai-message assistant";


    const avatar =
        document.createElement("div");

    avatar.className =
        "message-avatar";

    avatar.textContent =
        "✦";


    const typing =
        document.createElement("div");

    typing.className =
        "message-content ai-typing";


    typing.innerHTML = `
        <span></span>
        <span></span>
        <span></span>
    `;


    wrapper.appendChild(
        avatar
    );

    wrapper.appendChild(
        typing
    );


    messages.appendChild(
        wrapper
    );


    messages.scrollTop =
        messages.scrollHeight;


    return wrapper;
}