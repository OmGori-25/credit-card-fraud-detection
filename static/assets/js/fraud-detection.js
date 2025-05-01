// ========== Configuration ==========
const PAGE_SIZE = 10; // Number of results per page

// ========== DOM Elements ==========
const uploadForm = document.getElementById("uploadForm");
const dropZone = document.getElementById("dropZone");
const fileInput = document.getElementById("fileInput");
const browseButton = document.getElementById("browseButton");
const fileInfo = document.getElementById("fileInfo");
const fileName = document.getElementById("fileName");
const fileSize = document.getElementById("fileSize");
const fileRows = document.getElementById("fileRows");
const submitButton = document.getElementById("submitButton");
const loadingSpinner = document.getElementById("loadingSpinner");
const statusBadge = document.getElementById("statusBadge");
const noDataMessage = document.getElementById("noDataMessage");
const dataStats = document.getElementById("dataStats");
const noResultsMessage = document.getElementById("noResultsMessage");
const resultsVisualizations = document.getElementById("resultsVisualizations");
const noTableResultsMessage = document.getElementById("noTableResultsMessage");
const resultsTableContainer = document.getElementById("resultsTableContainer");
const resultsTableHeader = document.getElementById("resultsTableHeader");
const resultsTableBody = document.getElementById("resultsTableBody");
const searchInput = document.getElementById("searchInput");
const filterSelect = document.getElementById("filterSelect");
const visibleRowCount = document.getElementById("visibleRowCount");
const totalRowCount = document.getElementById("totalRowCount");
const prevPageBtn = document.getElementById("prevPageBtn");
const nextPageBtn = document.getElementById("nextPageBtn");
const paginationInfo = document.getElementById("paginationInfo");
const notification = document.getElementById("notification");
const notificationIcon = document.getElementById("notificationIcon");
const notificationTitle = document.getElementById("notificationTitle");
const notificationMessage = document.getElementById("notificationMessage");
const closeNotification = document.getElementById("closeNotification");

// ========== State Variables ==========
let predictions = [];
let metrics = {};
let filteredPredictions = [];
let currentPage = 1;
let predictionChart = null;
let accuracyChart = null;

// ========== Initialization ==========
document.addEventListener("DOMContentLoaded", function () {
  console.log("DOM fully loaded and parsed");

  // Initialize event listeners
  initEventListeners();
});

function initEventListeners() {
  console.log("Initializing event listeners");

  // Browse button click
  if (browseButton) {
    browseButton.addEventListener("click", function () {
      console.log("Browse button clicked");
      fileInput.click();
    });
  } else {
    console.error("Browse button not found");
  }

  // File input change
  if (fileInput) {
    fileInput.addEventListener("change", function (e) {
      console.log("File input changed");
      const file = e.target.files[0];
      if (file) {
        handleFileSelection(file);
      }
    });
  } else {
    console.error("File input not found");
  }

  // Form submission
  if (uploadForm) {
    uploadForm.addEventListener("submit", function (e) {
      e.preventDefault();
      console.log("Form submitted");
      submitFraudDetection();
    });
  } else {
    console.error("Upload form not found");
  }

  // Drag and drop
  if (dropZone) {
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, preventDefaults, false);
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(eventName, function () {
        dropZone.classList.add("active");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(eventName, function () {
        dropZone.classList.remove("active");
      });
    });

    dropZone.addEventListener("drop", function (e) {
      console.log("File dropped");
      const file = e.dataTransfer.files[0];
      if (file && file.name.endsWith(".csv")) {
        fileInput.files = e.dataTransfer.files;
        handleFileSelection(file);
      } else {
        showNotification("Error", "Please upload a CSV file", "error");
      }
    });
  } else {
    console.error("Drop zone not found");
  }

  // Search and filter
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      currentPage = 1;
      filterAndDisplayResults();
    });
  }

  if (filterSelect) {
    filterSelect.addEventListener("change", function () {
      currentPage = 1;
      filterAndDisplayResults();
    });
  }

  // Pagination
  if (prevPageBtn) {
    prevPageBtn.addEventListener("click", function () {
      if (currentPage > 1) {
        currentPage--;
        displayResults();
      }
    });
  }

  if (nextPageBtn) {
    nextPageBtn.addEventListener("click", function () {
      const maxPage = Math.ceil(filteredPredictions.length / PAGE_SIZE);
      if (currentPage < maxPage) {
        currentPage++;
        displayResults();
      }
    });
  }

  // Notification close
  if (closeNotification) {
    closeNotification.addEventListener("click", function () {
      hideNotification();
    });
  }

  console.log("Event listeners initialized");
}

// ========== Utility Functions ==========
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

function handleFileSelection(file) {
  console.log("Handling file selection:", file.name);

  // Update file information display
  fileName.textContent = file.name;
  fileSize.textContent = formatFileSize(file.size);
  fileRows.textContent = "Analyzing...";
  fileInfo.classList.remove("hidden");

  // Count CSV rows (approximate)
  countCSVRows(file).then((rowCount) => {
    fileRows.textContent = `${rowCount} rows`;
  });

  // Enable submit button
  submitButton.disabled = false;
}

function countCSVRows(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target.result;
      const rowCount = text.split("\n").length - 1; // subtract header
      resolve(rowCount);
    };
    // Read only first 100KB to estimate row count for large files
    const chunk = file.slice(0, 100000);
    reader.readAsText(chunk);
  });
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  else return (bytes / 1048576).toFixed(1) + " MB";
}

function submitFraudDetection() {
  console.log("Submitting fraud detection");

  // Update UI to loading state
  submitButton.disabled = true;
  loadingSpinner.classList.remove("hidden");
  updateStatus("Processing", "bg-yellow-200", "text-yellow-800");

  const formData = new FormData(uploadForm);

  // Get CSRF token from the form
  const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;

  fetch("/predict_fraud_csv/", {
    method: "POST",
    headers: {
      "X-CSRFToken": csrfToken,
    },
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`Network response error: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      console.log("Received data:", data);

      // Reset loading state
      submitButton.disabled = false;
      loadingSpinner.classList.add("hidden");

      if (data.error) {
        showNotification("Error", data.error, "error");
        updateStatus("Error", "bg-red-200", "text-red-800");
      } else {
        // Update UI with results
        predictions = data.predictions;
        metrics = data.metrics || {};

        // Show success notification
        showNotification(
          "Success",
          "Fraud detection completed successfully",
          "success"
        );
        updateStatus("Complete", "bg-green-200", "text-green-800");

        // Update statistics
        updateStatistics();

        // Display results
        displayResultsAndVisualizations();
      }
    })
    .catch((error) => {
      console.error("Error:", error);

      submitButton.disabled = false;
      loadingSpinner.classList.add("hidden");
      showNotification("Error", error.message, "error");
      updateStatus("Error", "bg-red-200", "text-red-800");
    });
}

function updateStatus(text, bgClass, textClass) {
  statusBadge.textContent = text;
  statusBadge.className = `px-3 py-1 rounded-full text-sm font-medium ${bgClass} ${textClass}`;
}

function updateStatistics() {
  // Hide no data message and show stats
  noDataMessage.classList.add("hidden");
  dataStats.classList.remove("hidden");

  // Count fraud and normal predictions
  const totalRows = predictions.length;
  const fraudCount = predictions.filter((p) => p.Prediction === "Fraud").length;
  const fraudRate = (fraudCount / totalRows) * 100;

  // Update stat displays
  document.getElementById("statTotal").textContent = totalRows;
  document.getElementById("statFraud").textContent = fraudCount;
  document.getElementById("statFraudRate").textContent = `${fraudRate.toFixed(
    1
  )}%`;

  // Detection rate from metrics if available
  if (metrics && metrics.detection_rate !== undefined) {
    const detectionRate = metrics.detection_rate * 100;
    document.getElementById(
      "statDetectionRate"
    ).textContent = `${detectionRate.toFixed(1)}%`;
  } else {
    document.getElementById("statDetectionRate").textContent = "N/A";
  }
}

function displayResultsAndVisualizations() {
  // Hide empty state messages
  noResultsMessage.classList.add("hidden");
  noTableResultsMessage.classList.add("hidden");

  // Show result containers
  resultsVisualizations.classList.remove("hidden");
  resultsTableContainer.classList.remove("hidden");

  // Update visualizations
  updateCharts();

  // Filter and display table results
  filterAndDisplayResults();
}

function updateCharts() {
  // Prediction distribution chart
  const fraudCount = predictions.filter((p) => p.Prediction === "Fraud").length;
  const normalCount = predictions.filter(
    (p) => p.Prediction === "Normal"
  ).length;

  // Destroy existing chart if it exists
  if (predictionChart) {
    predictionChart.destroy();
  }

  const predictionCtx = document
    .getElementById("predictionChart")
    .getContext("2d");
  predictionChart = new Chart(predictionCtx, {
    type: "doughnut",
    data: {
      labels: ["Normal", "Fraud"],
      datasets: [
        {
          label: "Predictions",
          data: [normalCount, fraudCount],
          backgroundColor: [
            "rgba(72, 187, 120, 0.7)", // green for normal
            "rgba(229, 62, 62, 0.7)", // red for fraud
          ],
          borderColor: ["rgba(72, 187, 120, 1)", "rgba(229, 62, 62, 1)"],
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            font: {
              size: 12,
            },
          },
        },
        tooltip: {
          callbacks: {
            label: function (context) {
              const label = context.label || "";
              const value = context.raw || 0;
              const total = fraudCount + normalCount;
              const percentage = Math.round((value / total) * 100);
              return `${label}: ${value} (${percentage}%)`;
            },
          },
        },
      },
    },
  });

  // Accuracy metrics chart
  if (metrics && metrics.true_frauds !== undefined) {
    // Destroy existing chart if it exists
    if (accuracyChart) {
      accuracyChart.destroy();
    }

    const accuracyCtx = document
      .getElementById("accuracyChart")
      .getContext("2d");
    accuracyChart = new Chart(accuracyCtx, {
      type: "bar",
      data: {
        labels: ["Actual Frauds", "Detected Frauds", "Correctly Detected"],
        datasets: [
          {
            label: "Fraud Detection Metrics",
            data: [
              metrics.true_frauds,
              metrics.detected_frauds,
              metrics.correct_frauds,
            ],
            backgroundColor: [
              "rgba(90, 103, 216, 0.7)",
              "rgba(229, 62, 62, 0.7)",
              "rgba(72, 187, 120, 0.7)",
            ],
            borderColor: [
              "rgba(90, 103, 216, 1)",
              "rgba(229, 62, 62, 1)",
              "rgba(72, 187, 120, 1)",
            ],
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
          },
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: function (context) {
                const label = context.label || "";
                const value = context.raw || 0;
                return `${label}: ${value}`;
              },
            },
          },
        },
      },
    });
  }

  // Add more visualization charts here as needed
}

function filterAndDisplayResults() {
  const searchTerm = searchInput.value.toLowerCase();
  const filterValue = filterSelect.value;

  // Apply filters
  filteredPredictions = predictions.filter((prediction) => {
    // Filter by prediction type if selected
    if (filterValue !== "all" && prediction.Prediction !== filterValue) {
      return false;
    }

    // Search across all fields
    if (searchTerm) {
      const matchesSearch = Object.values(prediction).some(
        (value) => value && value.toString().toLowerCase().includes(searchTerm)
      );
      return matchesSearch;
    }

    return true;
  });

  // Update row counts
  visibleRowCount.textContent = filteredPredictions.length;
  totalRowCount.textContent = predictions.length;

  // Display results
  displayResults();
}

function displayResults() {
  // Calculate pagination
  const startIndex = (currentPage - 1) * PAGE_SIZE;
  const endIndex = Math.min(startIndex + PAGE_SIZE, filteredPredictions.length);
  const pageData = filteredPredictions.slice(startIndex, endIndex);

  // Update pagination info
  const maxPage = Math.ceil(filteredPredictions.length / PAGE_SIZE);
  paginationInfo.textContent = `Page ${currentPage} of ${maxPage || 1}`;

  // Enable/disable pagination buttons
  prevPageBtn.disabled = currentPage <= 1;
  nextPageBtn.disabled = currentPage >= maxPage;

  // Show message if no results
  if (filteredPredictions.length === 0) {
    noTableResultsMessage.classList.remove("hidden");
    resultsTableHeader.innerHTML = "";
    resultsTableBody.innerHTML = "";
    return;
  }

  // Hide no results message
  noTableResultsMessage.classList.add("hidden");

  // Create table headers (based on first result's keys)
  if (pageData.length > 0) {
    const headerRow = document.createElement("tr");
    const columns = Object.keys(pageData[0]);

    columns.forEach((column) => {
      const th = document.createElement("th");
      th.textContent = column;
      th.className =
        "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider";
      headerRow.appendChild(th);
    });

    resultsTableHeader.innerHTML = "";
    resultsTableHeader.appendChild(headerRow);
  }

  // Create table rows
  resultsTableBody.innerHTML = "";

  pageData.forEach((row, index) => {
    const tableRow = document.createElement("tr");
    tableRow.className = index % 2 === 0 ? "bg-white" : "bg-gray-50";

    Object.values(row).forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      td.className = "px-4 py-2 whitespace-nowrap text-sm text-gray-500";

      // Highlight fraud predictions
      if (value === "Fraud") {
        td.className += " text-red-600 font-medium";
      }

      tableRow.appendChild(td);
    });

    resultsTableBody.appendChild(tableRow);
  });
}

function showNotification(title, message, type = "info") {
  // Set notification content
  notificationTitle.textContent = title;
  notificationMessage.textContent = message;

  // Set notification style based on type
  notification.className =
    "fixed inset-0 flex items-end justify-center px-4 py-6 pointer-events-none sm:p-6 sm:items-start sm:justify-end z-50 transform transition-all duration-500 ease-in-out";

  // Set icon based on type
  if (type === "success") {
    notificationIcon.innerHTML =
      '<svg class="h-6 w-6 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>';
    notification.classList.add("bg-green-50", "border-green-200");
  } else if (type === "error") {
    notificationIcon.innerHTML =
      '<svg class="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>';
    notification.classList.add("bg-red-50", "border-red-200");
  } else {
    notificationIcon.innerHTML =
      '<svg class="h-6 w-6 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>';
    notification.classList.add("bg-blue-50", "border-blue-200");
  }

  // Show notification
  notification.classList.remove("translate-y-2", "opacity-0");
  notification.classList.add("translate-y-0", "opacity-100");

  // Auto-hide after 5 seconds
  setTimeout(hideNotification, 5000);
}

function hideNotification() {
  notification.classList.remove("translate-y-0", "opacity-100");
  notification.classList.add("translate-y-2", "opacity-0");
}

// You might need to implement these additional functions that are referenced but not defined:
// - filterAndDisplayResults() - Used for filtering and displaying results
// - displayResults() - Used for displaying results based on current page
