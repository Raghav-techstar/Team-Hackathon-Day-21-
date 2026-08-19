// ============================================================
// DASHBOARD STATE
// ============================================================

let shipments = [];
let summaryData = null;
let dqData = null;

const API_BASE = "";


// ============================================================
// INITIALIZE
// ============================================================

document.addEventListener("DOMContentLoaded", () => {

    setupFilters();

    setupRefresh();

    setupModal();

    setupKPICards();

    loadDashboard();

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

            fetch(`${API_BASE}/status/summary`),

            fetch(`${API_BASE}/status/shipments`),

            fetch(`${API_BASE}/status/dq-report`)

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

        updateLastUpdated();


    } catch (error) {

        console.error(error);

        showErrorState(
            error.message
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

    updateShipmentTable();

    populateCarrierFilter();

    updateSystemStatus();

}


// ============================================================
// KPI CARDS
// ============================================================

function updateKPIs() {

    const total =
        shipments.length;


    const transit =
        shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "in transit"
        ).length;


    const delivered =
        shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delivered"
        ).length;


    const delayed =
        shipments.filter(
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
        shipments.length;


    const delivered =
        shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delivered"
        ).length;


    const delayed =
        shipments.filter(
            s =>
                normalizeStatus(s.status)
                === "delayed"
        ).length;


    const transit =
        shipments.filter(
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
            shipment.carrier || "Unknown";


        if (!carriers[carrier]) {

            carriers[carrier] = {
                total: 0,
                onTime: 0
            };

        }


        carriers[carrier].total++;


        const delay =
            Number(
                shipment.delay_days || 0
            );


        if (delay <= 0) {

            carriers[carrier].onTime++;

        }

    });


    const container =
        document.getElementById(
            "carrierPerformance"
        );


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
                    data-shipment-id="${shipment.shipment_id}"
                >

                    <td>
                        <span class="shipment-id">
                            ${shipment.shipment_id}
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

    const systemStatus =
        document.querySelector(
            ".system-status strong"
        );


    const systemDescription =
        document.querySelector(
            ".system-status small"
        );


    if (
        !dqData
    ) {

        return;

    }


    /*
     * Your DQ API may use a different
     * status field. We keep the dashboard
     * safe if it does.
     */

    const rawStatus =
        String(
            dqData.overall_status
            ||
            dqData.status
            ||
            "PASS"
        ).toUpperCase();


    if (
        rawStatus === "PASS"
    ) {

        systemStatus.textContent =
            "System Online";


        systemDescription.textContent =
            "API Connected";

    } else {

        systemStatus.textContent =
            "DQ Attention";


        systemDescription.textContent =
            "Check data quality";

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