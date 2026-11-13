async function loadStats() {
  const status = document.getElementById("status");
  try {
    const response = await fetch(chrome.runtime.getURL("data/ocr-index.json"));
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const index = await response.json();
    const stats = index.stats || {};
    status.textContent = "Bundled OCR index is available.";
    document.getElementById("pages").textContent = String(stats.source_files || "-");
    document.getElementById("submissions").textContent = String(stats.entries || "-");
    document.getElementById("generated").textContent = index.generated_at || "-";
  } catch (error) {
    status.textContent = `Could not read OCR index: ${error.message || error}`;
  }
}

loadStats();
