const BASE = location.origin; // used to build API and QR image URLs (e.g., ${BASE}/api/links).
let editingCode = null;
let auto = false,
  iv = null; // interval id used by setInterval when auto-refresh is on.

// ---------- Utilities (reusable helpers, called in this file) ----------
function setStatus(msg) { // updates the small #status element; central place to show non-modal status.
  document.getElementById("status").textContent = msg || ""; // document is the global DOM document object exposed by the browser representing the parsed HTML page
}
function showToast(msg) { // transient non-modal notification using #toast.
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.style.display = "block";
  setTimeout(() => (t.style.display = "none"), 1800);
}
function showError(obj) { // display structured errors in #errorbar.
  const e = document.getElementById("errorbar");
  if (!obj) {
    e.style.display = "none";
    e.textContent = "";
    return;
  }
  e.style.display = "block";
  if (obj.error) { // if it has error property show obj.error.message or obj.error
    e.textContent = obj.error.message || JSON.stringify(obj.error, null, 2);
  } else { // else show obj(string) or JSON.stringify(obj)
    e.textContent = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  }
}
async function readError(res) { // given a fetch Response object (nono-ok), parse API error responses as JSON
  try {
    return await res.json();
  } catch {
    return { error: { message: (await res.text()) || "Unknown error" } };
  }
}
async function copyText(text) { // writes text to clipboard via navigator.clipboard.
  try {
    await navigator.clipboard.writeText(text);
    showToast("Copied!");
  } catch {
    showToast("Copy failed");
  }
}
function fmtNullable(val) { // formats nullable date string or value to a locale string.
  if (!val) return "";
  try {
    const d = new Date(val);
    if (!isNaN(d)) return d.toLocaleString();
  } catch {}
  return String(val); // if val not parseable to a Date
} // Called from: fetchLinks() when rendering created_at in each row: <td>${fmtNullable(r.created_at)}</td>

// Sanitize text that will be inserted into HTML markup via innerHTML — replaces characters that carry HTML meaning.
function escapeHtml(s) { // Called from: fetchLinks() when building the target cell: escapeHtml(r.target_url)
  return String(s).replace(/[&<>"']/g, (m) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[m]));
} 
function escapeAttr(s) { // escape quotes for embedding inside attribute values embedded in JS templates (onclick strings).
  return String(s).replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

// Chech if link is active, Called from: fetchLinks() to compute active variable; also used indirectly by getExpiryStatus.
function isActive(exp) { 
  if (!exp) return true; // if not expiry treat as active
  const d = new Date(exp);
  return !isNaN(d) && d > new Date();
}

// Helper function to check if expired for display purposes, called from: getExpiryStatus
function isExpired(exp) {
  return !isActive(exp);
}

// Helper function to get proper status text and class
function getExpiryStatus(expiresAt) {
  if (!expiresAt) {
    return { status: "Active", class: "ok", expired: false };
  }

  const d = new Date(expiresAt);
  if (isNaN(d)) {
    return { status: "Active", class: "ok", expired: false };
  }

  const expired = isExpired(expiresAt);
  return {
    status: expired ? "Expired" : "Active",
    class: expired ? "exp" : "ok",
    expired: expired,
  };
}

// ---------- Auto-refresh ----------
function toggleAutoRefresh() { // When enabled, the UI calls fetchLinks() every 5 seconds (to refresh click counts and status)
  auto = !auto; // Flip the boolean. If auto was false -> true; if true -> false.
  const btn = document.getElementById("autoBtn"); // btn (local): the DOM button element with id "autoBtn". The function adds/removes classes to change visual state.
  btn.classList.toggle("on", auto);
  btn.classList.toggle("off", !auto);
  if (auto) {
    fetchLinks();
    iv = setInterval(fetchLinks, 5000);
    showToast("Auto-refresh ON");
  } else {
    clearInterval(iv);
    showToast("Auto-refresh OFF");
  }
} // onnected to the Auto-refresh button in the template via onclick="toggleAutoRefresh()". So it's triggered by user click.

// ---------- Editing UX ----------
function enterEditing(code) {
  editingCode = code; // set to the provided code so saveLink() knows which resource to update.
  document.getElementById("formWrap").classList.add("editing");
  document.getElementById("editingBanner").style.display = "block";
  document.getElementById("editingCodeLabel").textContent = code;
  document.getElementById("createBtn").style.display = "none"; // hide
  document.getElementById("saveBtn").style.display = "inline-block"; // show
  document.getElementById("cancelBtn").style.display = "inline-block"; // show
}
function exitEditing() {
  editingCode = null;
  document.getElementById("formWrap").classList.remove("editing");
  document.getElementById("editingBanner").style.display = "none";
  document.getElementById("editingCodeLabel").textContent = "";
  document.getElementById("createBtn").style.display = "inline-block";
  document.getElementById("saveBtn").style.display = "none";
  document.getElementById("cancelBtn").style.display = "none";
  setStatus("");
}
function cancelEdit() {
  document.querySelector("#url").value = "";
  document.querySelector("#exp").value = "";
  exitEditing(); // clears inputs and calls exitEditing() to remove the editing class and restore buttons.
}

// ---------- Fetch & Render ----------
async function fetchLinks() {
    /*
    loads the list of links from your API (GET /api/links), clears the table body (#tbl tbody), 
    builds a row for each link returned, inserts those rows into the DOM, and updates the UI status.
    */
  showError(null);
  setStatus("Loading..."); // Writes "Loading..." to the #status element.
  const res = await fetch(`${BASE}/api/links`); // Network call to the backend.
  if (!res.ok) {
    showError(await readError(res));
    setStatus("");
    return;
  }
  const data = await res.json(); // Parse JSON payload. 
  const tbody = document.querySelector("#tbl tbody"); // Selects the table body where rows will be rendered. 
  tbody.innerHTML = ""; // Clears previous rows by replacing the innerHTML of tbody with an empty string.
  for (const r of data) { // Iterates over each link object r from the server.
    const active = isActive(r.expires_at);
    const statusInfo = getExpiryStatus(r.expires_at);
    
    // Builds a small HTML snippet showing a badge and a small expiry string using fmtExpiryShort.
    const statusHtml = `
    <div class="status">
      <span class="badge ${statusInfo.class}">
        ${statusInfo.status}
      </span>
      <div class="small">${r.expires_at ? fmtExpiryShort(r.expires_at) : ""}</div>
    </div>`;

    // Create a new table row element.
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>
        <a href="${r.short_url}?t=${Date.now()}" target="_blank">${r.short_url}</a>
        <button class="iconbtn" title="Copy" onclick="copyText('${r.short_url}')" aria-label="Copy">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M16 1H4a2 2 0 0 0-2 2v12h2V3h12V1Zm3 4H8a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2Zm0 16H8V7h11v14Z"/></svg>
        </button>
      </td>

      <td class="cell-target" title="${r.target_url}">${escapeHtml(r.target_url)}</td>
      <td>${fmtNullable(r.created_at)}</td>
      <td>${r.click_count ?? 0}</td>
      <td>${statusHtml}</td>
      <td><img class="qr" src="${BASE}/api/links/${r.short_code}/qr" alt="QR" onclick="openQR('${r.short_code}')"/></td>
      <td class="actions">
        <!-- view -->
        <button class="iconbtn view" title="View details" onclick="viewLink('${r.short_code}')" aria-label="View">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 5C7 5 2.73 8.11 1 12c1.73 3.89 6 7 11 7s9.27-3.11 11-7c-1.73-3.89-6-7-11-7Zm0 12a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-2.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z"/></svg>
        </button>
        <!-- edit -->
        <button class="iconbtn edit" title="Edit" onclick="editLink('${r.short_code}','${escapeAttr(r.target_url)}','${r.expires_at ?? ""}')" aria-label="Edit">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25Zm2.92 2.83H5v-.92l8.06-8.06.92.92-8.06 8.06ZM20.71 7.04a1 1 0 0 0 0-1.41l-2.34-2.34a1 1 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83Z"/></svg>
        </button>
        <!-- delete -->
        <button class="iconbtn del" title="Delete" onclick="delLink('${r.short_code}')" aria-label="Delete">
          <svg viewBox="0 0 24 24" fill="currentColor"><path d="M9 3h6a1 1 0 0 1 1 1v1h4v2H4V5h4V4a1 1 0 0 1 1-1Zm-2 6h10l-1 11a2 2 0 0 1-2 2H10a2 2 0 0 1-2-2L7 9Z"/></svg>
        </button>
      </td>
    `;
    tbody.appendChild(tr); // Adds the row to the table. 
  }
  setStatus(`Loaded ${data.length} link(s).`); // Updates the #status element with number of loaded links.
}

// ---------- Create ----------
async function createLink() {
  showError(null);
  const url = document.querySelector("#url").value.trim(); // Reads the current value from the input element with id url (the target URL the user entered), trims whitespace, and stores it in the url variable.
  const raw = document.querySelector("#exp").value.trim();

  // Validate required fields
  if (!url) {
    showError("Please enter a URL");
    return;
  }

  if (!raw) {
    showError("Please select both date and time");
    return;
  }

  const body = { target_url: url };

  // Parse and validate datetime
  const d = parseDateTimeLocal(raw);
  if (!d) {
    showError("Please select a valid date and time");
    return;
  }
  body.expires_at = d.toISOString(); // Now body has { target_url, expires_at }.

  const res = await fetch(`${BASE}/api/links`, { // Performs a POST request to the backend POST ${BASE}/api/links
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    showError(await readError(res));
    return;
  }

  document.querySelector("#url").value = ""; //Clears the #url input field (resetting it to empty).
  document.querySelector("#exp").value = "";
  fetchLinks(); // reload the list of links from the server and update the table UI to include the newly created link.
  showToast("Link created!");
}

// ---------- Edit / Save (UPDATE) ----------
function editLink(code, url, exp) {
  document.querySelector("#url").value = url;
  document.querySelector("#exp").value = isoToLocalInput(exp); // converts an ISO timestamp (UTC) to a string formatted in local time
  enterEditing(code); // sets a module-level editingCode = code, toggles UI state into “editing” mode
  setStatus(`Editing ${code}...`);
}
async function saveLink() {
  if (!editingCode) return;
  showError(null); // Clear any existing error UI.

  const url = document.querySelector("#url").value.trim();
  const raw = document.querySelector("#exp").value.trim();

  const body = {};
  if (url) body.target_url = url;

  // Require both fields during edit
  if (!url || !raw) {
    showError("Both URL and expiration date/time are required");
    return;
  }

  const d = parseDateTimeLocal(raw);
  if (!d) {
    showError("Please select a valid date and time");
    return;
  }
  body.expires_at = d.toISOString();

  const res = await fetch(`${BASE}/api/links/${editingCode}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }); // Send a PUT request to the backend endpoint for the specific link (/api/links/{editingCode}).
  if (!res.ok) {
    showError(await readError(res));
    return;
  }

  cancelEdit();
  showToast("Saved");
  fetchLinks();
}

// Parse a datetime-local value (YYYY-MM-DDTHH:MM) -> Date (local) or null
function parseDateTimeLocal(s) {
  if (!s) return null;
  // Must have both date and time in the correct format
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(s)) return null; // Tests the string against a regular expression
  const d = new Date(s); // Construct a JavaScript Date object from the string s
  return isNaN(d) ? null : d;
}

// ---------- Delete ----------
async function delLink(code) {
  if (!confirm(`Delete ${code}?`)) return; // Uses the browser's confirm dialog to ask the user to confirm deletion
  const res = await fetch(`${BASE}/api/links/${code}`, { method: "DELETE" }); // Calls the backend DELETE endpoint for the link.
  if (!res.ok) {
    showError(await readError(res));
    return;
  }
  showToast("Deleted");
  fetchLinks();
}

// ---------- View detail (modal) ----------
async function viewLink(code) {
  const res = await fetch(`${BASE}/api/links/${code}`);
  const data = await res.json(); // Parse the response body as JSON and store it in data.
  document.getElementById("detailPre").textContent = JSON.stringify(data, null, 2); // Serialize data to a pretty-printed JSON string and set it as the textContent of the preformatted element #detailPre (so the raw JSON displays safely).
  document.getElementById("detailDlg").showModal(); // Open the dialog element #detailDlg (assumes it's a <dialog> element) by calling showModal() which displays the modal dialog.
}
function closeDetail() {
  document.getElementById("detailDlg").close(); // Close dialog element
}

// ---------- QR large modal ----------
function openQR(code) {
  const img = document.getElementById("qrImgLarge"); // inds the <img> element with id qrImgLarge
  img.src = `${BASE}/api/links/${code}/qr`; // Sets the image src attribute to the QR endpoint for that link
  document.getElementById("qrDlg").showModal(); // Opens the dialog element #qrDlg (assumed to be a <dialog>) in modal mode to show the large QR image.
}
function closeQR() {
  document.getElementById("qrDlg").close();
}

// Convert ISO (UTC) -> value for <input type="datetime-local"> (local time)
function isoToLocalInput(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return "";
  const pad = (n) => String(n).padStart(2, "0");
  const yyyy = d.getFullYear();
  const mm = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const hh = pad(d.getHours());
  const ii = pad(d.getMinutes());
  return `${yyyy}-${mm}-${dd}T${hh}:${ii}`;
} // Compose and return a datetime-local-formatted string

// Convert datetime-local (interpreted as local) back to ISO UTC
function localInputToIso(s) {
  if (!s) return null;
  const d = new Date(s); // parsed as local
  return d.toISOString(); // convert to UTC ISO
}

function fmtExpiryShort(iso) { // Return a compact human-friendly expiration string
  if (!iso) return "";
  const d = new Date(iso);
  if (isNaN(d)) return String(iso);
  // dd/mm/yyyy, hh:mm (24h)
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  const hh = String(d.getHours()).padStart(2, "0");
  const ii = String(d.getMinutes()).padStart(2, "0");
  return `${dd}/${mm}/${yyyy}, ${hh}:${ii}`;
}

// Listen for date input changes and set default time if needed
document.getElementById("exp").addEventListener("change", function (e) {
  const value = e.target.value;
  // If only date is selected (no time), default to end of day
  if (value && !value.includes("T")) {
    e.target.value = value + "T23:59";
  }
});

// Auto-load on page open
fetchLinks();
